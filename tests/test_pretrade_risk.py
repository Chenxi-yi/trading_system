import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniquant.risk.pretrade import assess_spot_order


class PretradeRiskTests(unittest.TestCase):
    def context(self):
        return dict(environment='demo',now_ms=1000,snapshot_ms=999,max_snapshot_age_ms=100,
                    bot_initial_nav=1000,bot_nav=1000,max_initial_loss_fraction=0.4,
                    bot_available_usdt=200,strategy_available_usdt=100,account_available_usdt=5000,
                    bot_inventory=0.01,strategy_inventory=0.01,account_available_base=1.01,protected_base=1,
                    max_order_notional=100,maximum_buy_fee_rate=0.001,lot=1e-8,minimum_quantity=0.00002)
    def intent(self,side='buy'):return dict(inst_id='BTC-USDT',mode='cash',side=side,quantity=0.001,maximum_price=80000)
    def test_strategy_budget_restricts_even_when_account_has_money(self):
        c=self.context();self.assertTrue(assess_spot_order(self.intent(),c)['allow'])
        c['strategy_available_usdt']=50
        self.assertEqual(assess_spot_order(self.intent(),c)['reason'],'insufficient_reserved_budget')
    def test_protected_assets_cannot_be_sold(self):
        c=self.context();c['account_available_base']=1.0001
        self.assertEqual(assess_spot_order(self.intent('sell'),c)['reason'],'protected_or_unowned_inventory')
    def test_loss_reference_is_initial_principal_and_sell_can_reduce(self):
        c=self.context();c['bot_nav']=600
        self.assertEqual(assess_spot_order(self.intent(),c)['reason'],'initial_capital_loss_stop')
        self.assertTrue(assess_spot_order(self.intent('sell'),c)['allow'])
    def test_no_live_submission_stale_data_or_missing_config(self):
        c=self.context();c['environment']='live';self.assertFalse(assess_spot_order(self.intent(),c)['allow'])
        c=self.context();c['snapshot_ms']=0;self.assertFalse(assess_spot_order(self.intent(),c)['allow'])
        self.assertFalse(assess_spot_order(self.intent(),{})['allow'])
        self.assertFalse(assess_spot_order(self.intent(),self.context())['submission_authorized'])
