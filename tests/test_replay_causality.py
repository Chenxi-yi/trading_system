"""Black-box prefix invariance: unknown prices/funding cannot alter earlier trades."""
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from miniquant.backtest.replay import replay, HOUR, DAY
from miniquant.backtest.perpetual import replay_perpetual


class ReplayCausalityTests(unittest.TestCase):
    def bars(self, step):
        rows = []
        for t in range(0, 200 * DAY, step):
            d = t / DAY
            price = 100 + 3 * math.sin(d / 3) + 0.05 * d
            rows.append(dict(ts=t, o=price, h=price + 0.3, l=price - 0.3, c=price + 0.1))
        return rows

    def test_spot_future_price_changes_leave_all_five_prefixes_unchanged(self):
        bars = self.bars(HOUR)
        cut = 150 * DAY
        changed = [b if b['ts'] < cut else dict(ts=b['ts'], **{k: b[k] * 5 for k in ('o', 'h', 'l', 'c')}) for b in bars]
        for family, param in [('trend', 60), ('reversion', 60), ('grid', 6), ('constant_mix', 0.5), ('hold', 0)]:
            with self.subTest(family=family):
                original = replay(bars, family, param, 90 * DAY, 200 * DAY, liquidate=False)
                altered = replay(changed, family, param, 90 * DAY, 200 * DAY, liquidate=False)
                truncated = replay([b for b in bars if b['ts'] < cut], family, param, 90 * DAY, cut, liquidate=False)
                prefix = [f for f in original.fills if f['ts'] < cut]
                self.assertGreater(len(prefix), 0)
                self.assertEqual(prefix, [f for f in altered.fills if f['ts'] < cut])
                self.assertEqual(prefix, truncated.fills)
                self.assertEqual([d for d in original.daily if d['ts'] <= cut], truncated.daily)
                self.assertEqual(truncated.daily, [d for d in altered.daily if d['ts'] <= cut])

    def test_perpetual_future_price_mark_and_funding_do_not_change_past(self):
        bars = [dict(b, h=b['o'] + 0.12, l=b['o'] - 0.12) for b in self.bars(4 * HOUR)]
        cut = 150 * DAY
        altered = [b if b['ts'] < cut else dict(ts=b['ts'], **{k: b[k] * 2 for k in ('o', 'h', 'l', 'c')}) for b in bars]
        funding = [dict(event_time_ms=t, realized_rate='0.0001') for t in range(0, 200 * DAY + 1, 8 * HOUR)]
        changed_funding = [f if f['event_time_ms'] < cut else dict(event_time_ms=f['event_time_ms'], realized_rate='0.01') for f in funding]
        a = replay_perpetual(bars, bars, funding, 20, 90 * DAY, 200 * DAY)
        b = replay_perpetual(altered, altered, changed_funding, 20, 90 * DAY, 200 * DAY)
        prefix = [f for f in a['fills'] if f['ts'] < cut]
        self.assertGreater(len(prefix), 0)
        self.assertEqual(prefix, [f for f in b['fills'] if f['ts'] < cut])
        self.assertEqual([f for f in a['funding_events'] if f['ts'] < cut], [f for f in b['funding_events'] if f['ts'] < cut])
        self.assertEqual([d for d in a['daily'] if d['ts'] <= cut], [d for d in b['daily'] if d['ts'] <= cut])
