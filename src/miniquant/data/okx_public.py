"""Unsigned, GET-only OKX public market adapter and strict candle contract."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import time
from urllib import request, error, parse

INTERVALS = {"1Dutc": 86_400_000, "4H": 14_400_000, "1H": 3_600_000, "15m": 900_000}
PATHS = {
    "trade": "/api/v5/market/history-candles",
    "mark": "/api/v5/market/history-mark-price-candles",
    "index": "/api/v5/market/history-index-candles",
    "funding": "/api/v5/public/funding-rate-history",
    "instruments": "/api/v5/public/instruments",
    "time": "/api/v5/public/time",
    "ticker": "/api/v5/market/ticker",
    "archive": "/api/v5/public/market-data-history",
    "open_interest": "/api/v5/public/open-interest",
    "books": "/api/v5/market/books",
}
PARAMS = {
    "trade": {"instId", "bar", "after", "limit"},
    "mark": {"instId", "bar", "after", "limit"},
    "index": {"instId", "bar", "after", "limit"},
    "funding": {"instId", "after", "limit"},
    "instruments": {"instType"}, "time": set(), "ticker": {"instId"},
    "open_interest": {"instType", "instId"}, "books": {"instId", "sz"},
    "archive": {"module", "instType", "instIdList", "instFamilyList", "dateAggrType", "begin", "end"},
}


class DataError(ValueError):
    pass


def number(value):
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise DataError("invalid_decimal") from None
    if not n.is_finite():
        raise DataError("nonfinite_decimal")
    return n


def integer(value):
    n = number(value)
    if n != n.to_integral_value() or n < 0:
        raise DataError("invalid_nonnegative_integer")
    return int(n)


def utc(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def candle(row, kind, inst_id, bar, ingested_ms, lineage_id):
    """available_at unknown for historical data: never synthesize a publication time."""
    if kind not in ("trade", "mark", "index") or bar not in INTERVALS:
        raise DataError("unsupported_candle_contract")
    if not isinstance(row, list) or len(row) != (9 if kind == "trade" else 6):
        raise DataError("candle_schema_changed")
    ts = integer(row[0])
    interval = INTERVALS[bar]
    if ts % interval or ts > ingested_ms:
        raise DataError("invalid_bar_boundary")
    values = [number(x) for x in row[1:5]]
    o, h, low, c = values
    if min(values) <= 0 or low > min(o, c) or h < max(o, c) or low > h:
        raise DataError("invalid_ohlc")
    if row[-1] not in ("0", "1"):
        raise DataError("invalid_confirm")
    if row[-1] == "1" and ts + interval > ingested_ms:
        raise DataError("completed_bar_in_future")
    result = {"schema_version": 1, "venue": "OKX", "source_environment": "public_market",
              "kind": kind, "inst_id": inst_id, "bar": bar,
              "open_time_ms": ts, "end_time_ms": ts + interval,
              "event_time": utc(ts + interval), "available_at": None,
              "availability_basis": "historical_publication_time_unknown",
              "ingested_at": utc(ingested_ms), "lineage_id": lineage_id,
              "open": str(o), "high": str(h), "low": str(low), "close": str(c),
              "complete": row[-1] == "1"}
    if kind == "trade":
        volumes = [number(x) for x in row[5:8]]
        if min(volumes) < 0:
            raise DataError("negative_volume")
        result.update(volume=str(volumes[0]), volume_ccy=str(volumes[1]),
                      volume_quote=str(volumes[2]),
                      volume_unit="contracts" if inst_id.endswith("-SWAP") else "base_currency")
    return result


def funding(row, inst_id, ingested_ms, lineage_id):
    if not isinstance(row, dict) or row.get("instId") != inst_id:
        raise DataError("funding_instrument_mismatch")
    ts = integer(row.get("fundingTime"))
    if ts > ingested_ms:
        raise DataError("future_funding_settlement")
    # fundingRate is not substituted for an unknown realizedRate.
    rate = row.get("realizedRate")
    return {"schema_version": 1, "venue": "OKX", "source_environment": "public_market",
            "kind": "funding", "inst_id": inst_id, "event_time_ms": ts,
            "event_time": utc(ts), "available_at": None,
            "availability_basis": "historical_publication_time_unknown",
            "ingested_at": utc(ingested_ms), "lineage_id": lineage_id,
            "realized_rate": str(number(rate)) if rate not in (None, "") else None,
            "predicted_rate": str(number(row["fundingRate"])) if row.get("fundingRate") not in (None, "") else None,
            "method": row.get("method"), "formula_type": row.get("formulaType")}


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PublicClient:
    """Single fixed official host. No auth, config reader, order paths or redirects."""
    def __init__(self):
        self.opener = request.build_opener(NoRedirect())
        self.last_request = 0.0

    def get(self, kind, params=None):
        params = params or {}
        if kind not in PATHS or not set(params) <= PARAMS[kind]:
            raise DataError("public_endpoint_or_parameter_not_allowed")
        url = "https://openapi.okx.com" + PATHS[kind]
        if params:
            url += "?" + parse.urlencode(params)
        for attempt in range(3):
            time.sleep(max(0, 0.3 - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            try:
                req = request.Request(url, headers={"User-Agent": "PersonalMiniQuantResearch/0.2"}, method="GET")
                started = int(time.time() * 1000)
                with self.opener.open(req, timeout=10) as response:
                    raw = response.read(4_000_001)
                if len(raw) > 4_000_000:
                    raise DataError("response_too_large")
                text = raw.decode("utf-8")
                payload = json.loads(text)
                if payload.get("code") != "0" or not isinstance(payload.get("data"), list):
                    if payload.get("code") == "50011" and attempt < 2:
                        time.sleep(0.5 * (2 ** attempt))
                        continue
                    raise DataError("public_api_response_rejected")
                envelope = {"url": url, "request_started_at_ms": started,
                            "ingested_at_ms": int(time.time() * 1000),
                            "body_sha256": hashlib.sha256(raw).hexdigest(), "body_text": text}
                return envelope
            except error.HTTPError as exc:
                if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise DataError("public_http_error_" + str(exc.code)) from None
            except (error.URLError, TimeoutError, OSError):
                if attempt == 2:
                    raise DataError("public_network_error") from None
            time.sleep(0.5 * (2 ** attempt))
        raise DataError("public_request_failed")


def coverage(records, kind, bar, start, end):
    """Measure a declared [start,end) window. No forward fill, no zero funding."""
    by_ts = {}
    duplicates = conflicts = incomplete = outside = 0
    for r in records:
        ts = r["event_time_ms"] if kind == "funding" else r["open_time_ms"]
        if not start <= ts < end:
            outside += 1
            continue
        if kind != "funding" and not r["complete"]:
            incomplete += 1
            continue
        if ts in by_ts:
            duplicates += 1
            fields = ("realized_rate", "predicted_rate", "method", "formula_type") if kind == "funding" else ("open", "high", "low", "close", "volume", "volume_ccy", "volume_quote")
            if any(r.get(k) != by_ts[ts].get(k) for k in fields):
                conflicts += 1
        else:
            by_ts[ts] = r
    times = sorted(by_ts)
    result = {"records": len(times), "duplicates": duplicates, "conflicting_revisions": conflicts,
              "incomplete_excluded": incomplete, "outside_window_excluded": outside,
              "requested_start": utc(start), "requested_end_exclusive": utc(end),
              "first": utc(times[0]) if times else None, "last": utc(times[-1]) if times else None,
              "research_ready": False}
    if kind == "funding":
        intervals = {}
        for a, b in zip(times, times[1:]):
            hours = str(Decimal(b-a) / Decimal(3_600_000))
            intervals[hours] = intervals.get(hours, 0) + 1
        result.update(interval_hours_histogram=intervals,
                      unknown_realized_rates=sum(r["realized_rate"] is None for r in by_ts.values()),
                      missing_event_count=None,
                      note="Funding schedule not assumed constant; intervals need schedule history to certify completeness.")
    else:
        interval = INTERVALS[bar]
        expected = set(range(start, end, interval))
        missing = sorted(expected - by_ts.keys())
        result.update(expected_records=len(expected), missing_records=len(missing),
                      missing_examples=[utc(x) for x in missing[:8]],
                      internal_missing_records=sum((b-a)//interval-1 for a,b in zip(times,times[1:])),
                      window_complete=not missing and not conflicts,
                      note="Window completeness is not point-in-time or strategy readiness.")
    return result, [by_ts[t] for t in times]
