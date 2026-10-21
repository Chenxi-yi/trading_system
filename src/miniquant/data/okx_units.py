"""017 current linear BTC unit checks, not OI-flow or vintage certification."""
import json
from decimal import Decimal
from miniquant.data.okx_public import DataError, digest, number, integer, candle, utc

INSTRUMENT = 'BTC-USDT-SWAP'
TOLERANCE = Decimal('0.00000001')
URLS = {
    'time': 'https://openapi.okx.com/api/v5/public/time',
    'instruments': 'https://openapi.okx.com/api/v5/public/instruments?instType=SWAP',
    'open_interest': 'https://openapi.okx.com/api/v5/public/open-interest?instType=SWAP&instId=BTC-USDT-SWAP',
    'trade': 'https://openapi.okx.com/api/v5/market/history-candles?instId=BTC-USDT-SWAP&bar=15m&limit=4',
}


def body(envelope, kind):
    if envelope.get('url') != URLS[kind]:
        raise DataError('Unit audit request identity mismatch')
    if digest(envelope['body_text']) != envelope['body_sha256']:
        raise DataError('Unit audit raw hash mismatch')
    received = integer(envelope['ingested_at_ms'])
    if received < 1_000_000_000_000:
        raise DataError('Invalid reception time unit')
    value = json.loads(envelope['body_text'])
    if value.get('code') != '0' or not isinstance(value.get('data'), list):
        raise DataError('Invalid unit audit response')
    return value['data'], received


def audit_units(metadata, interest, trades):
    instruments, meta_received = body(metadata, 'instruments')
    found = [row for row in instruments if row.get('instId') == INSTRUMENT]
    if len(found) != 1:
        raise DataError('Instrument not unique')
    spec = found[0]
    expected = dict(instType='SWAP', ctType='linear', settleCcy='USDT', ctValCcy='BTC')
    if any(spec.get(key) != value for key, value in expected.items()):
        raise DataError('Unsupported contract identity or currency')
    value = number(spec['ctVal'])
    if value <= 0 or number(spec['ctMult']) != 1:
        raise DataError('Contract multiplier interpretation not admitted')
    oi, oi_received = body(interest, 'open_interest')
    if len(oi) != 1 or oi[0].get('instId') != INSTRUMENT or oi[0].get('instType') != 'SWAP':
        raise DataError('OI instrument mismatch')
    row = oi[0]
    oi_time = integer(row['ts'])
    if not 1_000_000_000_000 <= oi_time <= oi_received:
        raise DataError('Invalid OI data-return timestamp')
    contracts, coins = number(row['oi']), number(row['oiCcy'])
    if min(contracts, coins) < 0:
        raise DataError('Negative OI')
    oi_error = abs(coins-contracts*value)
    raw_candles, trade_received = body(trades, 'trade')
    checks, seen, incomplete = [], set(), 0
    for raw in raw_candles:
        bar = candle(raw, 'trade', INSTRUMENT, '15m', trade_received, 'BTC-OKX-UNITS-017')
        if bar['open_time_ms'] in seen:
            raise DataError('Duplicate candle')
        seen.add(bar['open_time_ms'])
        if not bar['complete']:
            incomplete += 1
            continue
        error = abs(number(bar['volume_ccy'])-number(bar['volume'])*value)
        checks.append(dict(open_time_ms=bar['open_time_ms'], end_time_ms=bar['end_time_ms'],
                           absolute_btc_conversion_error=str(error), within_tolerance=error <= TOLERANCE))
    if not checks:
        raise DataError('No completed candles for unit check')
    return dict(instrument=INSTRUMENT, ctVal=str(value), ctValCcy='BTC', ctMult=spec['ctMult'],
                oi_absolute_btc_conversion_error=str(oi_error), oi_within_tolerance=oi_error <= TOLERANCE,
                completed_candle_checks=checks, incomplete_excluded=incomplete,
                quantity_conversion_consistent=oi_error <= TOLERANCE and all(x['within_tolerance'] for x in checks),
                tolerance_btc=str(TOLERANCE), oi_ts_role='REST_data_return_time_not_certified_trade_event',
                first_observed_at=dict(metadata=utc(meta_received), oi=utc(oi_received), candles=utc(trade_received)),
                historical_publication_certified=False, sided_counting_certified=False,
                oi_change_vs_volume_test_performed=False, pnl_tests=0)
