"""Frozen descriptive matching; future labels never participate in donor choice."""
import math
from statistics import median,stdev
from miniquant.backtest.replay import HOUR,DAY


def features(rows,events):
    index={b['ts']:i for i,b in enumerate(rows)}
    result=[]
    for event in events:
        i=index[event['bar_ts']]
        if i<181:raise ValueError('Insufficient prior state')
        sigma=max(stdev(math.log(rows[j]['c']/rows[j-1]['c']) for j in range(i-30,i)),1e-4)
        trend=math.log(rows[i-1]['c']/rows[i-181]['c'])/(sigma*math.sqrt(180))
        result.append(dict(event,severity=-event['shock_log_return']/sigma,sigma=sigma,trend_z=trend))
    return result


def ordinary_events(rows,start_ms):
    result=[];last=None
    for i in range(336,len(rows)):
        b=rows[i];signal=b['ts']+4*HOUR
        if signal<start_ms or b['v']<=0:continue
        sigma=max(stdev(math.log(rows[j]['c']/rows[j-1]['c']) for j in range(i-30,i)),1e-4)
        shock=math.log(b['c']/rows[i-1]['c'])
        normal=median(rows[i-42*k]['v'] for k in range(1,9))
        if normal<=0 or not .75<=b['v']/normal<1.5 or not -1.5*sigma<shock<=-.5*sigma:continue
        if last is not None and signal-last<72*HOUR:continue
        result.append(dict(signal_ms=signal,bar_ts=b['ts'],shock_log_return=shock,volume_ratio=b['v']/normal,volume_group='ordinary'))
        last=signal
    return result


def match_events(treated,donors,severity_match=True):
    output=[]
    for event in treated:
        choices=[]
        for donor in donors:
            age=event['signal_ms']-donor['signal_ms']
            if not 73*HOUR<=age<=365*DAY:continue
            vol=abs(math.log(event['sigma']/donor['sigma']))/math.log(2)
            trend=abs(event['trend_z']-donor['trend_z'])
            severity=abs(event['severity']-donor['severity'])/.5
            if vol>1 or trend>1 or (event['trend_z']>=0)!=(donor['trend_z']>=0):continue
            if severity_match and severity>1:continue
            distance=vol+trend+(severity if severity_match else 0)
            choices.append((distance,-donor['signal_ms'],donor))
        if not choices:output.append(dict(treated_ms=event['signal_ms'],status='unmatched'));continue
        distance,_,donor=min(choices,key=lambda x:(x[0],x[1]))
        output.append(dict(treated_ms=event['signal_ms'],donor_ms=donor['signal_ms'],distance=distance,status='matched',severity_gap=event['severity']-donor['severity'],trend_z_gap=event['trend_z']-donor['trend_z'],log_sigma_ratio=math.log(event['sigma']/donor['sigma'])))
    return output
