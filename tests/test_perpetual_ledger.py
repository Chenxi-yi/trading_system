from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniquant.accounting.perpetual import LinearPerpAccount


class PerpAccountingTests(unittest.TestCase):
    def test_short_pnl_and_funding_signs_and_margin_not_expense(self):
        a=LinearPerpAccount(10000,fee_rate=0,slippage=0)
        a.target(-1,10000,0)
        self.assertAlmostEqual(a.quantity,-0.75)
        self.assertEqual(a.cash,10000)
        self.assertAlmostEqual(a.equity(12000),8500)
        self.assertAlmostEqual(a.settle_funding(0.0001,12000,1),0.9)
        a.close(12000,2)
        self.assertAlmostEqual(a.cash,8500.9)

    def test_long_pays_positive_funding_and_contract_quantity_mapping(self):
        a=LinearPerpAccount(10000,fee_rate=0,slippage=0)
        a.target(1,10000,0)
        self.assertAlmostEqual(a.fills[0]['contracts'],75)
        self.assertAlmostEqual(a.settle_funding(0.001,10000,1),-7.5)
        self.assertAlmostEqual(a.cash,9992.5)
        with self.assertRaises(ValueError):a.settle_funding(float('nan'),10000,2)

    def test_fees_and_slippage_charged_on_both_legs(self):
        a=LinearPerpAccount(10000)
        a.target(1,10000,0);a.close(10000,1)
        self.assertLess(a.cash,10000)
        self.assertGreater(a.fees,0)
        self.assertEqual(len(a.fills),2)
        self.assertEqual(a.quantity,0)


if __name__=='__main__':unittest.main()
