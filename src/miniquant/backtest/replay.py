"""Causal spot replay on hourly bars. Features consume completed bars only.

No account/API operations. Grid uses independent finite-budget cells, at most
one fill per cell/hour and strict penetration. This is an execution assumption,
not proof of real limit-order fills.
"""
from dataclasses import dataclass
import math
from statistics import mean,stdev
from miniquant.accounting.spot import SpotAccount

HOUR=3600000
DAY=24*HOUR


def aggregate(bars,period):
    groups={}
    for b in bars:groups.setdefault(b['ts']//period*period,[]).append(b)
    out=[]
    for ts,rows in sorted(groups.items()):
        if len(rows)!=period//HOUR or rows[0]['ts']!=ts or any(b['ts']-a['ts']!=HOUR for a,b in zip(rows,rows[1:])):continue
        out.append(dict(ts=ts,end=ts+period,o=rows[0]['o'],h=max(x['h'] for x in rows),l=min(x['l'] for x in rows),c=rows[-1]['c']))
    return out


def true_range_atr(rows,n=14):
    if len(rows)<n+1:return None
    return mean(max(rows[j]['h']-rows[j]['l'],abs(rows[j]['h']-rows[j-1]['c']),abs(rows[j]['l']-rows[j-1]['c'])) for j in range(len(rows)-n,len(rows)))


@dataclass
class ReplayResult:
    daily: list
    fills: list
    fees: float
    turnover: float
    final_nav: float
    exposure_hours: float
    total_hours: int
    assumptions: dict


def replay(bars,family,param,start,end,fee_bps=10,slip_bps=5,initial=10000,liquidate=True):
    if family not in ('trend','reversion','constant_mix','grid','hold','cash'):raise ValueError('Unsupported spot family')
    if not bars or any(b['ts']-a['ts']!=HOUR for a,b in zip(bars,bars[1:])):raise ValueError('Hourly input gaps or duplicates')
    for b in bars:
        if b['ts']%HOUR or not all(math.isfinite(b[k]) and b[k]>0 for k in ('o','h','l','c')) or b['l']>min(b['o'],b['c']) or b['h']<max(b['o'],b['c']):raise ValueError('Invalid hourly bar')
    if start%DAY or end%DAY or end<=start:raise ValueError('Evaluation requires full UTC days')
    if bars[0]['ts']>start or bars[-1]['ts']+HOUR<end:raise ValueError('Evaluation window not covered')
    daily_bars=aggregate(bars,DAY);four_bars=aggregate(bars,4*HOUR)
    d_index=q_index=0;d=[];q=[]
    account=SpotAccount(initial,fee_rate=fee_bps/10000,slippage=slip_bps/10000)
    pending=None;stop=None;entry=None
    cells=[];grid_bounds=None;grid_reset=None
    result_daily=[];exposure=0.0;hours=0
    last_bar=None
    for b in bars:
        ts=b['ts'];close_time=ts+HOUR
        if ts>=end:break
        # Histories at the hourly OPEN contain only bars already closed by it.
        while d_index<len(daily_bars) and daily_bars[d_index]['end']<=ts:d.append(daily_bars[d_index]);d_index+=1
        while q_index<len(four_bars) and four_bars[q_index]['end']<=ts:q.append(four_bars[q_index]);q_index+=1
        if ts<start:continue
        last_bar=b;hours+=1;did_reset=False
        if pending is not None and pending['execute_at']<=ts:
            action=pending;pending=None
            if action['kind']=='target':
                before=account.quantity
                account.target(action['weight'],b['o'],ts,action['reason'])
                if before<account.minimum and account.quantity>=account.minimum:
                    entry=ts
                    stop=b['o']*(1+account.slippage)-action['stop_distance'] if action.get('stop_distance') else None
                if account.quantity<account.minimum:stop=None;entry=None
            elif action['kind']=='reset_grid':
                did_reset=True
                if account.quantity>=account.minimum:account.sell(account.quantity,b['o'],ts,'grid_reset')
                cells=[]
                anchor=action['anchor'];lo=anchor*0.8;hi=anchor*1.2
                levels=[lo*(hi/lo)**(j/param) for j in range(param+1)]
                budget=account.cash*0.95/param
                for j in range(param):
                    cell=dict(cash=budget,quantity=0.0,buy=levels[j],sell=levels[j+1])
                    if levels[j]>=b['o']:
                        before_cash=account.cash
                        cell['quantity']=account.buy(budget,b['o'],ts,'grid_initial')
                        cell['cash']-=before_cash-account.cash
                    cells.append(cell)
                grid_bounds=(lo,hi);grid_reset=ts+30*DAY
        # Protective stop is set at market entry, not estimated using future ATR.
        if stop is not None and account.quantity>=account.minimum and b['l']<=stop:
            price=min(b['o'],stop)
            account.sell(account.quantity,price,ts,'protective_stop')
            stop=None;entry=None
        if family=='grid' and cells and not did_reset and not(pending and pending['kind']=='reset_grid'):
            for cell in cells:
                # One prior-side fill per hour. Replenishment becomes eligible next hour.
                held=cell['quantity']>=account.minimum
                if held and b['h']>cell['sell']*1.0002:
                    before=account.cash
                    sold=account.sell(cell['quantity'],cell['sell'],ts,'grid_limit_sell',limit=True)
                    cell['quantity']-=sold;cell['cash']+=account.cash-before
                elif not held and b['l']<cell['buy']*0.9998:
                    before=account.cash
                    bought=account.buy(cell['cash'],cell['buy'],ts,'grid_limit_buy',limit=True)
                    cell['quantity']+=bought;cell['cash']-=before-account.cash
        nav=account.nav(b['c']);account.check()
        exposure+=account.quantity*b['c']/nav if nav>0 else 0
        if close_time%DAY==0:result_daily.append(dict(ts=close_time,nav=nav))
        # Append the just-completed aggregate before computing its close signal.
        while d_index<len(daily_bars) and daily_bars[d_index]['end']<=close_time:d.append(daily_bars[d_index]);d_index+=1
        while q_index<len(four_bars) and four_bars[q_index]['end']<=close_time:q.append(four_bars[q_index]);q_index+=1
        signal=None
        if family=='hold' and account.quantity<account.minimum and pending is None:
            signal=dict(kind='target',weight=0.95,reason='hold_entry')
        if family=='trend' and close_time%DAY==0 and len(d)>param:
            direction=d[-1]['c']>d[-1-param]['c'];held=account.quantity>=account.minimum
            if direction!=held:signal=dict(kind='target',weight=0.95 if direction else 0.0,reason='trend_signal')
        if family=='constant_mix' and close_time%DAY==0:
            weight=account.quantity*b['c']/nav
            if abs(weight-param)>0.05:signal=dict(kind='target',weight=param,reason='constant_mix')
        if family=='reversion' and close_time%(4*HOUR)==0 and len(q)>max(param,14):
            prior=[math.log(x['c']) for x in q[-param-1:-1]]
            sigma=stdev(prior);z=(math.log(q[-1]['c'])-mean(prior))/sigma if sigma>0 else None
            held=account.quantity>=account.minimum
            if held and (z is not None and z>=0 or entry is not None and close_time-entry>=12*4*HOUR):
                signal=dict(kind='target',weight=0.0,reason='reversion_exit')
            elif not held and z is not None and z<=-1.5:
                atr=true_range_atr(q[:-1],14)
                if atr is not None:signal=dict(kind='target',weight=0.5,reason='reversion_entry',stop_distance=2*atr)
        if family=='grid' and close_time%DAY==0 and len(d)>=20:
            reset=not cells or close_time>=grid_reset or b['c']<grid_bounds[0] or b['c']>grid_bounds[1]
            if reset:signal=dict(kind='reset_grid',anchor=mean(x['c'] for x in d[-20:]))
        if signal is not None:
            signal['decision_at']=close_time;signal['execute_at']=close_time+HOUR
            pending=signal
    if last_bar is None:raise ValueError('Empty evaluation')
    if liquidate and account.quantity>=account.minimum:
        account.sell(account.quantity,last_bar['c'],end,'scheduled_terminal_liquidation')
    final=account.nav(last_bar['c'])
    if result_daily:result_daily[-1]['nav']=final
    if len(result_daily)!=(end-start)//DAY:raise ValueError('Daily valuation coverage mismatch')
    return ReplayResult(result_daily,account.fills,account.fees,account.turnover,final,exposure,hours,
                        dict(fee_bps=fee_bps,slip_bps=slip_bps,execution_lag_hours=1,grid_limit_penetration_bps=2,
                             grid_limit_fill_model='at most one fill per cell/hour; fills assumed on strict penetration; sensitivity required',
                             risk='finite cash/inventory; venue order lifecycle not implemented',historical_product_rules='current snapshot assumption'))
