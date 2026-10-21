"""Preserved-run ledger audit and paired diagnostics; no new alpha candidates."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from miniquant.research.validation import daily_returns,block_bootstrap_mean
from tools.run_btc_cohort3 import stitch
from tools.okx_market_audit import atomic_json


def main():
    out=ROOT/'artifacts/BTC-LOOP-003';summary=json.loads((out/'summary.json').read_text());checks=[]
    for path in sorted((out/'runs').glob('*.json')):
        x=json.loads(path.read_text());fills=x['fills'];funding=x['funding_events']
        cash=10000+sum(f['realized_pnl']-f['fee'] for f in fills)+sum(f['pnl'] for f in funding)
        if abs(x['remaining_quantity'])>1e-10:raise ValueError('Residual position requires mark-based ledger audit')
        position_error=max((abs(f['quantity']-sum(v['quantity']*(1 if v['side']=='buy' else -1) for v in fills if v['ts']<f['ts'])) for f in funding),default=0)
        nav_error=abs(cash-x['daily'][-1]['nav'])
        if nav_error>1e-6 or position_error>1e-9:raise ValueError('Ledger invariant failed')
        checks.append(dict(run=path.name,nav_error=nav_error,funding_position_error=position_error))
    def control_daily(cid):
        return stitch([json.loads((out/f'runs/{cid}_{y}-01-01_{y+1}-01-01_base.json').read_text()) for y in (2024,2025)])
    pairs={}
    for left,right in [('P0','long_only_scaled'),('F0','long_only_fixed')]:
        a=daily_returns(summary['variants'][left]['daily']);b=daily_returns(control_daily(right))
        pairs[left+'_minus_'+right]=dict(mean_daily_difference=float(np.mean(a-b)),block_bootstrap=block_bootstrap_mean(a-b),interpretation='Paired realized daily-return diagnostic; exposure/margin differ, not a tradable hindsight allocation or fresh confirmation')
    for i in range(4):
        p=summary['variants']['P'+str(i)];f=summary['variants']['F'+str(i)]
        pairs['P'+str(i)+'_minus_F'+str(i)]=dict(mean_daily_difference=float(np.mean(daily_returns(p['daily'])-daily_returns(f['daily']))),block_bootstrap=block_bootstrap_mean(daily_returns(p['daily'])-daily_returns(f['daily'])))
    audit=dict(cached_runs=len(checks),max_nav_error=max(x['nav_error'] for x in checks),max_funding_position_error=max(x['funding_position_error'] for x in checks),checks=checks,paired_diagnostics=pairs,new_alpha_candidates=0)
    atomic_json(out/'implementation-audit.json',audit)
    print(json.dumps({k:audit[k] for k in ('cached_runs','max_nav_error','max_funding_position_error')},indent=2))


if __name__=='__main__':main()
