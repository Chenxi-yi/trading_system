"""Frozen, descriptive attribution of known returns. No new trading strategies."""
from pathlib import Path
import sys,json,hashlib,platform,fcntl
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from tools.okx_market_audit import atomic_json
from miniquant.backtest.replay import aggregate,DAY
from miniquant.research.market_regimes import observable_states,conditional_attribution,state_asof


def main():
    out=ROOT/'artifacts/BTC-REGIME-029';out.mkdir(exist_ok=True)
    with (out/'study.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        protocol=ROOT/'research/experiments/BTC-REGIME-029.json'
        paths=[ROOT/p for p in ['data/market-audit/btc-overnight-20261021/trade_BTC-USDT_1H.json','artifacts/BTC-NIGHT-001/summary.json','artifacts/BTC-NIGHT-001-PERP/summary.json']]
        code=[Path(__file__).resolve(),ROOT/'src/miniquant/research/market_regimes.py',ROOT/'src/miniquant/backtest/replay.py',ROOT/'src/miniquant/accounting/spot.py',ROOT/'tools/okx_market_audit.py']
        manifest=dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},code={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in code},python=platform.python_version(),numpy=np.__version__)
        mp=out/'manifest.json'
        if mp.exists() and json.loads(mp.read_text())!=manifest:raise ValueError('Frozen inputs changed')
        if not mp.exists():
            atomic_json(mp,manifest)
            for p in code+[protocol]:
                dest=out/'source_snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
        rows=json.loads(paths[0].read_text());bars=[dict(ts=x['open_time_ms'],o=float(x['open']),h=float(x['high']),l=float(x['low']),c=float(x['close'])) for x in rows if x['complete']]
        states=observable_states(aggregate(bars,DAY));atomic_json(out/'states.json',states)
        spot=json.loads(paths[1].read_text());perp=json.loads(paths[2].read_text())
        daily={k:spot['families'][k]['daily_walk_forward'] for k in ('trend','reversion','grid','constant_mix')};daily['breakout']=perp['daily_walk_forward']
        if len({tuple(r['ts'] for r in v) for v in daily.values()})!=1:raise ValueError('Different dates')
        results={k:conditional_attribution(v,states) for k,v in daily.items()}
        state_days=[state_asof(states,x['ts']-DAY)['state'] for x in daily['trend']];transitions={};spells=[];n=0;prior=None
        for state in state_days:
            if state!=prior:
                if prior is not None:spells.append(n);transitions[prior+'->'+state]=transitions.get(prior+'->'+state,0)+1
                n=1;prior=state
            else:n+=1
        if n:spells.append(n)
        summary=dict(completed_at=datetime.now(timezone.utc).isoformat(),attribution=results,state_day_counts={k:state_days.count(k) for k in set(state_days)},transitions=transitions,spells_days=spells,median_spell_days=float(np.median(spells)),research_qualified=0,demo_ready=0,note='Known historical attribution; expert inventories carried across states, means cannot be spliced into tradable returns')
        atomic_json(out/'summary.json',summary)
        lines=['# BTC-REGIME-029：可观测状态与旧策略收益归因','', '状态只使用此前完整日线；60日方向效率>=0.35才算趋势，20日波动与此前365个估计的75分位比较；六状态需连续3天确认。收益按当天开始时已知状态归属。全部历史已知，原WF专家参数不改。','', '| 状态 | 天数 | 趋势日均 | 回归日均 | 网格日均 | 再平衡日均 | 永续突破日均 |','|---|---:|---:|---:|---:|---:|---:|']
        for key in results['trend']:
            values=[results[k][key]['mean_daily'] for k in daily];formatted=['缺失' if v is None else f'{v:.3%}' for v in values]
            lines.append('| '+key+' | '+str(results['trend'][key]['days'])+' | '+' | '.join(formatted)+' |')
        lines+=['',f"状态段中位持续{summary['median_spell_days']}日，转换{sum(transitions.values())}次。完整sum/rms/worst/样本不足标志见artifact，不将条件均值当年化或独立检验。",'', '仅解释2024–2025旧账本；专家仓位跨状态继承，状态切换不代表可免费买入/卖出。网格仍受旧撮合/库存假设限制，永续仍含旧保证金/mark估值限制。不能看此表挑每格最优策略再拼接。030路由和四对照已在本结果前共同登记。']
        (ROOT/'research/reports/BTC_REGIME_029.md').write_text('\n'.join(lines)+'\n');print(json.dumps({k:summary[k] for k in ('state_day_counts','median_spell_days','research_qualified','demo_ready')},ensure_ascii=False))
if __name__=='__main__':main()
