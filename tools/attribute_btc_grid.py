"""Reconcile saved grid fills and mark all inventory; no new strategy search."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys,hashlib,fcntl,platform
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from tools.okx_market_audit import atomic_json
from miniquant.accounting.fifo_attribution import fifo_attribution


def main():
    out=ROOT/'artifacts/BTC-GRID-ATTRIBUTION-033';out.mkdir(exist_ok=True)
    with (out/'study.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        protocol=ROOT/'research/audits/BTC-GRID-ATTRIBUTION-033.json';cfg=json.loads(protocol.read_text());data=ROOT/'data/market-audit/btc-overnight-20261021/trade_BTC-USDT_1H.json'
        paths=[data]
        for name in cfg['runs']:
            paths.extend(ROOT/'artifacts/BTC-NIGHT-001/runs'/(name+suffix) for suffix in ('.json','.fills.json'))
        imported=[]
        for mod in list(sys.modules.values()):
            name=getattr(mod,'__file__',None)
            if name:
                p=Path(name).resolve()
                if ROOT in p.parents and p.suffix=='.py':imported.append(p)
        code=sorted(set(list((ROOT/'src').rglob('*.py'))+imported+[Path(__file__).resolve(),ROOT/'tests/test_fifo_attribution.py',ROOT/'pyproject.toml']))
        manifest=dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},code={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in code},python=platform.python_version())
        mp=out/'manifest.json'
        if mp.exists() and json.loads(mp.read_text())!=manifest:raise ValueError('Frozen source/input changed')
        if not mp.exists():
            atomic_json(mp,manifest)
            for p in code+[protocol]:
                dest=out/'source_snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
        price={row['open_time_ms']+3600000:float(row['close']) for row in json.loads(data.read_text()) if row['complete']};summary={}
        for name in cfg['runs']:
            original=json.loads((ROOT/'artifacts/BTC-NIGHT-001/runs'/(name+'.json')).read_text());fills=json.loads((ROOT/'artifacts/BTC-NIGHT-001/runs'/(name+'.fills.json')).read_text())
            result=fifo_attribution(fills,[dict(ts=d['ts'],price=price[d['ts']]) for d in original['daily']])
            error=max(abs(a['nav']-b['nav']) for a,b in zip(result['daily'],original['daily']))
            if error>1e-6:raise ValueError('Original account daily NAV mismatch')
            result['max_saved_nav_error']=error;summary[name]=result
        atomic_json(out/'summary.json',summary)
        lines=['# 033：旧网格成交与库存账本分解','', '只归因原已访问结果，不改参数、不产生新策略。买入手续费以BTC收取，FIFO成本按实际现金/净收到BTC分配；卖出扣费。每天总PnL=累计FIFO已实现+按市价未实现，完整现金库存与旧NAV核对。FIFO不是格子配对，原记录无cell_id。','', '| 窗口 | 总PnL/研究美元 | FIFO已实现 | 剩余未实现 | 期间最差未实现 | 最大库存占净值 |','|---|---:|---:|---:|---:|---:|']
        for name,r in summary.items():lines.append(f"| {name} | {r['final_pnl']:.2f} | {r['final_realized']:.2f} | {r['final_unrealized']:.2f} | {r['worst_unrealized']:.2f} | {r['max_inventory_weight']:.1%} |")
        lines+=['','| 窗口/卖出原因 | FIFO已实现 | 成交数（买入原因也保留在原artifact） |','|---|---:|---:|']
        for name,r in summary.items():
            for reason,x in r['reasons'].items():
                if 'sell' in reason or reason in ('grid_reset','scheduled_terminal_liquidation'):lines.append(f"| {name}/{reason} | {x['fifo_realized']:.2f} | {x['fills']} |")
        lines+=['',f"最大原逐日NAV差{max(x['max_saved_nav_error'] for x in summary.values()):.3g}；最大FIFO恒等式误差{max(x['max_identity_error'] for x in summary.values()):.3g}。",'', '已实现额和卖出原因分解依赖FIFO记账选择，不能称每格胜率或价差alpha。终点清仓使期末未实现接近零，不表示期间无库存亏损。不能把正的限价卖出FIFO利润单独当策略收益。无原始订单队列/格子ID/真实历史规则，需新诊断重放保留cell生命周期并逐日与旧结果一致，才能分析每格配对及重锚现金流。状态规则、区间有效性、执行成本和突破尾部应另行冻结后检验，不能按本表事后删亏损时段。研究0/Demo0，无新候选、账户、网络或订单。']
        (ROOT/'research/notes/BTC_GRID_ATTRIBUTION_033.md').write_text('\n'.join(lines)+'\n');print(json.dumps({name:{k:r[k] for k in ('final_pnl','worst_unrealized','max_inventory_weight','max_saved_nav_error')} for name,r in summary.items()}))
if __name__=='__main__':main()
