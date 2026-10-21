import unittest,sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniquant.research.matched_events import match_events,features
from miniquant.backtest.replay import HOUR,DAY

class MatchedEventsTests(unittest.TestCase):
    def event(self,time,severity=2,sigma=.01,trend=1,**kw):
        return dict(signal_ms=time,severity=severity,sigma=sigma,trend_z=trend,**kw)
    def test_only_preceding_mature_donors_and_fixed_calipers(self):
        treated=self.event(500*DAY)
        donors=[self.event(499*DAY),self.event(100*DAY),self.event(495*DAY,severity=3),self.event(490*DAY,trend=-1),self.event(480*DAY)]
        self.assertEqual(match_events([treated],donors)[0]['donor_ms'],480*DAY)
        self.assertEqual(match_events([treated],donors[:-1])[0]['status'],'unmatched')
    def test_future_labels_cannot_choose_donor_and_reuse_is_explicit(self):
        donor=self.event(400*DAY,labels={'24':999})
        a=match_events([self.event(410*DAY),self.event(411*DAY)],[donor])
        donor['labels']={'24':-999}
        self.assertEqual(a,match_events([self.event(410*DAY),self.event(411*DAY)],[donor]))
        self.assertEqual([x['donor_ms'] for x in a],[400*DAY]*2)
    def test_severity_only_relaxed_for_ordinary_reference(self):
        t=self.event(410*DAY);d=self.event(400*DAY,severity=.8)
        self.assertEqual(match_events([t],[d])[0]['status'],'unmatched')
        self.assertEqual(match_events([t],[d],False)[0]['status'],'matched')
    def test_state_excludes_current_and_future_close(self):
        rows=[dict(ts=i*4*HOUR,c=100*math.exp(i*.001+math.sin(i)*.002)) for i in range(400)]
        event=dict(bar_ts=350*4*HOUR,signal_ms=351*4*HOUR,shock_log_return=-.02)
        a=features(rows,[event])[0]
        for i in range(350,400):rows[i]['c']*=4
        self.assertEqual(a,features(rows,[event])[0])
