"""Separate tiny floating tails from open inventory; preserve original034 counts."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.okx_market_audit import atomic_json


def main():
    out=ROOT/'artifacts/BTC-GRID-CYCLE-REVIEW-035';out.mkdir(exist_ok=True);protocol=ROOT/'research/audits/BTC-GRID-CYCLE-REVIEW-035.json'
    parent=ROOT/'artifacts/BTC-GRID-CELLS-034';summary=json.loads((parent/'summary.json').read_text());paths=[parent/'manifest.json',parent/'summary.json']+sorted((parent/'runs').glob('*.trace.json'))
    code=[Path(__file__).resolve(),ROOT/'tools/okx_market_audit.py',ROOT/'src/miniquant/data/okx_public.py']
    manifest=dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},code={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in code})
    mp=out/'manifest.json'
    if mp.exists() and json.loads(mp.read_text())!=manifest:raise ValueError('Frozen inputs changed')
    if not mp.exists():
        atomic_json(mp,manifest)
        for p in code+[protocol]:
            dest=out/'source_snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    results={}
    for name in summary['runs']:
        cycles=json.loads((parent/'runs'/(name+'.trace.json')).read_text())['cycles']
        closed=[c for c in cycles if 'closed_at'in c];opened=[c for c in cycles if 'closed_at'not in c]
        if len(cycles)!=len(closed)+len(opened) or any(c['quantity']>1e-12 for c in closed) or any(c['quantity']<=1e-12 for c in opened):raise ValueError('Lifecycle partition inconsistent')
        results[name]=dict(cycles=len(cycles),closed=len(closed),open_dust=len(opened),closed_positive_floating_tail=sum(c['quantity']>0 for c in closed),note='Original remaining_dust_cycles incorrectly counted closed positive float tails too; raw034 kept unchanged')
    atomic_json(out/'summary.json',results)
    lines=['# 035：034生命周期计数边界复核','', '034代码在已实际冻结/运行后发现摘要remaining_dust_cycles采用quantity>0，混入已关闭周期的正浮点尾差，不能与completed_cycles相加。原码、manifest、trace、摘要保留；新复核按协议<=1e-12关闭阈值检查并给出互斥计数，经济成交与NAV不受影响。','', '| 窗口 | 全周期 | 已关闭 | 未关闭dust | 已关闭中正浮点尾差 |','|---|---:|---:|---:|---:|']
    for name,r in results.items():lines.append(f"| {name} | {r['cycles']} | {r['closed']} | {r['open_dust']} | {r['closed_positive_floating_tail']} |")
    lines+=['','这些微量残余不是盈利新证据，不能把dust周期算作独立交易样本。034格子记录中最大数量/现金/PnL容差与原交易规则限制保持；无新策略/回测选择。']
    (ROOT/'research/notes/BTC_GRID_CYCLE_REVIEW_035.md').write_text('\n'.join(lines)+'\n');print(json.dumps(results))
if __name__=='__main__':main()
