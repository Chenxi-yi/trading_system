"""Complete the four frozen breakout variants using validated mark/funding windows."""
import hashlib,json,fcntl,sys
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from tools.run_btc_night import load_bars,stamp
from tools.okx_market_audit import atomic_json
from miniquant.backtest.perpetual import replay_perpetual
from miniquant.research.validation import metrics,daily_returns,block_bootstrap_mean,cscv_sharpe


def main():
 out=ROOT/'artifacts/BTC-NIGHT-001-PERP';out.mkdir(parents=True,exist_ok=True)
 with (out/'study.lock').open('a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  paths=dict(trade='data/market-audit/btc-overnight-20261021/trade_BTC-USDT-SWAP_4H.json',mark='data/market-audit/btc-perp-mark-20261021/mark_BTC-USDT-SWAP_4H.json',funding='data/funding-archive/BTC-USDT-SWAP/normalized.json',config='research/experiments/BTC-NIGHT-001-PERP.json')
  manifest=dict(inputs={k:dict(path=p,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()) for k,p in paths.items()},code={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ('src/miniquant/backtest/perpetual.py','src/miniquant/accounting/perpetual.py','tools/run_btc_perpetual_night.py')})
  fingerprint=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
  if (out/'manifest.json').exists() and json.loads((out/'manifest.json').read_text())['fingerprint']!=fingerprint:raise ValueError('Perpetual input/code changed; preserve previous run')
  manifest['fingerprint']=fingerprint;atomic_json(out/'manifest.json',manifest)
  bars=load_bars(ROOT/paths['trade']);marks=load_bars(ROOT/paths['mark']);funding=json.loads((ROOT/paths['funding']).read_text());cfg=json.loads((ROOT/paths['config']).read_text())
  cache=out/'runs';cache.mkdir(exist_ok=True)
  def evaluate(param,start,end,stress=False):
   tag=f'{param}_{start}_{end}_{stress}';p=cache/(tag+'.json')
   if p.exists():return json.loads(p.read_text())
   result=replay_perpetual(bars,marks,funding,param,stamp(start),stamp(end),fee_bps=10 if stress else 5,slip_bps=10 if stress else 5)
   result.update(stats=metrics(result['daily']),param=param,start=start,end=end,stress=stress)
   atomic_json(p,result);print(tag,'completed',flush=True);return result
  params=cfg['variants'];wf=[];adverse=[];choices={}
  score=lambda x:x['stats']['daily_sharpe_365'] if x['stats']['daily_sharpe_365'] is not None else -float('inf')
  development=[evaluate(p,'2023-01-01','2024-01-01') for p in params]
  for year in (2024,2025):
   train=[evaluate(p,*cfg['walk_forward'][str(year)]['train']) for p in params]
   chosen=max(train,key=score)['param'];choices[str(year)]=chosen
   wf.append(evaluate(chosen,f'{year}-01-01',f'{year+1}-01-01'))
   adverse.append(evaluate(chosen,f'{year}-01-01',f'{year+1}-01-01',True))
  train=[evaluate(p,*cfg['sealed_choice_train']) for p in params];chosen=max(train,key=score)['param']
  choice=dict(walk_forward=choices,sealed=chosen,recorded_before_perpetual_sealed=True,spot_historical_sealed_already_seen=True)
  atomic_json(out/'sealed_choices.json',choice)
  sealed=evaluate(chosen,*cfg['sealed'])
  def stitch(evaluations):
   nav=10000;rows=[]
   for x in evaluations:
    for r,ret in zip(x['daily'],daily_returns(x['daily'])):nav*=1+float(ret);rows.append(dict(ts=r['ts'],nav=nav))
   return rows
  daily=stitch(wf);stress_daily=stitch(adverse);stats=metrics(daily);stress_stats=metrics(stress_daily)
  boot=block_bootstrap_mean(daily_returns(daily));pbo=cscv_sharpe(np.asarray([daily_returns(v['daily']) for v in development]).T)
  neighbor_positive=sum(x['stats']['net_return']>0 for x in train)/len(params)
  reasons=[]
  if stats['net_return']<=0:reasons.append('nonpositive_walk_forward_return')
  if any(x['stats']['net_return']<=0 for x in wf):reasons.append('nonpositive_walk_forward_year')
  if sealed['stats']['net_return']<=0:reasons.append('nonpositive_sealed_return')
  if stress_stats['net_return']<=0:reasons.append('nonpositive_adverse_cost_return')
  if stats['max_drawdown']< -0.35 or sealed['stats']['max_drawdown']< -0.35:reasons.append('research_drawdown_limit')
  if sum(len(x['fills']) for x in wf)<20:reasons.append('insufficient_fills')
  if not boot.get('all_lower_bounds_positive',False):reasons.append('mean_return_uncertainty_includes_no_edge')
  if neighbor_positive<0.75:reasons.append('parameter_neighbors_not_robust')
  if pbo.get('status')!='diagnostic' or pbo.get('pbo_strict',1)>0.2:reasons.append('selection_instability_or_undefined_PBO')
  if any(x['synthetic_margin_breaches'] for x in wf+[sealed]):reasons.append('synthetic_margin_stress_breach')
  summary=dict(manifest_fingerprint=fingerprint,selected_choices=choice,walk_forward=stats,walk_forward_years={str(y):x['stats'] for y,x in zip((2024,2025),wf)},sealed_historical=sealed['stats'],adverse_cost=stress_stats,bootstrap=boot,PBO=pbo,parameter_positive_fraction=neighbor_positive,research_reasons=reasons,research_status='screen_pass_pending_margin_review' if not reasons else 'rejected_or_insufficient',demo_ready=False,demo_blockers=sealed['limitations'],funding_pnl_wf=sum(x['funding_pnl'] for x in wf),fees_wf=sum(x['fees'] for x in wf),fills_wf=sum(len(x['fills']) for x in wf),daily_walk_forward=daily)
  atomic_json(out/'summary.json',summary)
  snap=out/'source_snapshot';snap.mkdir(exist_ok=True)
  for path in manifest['code']:
   target=snap/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/path).read_bytes())
  print('Summary',out/'summary.json',flush=True)


if __name__=='__main__':main()
