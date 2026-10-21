"""Explicit new transitive checkpoint and exact replication; old manifests stay intact."""
from pathlib import Path
import json,sys,hashlib,platform,importlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from tools.okx_market_audit import atomic_json
from miniquant.backtest.regime_router import expert_signals,replay_router
from tools.run_btc_regime_router import stamp


def main():
    for name in ('tools.research_btc_regimes','tools.run_btc_regime_router','tools.audit_btc_state_coverage'):importlib.import_module(name)
    out=ROOT/'artifacts/BTC-REGIME-VERIFY-032';out.mkdir(exist_ok=True)
    protocol=ROOT/'research/audits/BTC-REGIME-VERIFY-032.json';cfg=json.loads(protocol.read_text());parents=[];inputs={}
    for parent in cfg['parents']:
        path=ROOT/'artifacts'/parent/'manifest.json';inputs[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest();manifest=json.loads(path.read_text())
        for name,digest in manifest['code'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Current parent code drift')
        parents.append(parent)
    imported=[]
    for mod in list(sys.modules.values()):
        name=getattr(mod,'__file__',None)
        if name:
            p=Path(name).resolve()
            if ROOT in p.parents and p.suffix=='.py':imported.append(p)
    code=sorted(set(list((ROOT/'src').rglob('*.py'))+imported+[Path(__file__).resolve(),ROOT/'tests/test_market_regimes.py',ROOT/'tests/test_regime_router.py',ROOT/'pyproject.toml']))
    data=ROOT/'data/market-audit/btc-overnight-20261021/trade_BTC-USDT_1H.json';inputs[str(data.relative_to(ROOT))]=hashlib.sha256(data.read_bytes()).hexdigest()
    manifest=dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),inputs=inputs,code={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in code},python=platform.python_version(),numpy=np.__version__)
    mp=out/'manifest.json'
    if mp.exists() and json.loads(mp.read_text())!=manifest:raise ValueError('New checkpoint source/input drift')
    if not mp.exists():
        atomic_json(mp,manifest)
        for p in code+[protocol]:
            dest=out/'source_snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    rows=json.loads(data.read_text());bars=[dict(ts=x['open_time_ms'],o=float(x['open']),h=float(x['high']),l=float(x['low']),c=float(x['close']),v=float(x['volume'])) for x in rows if x['complete']]
    checks=[]
    for cid,threshold in [('R25',.25),('R35',.35),('R45',.45)]:
        run=replay_router(bars,expert_signals(bars,threshold),'router',stamp('2024-01-01'),stamp('2025-01-01'))
        parent=ROOT/'artifacts/BTC-LOOP-030/runs'/f'{cid}_2024-01-01_2025-01-01_base.json'
        if json.loads(parent.read_text())!=run:raise ValueError('New reproduction differs')
        checks.append(dict(id=cid,all_daily_fills_decisions_snapshots_exact=True,parent_run_sha256=hashlib.sha256(parent.read_bytes()).hexdigest()))
    atomic_json(out/'summary.json',dict(checks=checks,frozen_files=len(code),new_alpha_candidates=0,note='New verification of current sources. Original manifests unchanged; does not invent missing historical source evidence.'))
    print(json.dumps(dict(exact_replays=len(checks),frozen_files=len(code),new_alpha_candidates=0)))
if __name__=='__main__':main()
