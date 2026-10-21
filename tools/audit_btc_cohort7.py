"""Actual-data future perturbation audit; no new rules or alpha trials."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from miniquant.research.pressure_overlay import PressureOverlay
from miniquant.backtest.cohort3 import replay_cohort3
from tools.run_btc_night import stamp
from tools.okx_market_audit import atomic_json


def main():
    out=ROOT/'artifacts/BTC-LOOP-007';manifest=json.loads((out/'manifest.json').read_text())
    for item in manifest['inputs'].values():
        if hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Frozen input changed')
    for n,h in manifest['code'].items():
        if hashlib.sha256((out/'source_snapshot'/n).read_bytes()).hexdigest()!=h:raise ValueError('Frozen source changed')
    read=lambda key:json.loads((ROOT/manifest['inputs'][key]['path']).read_text())
    trade=read('trade');mark=read('mark');funding=read('funding');index=read('index');cfg=read('protocol')
    cut=stamp('2025-01-01')
    def change_raw(rows):return [r if r['open_time_ms']<cut else dict(r,**{k:str(float(r[k])*.9) for k in ('open','high','low','close')}) for r in rows]
    changedtrade=change_raw(trade);changedmark=change_raw(mark)
    changedfunding=[r if r['event_time_ms']<cut else dict(r,realized_rate='.0003') for r in funding]
    changedindex=change_raw(index)
    def bars(rows,volume=False):return [dict(ts=r['open_time_ms'],o=float(r['open']),h=float(r['high']),l=float(r['low']),c=float(r['close']),**(dict(v=float(r['volume'])) if volume else {})) for r in rows if r['complete']]
    checks=[]
    for mode in ('funding','premium','joint'):
        a=PressureOverlay(mode,funding,trade,index);b=PressureOverlay(mode,changedfunding,changedtrade,changedindex)
        original=replay_cohort3(bars(trade,True),bars(mark),funding,cfg['baseline'],stamp('2024-01-01'),stamp('2026-01-01'),target_transform=a)
        changed=replay_cohort3(bars(changedtrade,True),bars(changedmark),changedfunding,cfg['baseline'],stamp('2024-01-01'),stamp('2026-01-01'),target_transform=b)
        for key,field,inclusive in [('daily','ts',True),('fills','ts',False),('decisions','decision_at',True)]:
            prefix=lambda r:[x for x in r[key] if x[field]<=cut] if inclusive else [x for x in r[key] if x[field]<cut]
            if prefix(original)!=prefix(changed):raise ValueError('Future perturbation changed '+key)
        if [x for x in a.log if x['decision_ms']<=cut]!=[x for x in b.log if x['decision_ms']<=cut]:raise ValueError('Future pressure leak')
        checks.append(dict(mode=mode,unchanged_prefix_daily_fills_decisions_features=True))
    atomic_json(out/'causality-audit.json',dict(cut_ms=cut,checks=checks,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),note='Post-run engineering perturbation only; no additional candidate or selection. Future PnL not used for inference.'))
    print('Three actual-data perturbation audits passed')

if __name__=='__main__':main()
