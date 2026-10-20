import unittest
from tools.collect_okx_funding_archive import parse_funding_csv


class FundingArchiveTests(unittest.TestCase):
    def test_exact_retrospective_rate_and_instrument(self):
        rows=parse_funding_csv('instrument_name,funding_rate,funding_time\r\nBTC-USDT-SWAP,-0.0001,1700000000000\r\n')
        self.assertEqual(rows[0]['realized_rate'],'-0.0001')
        self.assertEqual(rows[0]['event_time_ms'],1700000000000)
        with self.assertRaises(ValueError):parse_funding_csv('instrument_name,funding_rate,funding_time\nETH-USDT-SWAP,0.1,1700000000000\n')

    def test_schema_or_missing_rate_cannot_be_filled_zero(self):
        with self.assertRaises(ValueError):parse_funding_csv('wrong,rate,time\nBTC,0.1,123\n')
        with self.assertRaises(ValueError):parse_funding_csv('instrument_name,funding_rate,funding_time\nBTC-USDT-SWAP,,1700000000000\n')
