"""Bounded ex-ante state router test. All history known; no exchange API."""
from pathlib import Path
import json,sys,hashlib,platform,fcntl
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from tools.okx_market_audit import atomic_json
from miniquant.backtest.regime_router import expert_signals,replay_router
from miniquant.research.validation import metrics,daily_returns,block_bootstrap_mean


def stamp(s):return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()*1000)

def stitched(runs):
    nav=10000;out=[]
    for run in runs:
        for row,r in zip(run['daily'],daily_returns(run['daily'])):nav*=1+float(r);out.append(dict(ts=row['ts'],nav=nav))
    return out


def ledger_check(run):
    cash=10000.;q=0.;index=0;max_error=0
    for snapshot in run['snapshots']:
        while index<len(run['fills']) and run['fills'][index]['ts']<snapshot['ts']:
            f=run['fills'][index]
            if f['side']=='buy':cash-=f['notional'];q+=f['quantity']
            else:cash+=f['notional']-f['fee'];q-=f['quantity']
            index+=1
        max_error=max(max_error,abs(snapshot['nav']-cash-q*snapshot['mark']))
    while index<len(run['fills']):
        f=run['fills'][index]
        if f['side']=='buy':cash-=f['notional'];q+=f['quantity']
        else:cash+=f['notional']-f['fee'];q-=f['quantity']
        index+=1
    # Scheduled liquidation may leave subminimum dust; final marked value includes it.
    if run['snapshots']:
        final_price=run['snapshots'][-1]['mark'];max_error=max(max_error,abs(run['daily'][-1]['nav']-cash-q*final_price))
    if max_error>1e-6:raise ValueError('Independent ledger mismatch')
    return max_error


