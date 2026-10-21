import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.audit_metrics_coverage import label_quality

class LabelQualityTests(unittest.TestCase):
    def test_outside_duplicate_and_backward_labels_do_not_hide_missing(self):
        rows=[dict(create_time=t) for t in ['2024-01-01 00:05:00','2024-01-01 00:00:00','2024-01-01T00:00:00','2024-01-02 00:00:00']]
        q=label_quality('2024-01-01',rows);self.assertEqual(len(q['missing_labels']),286);self.assertEqual(q['duplicate_labels'],1);self.assertEqual(q['raw_backward_steps'],1);self.assertEqual(q['outside_labels'],['2024-01-02 00:00:00'])
    def test_full_grid_reordering_only_is_not_missing_or_duplicated(self):
        from datetime import datetime,timedelta
        rows=[dict(create_time=str(datetime(2024,1,1)+timedelta(minutes=5*i))) for i in range(288)];rows[0],rows[1]=rows[1],rows[0];q=label_quality('2024-01-01',rows)
        self.assertEqual(q['missing_labels'],[]);self.assertEqual(q['outside_labels'],[]);self.assertEqual(q['duplicate_labels'],0);self.assertEqual(q['raw_backward_steps'],1)
