"""Frozen three-pressure-overlay study; actual perp ledger, no network/account/orders."""
from datetime import datetime,timezone
from collections import Counter
import fcntl,hashlib,json,platform,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from miniquant.backtest.cohort3 import replay_cohort3
from miniquant.research.pressure_overlay import PressureOverlay
from miniquant.research.validation import metrics,daily_returns,block_bootstrap_mean,cscv_sharpe
from tools.run_btc_cohort3 import stitch
from tools.run_btc_night import stamp
from tools.okx_market_audit import atomic_json


def main():
    out=ROOT/'artifacts/BTC-LOOP-007';out.mkdir(exist_ok=True)
    with (out/'study.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (out/'summary.json').exists():raise ValueError('Completed study immutable')
        paths=dict(protocol='research/experiments/BTC-LOOP-007.json',trade='data/market-audit/btc-overnight-20261021/trade_BTC-USDT-SWAP_4H.json',mark='data/market-audit/btc-perp-mark-20261021/mark_BTC-USDT-SWAP_4H.json',funding='artifacts/BTC-PRESSURE-DATA-006/funding-joined.json',index='data/market-audit/btc-long-index-20261021/index_BTC-USDT_4H.json')
        sources=list((ROOT/'src').rglob('*.py'))+[Path(__file__).resolve(),ROOT/'tools/run_btc_cohort3.py',ROOT/'tools/run_btc_night.py',ROOT/'tools/okx_market_audit.py',ROOT/'pyproject.toml']
        manifest=dict(inputs={k:dict(path=p,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()) for k,p in paths.items()},code={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},python=platform.python_version(),numpy=np.__version__)
        fp=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest();manifest['fingerprint']=fp
        target=out/'manifest.json'
        if target.exists() and json.loads(target.read_text())['fingerprint']!=fp:raise ValueError('Frozen code/input changed')
        if not target.exists():
            atomic_json(target,manifest)
            for p in sources+[ROOT/paths['protocol']]:
                saved=out/'source_snapshot'/p.relative_to(ROOT);saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(p.read_bytes())
        cfg=json.loads((ROOT/paths['protocol']).read_text())
        rawtrade=json.loads((ROOT/paths['trade']).read_text());index=json.loads((ROOT/paths['index']).read_text());funding=json.loads((ROOT/paths['funding']).read_text())
        def load(rows,volume=False):
            return [dict(ts=x['open_time_ms'],o=float(x['open']),h=float(x['high']),l=float(x['low']),c=float(x['close']),**(dict(v=float(x['volume'])) if volume else {})) for x in rows if x['complete']]
        bars=load(rawtrade,True);marks=load(json.loads((ROOT/paths['mark']).read_text()))
        cache=out/'runs';cache.mkdir(exist_ok=True)
        def evaluate(param,start,end,scenario='base'):
            path=cache/f"{param['id']}_{start}_{end}_{scenario}.json"
            if path.exists():return json.loads(path.read_text())
            overlay=PressureOverlay(param['mode'],funding,rawtrade,index,lag_hours=8 if scenario=='featurelag8h' else 4)
            r=replay_cohort3(bars,marks,funding,cfg['baseline'],stamp(start),stamp(end),fee_bps=10 if scenario=='stress' else 5,slip_bps=10 if scenario=='stress' else 5,lag_hours=8 if scenario=='delay8h' else 4,target_transform=overlay)
            r.update(stats=metrics(r['daily']),id=param['id'],start=start,end=end,scenario=scenario,pressure_decisions=overlay.log)
            atomic_json(path,r);print(path.name,flush=True);return r
        results={};dev={};runs_by_id={}
        for param in cfg['controls']+cfg['variants']:
            cid=param['id'];dev[cid]=evaluate(param,*cfg['windows']['development'])
            values={scenario:[evaluate(param,f'{y}-01-01',f'{y+1}-01-01',scenario) for y in (2024,2025)] for scenario in cfg['scenarios']}
            challenge=evaluate(param,*cfg['windows']['known_challenge'])
            runs_by_id[cid]=(values,challenge)
            daily=stitch(values['base']);decisions=[d for r in values['base'] for d in r['pressure_decisions']]
            positive=[d for d in decisions if d['base_target']>0]
            results[cid]=dict(parameters=param,years={str(y):r['stats'] for y,r in zip((2024,2025),values['base'])},scenarios={s:metrics(stitch(r)) for s,r in values.items()},challenge=challenge['stats'],daily=daily,bootstrap=block_bootstrap_mean(daily_returns(daily)),fills=sum(len(r['fills']) for r in values['base']),fees=sum(r['fees'] for r in values['base']),funding_pnl=sum(r['funding_pnl'] for r in values['base']),mean_absolute_exposure=float(np.mean([r['mean_absolute_exposure'] for r in values['base']])),long_decisions=len(positive),halved_long_decisions=sum(d['factor']==.5 for d in positive),missing_feature_flat_long_decisions=sum(d['factor']==0 for d in positive))
        baseline_checks=[]
        for start,end in [('2024-01-01','2025-01-01'),('2025-01-01','2026-01-01'),('2026-01-01','2026-07-01')]:
            old=json.loads((ROOT/f'artifacts/BTC-LOOP-003/runs/P0_{start}_{end}_base.json').read_text())
            new=json.loads((cache/f'C0_{start}_{end}_base.json').read_text())
            if old['daily']!=new['daily'] or old['fills']!=new['fills']:raise ValueError('Unfiltered baseline changed')
            baseline_checks.append(dict(start=start,end=end,daily_and_fills_identical=True))
        alphaids=[p['id'] for p in cfg['variants']]
        pbo=cscv_sharpe(np.asarray([daily_returns(dev[c]['daily']) for c in alphaids]).T)
        fraction=sum(results[c]['scenarios']['base']['net_return']>0 for c in alphaids)/len(alphaids)
        for cid in alphaids:
            r=results[cid];values,challenge=runs_by_id[cid];reasons=[];paired={}
            for control in ('C0','C1'):
                diff=daily_returns(r['daily'])-daily_returns(results[control]['daily'])
                paired[control]=block_bootstrap_mean(diff)
                if not paired[control].get('all_lower_bounds_positive'):reasons.append('uncertain_increment_vs_'+control)
            if any(v['net_return']<=0 for v in r['years'].values()):reasons.append('nonpositive_year')
            if r['challenge']['net_return']<=0:reasons.append('nonpositive_known_challenge')
            for s in ('stress','delay8h','featurelag8h'):
                if r['scenarios'][s]['net_return']<=0:reasons.append('nonpositive_'+s)
            if min(r['scenarios']['base']['max_drawdown'],r['challenge']['max_drawdown'])<-.35:reasons.append('drawdown_limit')
            if r['fills']<20:reasons.append('insufficient_fills')
            if not r['bootstrap'].get('all_lower_bounds_positive'):reasons.append('uncertain_mean')
            if any(x['synthetic_margin_breaches'] for group in values.values() for x in group) or challenge['synthetic_margin_breaches']:reasons.append('synthetic_margin_breach')
            if pbo.get('status')!='diagnostic' or pbo.get('pbo_strict',1)>.2:reasons.append('unstable_selection_diagnostic')
            if fraction<.75:reasons.append('weak_mechanism_consistency')
            r.update(paired_differences=paired,reasons=reasons,historical_screen_pass=not reasons)
        checks=[]
        for path in sorted(cache.glob('*.json')):
            x=json.loads(path.read_text());fills=x['fills'];cash=10000+sum(f['realized_pnl']-f['fee'] for f in fills)+sum(f['pnl'] for f in x['funding_events'])
            err=abs(cash-x['daily'][-1]['nav']);poserr=max((abs(f['quantity']-sum(v['quantity']*(1 if v['side']=='buy' else -1) for v in fills if v['ts']<f['ts'])) for f in x['funding_events']),default=0)
            if abs(x['remaining_quantity'])>1e-10 or err>1e-6 or poserr>1e-9:raise ValueError('Ledger identity failed')
            checks.append(dict(run=path.name,nav_error=err,funding_position_error=poserr))
        audit=dict(cached_runs=len(checks),max_nav_error=max(x['nav_error'] for x in checks),max_funding_position_error=max(x['funding_position_error'] for x in checks),baseline_checks=baseline_checks,checks=checks)
        atomic_json(out/'implementation-audit.json',audit)
        summary=dict(experiment=cfg['experiment_id'],completed_at=datetime.now(timezone.utc).isoformat(),results=results,development_pbo=pbo,positive_mechanism_fraction=fraction,alpha_candidates=3,controls_count=2,cumulative_alpha_candidates=39,cumulative_controls=12,historical_screen_pass_count=sum(results[c]['historical_screen_pass'] for c in alphaids),research_qualified=0,demo_ready=0)
        atomic_json(out/'summary.json',summary)
        lines=['# BTC-LOOP-007：拥挤压力是否帮助趋势多头减险？','',f"完成：{summary['completed_at']}；3候选+2固定对照，累计39alpha/12对照。",'',
        '全部历史已知/适应性。P为事前主要候选，不按表中收益选赢家。F=已结算funding，P=永续/指数收盘溢价代理，J=两者共同极端；超过自己过去90日90分位且为正，才将既有正多头目标减半。空头不改。C0不滤波，C1始终减半多头。',
        '压力数据结算/完整bar后+4H为可得假设，另测+8H；真实历史发布时间未知。收盘代理不同于官方冲击溢价。','',
        '| 候选/对照 | 2024 | 2025 | 两年 | 最大回撤 | 2026H1已知 | 压力成本两年 | 执行8H | 特征8H |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for cid,r in results.items():
            s=r['scenarios'];lines.append(f"| {cid} | {r['years']['2024']['net_return']:.2%} | {r['years']['2025']['net_return']:.2%} | {s['base']['net_return']:.2%} | {s['base']['max_drawdown']:.2%} | {r['challenge']['net_return']:.2%} | {s['stress']['net_return']:.2%} | {s['delay8h']['net_return']:.2%} | {s['featurelag8h']['net_return']:.2%} |")
        lines+=['','基准每边费用/滑点5+5bps，压力10+10，另计实际funding。Daily信号/4H延迟、首等待意图固定、TTL12H、5pp再平衡带与P0不变。每年参考本金重新初始化后拼接日收益，非真实账户复利路径。','',
        '| ID | 多头决策 | 减半 | 特征缺失归零 | 两年费用/研究单位 | funding/研究单位 |','|---|---:|---:|---:|---:|---:|']
        for cid,r in results.items():lines.append(f"| {cid} | {r['long_decisions']} | {r['halved_long_decisions']} | {r['missing_feature_flat_long_decisions']} | {r['fees']:.2f} | {r['funding_pnl']:.2f} |")
        lines+=['','## 配对增量及筛查','']
        for cid in alphaids:
            r=results[cid];lines.append(f"- {cid}: {', '.join(r['reasons']) or '历史筛查通过，仍待未知数据/工程'}。")
            for control,boot in r['paired_differences'].items():
                for block,v in boot.get('block_lengths',{}).items():lines.append(f"  - 对{control}，{block}日块，平均日收益差{v['mean']:.4%}，探索性5/95区间[{v['lower_one_sided_95']:.4%}, {v['upper_95']:.4%}]。")
        lines+=['',f"开发期3候选CSCV PBO={pbo.get('pbo_strict')}，只作相对排名诊断，不清除跨批人工选择；主候选固定而非按PBO挑选。历史筛查通过{summary['historical_screen_pass_count']}，研究达标0，Demo0。",'',
        f"工程：{audit['cached_runs']}份账本复核，最大NAV误差{audit['max_nav_error']:.3g}；C0的2024/2025/2026H1逐日NAV和成交与旧P0完全一致。",'',
        '限制：合成10%维护压力不是真实OKX强平tier，4H内可执行报价/排队未认证，账户隔离/真实风控执行仍未验收。统计区间与参数/窗口均不为结果放宽，所有失败保留。']
        (ROOT/'research/reports/BTC_LOOP_007.md').write_text('\n'.join(lines)+'\n')
        print('Complete',summary['historical_screen_pass_count'],'screen passed',flush=True)

if __name__=='__main__':main()
