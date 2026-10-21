import hashlib
import json
import unittest
from unittest.mock import Mock, patch
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError

from miniquant.data.binance_observation import DataError, PublicClient, normalize, url_for

NOW = 1_790_000_600_000


def envelope(kind, body):
    text = json.dumps(body)
    return dict(kind=kind, url=url_for(kind), requested_symbol='BTCUSDT',
                request_started_at_ms=NOW-100, ingested_at_ms=NOW,
                body_text=text, body_sha256=hashlib.sha256(text.encode()).hexdigest())


class BinanceObservationTests(unittest.TestCase):
    def test_taker_start_label_requires_period_to_close(self):
        rows = [dict(timestamp=NOW-400_000, buySellRatio='1', buyVol='2', sellVol='2'),
                dict(timestamp=NOW-100_000, buySellRatio='9', buyVol='9', sellVol='1')]
        result = normalize('taker_ratio', envelope('taker_ratio', rows))
        self.assertEqual(result['values']['buySellRatio'], '1')
        self.assertEqual(result['age_at_reception_ms'], 100_000)
        self.assertEqual(result['timestamp_role'], 'period_start')

    def test_oi_end_label_not_delayed_an_extra_period(self):
        raw = envelope('open_interest_history', [dict(symbol='BTCUSDT', timestamp=NOW-100,
                       sumOpenInterest='0', sumOpenInterestValue='0')])
        self.assertEqual(normalize('open_interest_history', raw)['age_at_reception_ms'], 100)
        self.assertFalse(normalize('open_interest_history', raw)['quantity_unit_certified'])

    def test_identity_and_hash_fail_closed(self):
        raw = envelope('open_interest_current', dict(symbol='BTCUSDT', time=NOW, openInterest='1'))
        for field, value in [('url', 'https://other.test'), ('requested_symbol', 'ETHUSDT'),
                             ('body_text', '{}'), ('kind', 'global_ratio')]:
            with self.subTest(field=field), self.assertRaises(DataError):
                normalize('open_interest_current', {**raw, field: value})

    def test_wrong_symbol_unit_future_nonfinite_rejected(self):
        row = dict(symbol='BTCUSDT', time=NOW, openInterest='1')
        for changes in [dict(symbol='ETHUSDT'), dict(time=NOW//1000), dict(time=NOW+1),
                        dict(openInterest='NaN'), dict(openInterest='-1')]:
            with self.subTest(changes=changes), self.assertRaises(DataError):
                normalize('open_interest_current', envelope('open_interest_current', {**row, **changes}))

    def test_duplicate_history_rejected(self):
        row = dict(symbol='BTCUSDT', timestamp=NOW, longShortRatio='1', longAccount='.5', shortAccount='.5')
        with self.assertRaises(DataError):
            normalize('global_ratio', envelope('global_ratio', [row, row]))

    def test_whitelist_and_attempt_budget_before_http(self):
        client = PublicClient()
        client.opener = Mock()
        for kind in ('order', 'top_position', 'account', 'https://other.test'):
            with self.assertRaises(DataError):
                client.get(kind)
        client.attempts = 5
        with self.assertRaises(DataError):
            client.get('time')
        client.opener.open.assert_not_called()

    def test_http_access_block_persists_and_prevents_next_http(self):
        from tools import observe_btc_binance as tool
        with TemporaryDirectory() as temp:
            root = Path(temp)
            for name in tool.SOURCES + ['research/audits/BTC-BINANCE-FORWARD-016.json']:
                path = root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('test source')
            client = Mock(attempts=1)
            client.get.side_effect = HTTPError(url_for('time'), 451, 'test', {}, None)
            with patch.object(tool, 'ROOT', root), patch.object(tool, 'PublicClient', return_value=client) as factory:
                tool.main()
                self.assertTrue((root/'data/forward-binance/BTC/access_blocked.json').exists())
                tool.main()
                self.assertEqual(factory.call_count, 1)
                self.assertEqual(client.get.call_count, 1)

    def test_clock_disagreement_rejected(self):
        with self.assertRaises(DataError):
            normalize('time', envelope('time', dict(serverTime=NOW+60_001)))


if __name__ == '__main__':
    unittest.main()
