import unittest
from miniquant.accounting.fifo_attribution import fifo_attribution

class FifoTests(unittest.TestCase):
    def test_buy_fee_in_coin_and_partial_sale(self):
        fills=[dict(ts=0,side='buy',quantity=.99,notional=100.,fee=1.,reason='entry'),dict(ts=2,side='sell',quantity=.5,notional=60.,fee=.6,reason='exit')]
        r=fifo_attribution(fills,[dict(ts=1,price=100.),dict(ts=3,price=120.)],initial=1000)
        self.assertAlmostEqual(r['final_pnl'],18.2);self.assertAlmostEqual(r['final_realized'],59.4-100*.5/.99);self.assertFalse(r['cell_cycle_profit_certified'])
    def test_marks_do_not_rewrite_realizations(self):
        fills=[dict(ts=0,side='buy',quantity=1.,notional=100.,fee=0.,reason='entry')]
        r=fifo_attribution(fills,[dict(ts=1,price=80.),dict(ts=2,price=110.)],initial=1000)
        self.assertEqual(r['worst_unrealized'],-20.);self.assertEqual(r['final_realized'],0.)
    def test_bad_inventory_and_unvalued_future(self):
        fills=[dict(ts=0,side='sell',quantity=1.,notional=100.,fee=0.,reason='exit')]
        with self.assertRaises(ValueError):fifo_attribution(fills,[dict(ts=1,price=100.)])
        fills[0]['ts']=2
        with self.assertRaises(ValueError):fifo_attribution(fills,[dict(ts=1,price=100.)])
