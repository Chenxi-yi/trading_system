"""018 offline, declared snapshots only; no network, no returns."""
from pathlib import Path
import hashlib
import json
import sys
from urllib.parse import urlparse, parse_qs
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from miniquant.data.okx_public import DataError, candle, number, utc
from miniquant.data.okx_units import body, INSTRUMENT, TOLERANCE
from miniquant.data.archive_collection import save_json


def main():
    protocol = ROOT/'research/audits/BTC-OKX-SAVED-UNITS-018.json'
    plan = json.loads(protocol.read_text())
    out = ROOT/'artifacts/BTC-OKX-SAVED-UNITS-018'
    out.mkdir(parents=True, exist_ok=False)
    names = ['tools/audit_okx_saved_units.py', 'src/miniquant/data/okx_units.py',
             'src/miniquant/data/okx_public.py', 'src/miniquant/data/archive_collection.py',
             'src/miniquant/data/binance_metrics.py']
    code = {n: hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
    save_json(out/'manifest.json', dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(), code=code, inputs=plan['inputs']))
    for n in names:
        target = out/'source_snapshot'/n;target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/n).read_bytes())
    summary = dict(complete=False, new_HTTP_attempts=0, pnl_tests=0, historical_units_certified=False,
                   sided_counting_certified=False, oi_change_vs_volume_test_performed=False)
    try:
        envelopes = []
        for name, expected in plan['inputs'].items():
            raw = (ROOT/name).read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected:
                raise DataError('Frozen offline input changed')
            envelopes.append(json.loads(raw))
        meta, oi, trades = envelopes
        specs, meta_received = body(meta, 'instruments')
        interest, oi_received = body(oi, 'open_interest')
        spec = [r for r in specs if r.get('instId') == INSTRUMENT]
        if len(spec) != 1 or any(spec[0].get(k) != v for k,v in dict(instType='SWAP',ctType='linear',ctValCcy='BTC',settleCcy='USDT').items()):
            raise DataError('Unsupported saved specification')
        spec = spec[0]
        factor = number(spec['ctVal'])
        if factor <= 0 or number(spec['ctMult']) != 1:
            raise DataError('Unsupported saved multiplier')
        if len(interest) != 1 or interest[0].get('instId') != INSTRUMENT:
            raise DataError('Saved OI identity mismatch')
        query = parse_qs(urlparse(trades['url']).query)
        if urlparse(trades['url']).scheme != 'https' or urlparse(trades['url']).netloc != 'openapi.okx.com' or urlparse(trades['url']).path != '/api/v5/market/history-candles' or query.get('instId') != [INSTRUMENT] or query.get('bar') != ['4H']:
            raise DataError('Saved trade identity mismatch')
        if hashlib.sha256(trades['body_text'].encode()).hexdigest() != trades['body_sha256']:
            raise DataError('Saved trade hash mismatch')
        payload = json.loads(trades['body_text'])
        if payload.get('code') != '0':
            raise DataError('Saved trade API error')
        errors, excluded, seen = [], 0, set()
        for raw in payload['data']:
            bar = candle(raw, 'trade', INSTRUMENT, '4H', trades['ingested_at_ms'], plan['id'])
            if bar['open_time_ms'] in seen:
                raise DataError('Duplicate saved candle')
            seen.add(bar['open_time_ms'])
            if not bar['complete']:
                excluded += 1;continue
            errors.append(abs(number(bar['volume_ccy'])-number(bar['volume'])*factor))
        if not errors:
            raise DataError('No completed saved candles')
        error = abs(number(interest[0]['oiCcy'])-number(interest[0]['oi'])*factor)
        summary.update(complete=True, ctVal=str(factor), oi_conversion_error_btc=str(error),
                       oi_within_tolerance=error <= TOLERANCE, candles_checked=len(errors), incomplete_excluded=excluded,
                       candle_violations=sum(e > TOLERANCE for e in errors), max_candle_error_btc=str(max(errors)),
                       tolerance_btc=str(TOLERANCE), metadata_received_at=utc(meta_received), oi_received_at=utc(oi_received),
                       candles_received_at=utc(trades['ingested_at_ms']), assumption='Saved specification, not historical point-in-time certification')
    except Exception as exc:
        summary['error_type'] = type(exc).__name__
    save_json(out/'summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
