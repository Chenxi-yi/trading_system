"""Past-only variance-ratio descriptors. No stationarity, alpha, or trade labels."""
import math
import numpy as np
H4=14400000


def variance_ratio(returns,q):
    r=np.asarray(returns,dtype=float)
    if r.ndim!=1 or type(q)is not int or not 2<=q<len(r) or not np.isfinite(r).all():raise ValueError('Invalid VR inputs')
    n=len(r);mu=float(np.mean(r));e=r-mu;s=float(np.dot(e,e));sigma1=s/(n-1)
    if sigma1<=1e-24:return dict(status='zero_variance',N=n,q=q,vr=None,z_hetero=None)
    cumulative=np.r_[0.,np.cumsum(r)];sums=cumulative[q:]-cumulative[:-q]-q*mu
    m=q*(n-q+1)*(1-q/n);sigmaq=float(np.dot(sums,sums))/m;vr=sigmaq/sigma1
    e2=e*e;theta=0.
    for j in range(1,q):
        delta=n*float(np.dot(e2[j:],e2[:-j]))/(s*s)
        theta+=(2*(q-j)/q)**2*delta
    if not all(math.isfinite(x) for x in (vr,theta)) or theta<=0:return dict(status='undefined_robust_variance',N=n,q=q,vr=vr if math.isfinite(vr) else None,z_hetero=None)
    z=math.sqrt(n)*(vr-1)/math.sqrt(theta)
    return dict(status='descriptive',N=n,q=q,vr=vr,z_hetero=z,sigma1=sigma1,sigmaq=sigmaq,finite_sample_m=m,robust_theta=theta,nonoverlap_spans=n//q,not_trading_signal=True)


def past_features(rows):
    if any(b['end']-a['end']!=H4 for a,b in zip(rows,rows[1:])):raise ValueError('Price gaps or duplicate end')
    for x in rows:
        if x.get('complete')is not True or x['end']%H4 or x['ts']+H4!=x['end'] or not math.isfinite(x['c']) or x['c']<=0:raise ValueError('Invalid completed price')
    if len(rows)<721:return dict(status='insufficient_history',features=None)
    closes=np.array([x['c'] for x in rows[-721:]],dtype=float);r=np.diff(np.log(closes))
    return dict(status='descriptive_only',event_time=rows[-1]['end'],modeled_available_at=rows[-1]['end'],historical_publication_certified=False,window_returns=720,direction60d_log_change=float(np.sum(r[-360:])),volatility20d_annual=float(np.std(r[-120:],ddof=1)*math.sqrt(6*365)),variance_ratios={str(q):variance_ratio(r,q) for q in (6,42)},trade_state=None,alpha_qualified=False)
