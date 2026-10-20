"""Predeclared grid fill-resolution sensitivity with already frozen WF choices.

No re-selection, no sealed re-optimization, no new parameter candidates.
"""
import fcntl
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from tools.run_btc_night import load_bars,stamp
from tools.okx_market_audit import atomic_json
from miniquant.backtest.replay import replay
from miniquant.research.validation import metrics,daily_returns


def main():
 source=ROOT/'data/market-audit/btc-overnight-20261021/trade_BTC-USDT_15m.json'
 if not source.exists():print('Fine-grid data pending');return
 choices=json.loads((ROOT/'artifacts/BTC-NIGHT-001/sealed_choices.json').read_text())['walk_forward_choices']['grid']
 bars=load_bars(source);periods=[];combined=[];nav=10000
 for year in (2024,2025):
  param=choices[str(year)]
  r=replay(bars,'grid',param,stamp(f'{year}-01-01'),stamp(f'{year+1}-01-01'),base_interval=900000)
  old=json.loads((ROOT/f'artifacts/BTC-NIGHT-001/runs/grid_{param}_{year}-01-01_{year+1}-01-01_base.json').read_text())
  periods.append(dict(year=year,parameter=param,fine_15m=metrics(r.daily),hourly=old['stats'],fine_fills=len(r.fills),hourly_fills=old['fill_count']))
  for row,ret in zip(r.daily,daily_returns(r.daily)):nav*=1+float(ret);combined.append(dict(ts=row['ts'],nav=nav))
 result=dict(kind='execution_resolution_sensitivity_not_new_candidate_selection',data_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),periods=periods,combined=metrics(combined),daily=combined,
             assumptions='Same 1h decision-to-fill lag, at most one fill/cell/hour, same already selected variants; strict15m penetration still not real queue evidence',demo_ready=False)
 atomic_json(ROOT/'artifacts/BTC-NIGHT-001/grid-resolution.json',result)
 print('Fine grid sensitivity completed')


if __name__=='__main__':
    lock_path=ROOT/'artifacts/BTC-NIGHT-001'/'grid-resolution.lock'
    lock_path.parent.mkdir(parents=True,exist_ok=True)
    with lock_path.open('a') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        main()
