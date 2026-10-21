"""Future-prefix checks on actual failed-breakout events and replay, no new trials."""
from pathlib import Path
import json,sys,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from miniquant.research.failed_breakout import failed_breakout_events,FailedBreakoutTarget
from miniquant.backtest.cohort3 import replay_cohort3
from miniquant.backtest.replay import HOUR
from tools.run_btc_night import stamp
from tools.okx_market_audit import atomic_json


def main():
    out=ROOT/'artifacts/BTC-LOOP-008';m=json.loads((out/'manifest.json').read_text())
    for x in m['inputs'].values():
        if hashlib.sha256((ROOT/x['path']).read_bytes()).hexdigest()!=x['sha256']:raise ValueError('Input changed')
    for name,h in m['code'].items():
        if hashlib.sha256((out/'source_snapshot'/name).read_bytes()).hexdigest()!=h:raise ValueError('Frozen source changed')
    def load(key,volume=False):return [dict(ts=x['open_time_ms'],o=float(x['open']),h=float(x['high']),l=float(x['low']),c=float(x['close']),**(dict(v=float(x['volume'])) if volume else {})) for x in json.loads((ROOT/m['inputs'][key]['path']).read_text()) if x['complete']]
    bars=load('trade',True);marks=load('mark');funding=json.loads((ROOT/m['inputs']['funding']['path']).read_text());cut=stamp('2025-01-01')
    change=lambda rows:[r if r['ts']<cut else dict(r,**{k:r[k]*.9 for k in ('o','h','l','c')}) for r in rows]
    changed=change(bars);changedmark=change(marks);changedfunding=[r if r['event_time_ms']<cut else dict(r,realized_rate='.0003') for r in funding]
    checks=[]
    for d in (20,60):
        a=failed_breakout_events(bars,d,stamp('2023-01-01'));b=failed_breakout_events(changed,d,stamp('2023-01-01'))
        truncated=failed_breakout_events([r for r in bars if r['ts']<cut],d,stamp('2023-01-01'))
        prefix=lambda rows:[r for r in rows if r['signal_ms']<=cut]
        if prefix(a)!=prefix(b) or prefix(a)!=truncated:raise ValueError('Event future leak')
        for hold in (24,72):
            original=replay_cohort3(bars,marks,funding,dict(horizons=[20],risk_mode='fixed'),stamp('2024-01-01'),stamp('2026-01-01'),target_transform=FailedBreakoutTarget(a,'reversion',hold,stamp('2024-01-01')),decision_hours=4)
            perturbed=replay_cohort3(changed,changedmark,changedfunding,dict(horizons=[20],risk_mode='fixed'),stamp('2024-01-01'),stamp('2026-01-01'),target_transform=FailedBreakoutTarget(b,'reversion',hold,stamp('2024-01-01')),decision_hours=4)
            if [r for r in original['daily'] if r['ts']<=cut]!=[r for r in perturbed['daily'] if r['ts']<=cut]:raise ValueError('NAV future leak')
            if [r for r in original['fills'] if r['ts']<cut]!=[r for r in perturbed['fills'] if r['ts']<cut]:raise ValueError('Fill future leak')
            if any(r['execute_at']<r['decision_at']+4*HOUR for r in original['decisions']):raise ValueError('Execution latency violated')
            checks.append(dict(range_days=d,hold_hours=hold,event_truncation_and_mutation_and_nav_fill_prefix=True))
    atomic_json(out/'causality-audit.json',dict(cut_ms=cut,checks=checks,new_candidates=0,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    print('Four actual-data causal replays passed')

if __name__=='__main__':main()
