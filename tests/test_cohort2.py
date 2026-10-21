import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniquant.backtest.cohort2 import replay_cohort2,trend_weight,pullback_entry
from miniquant.backtest.replay import HOUR,DAY


class Cohort2Tests(unittest.TestCase):
    def bars(self):
        rows=[]
        for ts in range(180*24):
            p=100+0.01*ts+math.sin(ts/20)
            rows.append(dict(ts=ts*HOUR,o=p,h=p+0.5,l=p-0.5,c=p+0.1,v=100))
        return rows
    def test_volatility_scaling_cannot_add_leverage_and_negative_trend_flat(self):
        self.assertLessEqual(trend_weight([100+i for i in range(181)],[20,60,120]),0.75)
        self.assertEqual(trend_weight([300-i for i in range(181)],[20,60,120]),0)
        self.assertIsNone(trend_weight([100]*30,[20,60,120]))
    def test_future_price_and_volume_do_not_change_decisions_or_fills(self):
        bars=self.bars();cut=160*DAY
        altered=[b if b['ts']<cut else dict(b,o=b['o']*3,h=b['h']*3,l=b['l']*3,c=b['c']*3,v=1) for b in bars]
        for family,param in [('multiscale_trend',dict(horizons=[20,60,120])),('confirmed_pullback',dict(shock_sigma=1.5,volume_filter=True))]:
            a=replay_cohort2(bars,family,param,140*DAY,180*DAY,liquidate=False)
            b=replay_cohort2(altered,family,param,140*DAY,180*DAY,liquidate=False)
            self.assertEqual([x for x in a['decisions'] if x['decision_at']<=cut],[x for x in b['decisions'] if x['decision_at']<=cut])
            self.assertEqual([x for x in a['fills'] if x['ts']<cut],[x for x in b['fills'] if x['ts']<cut])
    def test_zero_volume_hour_has_no_fill_and_pending_deadline_is_fixed(self):
        bars=self.bars();start=140*DAY
        for b in bars:
            if start<=b['ts']<start+5*HOUR:b['v']=0
        r=replay_cohort2(bars,'hold',{},start,142*DAY)
        self.assertEqual(r['fills'][0]['ts'],start+5*HOUR)
        self.assertEqual(r['decisions'][0]['execute_at'],start+2*HOUR)
        self.assertFalse(r['demo_ready'])
    def test_expired_order_does_not_trade_later(self):
        bars=self.bars();start=140*DAY
        for b in bars:
            if start<=b['ts']<start+20*HOUR:b['v']=0
        r=replay_cohort2(bars,'hold',{},start,142*DAY)
        self.assertEqual(r['fills'],[])
        self.assertEqual(r['expired_intents'],1)
    def test_missing_volume_or_gap_rejected(self):
        b=self.bars()
        with self.assertRaises(ValueError):replay_cohort2(b[:-1],'cash',{},140*DAY,180*DAY)
        b[100]['v']=-1
        with self.assertRaises(ValueError):replay_cohort2(b,'cash',{},140*DAY,180*DAY)
    def test_pullback_requires_shock_confirmation_and_daily_trend(self):
        daily=[dict(c=100+i*0.1) for i in range(120)]
        rows=[dict(c=100+0.1*math.sin(i),l=99,v=100) for i in range(34)]
        rows[-2]=dict(c=95,l=94,v=100);rows[-1]=dict(c=96,l=94.5,v=110)
        self.assertTrue(pullback_entry(rows,daily,1.5,True))
        rows[-1]['l']=93
        self.assertFalse(pullback_entry(rows,daily,1.5,True))

    def test_confirmed_pullback_replay_has_nonvacuous_delayed_entry(self):
        bars=self.bars();start=150*DAY
        for b in bars:
            if start+4*HOUR<=b['ts']<start+8*HOUR:
                b.update(o=115,h=116,l=114,c=115,v=120)
            if start+8*HOUR<=b['ts']<start+12*HOUR:
                b.update(o=116,h=119,l=115,c=118,v=130)
        r=replay_cohort2(bars,'confirmed_pullback',dict(shock_sigma=1.5,volume_filter=True),149*DAY,153*DAY)
        entries=[f for f in r['fills'] if f['reason']=='confirmed_pullback']
        self.assertGreater(len(entries),0)
        self.assertEqual(entries[0]['ts'],start+13*HOUR)
