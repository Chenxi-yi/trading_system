from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniquant.research.validation import metrics,block_bootstrap_mean,cscv_sharpe


class ValidationTests(unittest.TestCase):
    def test_nav_return_and_drawdown_hand_calculation(self):
        r=metrics([dict(nav=110),dict(nav=88)],100)
        self.assertAlmostEqual(r['net_return'],-0.12)
        self.assertAlmostEqual(r['max_drawdown'],-0.2)

    def test_bootstrap_deterministic_and_negative_constant_not_passed(self):
        r=block_bootstrap_mean([-0.001]*100,replicates=100)
        self.assertFalse(r['all_lower_bounds_positive'])
        self.assertEqual(r,block_bootstrap_mean([-0.001]*100,replicates=100))
        self.assertEqual(block_bootstrap_mean([0.01]*10)['status'],'insufficient_data')

    def test_cscv_rejects_nan_and_marks_undefined_scores(self):
        with self.assertRaises(ValueError):cscv_sharpe([[0,float('nan')]]*16)
        self.assertEqual(cscv_sharpe(np.zeros((80,4)))['status'],'undefined_splits_do_not_use_as_gate')

    def test_cscv_candidate_order_invariant_and_tail_disclosed(self):
        rng=np.random.default_rng(42);a=rng.normal(0,0.01,size=(83,4))
        x=cscv_sharpe(a);y=cscv_sharpe(a[:,::-1])
        self.assertAlmostEqual(x['pbo_strict'],y['pbo_strict'])
        self.assertEqual(x['explicit_tail_rows_trimmed'],3)
        self.assertEqual(x['valid_splits'],70)


if __name__=='__main__':unittest.main()
