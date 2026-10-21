import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniquant.research.quota_policy import quota_decision

class QuotaPolicyTests(unittest.TestCase):
    def snapshot(self,p=60,s=28):return dict(ordinaryUsageAllowed=True,rateLimits=dict(primary=dict(usedPercent=p,resetsAt=10000),secondary=dict(usedPercent=s,resetsAt=20000)))
    def test_normal_and_exact_ten_percent_continue(self):
        self.assertEqual(quota_decision(self.snapshot(),0)['action'],'continue')
        self.assertEqual(quota_decision(self.snapshot(90,90),0)['action'],'continue')
    def test_short_window_only_waits_for_short_reset_with_buffer(self):
        x=quota_decision(self.snapshot(91,28),0)
        self.assertEqual(x['blocking_windows'],['primary']);self.assertEqual(x['wake_at_epoch'],10140)
        self.assertIn('COUNT=1',x['suggested_one_off_rrule'])
    def test_both_low_wait_for_later_reset(self):
        x=quota_decision(self.snapshot(99,99),0)
        self.assertEqual(x['wake_at_epoch'],20160)
    def test_unknown_values_do_not_turn_into_zero_or_unlimited(self):
        for x in [{},dict(rateLimits={}),self.snapshot()]:
            if x.get('rateLimits'):x['rateLimits']['primary']['usedPercent']=None
            self.assertEqual(quota_decision(x,0)['action'],'hold_unknown')
    def test_usage_disallowed_and_past_reset_require_requery(self):
        x=self.snapshot();x['ordinaryUsageAllowed']=False
        self.assertEqual(quota_decision(x,0)['action'],'hold_unknown')
        self.assertEqual(quota_decision(self.snapshot(99,28),11000000)['action'],'hold_unknown')
    def test_named_bucket_preferred_without_account_details_in_output(self):
        x=self.snapshot();x.update(accountId='private',rateLimitsByLimitId=dict(codex=self.snapshot(92,28)['rateLimits']))
        result=quota_decision(x,0);self.assertEqual(result['action'],'wait_for_quota');self.assertNotIn('private',str(result))
