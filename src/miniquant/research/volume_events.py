"""Preregistered volume-conditioned downside event diagnostics, not strategies."""
import math
from statistics import median,stdev
import numpy as np
from miniquant.backtest.replay import HOUR,DAY


def detect_events(rows,start_ms):
    if any(b['ts']-a['ts']!=4*HOUR for a,b in zip(rows,rows[1:])):
        raise ValueError('Event input must be continuous4H')
    for b in rows:
        if not math.isfinite(b['c']) or b['c']<=0 or not math.isfinite(b['v']) or b['v']<0:
            raise ValueError('Invalid event price/volume')
    events=[];last_signal=None
    for i in range(336,len(rows)):
        b=rows[i];signal=b['ts']+4*HOUR
        if signal<start_ms:continue
        returns=[math.log(rows[j]['c']/rows[j-1]['c']) for j in range(i-30,i)]
        sigma=max(stdev(returns),1e-4)
        shock=math.log(b['c']/rows[i-1]['c'])
        if shock> -1.5*sigma or b['v']<=0:continue
        normal=median(rows[i-42*k]['v'] for k in range(1,9))
        if normal<=0:continue
        if last_signal is not None and signal-last_signal<72*HOUR:continue
        ratio=b['v']/normal
        group='low' if ratio<.75 else 'normal' if ratio<1.5 else 'high'
        events.append(dict(signal_ms=signal,bar_ts=b['ts'],shock_log_return=shock,prior_sigma=sigma,volume=b['v'],past_same_weekday_slot_volume=normal,volume_ratio=ratio,volume_group=group))
        last_signal=signal
    return events


def label_events(events,hourly,horizons=(24,72)):
    bytime={b['ts']:b for b in hourly};result=[]
    for event in events:
        labels={}
        entry_time=event['signal_ms']+HOUR
        for h in horizons:
            exit_time=entry_time+h*HOUR
            a,b=bytime.get(entry_time),bytime.get(exit_time)
            if a is None or b is None:
                labels[str(h)]=dict(status='future_or_input_unavailable');continue
            if a['v']<=0 or b['v']<=0:
                labels[str(h)]=dict(status='no_demonstrated_execution_volume');continue
            if min(a['o'],b['o'])<=0:raise ValueError('Invalid scheduled price')
            def net(fee,slip):return b['o']*(1-slip)/(a['o']*(1+slip))*(1-fee)**2-1
            labels[str(h)]=dict(status='labeled',entry_ms=entry_time,exit_ms=exit_time,gross_return=b['o']/a['o']-1,base_net=net(.001,.0005),stress_net=net(.002,.001))
        result.append(dict(event,labels=labels))
    return result


def calendar_joint_bootstrap(events,start_ms,end_ms,block_lengths=(14,30),replicates=2000,seed=20261021):
    cells=[(g,h) for g in ('low','normal','high') for h in (24,72)]
    n=(end_ms-start_ms+DAY-1)//DAY
    if n<30:raise ValueError('Insufficient calendar coverage')
    sums=np.zeros((n,6));counts=np.zeros((n,6))
    for event in events:
        day=(event['signal_ms']-start_ms)//DAY
        if not 0<=day<n:raise ValueError('Event outside declared calendar')
        for j,(group,h) in enumerate(cells):
            label=event['labels'][str(h)]
            if event['volume_group']==group and label['status']=='labeled':
                sums[day,j]+=label['base_net'];counts[day,j]+=1
    total=counts.sum(axis=0);observed=np.divide(sums.sum(axis=0),total,out=np.full(6,np.nan),where=total>0)
    rng=np.random.default_rng(seed);output={}
    for length in block_lengths:
        draws=np.full((replicates,6),np.nan)
        for first in range(0,replicates,50):
            size=min(50,replicates-first)
            starts=rng.integers(0,n,size=(size,math.ceil(n/length)))
            idx=(starts[:,:,None]+np.arange(length))%n
            idx=idx.reshape(size,-1)[:,:n]
            numer=sums[idx].sum(axis=1);denom=counts[idx].sum(axis=1)
            draws[first:first+size]=np.divide(numer,denom,out=np.full_like(numer,np.nan),where=denom>0)
        valid=draws[np.isfinite(draws).all(axis=1)]
        if len(valid)<int(.95*replicates):
            output[str(length)]=dict(status='too_many_empty_resamples',valid_joint_resamples=len(valid));continue
        se=valid.std(axis=0,ddof=1)
        maxdev=np.max(abs((valid-observed)/np.maximum(se,1e-12)),axis=1)
        cutoff=float(np.quantile(maxdev,.95))
        bands={}
        for j,(group,h) in enumerate(cells):
            bands[group+'_'+str(h)]=dict(events=int(total[j]),observed_mean=float(observed[j]),minimum30_met=bool(total[j]>=30),pointwise_lower5=float(np.quantile(valid[:,j],.05)),pointwise_upper95=float(np.quantile(valid[:,j],.95)),simultaneous_lower=float(observed[j]-cutoff*se[j]),simultaneous_upper=float(observed[j]+cutoff*se[j]))
        difference=valid[:,4]-valid[:,2]
        output[str(length)]=dict(status='exploratory_diagnostic',valid_joint_resamples=len(valid),cells=bands,primary_high_minus_normal24=dict(observed=float(observed[4]-observed[2]),lower5=float(np.quantile(difference,.05)),upper95=float(np.quantile(difference,.95))),note='Calendar blocks preserve some event dependence. Joint max-deviation bands are approximate, conditional on frozen6cells; no protection against earlier adaptive hypothesis discovery or all regime changes.')
    return output
