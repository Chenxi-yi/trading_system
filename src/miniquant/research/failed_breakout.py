"""Frozen completed-bar failed-range-break events; no order-flow causality claimed."""
from bisect import bisect_right
import math
from miniquant.backtest.replay import aggregate,DAY,HOUR


def failed_breakout_events(bars,range_days,start_ms):
    if range_days not in (20,60):raise ValueError('Unregistered range horizon')
    if any(b['ts']-a['ts']!=4*HOUR for a,b in zip(bars,bars[1:])):raise ValueError('Input gaps/duplicates')
    for b in bars:
        if not all(math.isfinite(b[k]) and b[k]>0 for k in ('o','h','l','c')) or not math.isfinite(b['v']) or b['v']<0:raise ValueError('Invalid market input')
    daily=aggregate(bars,DAY,base_interval=4*HOUR);ends=[r['end'] for r in daily]
    result=[];watch=None;last=None
    for i,b in enumerate(bars):
        signal=b['ts']+4*HOUR
        if i==0 or signal<start_ms:continue
        if watch is not None:
            age=(signal-watch['break_signal_ms'])//(4*HOUR)
            if 1<=age<=3 and b['v']>0 and watch['lower']<=b['c']<=watch['upper']:
                if last is None or signal-last>=96*HOUR:
                    result.append(dict(watch,signal_ms=signal,bar_ts=b['ts'],confirmation_close=b['c'],wait_bars=age,reversion_direction=-watch['break_direction']))
                    last=signal
                watch=None
                continue
            if age>=3:watch=None
            else:continue
        n=bisect_right(ends,b['ts']//DAY*DAY)
        if n<range_days or b['v']<=0:continue
        prior=daily[n-range_days:n];lower=min(r['l'] for r in prior);upper=max(r['h'] for r in prior)
        previous=bars[i-1]['c']
        if not lower<=previous<=upper:continue
        direction=1 if b['c']>upper else -1 if b['c']<lower else 0
        if direction:watch=dict(break_signal_ms=signal,break_direction=direction,lower=lower,upper=upper,range_last_day_end=prior[-1]['end'])
    return result


class FailedBreakoutTarget:
    def __init__(self,events,mode,hold_hours,start_ms):
        if mode not in ('reversion','continuation') or hold_hours not in (24,72):raise ValueError('Unregistered target')
        self.events=[e for e in events if e['signal_ms']>=start_ms];self.times=[e['signal_ms'] for e in self.events]
        self.mode=mode;self.hold=hold_hours*HOUR;self.log=[]
    def __call__(self,time,unused_weight):
        i=bisect_right(self.times,time)-1;event=self.events[i] if i>=0 else None
        active=event is not None and time<event['signal_ms']+self.hold
        target=.5*event['reversion_direction']*(1 if self.mode=='reversion' else -1) if active else 0.0
        self.log.append(dict(decision_ms=time,target=target,event_signal_ms=event['signal_ms'] if active else None))
        return target
