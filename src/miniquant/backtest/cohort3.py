"""Daily multi-horizon target on actual 4H perpetual prices/mark and funding.

Research-only: synthetic margin stress is not certified exchange liquidation.
"""
from bisect import bisect_right
import math
from statistics import mean,stdev
from miniquant.accounting.sized_perpetual import SizedPerpAccount
from miniquant.backtest.replay import aggregate,HOUR,DAY


def signed_weight(closes,param):
    horizons=param['horizons']
    if len(closes)<=max([20]+horizons):return None
    score=1 if param.get('passive') else mean(1 if closes[-1]>closes[-1-h] else -1 if closes[-1]<closes[-1-h] else 0 for h in horizons)
    if param.get('long_only'):score=max(0,score)
    risk=.75
    if param['risk_mode']=='vol_scaled':
        returns=[math.log(y/x) for x,y in zip(closes[-21:-1],closes[-20:])]
        risk=min(.75,.20/max(stdev(returns)*math.sqrt(365),1e-8))
    elif param['risk_mode']!='fixed':raise ValueError('Unknown risk mode')
    return score*risk


def replay_cohort3(bars,marks,funding,param,start,end,fee_bps=5,slip_bps=5,lag_hours=4):
    step=4*HOUR
    if lag_hours not in (4,8) or start%DAY or end%DAY or end<=start:raise ValueError('Invalid clock')
    for rows in (bars,marks):
        if not rows or any(b['ts']-a['ts']!=step for a,b in zip(rows,rows[1:])):raise ValueError('Input gaps/duplicates')
        for b in rows:
            if b['ts']%step or not all(math.isfinite(b[k]) and b[k]>0 for k in ('o','h','l','c')) or b['l']>min(b['o'],b['c']) or b['h']<max(b['o'],b['c']):raise ValueError('Invalid OHLC')
    if any('v' not in b or not math.isfinite(b['v']) or b['v']<0 for b in bars):raise ValueError('Unknown trade volume')
    active=[b for b in bars if start<=b['ts']<end]
    if len(active)!=(end-start)//step:raise ValueError('Trade coverage gap')
    bymark={b['ts']:b for b in marks}
    if any(b['ts'] not in bymark for b in active) or end not in bymark:raise ValueError('Mark boundary coverage gap')
    rates={}
    for f in funding:
        ts=f['event_time_ms'];r=float(f['realized_rate'])
        if ts in rates or not math.isfinite(r):raise ValueError('Invalid/duplicate funding')
        if start<=ts<=end and ts%(8*HOUR):raise ValueError('Off-grid settlement: declared8h schedule violated')
        rates[ts]=r
    if any(t not in rates for t in range(start,end+1,8*HOUR)):raise ValueError('Funding gap')
    days=aggregate(bars,DAY,base_interval=step);ends=[b['end'] for b in days]
    account=SizedPerpAccount(fee_rate=fee_bps/10000,slippage=slip_bps/10000)
    pending=None;daily=[];decisions=[];margin=[];halted=False;exposure=0.0
    for b in active:
        ts=b['ts'];close=ts+step;mark=bymark[ts]
        if ts in rates:account.funding(rates[ts],mark['o'],ts)
        if pending and ts>pending['expires_at']:pending=None
        if pending and pending['execute_at']<=ts and b['v']>0 and not halted:
            account.target(pending['weight'],b['o'],mark['o'],ts);pending=None
        if account.quantity:
            worst=mark['l'] if account.quantity>0 else mark['h']
            if account.equity(worst)<=.10*abs(account.quantity)*worst:
                margin.append(dict(ts=ts,executable=b['v']>0));halted=True;pending=None
                if b['v']>0:account.close(b['l'] if account.quantity>0 else b['h'],ts,'synthetic_margin_breach')
        if halted and account.quantity and b['v']>0:account.close(b['o'],ts,'delayed_stress_liquidation')
        nav=account.equity(mark['c'])
        if nav<=0:raise ArithmeticError('Insolvent research replay')
        exposure+=abs(account.quantity)*mark['c']/nav
        if close%DAY==0:
            daily.append(dict(ts=close,nav=nav))
            history=days[:bisect_right(ends,close)]
            target=signed_weight([d['c'] for d in history],param)
            actual=account.quantity*mark['c']/nav
            if target is not None and abs(target-actual)>.05 and pending is None and not halted:
                pending=dict(weight=target,decision_at=close,execute_at=close+lag_hours*HOUR,expires_at=close+12*HOUR)
                decisions.append(dict(pending))
    # Settlement happens before scheduled terminal liquidation at this boundary.
    if end in rates:account.funding(rates[end],bymark[end]['o'],end)
    last=active[-1]
    if last['v']>0:account.close(last['c'],end,'scheduled_terminal_liquidation')
    daily[-1]['nav']=account.equity(bymark[end]['o'])
    return dict(daily=daily,fills=account.fills,funding_events=account.funding_events,decisions=decisions,fees=account.fees,funding_pnl=account.funding_pnl,
                synthetic_margin_breaches=margin,mean_absolute_exposure=exposure/len(active),remaining_quantity=account.quantity,
                research_qualified=False,demo_ready=False,limitations=['Known adaptive historical exploration','Actual rates/time with4Hmark boundary estimate, not actual bills','Synthetic10%stress not OKX tier liquidation','4H executable quote/intrabar assumptions','Current contract step scenario','No real order adapter/account protection'])
