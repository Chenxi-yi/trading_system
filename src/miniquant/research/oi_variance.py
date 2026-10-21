"""Fixed prospective risk-information test. Predictions are not strategy PnL."""
import math
import numpy as np
from miniquant.data.asof_snapshots import milliseconds, unique
from miniquant.data.okx_public import DataError

BUCKET=900_000
EPSILON=1e-12


def rv(prices):
    if len(prices)!=17 or min(prices)<=0 or not all(math.isfinite(p) for p in prices):raise DataError('RV needs17 finite positive price points')
    result=sum(math.log(b/a)**2 for a,b in zip(prices,prices[1:]))
    if not math.isfinite(result):raise DataError('Nonfinite RV')
    return result


def samples(joined, books, start_ms):
    points={}
    for row in sorted(joined,key=lambda r:milliseconds(r['decision_at'])):
        at=milliseconds(row['decision_at'])
        if not row['eligible'] or at<start_ms:continue
        if not start_ms<=milliseconds(row['oi_available_at'])<=at:continue
        if float(row['oi_contract_count'])<=0 or float(row['mid'])<=0:continue
        points.setdefault(at//BUCKET,row)
    price={}
    for at,book in unique(books,'books'):
        if at<start_ms or at-milliseconds(book['event_time'])>30_000:continue
        bid=float(book['values']['bids'][0][0]);ask=float(book['values']['asks'][0][0])
        if not 0<bid<=ask:raise DataError('Invalid label book')
        price.setdefault(at//BUCKET,(at,(bid+ask)/2))
    result=[]
    for end in sorted(points):
        if end%16 or not all(i in points for i in range(end-16,end+1)):continue
        past=[points[i] for i in range(end-16,end+1)]
        at=milliseconds(past[-1]['decision_at'])
        elapsed=at-milliseconds(past[0]['decision_at'])
        if not 13_500_000<=elapsed<=15_300_000:continue
        values=[float(p['mid']) for p in past]
        contraction=max(1-float(past[-1]['oi_contract_count'])/float(past[0]['oi_contract_count']),0)
        item=dict(feature_at_ms=at,past_rv=rv(values),contraction=contraction,
                  label_available_ms=None,next_rv=None)
        if all(i in price for i in range(end+1,end+17)):
            future=[price[i] for i in range(end+1,end+17)]
            if 13_500_000<=future[-1][0]-at<=15_300_000 and future[0][0]>at:
                item.update(label_available_ms=future[-1][0],next_rv=rv([values[-1]]+[p[1] for p in future]))
        result.append(item)
    return result


def predict(rows, point, decision_ms, minimum_training=120):
    if point['feature_at_ms']>decision_ms:raise DataError('Future forecast features')
    fit_at=decision_ms//86_400_000*86_400_000
    training=[r for r in rows if r['label_available_ms'] is not None and
        r['label_available_ms']<fit_at and r['feature_at_ms']<fit_at]
    if len(training)<minimum_training:return None
    target=np.array([math.log(r['next_rv']+EPSILON) for r in training])
    forecasts={}
    for name,extra in [('B0',False),('M1',True)]:
        def x(r):return [1,math.log(r['past_rv']+EPSILON)]+([r['contraction']] if extra else [])
        design=np.array([x(r) for r in training],dtype=float)
        if not np.isfinite(design).all() or not np.isfinite(target).all():raise DataError('Nonfinite fit data')
        coefficients,_,rank,_=np.linalg.lstsq(design,target,rcond=None)
        if rank!=design.shape[1]:raise DataError('Rank deficient forecast fit')
        with np.errstate(over='raise',invalid='raise'):
            smear=float(np.mean(np.exp(target-design@coefficients)))
            forecast=math.exp(float(np.array(x(point))@coefficients))*smear
        if not math.isfinite(forecast) or forecast<=0:raise DataError('Invalid variance forecast')
        forecasts[name]=forecast
    return dict(fit_at_ms=fit_at,training_samples=len(training),forecasts=forecasts)
