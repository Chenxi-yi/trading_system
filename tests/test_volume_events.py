import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniquant.research.volume_events import detect_events,label_events,calendar_joint_bootstrap
from miniquant.backtest.replay import HOUR,DAY


class VolumeEventsTests(unittest.TestCase):
    def rows(self):
        rows=[dict(ts=i*4*HOUR,c=100+math.sin(i)*.01,v=100) for i in range(400)]
        for i,p in [(350,95),(360,90),(375,85)]:rows[i].update(c=p,v=200)
        return rows
    def test_past_same_slot_normalization_and_fixed_spacing(self):
        events=detect_events(self.rows(),0)
        self.assertEqual([e['bar_ts']//(4*HOUR) for e in events],[350,375])
        self.assertEqual(events[0]['past_same_weekday_slot_volume'],100)
        self.assertEqual(events[0]['volume_group'],'high')
        self.assertEqual(events[0]['volume_ratio'],2)
    def test_future_volume_price_cannot_change_earlier_events(self):
        rows=self.rows();a=detect_events(rows,0)
        changed=[r if i<=350 else dict(r,c=r['c']*3,v=1e6) for i,r in enumerate(rows)]
        b=detect_events(changed,0)
        self.assertEqual(a[0],b[0])
        self.assertEqual(a[0],detect_events(rows[:351],0)[0])
    def test_costs_and_unavailable_labels_are_not_zero_returns(self):
        event=dict(signal_ms=0,volume_group='normal')
        hourly=[dict(ts=HOUR,o=100,v=1),dict(ts=25*HOUR,o=110,v=1)]
        result=label_events([event],hourly)[0]['labels']
        self.assertAlmostEqual(result['24']['base_net'],110*.9995/(100*1.0005)*.999**2-1)
        self.assertLess(result['24']['stress_net'],result['24']['base_net'])
        self.assertEqual(result['72']['status'],'future_or_input_unavailable')
        hourly[1]['v']=0
        self.assertEqual(label_events([event],hourly)[0]['labels']['24']['status'],'no_demonstrated_execution_volume')
    def test_calendar_bootstrap_keeps_non_event_days_and_joint_cells(self):
        events=[]
        for day in range(0,180,3):
            for group in ('low','normal','high'):
                events.append(dict(signal_ms=day*DAY,volume_group=group,labels={str(h):dict(status='labeled',base_net=.01) for h in (24,72)}))
        out=calendar_joint_bootstrap(events,0,180*DAY,replicates=100)
        for v in out.values():
            self.assertEqual(v['status'],'exploratory_diagnostic')
            self.assertAlmostEqual(v['cells']['high_24']['observed_mean'],.01)
            self.assertEqual(v['cells']['high_24']['events'],60)
            self.assertAlmostEqual(v['primary_high_minus_normal24']['observed'],0)
    def test_gap_and_negative_volume_rejected(self):
        rows=self.rows()
        with self.assertRaises(ValueError):detect_events(rows[:-2]+rows[-1:],0)
        rows[350]['v']=-1
        with self.assertRaises(ValueError):detect_events(rows,0)
