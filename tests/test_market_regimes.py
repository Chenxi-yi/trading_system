import unittest,math
from miniquant.research.market_regimes import observable_states,state_asof,conditional_attribution,DAY

class RegimeTests(unittest.TestCase):
    def rows(self,n=550):return [dict(end=(i+1)*DAY,c=100*math.exp(.001*i+.01*math.sin(i))) for i in range(n)]
    def test_future_prefix_invariant(self):
        rows=self.rows();a=observable_states(rows);changed=[dict(r,c=r['c']*2) if i>=400 else r for i,r in enumerate(rows)]
        self.assertEqual(a[:400],observable_states(changed)[:400]);self.assertEqual(a[:400],observable_states(rows[:400]))
    def test_asof_boundary_and_confirmation(self):
        a=observable_states(self.rows());self.assertEqual(state_asof(a,a[300]['available_at']-1),a[299]);self.assertEqual(state_asof(a,0)['state'],'unknown')
        for i in range(2,len(a)):
            if a[i]['state']!=a[i-1]['state'] and a[i]['state']!='unknown':self.assertEqual(len(set(x['raw_state'] for x in a[i-2:i+1])),1)
    def test_prior_quantile_excludes_today(self):
        rows=self.rows();a=observable_states(rows);rows[-1]=dict(rows[-1],c=rows[-1]['c']*3);b=observable_states(rows)
        self.assertEqual(a[-1]['prior_vol_q75'],b[-1]['prior_vol_q75']);self.assertNotEqual(a[-1]['volatility'],b[-1]['volatility'])
    def test_zero_path_and_bad_input(self):
        flat=[dict(end=(i+1)*DAY,c=100) for i in range(250)];self.assertEqual(observable_states(flat)[-1]['state'],'range_normal')
        with self.assertRaises(ValueError):observable_states(flat[:100]+flat[101:])
        flat[-1]['c']=float('nan')
        with self.assertRaises(ValueError):observable_states(flat)
    def test_attribution_uses_day_start(self):
        s=[dict(available_at=DAY,state='up_normal'),dict(available_at=2*DAY,state='down_high')]
        r=conditional_attribution([dict(ts=2*DAY,nav=10100)],s)
        self.assertEqual(r['up_normal']['days'],1);self.assertEqual(r['down_high']['days'],0)
