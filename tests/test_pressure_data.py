import sys,unittest,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniquant.research.pressure_data import prepare_funding,lagged_funding,synchronized_close_premium
from miniquant.backtest.replay import HOUR

class PressureDataTests(unittest.TestCase):
    def test_realized_rate_only_after_explicit_lag(self):
        rows=prepare_funding([dict(event_time_ms=8*HOUR,realized_rate='.01'),dict(event_time_ms=16*HOUR,realized_rate='-.02')])
        self.assertEqual(lagged_funding(rows,11*HOUR)['status'],'no_mature_settlement')
        record=lagged_funding(rows,12*HOUR)
        self.assertEqual(record['realized_rate'],.01)
        self.assertIsNone(record['available_at'])
        self.assertEqual(record['assumed_available_ms'],12*HOUR)
        self.assertEqual(lagged_funding(rows,19*HOUR)['realized_rate'],.01)
        self.assertEqual(lagged_funding(rows,20*HOUR)['realized_rate'],-.02)
    def test_future_mutation_and_truncation_do_not_change_past(self):
        a=prepare_funding([dict(event_time_ms=8*HOUR,realized_rate='.01')])
        b=prepare_funding([dict(event_time_ms=8*HOUR,realized_rate='.01'),dict(event_time_ms=16*HOUR,realized_rate='99')])
        self.assertEqual(lagged_funding(a,15*HOUR),lagged_funding(b,15*HOUR))
        self.assertEqual(lagged_funding(a,33*HOUR)['status'],'stale_settlement')
    def test_bad_rates_duplicates_and_assumptions_rejected(self):
        for rate in ['nan','inf']:
            with self.assertRaises(ValueError):prepare_funding([dict(event_time_ms=0,realized_rate=rate)])
        with self.assertRaises(ValueError):prepare_funding([dict(event_time_ms=0,realized_rate=0)]*2)
        with self.assertRaises(ValueError):lagged_funding([],0,lag_ms=0)
    def test_premium_proxy_requires_complete_matching_bars(self):
        a=dict(open_time_ms=0,end_time_ms=4*HOUR,complete=True,close='101')
        b=dict(a,close='100')
        self.assertAlmostEqual(synchronized_close_premium(a,b)['value'],.01)
        self.assertIsNone(synchronized_close_premium(a,b)['available_at'])
        for bad in [dict(b,end_time_ms=8*HOUR),dict(b,complete=False),dict(b,close=0)]:
            with self.assertRaises(ValueError):synchronized_close_premium(a,bad)
