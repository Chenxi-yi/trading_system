import unittest
from unittest.mock import Mock
from miniquant.research.study_gate import dispatch


class StudyGateTests(unittest.TestCase):
    def test_evaluate_before_end_never_reads_or_refreshes_data(self):
        callbacks=[Mock(side_effect=AssertionError('Must not call')) for _ in range(5)]
        result=dispatch('evaluate',99,100,*callbacks)
        self.assertEqual(result['status'],'not_due')
        for callback in callbacks:callback.assert_not_called()

    def test_false_support_or_invalidation_blocks_both_actions(self):
        for mode in ('prepare','evaluate'):
            for supported,invalid in [(False,False),(True,True),('true',False)]:
                refresh=Mock();prepare=Mock();evaluate=Mock()
                result=dispatch(mode,100,100,refresh,lambda:{'study_supported':supported},lambda:invalid,prepare,evaluate)
                self.assertEqual(result['status'],'study_blocked')
                refresh.assert_called_once();prepare.assert_not_called();evaluate.assert_not_called()

    def test_supported_dispatches_only_requested_action(self):
        for mode in ('prepare','evaluate'):
            prepare=Mock();evaluate=Mock()
            result=dispatch(mode,100,100,Mock(),lambda:{'study_supported':True},lambda:False,prepare,evaluate)
            self.assertTrue(result['action_dispatched'])
            self.assertEqual(prepare.call_count,1 if mode=='prepare' else 0)
            self.assertEqual(evaluate.call_count,1 if mode=='evaluate' else 0)
