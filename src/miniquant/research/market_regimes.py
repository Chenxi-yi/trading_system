"""Observable states, never hindsight labels or smoothed latent regimes."""
from bisect import bisect_right
import math
from statistics import stdev
import numpy as np
DAY=86400000


def observable_states(daily, threshold=.35, confirmation=3):
    if not .0 < threshold < 1 or type(confirmation) is not int or confirmation<1:
        raise ValueError('Invalid state rule')
    if any(b['end']-a['end']!=DAY for a,b in zip(daily,daily[1:])):
        raise ValueError('Daily gaps or duplicates')
    if any(x['end']%DAY or not math.isfinite(x['c']) or x['c']<=0 for x in daily):
        raise ValueError('Invalid daily data')
    closes=[];returns=[];vols=[];out=[];last_raw=None;count=0;active='unknown'
    for row in daily:
        if closes:returns.append(math.log(row['c']/closes[-1]))
        closes.append(row['c'])
        vol=stdev(returns[-20:])*math.sqrt(365) if len(returns)>=20 else None
        prior=[v for v in vols[-365:] if v is not None]
        cutoff=float(np.quantile(prior,.75)) if len(prior)>=180 else None
        vols.append(vol)
        raw='unknown';eff=None
        if len(returns)>=60 and cutoff is not None:
            change=sum(returns[-60:]);path=sum(abs(x) for x in returns[-60:]);eff=abs(change)/path if path else 0.
            direction=('up' if change>0 else 'down') if eff>=threshold and change!=0 else 'range'
            raw=direction+('_high' if vol>cutoff else '_normal')
        if raw==last_raw:count+=1
        else:last_raw=raw;count=1
        if raw=='unknown':active='unknown'
        elif count>=confirmation:active=raw
        out.append(dict(available_at=row['end'],state=active,raw_state=raw,efficiency=eff,volatility=vol,prior_vol_q75=cutoff))
    return out


def state_asof(states,timestamp):
    i=bisect_right([x['available_at'] for x in states],timestamp)-1
    return states[i] if i>=0 else dict(available_at=None,state='unknown',volatility=None)


def conditional_attribution(daily,states,initial=10000):
    names=[d+'_'+v for d in ('up','range','down') for v in ('normal','high')]+['unknown']
    grouped={k:[] for k in names};previous=initial
    for row in daily:
        r=row['nav']/previous-1;previous=row['nav']
        if not math.isfinite(r):raise ValueError('Nonfinite return')
        grouped[state_asof(states,row['ts']-DAY)['state']].append(r)
    return {k:dict(days=len(v),mean_daily=float(np.mean(v)) if v else None,rms_daily=float(np.sqrt(np.mean(np.square(v)))) if v else None,worst_daily=min(v) if v else None,sum_daily_returns=sum(v),minimum60_days_met=len(v)>=60) for k,v in grouped.items()}
