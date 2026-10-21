"""Preregistered pressure reductions on positive targets; no exchange access."""
from bisect import bisect_right,bisect_left
import math
import numpy as np
from miniquant.backtest.replay import DAY,HOUR
from miniquant.research.pressure_data import prepare_funding,lagged_funding,synchronized_close_premium


class PressureOverlay:
    def __init__(self,mode,funding,trade,index,lag_hours=4):
        if mode not in ('none','half_long','funding','premium','joint') or lag_hours not in (4,8):raise ValueError('Invalid pressure policy')
        self.mode=mode;self.lag=lag_hours*HOUR;self.log=[]
        self.funding=prepare_funding(funding);self.ft=[r[0] for r in self.funding]
        bytime={r['open_time_ms']:r for r in index}
        self.premium=[synchronized_close_premium(r,bytime[r['open_time_ms']]) for r in trade if r['complete'] and r['open_time_ms'] in bytime]
        self.pt=[r['event_time_ms'] for r in self.premium]
        if any(b-a!=4*HOUR for a,b in zip(self.pt,self.pt[1:])):raise ValueError('Premium input gaps/duplicates')

    def funding_pressure(self,decision):
        f=lagged_funding(self.funding,decision,lag_ms=self.lag)
        if f['status']!='usable_under_assumption':return dict(status=f['status'])
        current=f['event_time_ms'];i=bisect_left(self.ft,current);j=bisect_left(self.ft,current-90*DAY)
        values=[v for _,v in self.funding[j:i]]
        if len(values)<250:return dict(status='not_warmed')
        q=float(np.quantile(values,.9));value=f['realized_rate']
        return dict(status='usable',event_time_ms=current,value=value,threshold=q,crowded=value>max(0,q))

    def premium_pressure(self,decision):
        i=bisect_right(self.pt,decision-self.lag)-1
        if i<0:return dict(status='no_mature_premium')
        if decision-self.pt[i]>24*HOUR:return dict(status='stale_premium')
        if i<540:return dict(status='not_warmed')
        values=[r['value'] for r in self.premium[i-540:i]]
        q=float(np.quantile(values,.9));value=self.premium[i]['value']
        return dict(status='usable',event_time_ms=self.pt[i],value=value,threshold=q,crowded=value>max(0,q))

    def __call__(self,decision,target):
        if not math.isfinite(target):raise ValueError('Nonfinite target')
        state={};factor=1.0
        if target>0:
            if self.mode=='half_long':factor=.5
            elif self.mode!='none':
                if self.mode in ('funding','joint'):state['funding']=self.funding_pressure(decision)
                if self.mode in ('premium','joint'):state['premium']=self.premium_pressure(decision)
                if any(v['status']!='usable' for v in state.values()):factor=0.0
                elif all(v['crowded'] for v in state.values()):factor=.5
        result=target*factor
        self.log.append(dict(decision_ms=decision,base_target=target,target=result,factor=factor,features=state))
        return result
