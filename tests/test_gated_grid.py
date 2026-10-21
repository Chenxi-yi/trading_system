import unittest,math
from miniquant.backtest.gated_grid import replay_gated_grid
from miniquant.backtest.replay import replay,DAY,HOUR

class GatedGridTests(unittest.TestCase):
    def bars(self,days=160):
        out=[]
        for i in range(days*24):
            o=100+5*math.sin(i/100);c=100+5*math.sin((i+1)/100)
            if i>=140*24:o*=.7;c*=.7
            out.append(dict(ts=i*HOUR,o=o,c=c,h=max(o,c)+.1,l=min(o,c)-.1,v=10.))
        return out
    def test_control_same_economics(self):
        b=self.bars();a=replay(b,'grid',8,120*DAY,160*DAY);r=replay_gated_grid(b,'grid',8,120*DAY,160*DAY,gate_mode='always')
        self.assertEqual(a.daily,r.daily);self.assertEqual(a.fills,r.fills)
    def test_active_exit_but_entry_only_waits(self):
        b=self.bars();a=replay_gated_grid(b,'grid',8,120*DAY,160*DAY,gate_mode='active');c=replay_gated_grid(b,'grid',8,120*DAY,160*DAY,gate_mode='entry_only')
        self.assertTrue(any(f['reason']=='gate_exit' for f in a.fills));self.assertFalse(any(f['reason']=='gate_exit' for f in c.fills))
        for f in a.fills:
            if f['reason']=='gate_exit':self.assertEqual(f['ts']%DAY,HOUR)
    def test_zero_volume_wait_and_ttl(self):
        b=self.bars();s=120*DAY
        # First daily decision is day121 close; all initial execution slots have zero volume through expiry.
        for x in b:
            if 121*DAY+HOUR<=x['ts']<=122*DAY:x['v']=0
        a=replay_gated_grid(b,'grid',8,s,125*DAY,gate_mode='always')
        self.assertTrue(all(b[f['ts']//HOUR]['v']>0 for f in a.fills if f['ts']<125*DAY))
        self.assertFalse(any(121*DAY+HOUR<=f['ts']<=122*DAY for f in a.fills))
    def test_actual_decision_prefix_and_unknown_cash(self):
        b=self.bars();p=145*24;changed=[dict(x,o=x['o']*1.5,c=x['c']*1.5,h=x['h']*1.5,l=x['l']*1.5) if i>=p else x for i,x in enumerate(b)]
        a=replay_gated_grid(b,'grid',8,120*DAY,145*DAY);c=replay_gated_grid(changed,'grid',8,120*DAY,145*DAY)
        self.assertEqual(a,c)
        r=replay_gated_grid(b[:60*24],'grid',8,20*DAY,60*DAY);self.assertFalse(r.fills)
    def test_hold_has_no_grid_fills_and_half_risk(self):
        b=self.bars();r=replay_gated_grid(b,'grid',8,120*DAY,160*DAY,gate_mode='hold');self.assertTrue(all('grid' not in f['reason'] for f in r.fills))
        half=replay_gated_grid(b,'grid',8,120*DAY,160*DAY,gate_mode='always',budget_fraction=.475)
        full=replay_gated_grid(b,'grid',8,120*DAY,160*DAY,gate_mode='always')
        self.assertLess(half.turnover,full.turnover)
