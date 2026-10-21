"""Independent recording-only grid replay; old fills and NAV must match exactly."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys,platform,fcntl
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from tools.okx_market_audit import atomic_json
from miniquant.backtest.grid_trace import replay_grid_trace
from miniquant.backtest.replay import DAY


def stamp(s):return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()*1000)


def main():
    out=ROOT/'artifacts/BTC-GRID-CELLS-034';out.mkdir(exist_ok=True)
    with (out/'study.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        protocol=ROOT/'research/audits/BTC-GRID-CELLS-034.json';cfg=json.loads(protocol.read_text());data=ROOT/'data/market-audit/btc-overnight-20261021/trade_BTC-USDT_1H.json'
        paths=[data]
        for name in cfg['runs']:paths.extend(ROOT/'artifacts/BTC-NIGHT-001/runs'/(name+suffix) for suffix in ('.json','.fills.json'))
        imported=[]
        for mod in list(sys.modules.values()):
            name=getattr(mod,'__file__',None)
            if name:
                p=Path(name).resolve()
                if ROOT in p.parents and p.suffix=='.py':imported.append(p)
        code=sorted(set(list((ROOT/'src').rglob('*.py'))+imported+[Path(__file__).resolve(),ROOT/'tests/test_grid_cells.py',ROOT/'pyproject.toml']))
        manifest=dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},code={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in code},python=platform.python_version())
        mp=out/'manifest.json'
        if mp.exists() and json.loads(mp.read_text())!=manifest:raise ValueError('Frozen source/input changed')
        if not mp.exists():
            atomic_json(mp,manifest)
            for p in code+[protocol]:
                dest=out/'source_snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
        rows=json.loads(data.read_text());bars=[dict(ts=x['open_time_ms'],o=float(x['open']),h=float(x['high']),l=float(x['low']),c=float(x['close']),v=float(x['volume'])) for x in rows if x['complete']]
        summary={};cache=out/'runs';cache.mkdir(exist_ok=True)
        for name in cfg['runs']:
            old=json.loads((ROOT/'artifacts/BTC-NIGHT-001/runs'/(name+'.json')).read_text());old_fills=json.loads((ROOT/'artifacts/BTC-NIGHT-001/runs'/(name+'.fills.json')).read_text())
            result=replay_grid_trace(bars,'grid',old['param'],stamp(old['start']),stamp(old['end']))
            if result.daily!=old['daily'] or result.fills!=old_fills or result.fees!=old['fees'] or result.turnover!=old['turnover']:raise ValueError('New instrumentation changed economic replay')
            if abs(result.exposure_hours/result.total_hours-old['exposure'])>1e-12:raise ValueError('Exposure changed')
            if len(result.trace['events'])!=len(result.fills) or [e['fill_index'] for e in result.trace['events']]!=list(range(len(result.fills))):raise ValueError('Trace fill linkage mismatch')
            for a,b in zip(result.trace['daily'],old['daily']):
                if a['ts']!=b['ts'] or abs(a['nav']-b['nav'])>1e-6:raise ValueError('Owner trace daily NAV mismatch')
            cid=cache/(name+'.trace.json')
            if cid.exists() and json.loads(cid.read_text())!=result.trace:raise ValueError('Existing trace changed')
            if not cid.exists():atomic_json(cid,result.trace)
            groups={}
            for e in result.trace['events']:
                if e['side']!='sell':continue
                key=e['reason']+(':'+','.join(e['reset_flags']) if e['reset_flags'] else '')
                v=groups.setdefault(key,dict(fills=0,matched_realized=0.,fees=0.));v['fills']+=1;v['matched_realized']+=sum(p['realized'] for p in e['parts']);v['fees']+=e['fee']
            summary[name]=dict(economic_fills_exact=True,daily_NAV_exact=True,fees_turnover_exposure_exact=True,fills=len(result.fills),cycles=len(result.trace['cycles']),completed_cycles=sum('closed_at'in c for c in result.trace['cycles']),remaining_dust_cycles=sum(c['quantity']>0 for c in result.trace['cycles']),reset_events=result.trace['resets'],sell_reason_attribution=groups,max_identity_error=max(r['identity_error'] for r in result.trace['daily']),final_realized=result.trace['daily'][-1]['realized'],final_unrealized=result.trace['daily'][-1]['unrealized'],final_pnl=result.daily[-1]['nav']-10000)
        a=stamp('2024-01-01');b=stamp('2025-01-01');cut=stamp('2024-07-01');param=6
        original=replay_grid_trace(bars,'grid',param,a,cut);changed=[dict(x,o=x['o']*1.5,h=x['h']*1.5,l=x['l']*1.5,c=x['c']*1.5) if x['ts']>=cut else x for x in bars];mutated=replay_grid_trace(changed,'grid',param,a,cut);truncated=replay_grid_trace([x for x in bars if x['ts']<cut],'grid',param,a,cut)
        if original!=mutated or original!=truncated:raise ValueError('Future changed historical trace')
        payload=dict(runs=summary,actual_future_perturbation_and_truncation_invariant=True,research_qualified=0,demo_ready=0,alpha_candidates=0,limitations=['Inherited original OHLC/queue/zero-volume assumptions, no fill certification','Proportional aggregate sale ownership is an accounting allocation','Known historical analysis, no state selection or promotion'])
        atomic_json(out/'summary.json',payload)
        lines=['# 034：网格格子生命周期与重锚原因','', '独立复制旧回放，只增加reset:cell及buy-cycle身份、reset决策标志和账本记录；原源码/原产物不动。三历史窗全部经济成交/逐日NAV/费/换手/暴露完全一致。限价卖出仅匹配同一格子成本；聚合退出按owner库存比例分配，旧dust继续保留。','', '| 窗口 | 成交数 | 买入周期 | 完全关闭周期 | 仍有dust周期 | 总PnL/研究美元 |','|---|---:|---:|---:|---:|---:|']
        for name,r in summary.items():lines.append(f"| {name} | {r['fills']} | {r['cycles']} | {r['completed_cycles']} | {r['remaining_dust_cycles']} | {r['final_pnl']:.2f} |")
        lines+=['','| 窗口/卖出原因及当时可见reset标志 | 同格子成本归因已实现 | 次数 |','|---|---:|---:|']
        for name,r in summary.items():
            for reason,v in r['sell_reason_attribution'].items():lines.append(f"| {name}/{reason} | {v['matched_realized']:.2f} | {v['fills']} |")
        lines+=['', 'reset原因在原决策时固定，执行继承，不按卖出后收益重命名；多个标志并存。scheduled30d不等于强平，lower_bound不是未来熊市标签。末端强制清仓计入成本，剩余细小库存仍按市价，不把dust硬写成0。','', '同owner分配改进了033全账户FIFO的格子归属，但实际聚合退出的分配仍是会计约定；无真实交易所cell ID/队列，不能称实盘格子利润已认证。旧模型极端合成高频整区间穿越时浮点库存检查失败已复现并保留测试，未改旧数值规则；旧零量/撮合假设仍未解决，不能直接用于生产。','', '真实未来价格扰动和截断不改变过去完整trace/成交/NAV。规则及当时可观测特征可用于下一条独立假设，但不得按这些亏损片段反向挑状态。研究0/Demo0，无新策略或订单。']
        (ROOT/'research/notes/BTC_GRID_CELLS_034.md').write_text('\n'.join(lines)+'\n');print(json.dumps(payload,ensure_ascii=False))
if __name__=='__main__':main()
