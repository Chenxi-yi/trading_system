import unittest
import test_pretrade_risk as legacy_tests
from miniquant.risk.pretrade import assess_spot_order as legacy_assess
from miniquant.risk.pretrade_strict import assess_spot_order


class StrictRiskTests(unittest.TestCase):
    def fixture(self):
        legacy=legacy_tests.PretradeRiskTests()
        return legacy.intent(),legacy.context()

    def test_boolean_regression_and_extreme_lot_fail_closed(self):
        intent,context=self.fixture();context.update(lot=1,minimum_quantity=1)
        intent.update(quantity=True,maximum_price=1)
        self.assertTrue(legacy_assess(intent,context)['allow'])
        self.assertFalse(assess_spot_order(intent,context)['allow'])
        intent,context=self.fixture();intent['quantity']=1e308;context['lot']=1e-308
        result=assess_spot_order(intent,context)
        self.assertFalse(result['allow']);self.assertFalse(result['submission_authorized'])

    def test_every_numeric_context_field_rejects_boolean(self):
        from miniquant.risk.pretrade_strict import NUMERIC_FIELDS
        for name in NUMERIC_FIELDS:
            intent,context=self.fixture();context[name]=True
            with self.subTest(field=name):self.assertFalse(assess_spot_order(intent,context)['allow'])

    def test_huge_integer_nonfinite_and_bad_mapping_are_rejected(self):
        for value in (10**400,float('inf'),float('nan'),'1',None):
            intent,context=self.fixture();intent['quantity']=value
            with self.subTest(value_type=type(value).__name__):self.assertFalse(assess_spot_order(intent,context)['allow'])
        self.assertFalse(assess_spot_order(None,{})['allow'])

    def test_valid_semantics_loss_stop_and_inventory_still_hold(self):
        intent,context=self.fixture()
        self.assertEqual(assess_spot_order(intent,context)['allow'],legacy_assess(intent,context)['allow'])
        self.assertFalse(assess_spot_order(intent,context)['submission_authorized'])
        context['bot_nav']=600
        self.assertEqual(assess_spot_order(intent,context)['reason'],'initial_capital_loss_stop')
        intent['side']='sell';context['account_available_base']=1.0001
        self.assertEqual(assess_spot_order(intent,context)['reason'],'protected_or_unowned_inventory')
