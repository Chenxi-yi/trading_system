"""One real cash/inventory ledger routes causal expert intents, not return slices."""
from bisect import bisect_right
import math
from statistics import mean,stdev
from miniquant.backtest.replay import HOUR,DAY,aggregate,true_range_atr
from miniquant.accounting.spot import SpotAccount
from miniquant.research.market_regimes import observable_states


def expert_signals(bars,threshold=.35):
    if not bars or any(b['ts']-a['ts']!=HOUR for a,b in zip(bars,bars[1:])):
        raise ValueError('Hourly gaps/duplicates')
    for b in bars:
        if b['ts']%HOUR or any(not math.isfinite(b[k]) or b[k]<=0 for k in ('o','h','l','c')) or not math.isfinite(b['v']) or b['v']<0 or b['h']<max(b['o'],b['c']) or b['l']>min(b['o'],b['c']):raise ValueError('Invalid hourly bar')
    daily=aggregate(bars,DAY);four=aggregate(bars,4*HOUR);states=observable_states(daily,threshold);ends=[x['end'] for x in daily]
    out=[];held=False;entered=None;stop=None
    for i,row in enumerate(four):
        when=row['end'];j=bisect_right(ends,when)-1
        if j<0:continue
        state=states[j];trend=0.;risk=0.;z=None
        if j>=120 and state['volatility'] is not None:
            risk=min(.75,.20/max(state['volatility'],1e-8))
            trend=max(0.,mean(1 if daily[j]['c']>daily[j-h]['c'] else -1 if daily[j]['c']<daily[j-h]['c'] else 0 for h in (20,60,120)))*risk
        if i>=180:
            prior=[math.log(x['c']) for x in four[i-180:i]];sigma=stdev(prior)
            z=(math.log(row['c'])-mean(prior))/sigma if sigma>0 else None
            if held and (z is not None and z>=0 or when-entered>=48*HOUR or row['c']<=stop):held=False;entered=None;stop=None
            elif not held and z is not None and z<=-1.5:
                atr=true_range_atr(four[:i],14)
                if atr is not None:held=True;entered=when;stop=row['c']-2*atr
        out.append(dict(decision_at=when,state=state['state'],state_available_at=state['available_at'],risk=risk,trend=trend,reversion=(.5*risk/.75 if held else 0.),z=z))
    return out


def target_for(signal,policy):
    if signal['state']=='unknown':return 0.
    if policy=='trend_only':return signal['trend']
    if policy=='reversion_only':return signal['reversion']
    if policy=='equal_mix':return .5*(signal['trend']+signal['reversion'])
    if policy=='vol_only':return signal['risk']
    if policy=='router':
        return signal['trend'] if signal['state'].startswith('up_') else signal['reversion'] if signal['state'].startswith('range_') else 0.
    raise ValueError('Unknown policy')


def replay_router(bars,signals,policy,start,end,fee_bps=10,slip_bps=5,lag_hours=1):
    if type(lag_hours) is not int or not 1<=lag_hours<=12 or start%DAY or end%DAY or start>=end:raise ValueError('Invalid clock')
    if not bars or bars[0]['ts']>start or bars[-1]['ts']+HOUR<end:raise ValueError('Missing coverage')
    if any(b['decision_at']<=a['decision_at'] for a,b in zip(signals,signals[1:])):raise ValueError('Signal order')
    for s in signals:
        if s['state_available_at']>s['decision_at']:raise ValueError('Future state')
        if not all(math.isfinite(s[k]) and 0<=s[k]<=.75 for k in ('risk','trend','reversion')):raise ValueError('Invalid expert target')
    account=SpotAccount(10000,fee_rate=fee_bps/10000,slippage=slip_bps/10000);lookup={x['decision_at']:x for x in signals}
    daily=[];decisions=[];snapshots=[];pending=None;expired=0;last=None
    for bar in bars:
        ts=bar['ts'];close=ts+HOUR
        if ts<start:continue
        if ts>=end:break
        last=bar
        if pending and ts>pending['expires_at']:pending=None;expired+=1
        if pending and ts>=pending['execute_at'] and bar['v']>0:
            account.target(pending['weight'],bar['o'],ts,pending['reason']);pending=None
        nav=account.nav(bar['c']);account.check()
        if close%DAY==0:daily.append(dict(ts=close,nav=nav))
        if close in lookup:
            s=lookup[close];weight=target_for(s,policy)
            if abs(account.quantity*bar['c']/nav-weight)>.05 and pending is None:
                pending=dict(decision_at=close,execute_at=close+lag_hours*HOUR,expires_at=close+12*HOUR,weight=weight,reason=policy+':'+s['state'])
                decisions.append(dict(pending))
            snapshots.append(dict(ts=close,cash=account.cash,quantity=account.quantity,mark=bar['c'],nav=nav,state=s['state'],desired_weight=weight))
    if last is None or len(daily)!=(end-start)//DAY:raise ValueError('Daily coverage mismatch')
    if last['v']>0 and account.quantity>=account.minimum:account.sell(account.quantity,last['c'],end,'scheduled_terminal_liquidation')
    daily[-1]['nav']=account.nav(last['c'])
    return dict(daily=daily,fills=account.fills,fees=account.fees,turnover=account.turnover,decisions=decisions,snapshots=snapshots,expired_intents=expired,remaining_inventory=account.quantity,research_qualified=False,demo_ready=False)
