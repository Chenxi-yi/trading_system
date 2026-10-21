import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniquant.accounting.sized_perpetual import SizedPerpAccount
from miniquant.backtest.cohort3 import replay_cohort3,signed_weight
from miniquant.backtest.replay import DAY,HOUR


class SizedPerpTests(unittest.TestCase):
    def test_add_reduce_reverse_realized_and_mark_equity_conserve(self):
        a=SizedPerpAccount(cash=1000,fee_rate=0,slippage=0,step=.01)
        a._trade(2,100,0,'open');a._trade(2,120,1,'add')
        self.assertEqual(a.entry,110)
        self.assertEqual(a.equity(120),1040)
        a._trade(-1,130,2,'reduce');self.assertEqual(a.cash,1020);self.assertEqual(a.entry,110)
        a._trade(-5,100,3,'reverse');self.assertEqual(a.cash,990);self.assertEqual(a.quantity,-2);self.assertEqual(a.entry,100)
        a.close(90,4,'exit');self.assertEqual(a.cash,1010);self.assertEqual(a.quantity,0)
    def test_fees_and_signed_funding(self):
        a=SizedPerpAccount(cash=1000,fee_rate=.001,slippage=0,step=.01)
        a._trade(-2,100,0,'short');a.funding(.01,100,1)
        self.assertAlmostEqual(a.cash,1001.8)
        a.close(90,2,'exit');self.assertAlmostEqual(a.cash,1021.62)
        self.assertAlmostEqual(a.fees,.38)
    def test_target_cap_and_contract_step(self):
        a=SizedPerpAccount();a.target(-.75,80000,80000,0)
        self.assertLessEqual(abs(a.quantity)*a.fills[-1]['price'],7500+1e-8)
        with self.assertRaises(ValueError):a.target(.76,80000,80000,1)
        with self.assertRaises(ValueError):a.funding(float('nan'),80000,1)


class Cohort3Tests(unittest.TestCase):
    def data(self):
        bars=[]
        for ts in range(0,200*DAY,4*HOUR):
            p=300-ts/DAY*.5+2*math.sin(ts/DAY/3)
            bars.append(dict(ts=ts,o=p,h=p+1,l=p-1,c=p+.1,v=100))
        mark=bars+[dict(ts=200*DAY,o=200,h=201,l=199,c=200,v=100)]
        funding=[dict(event_time_ms=t,realized_rate='0.0001') for t in range(0,200*DAY+1,8*HOUR)]
        return bars,mark,funding
    def param(self):return dict(horizons=[20,60,120],risk_mode='fixed',long_only=False)
    def test_downtrend_has_delayed_short_and_funding_reconciles(self):
        b,m,f=self.data();r=replay_cohort3(b,m,f,self.param(),150*DAY,200*DAY)
        self.assertGreater(len(r['fills']),0);self.assertEqual(r['fills'][0]['side'],'sell')
        self.assertGreaterEqual(r['fills'][0]['ts'],r['decisions'][0]['decision_at']+4*HOUR)
        cash=10000+sum(x['realized_pnl']-x['fee'] for x in r['fills'])+sum(x['pnl'] for x in r['funding_events'])
        self.assertAlmostEqual(cash,r['daily'][-1]['nav'])
        self.assertFalse(r['demo_ready'])
    def test_future_prices_and_funding_do_not_change_prefix(self):
        b,m,f=self.data();cut=180*DAY
        change=lambda rows:[x if x['ts']<cut else dict(x,o=x['o']*.8,h=x['h']*.8,l=x['l']*.8,c=x['c']*.8) for x in rows]
        ff=[x if x['event_time_ms']<cut else dict(x,realized_rate='.001') for x in f]
        a=replay_cohort3(b,m,f,self.param(),150*DAY,200*DAY);z=replay_cohort3(change(b),change(m),ff,self.param(),150*DAY,200*DAY)
        self.assertEqual([x for x in a['fills'] if x['ts']<cut],[x for x in z['fills'] if x['ts']<cut])
        self.assertEqual([x for x in a['daily'] if x['ts']<=cut],[x for x in z['daily'] if x['ts']<=cut])
    def test_missing_funding_duplicate_and_mark_rejected(self):
        b,m,f=self.data()
        for mm,ff in [(m[:-1],f),(m,f[:-1]),(m,f+[f[-1]])]:
            with self.assertRaises(ValueError):replay_cohort3(b,mm,ff,self.param(),150*DAY,200*DAY)
    def test_long_only_flat_in_negative_trend_and_zero_volume_no_fill(self):
        b,m,f=self.data();p=dict(self.param(),long_only=True)
        self.assertEqual(replay_cohort3(b,m,f,p,150*DAY,200*DAY)['fills'],[])
        for x in b:
            if 151*DAY<=x['ts']<152*DAY:x['v']=0
        r=replay_cohort3(b,m,f,self.param(),150*DAY,200*DAY)
        self.assertFalse(any(151*DAY<=x['ts']<152*DAY for x in r['fills']))