def main():
    out=ROOT/'artifacts/BTC-LOOP-030';out.mkdir(exist_ok=True)
    with (out/'study.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        protocol=ROOT/'research/experiments/BTC-LOOP-030.json';cfg=json.loads(protocol.read_text())
        data=ROOT/'data/market-audit/btc-overnight-20261021/trade_BTC-USDT_1H.json'
        sources=[Path(__file__).resolve()]+[ROOT/p for p in ['src/miniquant/backtest/regime_router.py','src/miniquant/research/market_regimes.py','src/miniquant/backtest/replay.py','src/miniquant/accounting/spot.py','src/miniquant/research/validation.py','tools/okx_market_audit.py']]
        manifest=dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),inputs={str(data.relative_to(ROOT)):hashlib.sha256(data.read_bytes()).hexdigest()},code={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},python=platform.python_version(),numpy=np.__version__)
        mp=out/'manifest.json'
        if mp.exists() and json.loads(mp.read_text())!=manifest:raise ValueError('Frozen source/input changed')
        if not mp.exists():
            atomic_json(mp,manifest)
            for p in sources+[protocol]:
                dest=out/'source_snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
        rows=json.loads(data.read_text());bars=[dict(ts=x['open_time_ms'],o=float(x['open']),h=float(x['high']),l=float(x['low']),c=float(x['close']),v=float(x['volume'])) for x in rows if x['complete']]
        signals={v['id']:expert_signals(bars,v['efficiency_threshold']) for v in cfg['candidates']}
        policies={x['id']:'router' for x in cfg['candidates']};policies.update({x:x for x in cfg['controls_ids']})
        cache=out/'runs';cache.mkdir(exist_ok=True);results={};errors=[]
        for cid,policy in policies.items():
            sig=signals[cid if cid in signals else 'R35'];results[cid]={}
            for scenario in ('base','stress','delay4h'):
                results[cid][scenario]=[]
                for a,b in cfg['periods']:
                    p=cache/f'{cid}_{a}_{b}_{scenario}.json'
                    if p.exists():run=json.loads(p.read_text())
                    else:
                        run=replay_router(bars,sig,policy,stamp(a),stamp(b),fee_bps=20 if scenario=='stress' else 10,slip_bps=10 if scenario=='stress' else 5,lag_hours=4 if scenario=='delay4h' else 1)
                        atomic_json(p,run);print(p.stem,flush=True)
                    errors.append(ledger_check(run));results[cid][scenario].append(run)
        summary={};control='equal_mix'
        for cid in policies:
            scenarios={}
            for scenario,runs in results[cid].items():
                joined=stitched(runs[:2]);ref=stitched(results[control][scenario][:2]);delta=daily_returns(joined)-daily_returns(ref)
                scenarios[scenario]=dict(two_year=metrics(joined),years=[metrics(r['daily']) for r in runs],fees=sum(r['fees'] for r in runs[:2]),turnover=sum(r['turnover'] for r in runs[:2]),fills=sum(len(r['fills']) for r in runs[:2]),mean_daily_increment_vs_equal=float(np.mean(delta)),known_period_increment_means=[float(np.mean(daily_returns(r['daily'])-daily_returns(c['daily']))) for r,c in zip(runs,results[control][scenario])])
            diff=daily_returns(stitched(results[cid]['base'][:2]))-daily_returns(stitched(results[control]['base'][:2]));boot=block_bootstrap_mean(diff)
            reasons=[]
            if cid in signals:
                if not boot.get('all_lower_bounds_positive'):reasons.append('uncertain_increment_vs_equal_mix')
                if any(v<=0 for z in scenarios.values() for v in z['known_period_increment_means']):reasons.append('increment_not_consistent_across_periods_scenarios')
                if any(z['two_year']['max_drawdown']<-.35 or any(v['max_drawdown']<-.35 for v in z['years']) for z in scenarios.values()):reasons.append('drawdown_limit')
                if scenarios['base']['two_year']['net_return']<=0:reasons.append('nonpositive_net_return')
            summary[cid]=dict(scenarios=scenarios,paired_bootstrap=boot,reasons=reasons,historical_support=cid in signals and not reasons,research_qualified=False,demo_ready=False)
        cutoff=stamp('2025-01-01');changed=[dict(x,o=x['o']*1.4,h=x['h']*1.4,l=x['l']*1.4,c=x['c']*1.4) if x['ts']>=cutoff else x for x in bars]
        audits=[]
        for variant in cfg['candidates']:
            cid=variant['id'];altered=expert_signals(changed,variant['efficiency_threshold']);old=[s for s in signals[cid] if s['decision_at']<=cutoff];new=[s for s in altered if s['decision_at']<=cutoff]
            if old!=new:raise ValueError('Future price changes prior signals')
            original=replay_router(bars,signals[cid],'router',stamp('2024-01-01'),cutoff);mutated=replay_router(changed,altered,'router',stamp('2024-01-01'),cutoff)
            if original!=mutated:raise ValueError('Future price changes past account')
            audits.append(dict(id=cid,actual_future_price_prefix_invariant=True))
        payload=dict(completed_at=datetime.now(timezone.utc).isoformat(),rules=summary,ledger_runs=len(errors),max_ledger_error=max(errors),causality_audits=audits,alpha_candidates=3,controls=4,research_qualified=0,demo_ready=0,known_adaptive_history=True)
        atomic_json(out/'summary.json',payload)
        lines=['# BTC-LOOP-030：可观测市场状态路由','', '全部已知历史探索。R35是事前主要规则：上行趋势用趋势、震荡用回归、下行/未知现金；R25/R45只作固定敏感性。条件归因029结果前已经固定此映射，未挑每状态历史赢家。','', '| 规则 | 2024–2025净收益 | 最大回撤 | 2026H1净收益 | 压力成本两年 | 4H延迟两年 | 相对固定混合平均日增量 |','|---|---:|---:|---:|---:|---:|---:|']
        for cid,x in summary.items():
            a=x['scenarios'];v=a['base'];lines.append(f"| {cid} | {v['two_year']['net_return']:.2%} | {v['two_year']['max_drawdown']:.2%} | {v['years'][2]['net_return']:.2%} | {a['stress']['two_year']['net_return']:.2%} | {a['delay4h']['two_year']['net_return']:.2%} | {v['mean_daily_increment_vs_equal']:.4%} |")
        lines+=['','无借贷现货，每边基准10bps费用+5bps滑点，压力20+10；真实现金库存账本，所有切换/退出计成本。4H目标/1H延迟、5pp带、首意图TTL12H、零量不成交；年界重建计费用，收益非年化。','', '专家为统一因果目标信号而非旧收益拼接：趋势20/60/120日正向，回归前180根4H z<=-1.5进入，z>=0/48h/收盘跌破信号价减2ATR退出；此为新专家定义，不冒充复现首轮回归。回归专家状态独立演化，切换时只能按当前目标实买卖，不追溯赚取旧收益。高波动标签没有额外减半，以区分状态路由与共同连续波动率缩放。','']
        for cid in signals:
            lines.append(f"- {cid}: {', '.join(summary[cid]['reasons']) or '仅历史增量支持，仍需前瞻与工程'}")
            for block,v in summary[cid]['paired_bootstrap'].get('block_lengths',{}).items():lines.append(f"  - {block}日块日增量5/95区间[{v['lower_one_sided_95']:.4%}, {v['upper_95']:.4%}]。")
        lines+=['',f"{len(errors)}份账本独立复算最大误差{max(errors):.3g}，3个实际未来价格扰动/截断比较通过。",'', '没有加入网格撮合、真实交易所订单/深度/历史规则认证；网格切换涉及撤单与库存，须独立研究。所有结果不是新OOS、前瞻或盈利保证；不按表改阈值、持有期、方向。新门槛看固定混合的增量，不要求每年策略绝对盈利，不修改旧失败。研究0/Demo0。']
        (ROOT/'research/reports/BTC_LOOP_030.md').write_text('\n'.join(lines)+'\n');print('Completed regime router; no exchange operations',flush=True)
if __name__=='__main__':main()
