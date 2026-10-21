import unittest,math
import numpy as np
from miniquant.research.range_features import variance_ratio,past_features,H4

class RangeFeatureTests(unittest.TestCase):
    def test_hand_variance_overlap_and_robust(self):
        r=[1.,-1.,2.,-2.,1.,-1.];q=2;n=len(r);mu=sum(r)/n
        s1=sum((x-mu)**2 for x in r)/(n-1);sq=sum((sum(r[i:i+q])-q*mu)**2 for i in range(n-q+1))/(q*(n-q+1)*(1-q/n))
        e=[x-mu for x in r];delta=n*sum(e[i]**2*e[i-1]**2 for i in range(1,n))/(sum(x*x for x in e)**2)
        v=variance_ratio(r,q);self.assertAlmostEqual(v['vr'],sq/s1);self.assertAlmostEqual(v['robust_theta'],delta);self.assertAlmostEqual(v['z_hetero'],math.sqrt(n)*(v['vr']-1)/math.sqrt(delta))
    def test_drift_scale_and_undefined(self):
        r=np.random.default_rng(1).normal(size=720);a=variance_ratio(r,42);b=variance_ratio(r*2+.3,42)
        self.assertAlmostEqual(a['vr'],b['vr']);self.assertAlmostEqual(a['z_hetero'],b['z_hetero'])
        self.assertEqual(variance_ratio([.001]*720,6)['status'],'zero_variance')
        with self.assertRaises(ValueError):variance_ratio([1.,float('nan'),2.],2)
        with self.assertRaises(ValueError):variance_ratio([1.,2.,3.],True)
    def rows(self,n=800):return [dict(ts=i*H4,end=(i+1)*H4,c=100*math.exp(.001*i+.005*math.sin(i)),complete=True) for i in range(n)]
    def test_no_future_prefix_and_no_signal(self):
        rows=self.rows();a=past_features(rows[:750]);changed=[dict(x,c=x['c']*3) if i>=750 else x for i,x in enumerate(rows)]
        self.assertEqual(a,past_features(changed[:750]));self.assertIsNone(a['trade_state']);self.assertFalse(a['historical_publication_certified'])
    def test_missing_and_unfinished_rejected(self):
        rows=self.rows()
        with self.assertRaises(ValueError):past_features(rows[:300]+rows[301:])
        rows[-1]['complete']=False
        with self.assertRaises(ValueError):past_features(rows)
        self.assertEqual(past_features(self.rows(700))['status'],'insufficient_history')
