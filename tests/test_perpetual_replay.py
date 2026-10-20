import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniquant.backtest.perpetual import replay_perpetual
from miniquant.backtest.replay import HOUR,DAY


class PerpetualReplayTests(unittest.TestCase):
    def data(self):
        bars=[dict(ts=t,o=100,h=101,l=99,c=100) for t in range(0,20*DAY,4*HOUR)]
        funding=[dict(event_time_ms=t,realized_rate='0.0001') for t in range(0,20*DAY+1,8*HOUR)]
        return bars,funding

    def test_flat_market_does_not_create_breakout_income(self):
        bars,funding=self.data()
        r=replay_perpetual(bars,bars,funding,20,10*DAY,20*DAY)
        self.assertEqual(r['daily'][-1]['nav'],10000)
        self.assertEqual(r['fills'],[])
        self.assertFalse(r['demo_ready'])

    def test_missing_mark_or_funding_is_not_zero_filled(self):
        bars,funding=self.data()
        with self.assertRaises(ValueError):replay_perpetual(bars,bars[:-1],funding,20,10*DAY,20*DAY)
        with self.assertRaises(ValueError):replay_perpetual(bars,bars,funding[:-2],20,10*DAY,20*DAY)
