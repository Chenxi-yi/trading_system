import json
import unittest
from unittest.mock import Mock
from miniquant.data.okx_public import digest, DataError
from miniquant.data.okx_units import audit_units, URLS

NOW = 1_790_000_100_000
START = NOW//900_000*900_000-900_000


def envelope(data):
    text = json.dumps(dict(code='0', data=data))
    kind = 'instruments' if isinstance(data[0], dict) and 'ctVal' in data[0] else ('open_interest' if isinstance(data[0], dict) else 'trade')
    return dict(url=URLS[kind], body_text=text, body_sha256=digest(text), ingested_at_ms=NOW)


def inputs():
    spec = dict(instId='BTC-USDT-SWAP', instType='SWAP', ctType='linear',
                settleCcy='USDT', ctValCcy='BTC', ctVal='.01', ctMult='1')
    oi = dict(instId='BTC-USDT-SWAP', instType='SWAP', oi='123.5', oiCcy='1.235', ts=str(NOW))
    bars = [[str(START), '100', '101', '99', '100', '12.5', '.125', '12.5', '1']]
    return spec, oi, bars


class OkxUnitsTests(unittest.TestCase):
    def test_decimal_conversion_and_explicit_limits(self):
        spec, oi, bars = inputs()
        result = audit_units(envelope([spec]), envelope([oi]), envelope(bars))
        self.assertTrue(result['quantity_conversion_consistent'])
        self.assertFalse(result['sided_counting_certified'])
        self.assertFalse(result['historical_publication_certified'])
        self.assertFalse(result['oi_change_vs_volume_test_performed'])

    def test_conversion_failure_is_reported_not_corrected(self):
        spec, oi, bars = inputs()
        oi['oiCcy'] = '2'
        self.assertFalse(audit_units(envelope([spec]), envelope([oi]), envelope(bars))['quantity_conversion_consistent'])

    def test_inverse_wrong_currency_multiplier_rejected(self):
        spec, oi, bars = inputs()
        for change in [dict(ctType='inverse'), dict(ctValCcy='USD'), dict(ctMult='2'), dict(settleCcy='BTC')]:
            with self.subTest(change=change), self.assertRaises(DataError):
                audit_units(envelope([{**spec, **change}]), envelope([oi]), envelope(bars))

    def test_tampered_payload_and_wrong_oi_identity_rejected(self):
        spec, oi, bars = inputs()
        raw = envelope(bars);raw['body_text'] = '{}'
        with self.assertRaises(DataError):
            audit_units(envelope([spec]), envelope([oi]), raw)
        with self.assertRaises(DataError):
            audit_units(envelope([spec]), envelope([{**oi, 'instId':'ETH-USDT-SWAP'}]), envelope(bars))

    def test_incomplete_bar_excluded_and_duplicate_rejected(self):
        spec, oi, bars = inputs()
        partial = [str(START+900_000), '100', '101', '99', '100', '1', '999', '100', '0']
        result = audit_units(envelope([spec]), envelope([oi]), envelope(bars+[partial]))
        self.assertEqual(result['incomplete_excluded'], 1)
        self.assertTrue(result['quantity_conversion_consistent'])
        with self.assertRaises(DataError):
            audit_units(envelope([spec]), envelope([oi]), envelope(bars+bars))

    def test_future_oi_and_future_confirmed_bar_rejected(self):
        spec, oi, bars = inputs()
        with self.assertRaises(DataError):
            audit_units(envelope([spec]), envelope([{**oi, 'ts':str(NOW+1)}]), envelope(bars))
        bars[0][0] = str(START+900_000)
        with self.assertRaises(DataError):
            audit_units(envelope([spec]), envelope([oi]), envelope(bars))

    def test_volume_request_cannot_be_from_other_market(self):
        spec, oi, bars = inputs()
        raw = envelope(bars)
        raw['url'] = raw['url'].replace('BTC-USDT-SWAP', 'BTC-USDT')
        with self.assertRaises(DataError):
            audit_units(envelope([spec]), envelope([oi]), raw)

    def test_transport_counts_failure_without_hidden_retries(self):
        from tools.audit_okx_units import BoundedClient
        client = BoundedClient()
        client.opener = Mock()
        client.opener.open.side_effect = TimeoutError()
        with self.assertRaises(TimeoutError):
            client.get('time')
        self.assertEqual(client.attempts, 1)
        self.assertEqual(client.opener.open.call_count, 1)
        client.attempts = 4
        for kind in ('time', 'order', 'account'):
            with self.assertRaises(DataError):
                client.get(kind)
        self.assertEqual(client.opener.open.call_count, 1)


if __name__ == '__main__':
    unittest.main()
