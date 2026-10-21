import unittest,math
from miniquant.research.grid_cells import GridCellTrace
from miniquant.backtest.replay import replay,HOUR,DAY
from miniquant.backtest.grid_trace import replay_grid_trace

class GridCellTests(unittest.TestCase):
    def test_coin_fee_cell_pair_and_aggregate(self):
        t=GridCellTrace(1000)
        t.buy('1:0',dict(ts=0,quantity=.99,notional=100.,fee=1.,reason='grid_initial'),0)
        t.buy('1:1',dict(ts=0,quantity=2.,notional=200.,fee=0.,reason='grid_limit_buy'),1)
        t.sell('1:0',dict(ts=1,quantity=.5,notional=60.,fee=.6,reason='grid_limit_sell'),2)
        t.mark(2,120,759.4,2.49)
        t.sell(None,dict(ts=3,quantity=2.49,notional=298.8,fee=0.,reason='grid_reset'),3,['lower_bound'])
        t.mark(4,120,1058.2,0.)
        self.assertAlmostEqual(t.daily[-1]['realized'],58.2)
        self.assertEqual(len(t.events),4);self.assertEqual(t.events[-1]['reset_flags'],['lower_bound'])
        self.assertAlmostEqual(sum(x['quantity'] for x in t.events[-1]['parts']),2.49)
    def test_no_cross_cell_sale_and_dust_retained(self):
        t=GridCellTrace(1000);t.buy('1:0',dict(ts=0,quantity=1.,notional=100.,fee=0.,reason='buy'),0)
        with self.assertRaises(ValueError):t.sell('1:1',dict(ts=1,quantity=.1,notional=10.,fee=0.,reason='sell'),1)
        t.sell('1:0',dict(ts=1,quantity=.99999999,notional=99.999999,fee=0.,reason='sell'),1)
        t.mark(2,100.,999.999999,.00000001)
        self.assertGreater(t.cycles[0]['quantity'],0);self.assertNotIn('closed_at',t.cycles[0])
    def bars(self,days=70):
        rows=[]
        for i in range(days*24):
            o=100+15*math.sin(i/17);c=100+15*math.sin((i+1)/17)
            rows.append(dict(ts=i*HOUR,o=o,h=max(o,c)+.15,l=min(o,c)-.15,c=c,v=10.))
        return rows
    def test_instrumented_economics_identical_and_linked(self):
        b=self.bars();a=replay(b,'grid',6,20*DAY,70*DAY);r=replay_grid_trace(b,'grid',6,20*DAY,70*DAY)
        self.assertEqual(a.daily,r.daily);self.assertEqual(a.fills,r.fills);self.assertEqual(a.fees,r.fees);self.assertEqual(a.turnover,r.turnover)
        self.assertEqual(len(r.fills),len(r.trace['events']));self.assertEqual([x['fill_index'] for x in r.trace['events']],list(range(len(r.fills))))
        self.assertTrue(all(x['identity_error']<1e-6 for x in r.trace['daily']));self.assertTrue(any('scheduled30d' in x['flags'] for x in r.trace['resets']))
    def test_future_prefix_and_reject_non_grid(self):
        b=self.bars();changed=[dict(x,h=150.,l=50.,o=140.,c=140.) if x['ts']>=50*DAY else x for x in b]
        a=replay_grid_trace(b,'grid',6,20*DAY,50*DAY);r=replay_grid_trace(changed,'grid',6,20*DAY,50*DAY)
        self.assertEqual(a.daily,r.daily);self.assertEqual(a.fills,r.fills);self.assertEqual(a.trace,r.trace)
        with self.assertRaises(ValueError):replay_grid_trace(b,'trend',6,20*DAY,50*DAY)

    def test_legacy_pathological_rounding_failure_preserved(self):
        b=[dict(ts=i*HOUR,o=100+15*math.sin(i/17),h=120.,l=80.,c=100+15*math.sin((i+1)/17),v=10.) for i in range(70*24)]
        with self.assertRaises(ValueError):replay(b,'grid',6,20*DAY,70*DAY)
