import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniquant.accounting.spot import SpotAccount
from miniquant.backtest.replay import aggregate,replay,HOUR,DAY


def hourly(days,price=100):
    return [dict(ts=j*HOUR,o=float(price),h=float(price),l=float(price),c=float(price)) for j in range(days*24)]


class SpotAccountingTests(unittest.TestCase):
    def test_buy_received_currency_fee_and_cash_conservation(self):
        a=SpotAccount(1000,fee_rate=0.01,slippage=0)
        qty=a.buy(500,100,0)
        self.assertAlmostEqual(qty,4.95)
        self.assertAlmostEqual(a.cash,500)
        self.assertAlmostEqual(a.nav(100),995)
        a.sell(qty,100,1)
        self.assertAlmostEqual(a.cash,990.05)
        self.assertAlmostEqual(a.fees,9.95)
        self.assertAlmostEqual(a.quantity,0)

    def test_no_borrow_or_oversell_and_finite_budget(self):
        a=SpotAccount(100,slippage=0,fee_rate=0)
        a.buy(1000,100,0)
        self.assertAlmostEqual(a.quantity,1)
        with self.assertRaises(ValueError):a.sell(2,100,1)
        with self.assertRaises(ValueError):a.target(1.1,100,1)
        with self.assertRaises(ValueError):a.buy(float('nan'),100,1)
        self.assertGreaterEqual(a.cash,0)

    def test_minimum_order_and_slippage_accounted_once(self):
        a=SpotAccount(1000,fee_rate=0,slippage=0.01)
        self.assertEqual(a.buy(0.000001,100,0),0)
        a.buy(101,100,0)
        self.assertAlmostEqual(a.quantity,1)
        self.assertAlmostEqual(a.nav(100),999)


class CausalReplayTests(unittest.TestCase):
    def test_cash_is_flat_and_hold_roundtrip_cost_is_negative(self):
        rows=hourly(5)
        cash=replay(rows,'cash',0,0,5*DAY)
        held=replay(rows,'hold',0,0,5*DAY)
        self.assertEqual(cash.final_nav,10000)
        self.assertLess(held.final_nav,10000)
        self.assertEqual(len(held.fills),2)
        self.assertEqual(held.fills[0]['ts'],2*HOUR)

    def test_signal_uses_closed_day_and_execution_lags(self):
        rows=hourly(6)
        for b in rows:
            p=100+b['ts']//DAY*10
            b.update(o=p,h=p,l=p,c=p)
        r=replay(rows,'trend',1,2*DAY,6*DAY,fee_bps=0,slip_bps=0)
        entry=r.fills[0]
        self.assertEqual(entry['ts'],3*DAY+HOUR)
        self.assertEqual(entry['price'],130)

    def test_future_prices_cannot_change_earlier_fills(self):
        rows=hourly(10)
        for b in rows:
            p=100+10*math.sin(b['ts']/DAY)
            b.update(o=p,h=p+1,l=p-1,c=p)
        base=replay(rows,'constant_mix',0.5,0,10*DAY,liquidate=False)
        changed=[dict(x) for x in rows]
        for b in changed:
            if b['ts']>=7*DAY:
                for k in ('o','h','l','c'):b[k]*=10
        altered=replay(changed,'constant_mix',0.5,0,10*DAY,liquidate=False)
        a=[f for f in base.fills if f['ts']<7*DAY]
        b=[f for f in altered.fills if f['ts']<7*DAY]
        self.assertEqual(a,b)

    def test_gaps_fail_closed_and_partial_aggregate_not_used(self):
        rows=hourly(3)
        self.assertEqual(len(aggregate(rows[:-1],DAY)),2)
        with self.assertRaises(ValueError):replay(rows[:10]+rows[11:],'hold',0,0,3*DAY)

    def test_grid_cannot_sell_preexisting_or_create_free_roundtrips(self):
        rows=hourly(30)
        for b in rows:b.update(h=150,l=50)
        r=replay(rows,'grid',6,20*DAY,30*DAY)
        self.assertGreaterEqual(r.final_nav,0)
        self.assertTrue(all(f['notional']>=0 for f in r.fills))
        self.assertLessEqual(len(r.fills),r.total_hours*6+20)


if __name__=='__main__':unittest.main()
