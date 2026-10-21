"""One preregistered gate and four fixed controls. Known adaptive history only."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys,fcntl,platform
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from tools.okx_market_audit import atomic_json
from miniquant.backtest.gated_grid import replay_gated_grid
from miniquant.research.validation import metrics,daily_returns,block_bootstrap_mean
from tools.run_btc_regime_router import stamp,stitched


def ledger(run,prices):
    cash=10000.;q=0.;i=0;error=0.
    for j,row in enumerate(run['daily']):
        while i<len(run['fills']) and (run['fills'][i]['ts']<row['ts'] or j==len(run['daily'])-1 and run['fills'][i]['ts']==row['ts']):
            f=run['fills'][i];i+=1
            if f['side']=='buy':cash-=f['notional'];q+=f['quantity']
            else:cash+=f['notional']-f['fee'];q-=f['quantity']
        error=max(error,abs(row['nav']-cash-q*prices[row['ts']]))
    if i!=len(run['fills']) or error>1e-6:raise ValueError('Independent ledger failed')
    return error


def utility(rows):
    r=daily_returns(rows);return r-1.5*r*r


def main():
    out=ROOT/'artifacts/BTC-LOOP-036';out.mkdir(exist_ok=True)
    with (out/'study.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        protocol=ROOT/'research/experiments/BTC-LOOP-036.json';cfg=json.loads(protocol.read_text());data=ROOT/'data/market-audit/btc-overnight-20261021/trade_BTC-USDT_1H.json'
        original_paths=[ROOT/'artifacts/BTC-NIGHT-001/runs'/f'grid_8_{a}_{b}_base{suffix}' for a,b in cfg['periods'][1:] for suffix in ('.json','.fills.json')]
        imported=[]
        for mod in list(sys.modules.values()):
            name=getattr(mod,'__file__',None)
            if name:
                p=Path(name).resolve()
                if ROOT in p.parents and p.suffix=='.py':imported.append(p)
        code=sorted(set(list((ROOT/'src').rglob('*.py'))+imported+[Path(__file__).resolve(),ROOT/'tests/test_gated_grid.py',ROOT/'pyproject.toml']))
        manifest=dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [data]+original_paths},code={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in code},python=platform.python_version(),numpy=np.__version__)
        mp=out/'manifest.json'
        if mp.exists() and json.loads(mp.read_text())!=manifest:raise ValueError('Frozen source/input changed')
        if not mp.exists():
            atomic_json(mp,manifest)
            for p in code+[protocol]:
                dest=out/'source_snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
        raw=json.loads(data.read_text());bars=[dict(ts=x['open_time_ms'],o=float(x['open']),h=float(x['high']),l=float(x['low']),c=float(x['close']),v=float(x['volume'])) for x in raw if x['complete']];prices={x['ts']+3600000:x['c'] for x in bars}
        cache=out/'runs';cache.mkdir(exist_ok=True);results={};errors=[]
        for variant in cfg['candidates']+cfg['control_variants']:
            cid=variant['id'];results[cid]={}
            for scenario in ('base','stress','delay4h'):
                results[cid][scenario]=[]
                for a,b in cfg['periods']:
                    target=cache/f'{cid}_{a}_{b}_{scenario}.json'
                    if target.exists():run=json.loads(target.read_text())
                    else:
                        result=replay_gated_grid(bars,'grid',8,stamp(a),stamp(b),fee_bps=20 if scenario=='stress' else 10,slip_bps=10 if scenario=='stress' else 5,execution_lag_hours=4 if scenario=='delay4h' else 1,gate_mode=variant['mode'],budget_fraction=variant['budget_fraction'])
                        run=dict(daily=result.daily,fills=result.fills,fees=result.fees,turnover=result.turnover,mean_exposure=result.exposure_hours/result.total_hours,trace=result.trace)
                        atomic_json(target,run);print(target.stem,flush=True)
                    errors.append(ledger(run,prices));results[cid][scenario].append(run)
        for i,(a,b) in enumerate(cfg['periods'][1:],1):
            old=json.loads((ROOT/'artifacts/BTC-NIGHT-001/runs'/f'grid_8_{a}_{b}_base.json').read_text());fills=json.loads((ROOT/'artifacts/BTC-NIGHT-001/runs'/f'grid_8_{a}_{b}_base.fills.json').read_text());new=results['C0_grid']['base'][i]
            if new['daily']!=old['daily'] or new['fills']!=fills:raise ValueError('Unfiltered parent equivalence failed')
        summary={}
        for cid,scenarios in results.items():
            summary[cid]={}
            for scenario,runs in scenarios.items():
                days=stitched(runs[:2]);summary[cid][scenario]=dict(two_year=metrics(days),periods=[metrics(r['daily']) for r in runs],fees=sum(r['fees'] for r in runs[:2]),turnover=sum(r['turnover'] for r in runs[:2]),fills=sum(len(r['fills']) for r in runs[:2]),mean_exposure=sum(r['mean_exposure']*len(r['daily']) for r in runs[:2])/len(days))
        comparisons={};reasons=[];primary=cfg['primary'];primary_base=stitched(results[primary]['base'][:2]);s=metrics(primary_base)
        if s['net_return']<=0:reasons.append('nonpositive_base_net_return')
        if any(x['max_drawdown']<-.35 for v in summary[primary].values() for x in [v['two_year']]+v['periods']):reasons.append('drawdown_limit')
        for ref in ('C0_grid','C1_half_grid'):
            delta=utility(primary_base)-utility(stitched(results[ref]['base'][:2]));boot=block_bootstrap_mean(delta)
            scenario_means={scenario:float(np.mean(utility(stitched(results[primary][scenario][:2]))-utility(stitched(results[ref][scenario][:2])))) for scenario in ('stress','delay4h')}
            known=float(np.mean(utility(results[primary]['base'][2]['daily'])-utility(results[ref]['base'][2]['daily'])))
            comparisons[ref]=dict(paired_utility_bootstrap=boot,scenario_mean_utility_increment=scenario_means,known2026H1_mean_utility_increment=known)
            if not boot.get('all_lower_bounds_positive'):reasons.append('uncertain_utility_increment_vs_'+ref)
            if any(v<=0 for v in scenario_means.values()):reasons.append('nonpositive_stress_or_delay_utility_vs_'+ref)
            if known<=0:reasons.append('nonpositive_known_challenge_utility_vs_'+ref)
        a=stamp('2024-01-01');cut=stamp('2025-01-01');changed=[dict(x,o=x['o']*1.4,c=x['c']*1.4,h=x['h']*1.4,l=x['l']*1.4) if x['ts']>=cut else x for x in bars]
        original=replay_gated_grid(bars,'grid',8,a,cut);mutated=replay_gated_grid(changed,'grid',8,a,cut);truncated=replay_gated_grid([x for x in bars if x['ts']<cut],'grid',8,a,cut)
        if original!=mutated or original!=truncated:raise ValueError('Future changed old account/decisions')
        payload=dict(completed_at=datetime.now(timezone.utc).isoformat(),rules=summary,primary=primary,comparisons=comparisons,reasons=reasons,historical_support=not reasons,research_qualified=0,demo_ready=0,ledger_runs=len(errors),max_ledger_error=max(errors),parent_C0_exact_windows=2,actual_future_prefix_and_truncation_invariant=True,alpha_candidates=1,controls=4,known_adaptive_history=True)
        atomic_json(out/'summary.json',payload)
        lines=['# BTC-LOOP-036：方向门控网格与四对照','', '事前主规则G120_active：日收盘低于120日均价停止网格并延迟清仓，高于才运行；固定8格/20日锚/±20%界限/30日重锚，无阈值或参数搜索。全部已知适应性历史，不是新OOS。','', '| 规则 | 2024–2025净收益 | 最大回撤 | 2026H1净收益 | 压力成本两年 | 4H延迟两年 | 两年平均BTC权重 |','|---|---:|---:|---:|---:|---:|---:|']
        for cid,v in summary.items():
            base=v['base'];lines.append(f"| {cid} | {base['two_year']['net_return']:.2%} | {base['two_year']['max_drawdown']:.2%} | {base['periods'][2]['net_return']:.2%} | {v['stress']['two_year']['net_return']:.2%} | {v['delay4h']['two_year']['net_return']:.2%} | {base['mean_exposure']:.1%} |")
        lines+=['','C0一直网格；C1只用半预算；C2相同方向条件下持有BTC；C3仅过滤新开网格、原网格等到正常重置才退出。全部一个现金库存账本，切换与退出计费用，未借贷。每边基准10bps费用+5bps滑点，压力20+10；日决策1H延迟、12H首意图TTL/风险退出优先、零量不成交。年界重建并计成本，非连续实盘组合路径，收益非年化。','', '主要风险效用代理u=r-1.5r²（研究gamma3场景，不代表PM风险偏好或精确确定性等价），用以区分减少方向暴露与网格增量；同时保留所有净收益与风险指标。','']
        for ref,v in comparisons.items():
            lines.append('- 对'+ref+'：')
            for block,z in v['paired_utility_bootstrap'].get('block_lengths',{}).items():lines.append(f"  - {block}日块平均日效用增量5/95区间[{z['lower_one_sided_95']:.4%}, {z['upper_95']:.4%}]。")
        lines+=['', '未通过项：'+(', '.join(reasons) or '固定历史增量门槛暂支持，仍需冻结前瞻与工程验证，不能称有效alpha。'),'', f"{len(errors)}份账本独立核算最大NAV误差{max(errors):.3g}；C0两旧窗全经济成交/逐日NAV精确一致；实际未来价格扰动与截断不改过去信号/账本。",'', '方向门控不是区间平稳性认证，不推断空头方向收益。已有OHLC穿价/排队/当前产品规则/数值lot限制未解决，历史结果不授权交易。未加入真实交易所下单或账户隔离，研究0/Demo0；未按结果改变120天、8格、退出时点或成本。']
        (ROOT/'research/reports/BTC_LOOP_036.md').write_text('\n'.join(lines)+'\n');print('Completed frozen direction-gated grid study',flush=True)
if __name__=='__main__':main()
