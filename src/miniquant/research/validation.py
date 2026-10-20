"""Explicit research diagnostics. No function claims to certify future alpha."""
from itertools import combinations
import math
import numpy as np


def daily_returns(daily,initial=10000):
    values=np.asarray([initial]+[x['nav'] for x in daily],dtype=float)
    if not np.isfinite(values).all() or (values<=0).any():raise ValueError('Invalid NAV')
    return values[1:]/values[:-1]-1


def metrics(daily,initial=10000):
    r=daily_returns(daily,initial)
    if len(r)<2:raise ValueError('Insufficient observations')
    nav=np.asarray([initial]+[x['nav'] for x in daily],dtype=float)
    sd=float(r.std(ddof=1));ratio=nav[-1]/initial
    return dict(days=len(r),net_return=float(ratio-1),CAGR=float(ratio**(365/len(r))-1),
                daily_sharpe_365=float(r.mean()/sd*math.sqrt(365)) if sd>1e-14 else None,
                max_drawdown=float(np.min(nav/np.maximum.accumulate(nav)-1)),
                mean_daily=float(r.mean()),volatility_annual=float(sd*math.sqrt(365)),
                worst_day=float(r.min()),best_day=float(r.max()))


def block_bootstrap_mean(returns,blocks=(7,14,30),replicates=2000,seed=20261021):
    r=np.asarray(returns,dtype=float)
    if len(r)<60 or not np.isfinite(r).all():return dict(status='insufficient_data')
    rng=np.random.default_rng(seed);out={}
    for block in blocks:
        means=np.empty(replicates)
        for batch in range(0,replicates,100):
            count=min(100,replicates-batch)
            starts=rng.integers(0,len(r),size=(count,math.ceil(len(r)/block)))
            idx=(starts[:,:,None]+np.arange(block))%len(r)
            sample=r[idx.reshape(count,-1)[:,:len(r)]]
            means[batch:batch+count]=sample.mean(axis=1)
        out[str(block)]=dict(lower_one_sided_95=float(np.quantile(means,0.05)),
                             upper_95=float(np.quantile(means,0.95)),
                             mean=float(r.mean()))
    return dict(status='diagnostic',block_lengths=out,replicates=replicates,
                all_lower_bounds_positive=all(x['lower_one_sided_95']>0 for x in out.values()),
                note='Dependent historical resampling; not a future profit probability.')


def cscv_sharpe(matrix,blocks=8):
    a=np.asarray(matrix,dtype=float)
    if a.ndim!=2 or a.shape[1]<2 or not np.isfinite(a).all() or blocks<2 or blocks%2:raise ValueError('Invalid CSCV matrix')
    trim=len(a)%blocks
    a=a[:len(a)-trim] if trim else a
    if len(a)<blocks*2:return dict(status='insufficient_data')
    splits=[];invalid=0
    block_size=len(a)//blocks
    def scores(x):
        sd=x.std(axis=0,ddof=1)
        return np.divide(x.mean(axis=0),sd,out=np.full(x.shape[1],np.nan),where=sd>1e-14)
    for selected in combinations(range(blocks),blocks//2):
        mask=np.isin(np.arange(len(a))//block_size,selected)
        train,test=scores(a[mask]),scores(a[~mask])
        if not np.isfinite(train).all() or not np.isfinite(test).all():invalid+=1;continue
        winners=np.flatnonzero(np.isclose(train,train.max(),rtol=0,atol=1e-12))
        probabilities=[];medians=[]
        for j in winners:
            equal=np.isclose(test,test[j],rtol=0,atol=1e-12)
            below=(test<test[j])&~equal
            rank=int(below.sum())+(int(equal.sum())+1)/2
            probabilities.append(float(rank<(a.shape[1]+1)/2));medians.append(float(rank==(a.shape[1]+1)/2))
        splits.append(dict(is_blocks=list(selected),below_fraction=float(np.mean(probabilities)),median_fraction=float(np.mean(medians))))
    return dict(status='diagnostic' if invalid==0 else 'undefined_splits_do_not_use_as_gate',
                pbo_strict=float(np.mean([s['below_fraction'] for s in splits])) if splits else None,
                median_mass=float(np.mean([s['median_fraction'] for s in splits])) if splits else None,
                valid_splits=len(splits),invalid_splits=invalid,explicit_tail_rows_trimmed=trim,blocks=blocks,
                note='Relative selection diagnostic on development only; overlapping splits are dependent, not independent trials.',splits=splits)
