import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniquant.research.pressure_overlay import PressureOverlay
from miniquant.backtest.replay import DAY,HOUR
from miniquant.backtest.cohort3 import replay_cohort3

class PressureOverlayTests(unittest.TestCase):
    def data(self):
        trade=[];index=[]
        for i in range(601):
            b=dict(open_time_ms=i*4*HOUR,end_time_ms=(i+1)*4*HOUR,complete=True,close='100')
            index.append(b);trade.append(dict(b,close='100.01' if i<560 else '101'))
        funding=[dict(event_time_ms=t,realized_rate='.0001' if t<95*DAY else '.001') for t in range(0,101*DAY,8*HOUR)]
        return funding,trade,index
    def test_only_mature_premium_and_past_quantile(self):
        f,t,i=self.data();a=PressureOverlay('premium',f,t,i)
        before=a((561*4)*HOUR,.6);after=a(562*4*HOUR,.6)
        self.assertEqual(before,.6);self.assertEqual(after,.3)
        self.assertLess(a.log[-1]['features']['premium']['threshold'],.001)
        self.assertEqual(a(562*4*HOUR,-.6),-.6)
    def test_missing_fails_closed_only_for_positive_target_and_ties_not_extreme(self):
        f,t,i=self.data();a=PressureOverlay('premium',f,t,i)
        self.assertEqual(a(20*DAY,.6),0)
        self.assertEqual(a(20*DAY,-.6),-.6)
        self.assertEqual(a(91*DAY,.6),.6)
    def test_future_price_funding_mutation_does_not_change_prefix(self):
        f,t,i=self.data();decision=94*DAY
        a=PressureOverlay('joint',f,t,i);a(decision,.6)
        ff=[r if r['event_time_ms']<decision else dict(r,realized_rate='99') for r in f]
        tt=[r if r['end_time_ms']<decision else dict(r,close='999') for r in t]
        b=PressureOverlay('joint',ff,tt,i);b(decision,.6)
        self.assertEqual(a.log,b.log)
        truncated=PressureOverlay('joint',[r for r in f if r['event_time_ms']<decision],[r for r in t if r['end_time_ms']<decision],[r for r in i if r['end_time_ms']<decision]);truncated(decision,.6)
        self.assertEqual(a.log,truncated.log)
    def test_joint_requires_both_and_fixed_long_control_preserves_shorts(self):
        f,t,i=self.data();a=PressureOverlay('joint',f,t,i)
        self.assertEqual(a(96*DAY,.6),.3)
        self.assertEqual(a(94*DAY,.6),.6)
        b=PressureOverlay('half_long',f,t,i)
        self.assertEqual(b(0,.6),.3);self.assertEqual(b(0,-.6),-.6)
    def test_hook_none_matches_original_path_and_invalid_target_rejected(self):
        bars=[dict(ts=t,o=100+t/DAY,h=102+t/DAY,l=99+t/DAY,c=101+t/DAY,v=100) for t in range(0,40*DAY,4*HOUR)]
        marks=bars+[dict(ts=40*DAY,o=140,h=142,l=139,c=141)]
        f=[dict(event_time_ms=t,realized_rate='.0001') for t in range(0,40*DAY+1,8*HOUR)]
        param=dict(horizons=[2],risk_mode='fixed')
        a=replay_cohort3(bars,marks,f,param,25*DAY,40*DAY)
        b=replay_cohort3(bars,marks,f,param,25*DAY,40*DAY,target_transform=lambda t,w:w)
        self.assertEqual(a,b)
        with self.assertRaises(ValueError):replay_cohort3(bars,marks,f,param,25*DAY,40*DAY,target_transform=lambda t,w:2)
