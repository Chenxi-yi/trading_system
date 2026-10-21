"""Second-cohort exploratory spot policies. No exchange/account API access.

Histories may be computed up front, but decisions query completed bars only.
The old cohort and its fingerprints/results are preserved unchanged.
"""
from bisect import bisect_right
import math
from statistics import mean, median, stdev
from miniquant.accounting.spot import SpotAccount
from miniquant.backtest.replay import aggregate, HOUR, DAY, true_range_atr


def trend_weight(closes, horizons, scale_vol=True):
    if len(closes) <= max(max(horizons), 20):
        return None
    score = mean(1 if closes[-1] > closes[-1-n] else -1 if closes[-1] < closes[-1-n] else 0 for n in horizons)
    risk = 0.75
    if scale_vol:
        r = [math.log(b/a) for a,b in zip(closes[-21:-1], closes[-20:])]
        vol = stdev(r)*math.sqrt(365)
        risk = min(0.75, 0.20/max(vol, 1e-8))
    return max(0, score)*risk


def pullback_entry(rows, daily, shock_sigma, volume_filter):
    if len(rows) < 34 or len(daily) < 120:
        return False
    if daily[-1]['c'] <= mean(b['c'] for b in daily[-120:]):
        return False
    # Exclude both the just-observed confirmation bar and prior shock bar.
    old = rows[-33:-2]
    old_returns = [math.log(b['c']/a['c']) for a,b in zip(old, old[1:])]
    shock = math.log(rows[-2]['c']/rows[-3]['c'])
    prior, current = rows[-2:]
    return (shock <= -shock_sigma*max(stdev(old_returns),1e-8)
            and current['c'] > prior['c'] and current['l'] >= prior['l']
            and (not volume_filter or current['v'] >= median(b['v'] for b in rows[-31:-1])))


def replay_cohort2(bars, family, parameters, start, end, fee_bps=10, slip_bps=5, lag_hours=1, liquidate=True):
    if family not in ('multiscale_trend','confirmed_pullback','cash','hold','vol_only','trend_unscaled'):
        raise ValueError('Unknown policy')
    if type(lag_hours) is not int or not 1 <= lag_hours <= 12 or start % DAY or end % DAY or end <= start:
        raise ValueError('Invalid clock')
    if not bars or bars[0]['ts'] > start or bars[-1]['ts']+HOUR < end:
        raise ValueError('Coverage missing')
    if any(b['ts']-a['ts'] != HOUR for a,b in zip(bars,bars[1:])):
        raise ValueError('Input gaps/duplicates')
    for b in bars:
        if b['ts']%HOUR or not all(math.isfinite(b[k]) and b[k]>0 for k in ('o','h','l','c')) or not math.isfinite(b['v']) or b['v']<0 or b['l']>min(b['o'],b['c']) or b['h']<max(b['o'],b['c']):
            raise ValueError('Invalid OHLC/volume')
    d = aggregate(bars,DAY); q = aggregate(bars,4*HOUR)
    volumes = {}
    for b in bars:
        key=b['ts']//(4*HOUR)*(4*HOUR)
        volumes[key]=volumes.get(key,0)+b['v']
    for b in q:b['v']=volumes[b['ts']]
    dt=[b['end'] for b in d];qt=[b['end'] for b in q]
    account=SpotAccount(10000,fee_rate=fee_bps/10000,slippage=slip_bps/10000)
    daily=[];decisions=[];pending=None;stop=None;entry=None;held_once=False;stale_dropped=0
    for b in bars:
        ts=b['ts'];close=ts+HOUR
        if ts<start:continue
        if ts>=end:break
        if pending and ts>pending['expires_at']:
            pending=None;stale_dropped+=1
        if pending and pending['execute_at']<=ts and b['v']>0:
            before=account.quantity
            account.target(pending['weight'],b['o'],ts,pending['reason'])
            if before<account.minimum and account.quantity>=account.minimum:
                entry=ts
                stop=b['o']*(1+account.slippage)-pending['stop_distance'] if pending.get('stop_distance') else None
            if account.quantity<account.minimum:entry=None;stop=None
            pending=None
        if stop is not None and account.quantity>=account.minimum and b['v']>0 and b['l']<=stop:
            account.sell(account.quantity,min(b['o'],stop),ts,'protective_stop');stop=None;entry=None
        nav=account.nav(b['c']);account.check()
        if close%DAY==0:daily.append(dict(ts=close,nav=nav))
        signal=None
        decision_bar=(family in ('multiscale_trend','trend_unscaled','vol_only') and close%DAY==0) or (family=='confirmed_pullback' and close%(4*HOUR)==0)
        dh=d[:bisect_right(dt,close)] if decision_bar else []
        qh=q[:bisect_right(qt,close)] if family=='confirmed_pullback' and decision_bar else []
        if family=='hold' and not held_once:
            signal=dict(weight=0.75,reason='hold');held_once=True
        elif family in ('multiscale_trend','trend_unscaled','vol_only') and close%DAY==0:
            if family=='vol_only' and len(dh)>20:
                closes=[x['c'] for x in dh];r=[math.log(y/x) for x,y in zip(closes[-21:-1],closes[-20:])]
                target=min(0.75,0.20/max(stdev(r)*math.sqrt(365),1e-8))
            else:
                target=trend_weight([x['c'] for x in dh],parameters.get('horizons',[20,60,120]),family!='trend_unscaled')
            if target is not None and abs(account.quantity*b['c']/nav-target)>0.05:
                signal=dict(weight=target,reason=family)
        elif family=='confirmed_pullback' and close%(4*HOUR)==0 and len(qh)>=34 and len(dh)>=120:
            held=account.quantity>=account.minimum
            if held and (qh[-1]['c']>=mean(x['c'] for x in qh[-21:-1]) or close-entry>=12*4*HOUR or dh[-1]['c']<=mean(x['c'] for x in dh[-120:])):
                signal=dict(weight=0,reason='pullback_exit')
            elif not held and pullback_entry(qh,dh,parameters['shock_sigma'],parameters['volume_filter']):
                signal=dict(weight=0.5,reason='confirmed_pullback',stop_distance=2*true_range_atr(qh[:-1],14))
        # First intent stays fixed until fill/expiry; repeated signals cannot postpone it.
        if signal is not None and pending is None:
            pending=dict(signal,decision_at=close,execute_at=close+lag_hours*HOUR,expires_at=close+12*HOUR)
            decisions.append(dict(pending))
    last=next(b for b in reversed(bars) if b['ts']<end)
    if liquidate and last['v']>0 and account.quantity>=account.minimum:
        account.sell(account.quantity,last['c'],end,'scheduled_terminal_liquidation')
    daily[-1]['nav']=account.nav(last['c'])
    if len(daily)!=(end-start)//DAY:raise ValueError('Daily coverage mismatch')
    return dict(daily=daily,fills=account.fills,fees=account.fees,turnover=account.turnover,decisions=decisions,
                expired_intents=stale_dropped,remaining_inventory=account.quantity,
                research_qualified=False,demo_ready=False,
                limitations=['Adaptive historical exploration, not independent OOS','Unknown publication times; modeled lag','OHLC volume>0 is necessary, not proof of executable depth','Current tick/min/lot scenario','No exchange execution or prospective evidence'])
