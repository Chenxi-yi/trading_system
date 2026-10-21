"""Historical pressure inputs: explicit assumed availability, never future settlement."""
from bisect import bisect_right
import math
from miniquant.backtest.replay import HOUR


def prepare_funding(records):
    result=[]
    for row in records:
        ts=row['event_time_ms'];rate=float(row['realized_rate'])
        if not isinstance(ts,int) or ts<0 or not math.isfinite(rate):raise ValueError('Invalid funding event')
        result.append((ts,rate))
    result.sort()
    if len({t for t,_ in result})!=len(result):raise ValueError('Duplicate funding settlement')
    return result


def lagged_funding(prepared,decision_ms,lag_ms=4*HOUR,max_age_ms=24*HOUR):
    if lag_ms<=0 or max_age_ms<lag_ms:raise ValueError('Invalid availability/age assumptions')
    i=bisect_right(prepared,(decision_ms-lag_ms,math.inf))-1
    if i<0:return dict(status='no_mature_settlement')
    event,rate=prepared[i]
    if decision_ms-event>max_age_ms:return dict(status='stale_settlement',event_time_ms=event)
    return dict(status='usable_under_assumption',event_time_ms=event,realized_rate=rate,available_at=None,
                assumed_available_ms=event+lag_ms,availability_basis='historical_publication_unknown; assumed settlement+lag, not observed',age_ms=decision_ms-event)


def synchronized_close_premium(trade,index):
    if trade['end_time_ms']!=index['end_time_ms'] or trade['open_time_ms']!=index['open_time_ms']:raise ValueError('Unsynchronized bar boundaries')
    if not trade['complete'] or not index['complete']:raise ValueError('Incomplete bar')
    a,b=float(trade['close']),float(index['close'])
    if not math.isfinite(a) or not math.isfinite(b) or min(a,b)<=0:raise ValueError('Invalid close')
    return dict(value=a/b-1,event_time_ms=trade['end_time_ms'],available_at=None,
                kind='trade_close_to_index_close_proxy',limitation='Not official impact-price premium index or executable simultaneous spread; historical publication times unknown')
