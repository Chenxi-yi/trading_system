import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniquant.research.failed_breakout import failed_breakout_events,FailedBreakoutTarget
from miniquant.backtest.replay import DAY,HOUR

class FailedBreakoutTests(unittest.TestCase):
    def bars(self):return [dict(ts=i*4*HOUR,o=100,h=101,l=99,c=100,v=1) for i in range(180)]
    def test_only_next_close_can_confirm_and_levels_are_prior_days(self):
        b=self.bars();b[130].update(c=102,h=103);b[131].update(c=100)
        e=failed_breakout_events(b,20,0)
        self.assertEqual(len(e),1);self.assertEqual(e[0]['signal_ms'],132*4*HOUR)
        self.assertEqual(e[0]['upper'],101);self.assertEqual(e[0]['reversion_direction'],-1)
        self.assertLessEqual(e[0]['range_last_day_end'],b[130]['ts']//DAY*DAY)
    def test_future_change_and_truncation_cannot_select_event(self):
        b=self.bars();b[130].update(c=102,h=103)
        a=failed_breakout_events(b,20,0)
        changed=[r if i<=131 else dict(r,c=105,h=106,o=105,l=104,v=999) for i,r in enumerate(b)]
        self.assertEqual(a,failed_breakout_events(changed,20,0));self.assertEqual(a,failed_breakout_events(b[:132],20,0))
    def test_timeout_zero_volume_and_no_same_bar_wick_event(self):
        b=self.bars();b[130]['h']=110
        self.assertEqual(failed_breakout_events(b,20,0),[])
        for i in range(130,134):b[i].update(c=102,h=103)
        self.assertEqual(failed_breakout_events(b,20,0),[])
        b=self.bars();b[130].update(c=102,h=103)
        for i in range(131,134):b[i]['v']=0
        self.assertEqual(failed_breakout_events(b,20,0),[])
    def test_fixed_horizon_and_matching_opposite_control(self):
        e=[dict(signal_ms=200*HOUR,reversion_direction=-1)]
        a=FailedBreakoutTarget(e,'reversion',24,0);b=FailedBreakoutTarget(e,'continuation',24,0)
        self.assertEqual(a(199*HOUR,1),0);self.assertEqual(a(200*HOUR,1),-.5)
        self.assertEqual(b(200*HOUR,1),.5);self.assertEqual(a(224*HOUR,1),0)
        self.assertEqual(FailedBreakoutTarget(e,'reversion',24,201*HOUR)(210*HOUR,1),0)
    def test_downside_and_fixed_event_cooldown(self):
        b=self.bars();b[130].update(c=98,l=97);b[135].update(c=98,l=97)
        e=failed_breakout_events(b,20,0);self.assertEqual(len(e),1);self.assertEqual(e[0]['reversion_direction'],1)

    def test_four_hour_replay_entry_exit_latency_and_zero_volume(self):
        from miniquant.backtest.cohort3 import replay_cohort3
        bars=[dict(ts=t,o=100,h=101,l=99,c=100,v=1) for t in range(0,30*DAY,4*HOUR)]
        marks=bars+[dict(ts=30*DAY,o=100,h=101,l=99,c=100)]
        funding=[dict(event_time_ms=t,realized_rate='0') for t in range(0,30*DAY+1,8*HOUR)]
        e=[dict(signal_ms=26*DAY+4*HOUR,reversion_direction=1)]
        target=FailedBreakoutTarget(e,'reversion',24,25*DAY)
        param=dict(horizons=[2],risk_mode='fixed')
        a=replay_cohort3(bars,marks,funding,param,25*DAY,30*DAY,target_transform=target,decision_hours=4)
        self.assertEqual([f['ts'] for f in a['fills']],[26*DAY+8*HOUR,27*DAY+8*HOUR])
        for r in bars:
            if r['ts']==26*DAY+8*HOUR:r['v']=0
        b=replay_cohort3(bars,marks,funding,param,25*DAY,30*DAY,target_transform=FailedBreakoutTarget(e,'reversion',24,25*DAY),decision_hours=4)
        self.assertEqual(b['fills'][0]['ts'],26*DAY+12*HOUR)
