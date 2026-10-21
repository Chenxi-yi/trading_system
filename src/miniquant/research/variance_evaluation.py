"""End-gated, paired volatility information evaluation. No trading admission."""
import math
import numpy as np
from miniquant.data.okx_public import DataError

DAY=86_400_000
FOUR_HOURS=14_400_000
SEED=20261021


class EvaluationNotDue(DataError):pass


def planned_anchors(start,end):
    first=((start+FOUR_HOURS+FOUR_HOURS-1)//FOUR_HOURS)*FOUR_HOURS
    return list(range(first,end-FOUR_HOURS+1,FOUR_HOURS))


def qlike(forecast,observed):
    if not math.isfinite(forecast) or forecast<=0 or not math.isfinite(observed) or observed<0:
        raise DataError('Invalid variance score input')
    result=math.log(forecast)+observed/forecast
    if not math.isfinite(result):raise DataError('Nonfinite variance score')
    return result


def calendar_bootstrap(pairs,start,end,block_days,replications=10_000):
    first=start//DAY;days=(end-1)//DAY-first+1
    if not 1<=block_days<=days:raise DataError('Bootstrap block invalid')
    totals=np.zeros(days);counts=np.zeros(days)
    for at,gain in pairs:
        index=at//DAY-first
        if not 0<=index<days or not math.isfinite(gain):raise DataError('Bootstrap observation invalid')
        totals[index]+=gain;counts[index]+=1
    rng=np.random.default_rng(SEED);draws=[];invalid=0
    for _ in range(replications):
        starts=rng.integers(0,days-block_days+1,size=math.ceil(days/block_days))
        indices=np.concatenate([np.arange(s,s+block_days) for s in starts])[:days]
        weight=counts[indices].sum()
        if not weight:invalid+=1;continue
        draws.append(float(totals[indices].sum()/weight))
    interval=[float(v) for v in np.quantile(draws,[.025,.975])] if draws else None
    return dict(block_days=block_days,calendar_days=days,replications=replications,
                invalid_replicates=invalid,interval95=interval,seed=SEED)


def evaluate_when_due(loader,start,end,now):
    if now<end:raise EvaluationNotDue('Fixed evaluation window has not ended')
    rows,predictions=loader()
    return evaluate(rows,predictions,start,end)


def evaluate(rows,predictions,start,end):
    anchors=planned_anchors(start,end)
    if not anchors:raise DataError('Empty planned window')
    allowed=set(anchors);by_time={};covered=set()
    for row in rows:
        at=row['feature_at_ms'];anchor=at//FOUR_HOURS*FOUR_HOURS
        if anchor not in allowed or at-anchor>=900_000:continue
        if at in by_time:raise DataError('Duplicate evaluation sample')
        by_time[at]=row
        if row['label_available_ms'] is not None and row['label_available_ms']<=end:
            if row['label_available_ms']<=at:raise DataError('Invalid label receipt order')
            if not math.isfinite(row['next_rv']) or row['next_rv']<0:raise DataError('Invalid target RV')
            if anchor in covered:raise DataError('Multiple samples for one anchor')
            covered.add(anchor)
    first_fit=(anchors[0]+120*FOUR_HOURS)//DAY*DAY+DAY
    planned_predictions={a for a in anchors if a>=first_fit}
    pairs=[];forecast_covered=set();seen=set();log_mse=[]
    for prediction in predictions:
        at=prediction['feature_at_ms']
        if at in seen:raise DataError('Duplicate forecast')
        seen.add(at)
        if not 0<=prediction['generated_at_ms']-at<=120_000:raise DataError('Late or premature forecast')
        fit=at//DAY*DAY
        expected_training=sum(r['label_available_ms'] is not None and r['label_available_ms']<fit and r['feature_at_ms']<fit for r in rows)
        if prediction['fit_at_ms']!=fit or prediction['training_samples']!=expected_training or expected_training<120:
            raise DataError('Prediction training provenance invalid')
        row=by_time.get(at)
        if row is None or row['label_available_ms'] is None or row['label_available_ms']>end:continue
        y=row['next_rv'];b=prediction['forecasts']['B0'];m=prediction['forecasts']['M1']
        gain=qlike(b,y)-qlike(m,y)
        pairs.append((at,gain));forecast_covered.add(at//FOUR_HOURS*FOUR_HOURS)
        log_mse.append((math.log(b+1e-12)-math.log(y+1e-12))**2-(math.log(m+1e-12)-math.log(y+1e-12))**2)
    coverage=len(covered)/len(anchors)
    prediction_coverage=len(forecast_covered & planned_predictions)/len(planned_predictions) if planned_predictions else 0
    result=dict(status='inconclusive',planned_anchors=len(anchors),complete_anchors=len(covered),coverage=coverage,
        planned_forecast_anchors=len(planned_predictions),prediction_coverage=prediction_coverage,
        paired_predictions=len(pairs),trading_qualified=False,real_pnl_test=False)
    if len(pairs)<120 or coverage<.8 or prediction_coverage<.8:
        result['reason']='insufficient_fixed_window_coverage_or_pairs';return result
    pairs.sort()
    mean=float(np.mean([p[1] for p in pairs]))
    primary=calendar_bootstrap(pairs,start,end,2)
    sensitivities=[calendar_bootstrap(pairs,start,end,b) for b in (1,4)]
    midpoint=(start+end)//2
    halves=[]
    for low,high in ((start,midpoint),(midpoint,end)):
        subset=[gain for at,gain in pairs if low<=at<high]
        halves.append(dict(n=len(subset),mean_gain=float(np.mean(subset)) if subset else None))
    result.update(mean_qlike_gain=mean,primary=primary,descriptive_sensitivity=sensitivities,
        descriptive_log_mse_gain=float(np.mean(log_mse)),descriptive_halves=halves,
        coefficient_sign='not_available_coefficients_not_persisted_by024')
    if primary['invalid_replicates']:
        result['reason']='zero_weight_primary_bootstrap_replicate_no_redraw'
    else:
        result['status']='incremental_forecast_evidence' if mean>0 and primary['interval95'][0]>0 else 'not_supported'
    return result
