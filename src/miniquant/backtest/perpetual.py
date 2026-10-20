"""4H BTC breakout research with realized funding and mark valuations.

Margin stress is synthetic, not a certified exchange liquidation implementation.
"""
import math
from statistics import mean
from miniquant.accounting.perpetual import LinearPerpAccount
from miniquant.backtest.replay import HOUR,DAY,true_range_atr


def replay_perpetual(bars,marks,funding,param,start,end,fee_bps=5,slip_bps=5):
    step=4*HOUR
    if start%DAY or end%DAY or end<=start:raise ValueError('Full days required')
    bymark={x['ts']:x for x in marks}
    settlements={x['event_time_ms']:float(x['realized_rate']) for x in funding}
    active=[x for x in bars if start<=x['ts']<end]
    if len(active)!=(end-start)//step or any(b['ts']-a['ts']!=step for a,b in zip(active,active[1:])):raise ValueError('Perpetual trade coverage gap')
    if any(x['ts'] not in bymark for x in active):raise ValueError('Mark coverage gap')
    # BTC sampled archive reports 8h events; do not replace missing funding by zero.
    expected=range((start+8*HOUR-1)//(8*HOUR)*8*HOUR,end+1,8*HOUR)
    if any(t not in settlements for t in expected):raise ValueError('Funding coverage gap under declared 8h schedule assumption')
    account=LinearPerpAccount(10000,fee_rate=fee_bps/10000,slippage=slip_bps/10000)
    history=[];pending=None;stop=None;entry=None;daily=[];margin_stress=[]
    exposure=0.0;count=0
    for b in bars:
        ts=b['ts'];close=ts+step
        if ts>=end:break
        if ts<start:history.append(b);continue
        mark=bymark[ts];count+=1
        if ts in settlements:account.settle_funding(settlements[ts],mark['o'],ts)
        if pending and pending['time']<=ts:
            direction,atr=pending['direction'],pending.get('atr');pending=None
            old=account.quantity;account.target(direction,b['o'],ts)
            if account.quantity and (not old or old*account.quantity<0):
                entry=ts;stop=account.entry-(3*atr)*(1 if account.quantity>0 else -1) if atr else None
            elif not account.quantity:stop=None;entry=None
        if account.quantity:
            worst=mark['l'] if account.quantity>0 else mark['h']
            if account.equity(worst)<=0.10*abs(account.quantity)*worst:
                margin_stress.append(ts)
                account.close(b['l'] if account.quantity>0 else b['h'],ts,'synthetic_margin_breach')
                stop=None;entry=None
        if account.quantity and stop is not None:
            if account.quantity>0 and b['l']<=stop:
                account.close(min(b['o'],stop),ts,'protective_stop');stop=None;entry=None
            elif account.quantity<0 and b['h']>=stop:
                account.close(max(b['o'],stop),ts,'protective_stop');stop=None;entry=None
        nav=account.equity(mark['c'])
        if nav<=0:raise ArithmeticError('Research account insolvent')
        exposure+=abs(account.quantity)*mark['c']/nav
        if close%DAY==0:daily.append(dict(ts=close,nav=nav))
        direction=1 if account.quantity>0 else -1 if account.quantity<0 else 0
        signal=None
        if direction and len(history)>=10:
            exit_level=min(x['l'] for x in history[-10:]) if direction>0 else max(x['h'] for x in history[-10:])
            if direction*(b['c']-exit_level)<0 or entry is not None and close-entry>=30*step:signal=0
        elif direction==0 and len(history)>=max(param,15):
            prior=history[-param:];hi=max(x['h'] for x in prior);lo=min(x['l'] for x in prior)
            if (hi-lo)/mean(x['c'] for x in prior)<=0.12:
                if b['c']>hi:signal=1
                elif b['c']<lo:signal=-1
        if signal is not None:pending=dict(time=close+step,direction=signal,atr=true_range_atr(history,14))
        history.append(b)
    last=active[-1]
    if end in settlements:account.settle_funding(settlements[end],bymark[last['ts']]['c'],end)
    account.close(last['c'],end,'scheduled_terminal_liquidation')
    daily[-1]['nav']=account.cash
    return dict(daily=daily,fills=account.fills,fees=account.fees,funding_pnl=account.funding_pnl,
                funding_events=account.funding_events,mean_exposure=exposure/count,synthetic_margin_breaches=margin_stress,
                demo_ready=False,limitations=['Synthetic margin stress, historical OKX tiers/mark trigger execution not certified','4H intra-bar path and executable quote assumptions','Historical publication times unknown','No order adapter or live account operations'])
