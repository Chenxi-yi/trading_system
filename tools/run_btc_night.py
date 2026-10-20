"""Frozen spot-family study. Caches every evaluation and seals choices before validation.

No networking, credentials or exchange orders. One OS file lock prevents duplicate runs.
"""
from dataclasses import asdict
from datetime import datetime,timezone
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from miniquant.backtest.replay import replay,DAY
from miniquant.research.validation import metrics,daily_returns,block_bootstrap_mean,cscv_sharpe
from tools.okx_market_audit import atomic_json

OUT=ROOT/'artifacts/BTC-NIGHT-001'
DATA=ROOT/'data/market-audit/btc-overnight-20261021/trade_BTC-USDT_1H.json'
CONFIG=ROOT/'research/experiments/BTC-NIGHT-001.json'


def stamp(date):return int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp()*1000)


def load_bars(path):
    data=json.loads(path.read_text())
    return [dict(ts=x['open_time_ms'],o=float(x['open']),h=float(x['high']),l=float(x['low']),c=float(x['close'])) for x in data if x['complete']]


def run_study():
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'study.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:print('Study already active');return
        config=json.loads(CONFIG.read_text())
        data_hash=hashlib.sha256(DATA.read_bytes()).hexdigest();config_hash=hashlib.sha256(CONFIG.read_bytes()).hexdigest()
        bars=load_bars(DATA)
        code_files=['src/miniquant/backtest/replay.py','src/miniquant/accounting/spot.py','src/miniquant/research/validation.py','tools/run_btc_night.py']
        code_hashes={x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in code_files}
        fingerprint=hashlib.sha256(json.dumps(dict(data=data_hash,config=config_hash,code=code_hashes),sort_keys=True).encode()).hexdigest()
        manifest=dict(experiment='BTC-NIGHT-001',data_path=str(DATA.relative_to(ROOT)),data_sha256=data_hash,
                      config_sha256=config_hash,code_hashes=code_hashes,fingerprint=fingerprint,
                      git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=ROOT).strip(),
                      python=sys.version,numpy=np.__version__,created_at=datetime.now(timezone.utc).isoformat())
        if (OUT/'manifest.json').exists():
            old=json.loads((OUT/'manifest.json').read_text())
            if old['fingerprint']!=fingerprint:raise ValueError('Run inputs/code changed: archive existing result directory and record repair before rerun')
        else:atomic_json(OUT/'manifest.json',manifest)
        cache=OUT/'runs';cache.mkdir(exist_ok=True)
        def evaluate(family,param,start,end,adverse=False):
            tag=f'{family}_{param}_{start}_{end}_{"stress" if adverse else "base"}'
            p=cache/(tag+'.json')
            if p.exists():return json.loads(p.read_text())
            result=replay(bars,family,param,stamp(start),stamp(end),fee_bps=20 if adverse else 10,slip_bps=10 if adverse else 5)
            value=dict(family=family,param=param,start=start,end=end,scenario='stress' if adverse else 'base',
                       stats=metrics(result.daily),daily=result.daily,fees=result.fees,turnover=result.turnover,
                       fill_count=len(result.fills),exposure=result.exposure_hours/result.total_hours,
                       assumptions=result.assumptions)
            atomic_json(p,value);atomic_json(cache/(tag+'.fills.json'),result.fills)
            print(tag,'completed',flush=True)
            return value
        families=('trend','reversion','grid','constant_mix')
        development={};wf={};selected={};stress={};fold_choices={}
        for family in families:
            variants=config['families'][family]['variants']
            development[family]=[];wf[family]=[];stress[family]=[];fold_choices[family]={}
            for param in variants:
                development[family].append(evaluate(family,param,'2021-01-01','2024-01-01'))
            for year in (2024,2025):
                train=[evaluate(family,p,f'{year-2}-01-01',f'{year}-01-01') for p in variants]
                score=lambda x:x['stats']['daily_sharpe_365'] if x['stats']['daily_sharpe_365'] is not None else -float('inf')
                winner=max(train,key=score)['param'];fold_choices[family][str(year)]=winner
                wf[family].append(evaluate(family,winner,f'{year}-01-01',f'{year+1}-01-01'))
                stress[family].append(evaluate(family,winner,f'{year}-01-01',f'{year+1}-01-01',True))
            train=[evaluate(family,p,'2024-01-01','2026-01-01') for p in variants]
            selected[family]=max(train,key=score)['param']
        # Persist all choices BEFORE evaluating any sealed outcome.
        choice=dict(selected_for_sealed=selected,walk_forward_choices=fold_choices,manifest_fingerprint=fingerprint,
                    sealed_start='2026-01-01',sealed_end_exclusive='2026-07-01',frozen_at=datetime.now(timezone.utc).isoformat())
        choices_path=OUT/'sealed_choices.json'
        if choices_path.exists():
            old=json.loads(choices_path.read_text())
            if old['selected_for_sealed']!=selected:raise ValueError('Sealed choices changed')
        else:atomic_json(choices_path,choice)
        pool=[];results={}
        def stitch(evaluations):
            out=[];nav=10000
            for evaluation in evaluations:
                for row,r in zip(evaluation['daily'],daily_returns(evaluation['daily'])):
                    nav*=1+float(r);out.append(dict(ts=row['ts'],nav=nav))
            return out
        for family in families:
            matrix=np.asarray([daily_returns(v['daily']) for v in development[family]]).T
            pbo=cscv_sharpe(matrix);pool.extend(matrix.T)
            combined=stitch(wf[family]);stressed=stitch(stress[family])
            boot=block_bootstrap_mean(daily_returns(combined))
            sealed=evaluate(family,selected[family],'2026-01-01','2026-07-01')
            variations=[evaluate(family,p,'2024-01-01','2026-01-01') for p in config['families'][family]['variants']]
            positive_fraction=sum(v['stats']['net_return']>0 for v in variations)/len(variations)
            wf_stats=metrics(combined);stress_stats=metrics(stressed)
            reasons=[]
            if wf_stats['net_return']<=0:reasons.append('nonpositive_walk_forward_net_return')
            if any(v['stats']['net_return']<=0 for v in wf[family]):reasons.append('nonpositive_walk_forward_year')
            if sealed['stats']['net_return']<=0:reasons.append('nonpositive_sealed_historical_return')
            if stress_stats['net_return']<=0:reasons.append('nonpositive_adverse_cost_return')
            if wf_stats['max_drawdown']< -0.35 or sealed['stats']['max_drawdown']< -0.35:reasons.append('research_drawdown_limit')
            if sum(v['fill_count'] for v in wf[family])<20:reasons.append('insufficient_fills')
            if not boot.get('all_lower_bounds_positive',False):reasons.append('mean_return_uncertainty_includes_no_edge')
            if positive_fraction<0.75:reasons.append('parameter_neighbors_not_robust')
            if pbo.get('status')!='diagnostic' or pbo.get('pbo_strict',1)>0.2:reasons.append('selection_instability_or_undefined_PBO')
            # Historical current rule metadata is still unverified: flag, never silently certify venue history.
            limitations=['Historical publication times unknown; lag modeled','Current venue rules imposed as scenario, not certified historical rules',
                         'No prospective performance yet','No exchange execution adapter/order-state drills/inventory protection yet']
            if family=='grid':
                reasons.append('grid_real_fill_model_unverified')
                limitations.append('Strict hourly penetration assumes fills; queue/adverse-selection and fine-frequency replay pending')
            results[family]=dict(selected_parameter=selected[family],walk_forward=wf_stats,
                walk_forward_years={str(y):v['stats'] for y,v in zip((2024,2025),wf[family])},
                sealed_historical=sealed['stats'],adverse_cost=stress_stats,
                fills=sum(v['fill_count'] for v in wf[family]),fees=sum(v['fees'] for v in wf[family]),
                mean_exposure=float(np.mean([v['exposure'] for v in wf[family]])),
                parameter_positive_fraction=positive_fraction,bootstrap=boot,PBO=pbo,
                research_status='screen_pass_pending_data_review' if not reasons else 'rejected_or_insufficient',
                research_reasons=reasons,demo_ready=False,demo_blockers=limitations,
                daily_walk_forward=combined)
        results['breakout']=dict(research_status='pending_perpetual_data_and_model',demo_ready=False,
                                reason='Perpetual funding/margin/mark and execution model not complete. No multi-year net profitability claim from spot proxy.')
        baselines={f:evaluate(f,0,'2024-01-01','2026-01-01') for f in ('cash','hold')}
        summary=dict(manifest_fingerprint=fingerprint,families=results,baselines={k:v['stats'] for k,v in baselines.items()},
                     pool_PBO_development=cscv_sharpe(np.asarray(pool).T),
                     DSR=dict(status='not_estimated',reason='Effective independent trial count and serial-dependence adjustments not established; no false precision'),
                     selected_choices=choice,conclusions='Historical screen only. No demo/live strategy ready by this report alone.')
        atomic_json(OUT/'summary.json',summary)
        print('Summary:',OUT/'summary.json',flush=True)


if __name__=='__main__':run_study()
