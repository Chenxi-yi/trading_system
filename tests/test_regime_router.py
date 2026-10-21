import unittest,math
from miniquant.backtest.regime_router import expert_signals,replay_router,target_for,HOUR,DAY

class RouterTests(unittest.TestCase):
    def bars(self,days=250):
        return [dict(ts=i*HOUR,o=100+2*math.sin(i/24),h=104,l=96,c=100+2*math.sin((i+1)/24),v=10.) for i in range(days*24)]
    def test_expert_prefix_no_future(self):
        b=self.bars();p=220*24;changed=[dict(x,o=x['o']*2,h=x['h']*2,l=x['l']*2,c=x['c']*2) if i>=p else x for i,x in enumerate(b)]
        a=[s for s in expert_signals(b) if s['decision_at']<=p*HOUR]
        self.assertEqual(a,[s for s in expert_signals(changed) if s['decision_at']<=p*HOUR])
        self.assertEqual(a,expert_signals(b[:p]))
    def test_routing_and_cash(self):
        s=dict(state='range_high',trend=.7,reversion=.3,risk=.75)
        self.assertEqual(target_for(s,'router'),.3);s['state']='down_normal';self.assertEqual(target_for(s,'router'),0)
        self.assertAlmostEqual(target_for(s,'equal_mix'),.5);s['state']='unknown';self.assertEqual(target_for(s,'vol_only'),0)
    def test_delay_zero_volume_and_ledger(self):
        b=self.bars(3);s=[dict(decision_at=4*HOUR,state_available_at=0,state='up_normal',trend=.5,reversion=0.,risk=.75)]
        b[5]['v']=0;v=replay_router(b,s,'router',0,3*DAY)
        self.assertEqual(v['fills'][0]['ts'],6*HOUR)
        q=0;cash=10000
        for f in v['fills']:
            if f['side']=='buy':cash-=f['notional'];q+=f['quantity']
            else:cash+=f['notional']-f['fee'];q-=f['quantity']
        self.assertAlmostEqual(v['daily'][-1]['nav'],cash+q*b[-1]['c'])
    def test_future_target_rejected_and_bad_bars(self):
        b=self.bars(3);s=[dict(decision_at=4*HOUR,state_available_at=5*HOUR,state='up_normal',trend=.5,reversion=0.,risk=.75)]
        with self.assertRaises(ValueError):replay_router(b,s,'router',0,3*DAY)
        with self.assertRaises(ValueError):expert_signals(b[:20]+b[21:])
    def test_first_intent_not_postponed_and_ttl(self):
        b=self.bars(3);s=[dict(decision_at=i*HOUR,state_available_at=0,state='up_normal',trend=.5,reversion=0.,risk=.75) for i in (4,8,12)]
        for x in b[5:18]:x['v']=0
        v=replay_router(b,s,'router',0,3*DAY)
        self.assertEqual(v['expired_intents'],1);self.assertEqual(v['decisions'][0]['expires_at'],16*HOUR)
        self.assertFalse(v['fills'])
