"""Unauthenticated, bounded USD-M observations. No historical archive certification."""
import hashlib
import json
import time
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from miniquant.data.okx_public import DataError, NoRedirect, integer, number, utc

HOST = 'https://fapi.binance.com'
JOBS = {
    'time': ('/fapi/v1/time', {}),
    'open_interest_current': ('/fapi/v1/openInterest', {'symbol': 'BTCUSDT'}),
    'open_interest_history': ('/futures/data/openInterestHist', {'symbol': 'BTCUSDT', 'period': '5m', 'limit': '2'}),
    'global_ratio': ('/futures/data/globalLongShortAccountRatio', {'symbol': 'BTCUSDT', 'period': '5m', 'limit': '2'}),
    'taker_ratio': ('/futures/data/takerlongshortRatio', {'symbol': 'BTCUSDT', 'period': '5m', 'limit': '2'}),
}


def url_for(kind):
    if kind not in JOBS:
        raise DataError('Endpoint outside public whitelist')
    path, params = JOBS[kind]
    return HOST + path + ('?' + urlencode(params) if params else '')


class PublicClient:
    def __init__(self):
        self.attempts = 0
        self.opener = build_opener(NoRedirect())

    def get(self, kind):
        url = url_for(kind)
        if self.attempts >= 5:
            raise DataError('Invocation request budget exhausted')
        self.attempts += 1
        started = time.time_ns() // 1_000_000
        with self.opener.open(Request(url, method='GET'), timeout=10) as response:
            body = response.read(1_048_577)
        received = time.time_ns() // 1_000_000
        if len(body) > 1_048_576:
            raise DataError('Response too large')
        return dict(kind=kind, url=url, requested_symbol='BTCUSDT',
                    request_started_at_ms=started, ingested_at_ms=received,
                    body_text=body.decode('utf-8'), body_sha256=hashlib.sha256(body).hexdigest())


def timestamp(value):
    result = integer(value)
    if result < 1_000_000_000_000:
        raise DataError('Timestamp is not plausible milliseconds')
    return result


def payload(kind, envelope):
    if envelope['kind'] != kind or envelope['url'] != url_for(kind) or envelope['requested_symbol'] != 'BTCUSDT':
        raise DataError('Request identity mismatch')
    if hashlib.sha256(envelope['body_text'].encode()).hexdigest() != envelope['body_sha256']:
        raise DataError('Body hash mismatch')
    received = timestamp(envelope['ingested_at_ms'])
    if timestamp(envelope['request_started_at_ms']) > received:
        raise DataError('Reception precedes request')
    return json.loads(envelope['body_text']), received


def normalize(kind, envelope):
    body, received = payload(kind, envelope)
    if kind == 'time':
        server = timestamp(body['serverTime'])
        if abs(server - received) > 60_000:
            raise DataError('Clock disagreement')
        return dict(server_time_ms=server, received_at_ms=received)
    fields = {
        'open_interest_current': ('openInterest',),
        'open_interest_history': ('sumOpenInterest', 'sumOpenInterestValue'),
        'global_ratio': ('longShortRatio', 'longAccount', 'shortAccount'),
        'taker_ratio': ('buySellRatio', 'buyVol', 'sellVol'),
    }[kind]
    rows = [body] if kind == 'open_interest_current' else body
    if not isinstance(rows, list) or not rows:
        raise DataError('Expected nonempty observations')
    seen, closed = set(), []
    for row in rows:
        if row.get('symbol', 'BTCUSDT' if kind == 'taker_ratio' else None) != 'BTCUSDT':
            raise DataError('Payload instrument mismatch')
        label = timestamp(row['time'] if kind == 'open_interest_current' else row['timestamp'])
        if label in seen:
            raise DataError('Duplicate timestamp')
        seen.add(label)
        for field in fields:
            value = number(row[field])
            if value < 0 or (field in ('longAccount', 'shortAccount') and value > 1):
                raise DataError('Invalid public metric')
        end = label + (300_000 if kind == 'taker_ratio' else 0)
        if end <= received:
            closed.append((end, label, row))
    if not closed:
        raise DataError('No closed observation available at reception')
    end, label, row = max(closed, key=lambda item: item[0])
    return dict(kind=kind, symbol='BTCUSDT', label_time_ms=label, event_time=utc(end),
                available_at=utc(received), ingested_at=utc(received),
                timestamp_role='period_start' if kind == 'taker_ratio' else
                ('snapshot' if kind == 'open_interest_current' else 'period_end'),
                values={field: str(row[field]) for field in fields},
                archive_mapping_certified=False, quantity_unit_certified=False,
                body_sha256=envelope['body_sha256'], age_at_reception_ms=received-end)
