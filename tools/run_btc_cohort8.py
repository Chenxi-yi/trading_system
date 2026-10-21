"""Frozen failed-breakout versus same-event continuation study; no network/orders."""
from datetime import datetime,timezone
import fcntl,hashlib,json,platform,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from miniquant.backtest.cohort3 import replay_cohort3
from miniquant.research.failed_breakout import failed_breakout_events,FailedBreakoutTarget
from miniquant.research.validation import metrics,daily_returns,block_bootstrap_mean,cscv_sharpe
from tools.run_btc_cohort3 import stitch
from tools.run_btc_night import stamp
from tools.okx_market_audit import atomic_json


def main():
    out=ROOT/'artifacts/BTC-LOOP-008';out.mkdir(exist_ok=True)
    with (out/'study.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (out/'summary.json').exists():raise ValueError('Completed study immutable')
        paths=dict(protocol='research/experiments/BTC-LOOP-008.json',trade='data/market-audit/btc-overnight-20261021/trade_BTC-USDT-SWAP_4H.json',mark='data/market-audit/btc-perp-mark-20261021/mark_BTC-USDT-SWAP_4H.json',funding='artifacts/BTC-PRESSURE-DATA-006/funding-joined.json')
        sources=list((ROOT/'src').rglob('*.py'))+[Path(__file__).resolve(),ROOT/'tools/run_btc_cohort3.py',ROOT/'tools/run_btc_night.py',ROOT/'tools/okx_market_audit.py',ROOT/'pyproject.toml']
        manifest=dict(inputs={k:dict(path=p,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()) for k,p in paths.items()},code={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},python=platform.python_version(),numpy=np.__version__)
        fp=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest();manifest['fingerprint']=fp
        target=out/'manifest.json'
        if target.exists() and json.loads(target.read_text())['fingerprint']!=fp:raise ValueError('Frozen code/input changed')
        if not target.exists():
            atomic_json(target,manifest)
            for p in sources+[ROOT/paths['protocol']]:
                dest=out/'source_snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
        cfg=json.loads((ROOT/paths['protocol']).read_text())
        def load(key,volume=False):
            return [dict(ts=x['open_time_ms'],o=float(x['open']),h=float(x['high']),l=float(x['low']),c=float(x['close']),**(dict(v=float(x['volume'])) if volume else {})) for x in json.loads((ROOT/paths[key]).read_text()) if x['complete']]
        bars=load('trade',True);marks=load('mark');funding=json.loads((ROOT/paths['funding']).read_text())
        events={d:failed_breakout_events(bars,d,stamp('2023-01-01')) for d in (20,60)}
        atomic_json(out/'events.json',{str(k):v for k,v in events.items()})
        cache=out/'runs';cache.mkdir(exist_ok=True)
        def evaluate(param,start,end,scenario='base'):
            path=cache/f"{param['id']}_{start}_{end}_{scenario}.json"
            if path.exists():return json.loads(path.read_text())
            schedule=FailedBreakoutTarget(events[param['range_days']],param['mode'],param['hold_hours'],stamp(start))
            result=replay_cohort3(bars,marks,funding,dict(horizons=[20],risk_mode='fixed'),stamp(start),stamp(end),fee_bps=10 if scenario=='stress' else 5,slip_bps=10 if scenario=='stress' else 5,lag_hours=8 if scenario=='delay8h' else 4,target_transform=schedule,decision_hours=4)
            result.update(stats=metrics(result['daily']),id=param['id'],start=start,end=end,scenario=scenario,signal_log=schedule.log)
            atomic_json(path,result);print(path.name,flush=True);return result
        results={};dev={};by_id={}
        for param in cfg['controls']+cfg['variants']:
            cid=param['id'];dev[cid]=evaluate(param,*cfg['windows']['development'])
            values={s:[evaluate(param,f'{y}-01-01',f'{y+1}-01-01',s) for y in (2024,2025)] for s in cfg['scenarios']}
            challenge=evaluate(param,*cfg['windows']['challenge']);by_id[cid]=(values,challenge)
            daily=stitch(values['base'])
            results[cid]=dict(parameters=param,years={str(y):r['stats'] for y,r in zip((2024,2025),values['base'])},scenarios={s:metrics(stitch(v)) for s,v in values.items()},challenge=challenge['stats'],daily=daily,bootstrap=block_bootstrap_mean(daily_returns(daily)),fills=sum(len(v['fills']) for v in values['base']),fees=sum(v['fees'] for v in values['base']),funding_pnl=sum(v['funding_pnl'] for v in values['base']),mean_absolute_exposure=float(np.mean([v['mean_absolute_exposure'] for v in values['base']])))
        alphaids=[p['id'] for p in cfg['variants']];pbo=cscv_sharpe(np.asarray([daily_returns(dev[c]['daily']) for c in alphaids]).T)
        fraction=sum(results[c]['scenarios']['base']['net_return']>0 for c in alphaids)/len(alphaids)
        for cid in alphaids:
            r=results[cid];values,challenge=by_id[cid];control='C'+cid[1:];reasons=[]
            diff=daily_returns(r['daily'])-daily_returns(results[control]['daily']);paired=block_bootstrap_mean(diff)
            if not paired.get('all_lower_bounds_positive'):reasons.append('uncertain_increment_vs_continuation')
            if any(v['net_return']<=0 for v in r['years'].values()):reasons.append('nonpositive_year')
            if r['challenge']['net_return']<=0:reasons.append('nonpositive_known_challenge')
            for scenario in ('stress','delay8h'):
                if r['scenarios'][scenario]['net_return']<=0:reasons.append('nonpositive_'+scenario)
            if min(r['scenarios']['base']['max_drawdown'],r['challenge']['max_drawdown'])<-.35:reasons.append('drawdown_limit')
            if r['fills']<20:reasons.append('insufficient_fills')
            if not r['bootstrap'].get('all_lower_bounds_positive'):reasons.append('uncertain_mean')
            if any(v['synthetic_margin_breaches'] for group in values.values() for v in group) or challenge['synthetic_margin_breaches']:reasons.append('synthetic_margin_breach')
            if pbo.get('status')!='diagnostic' or pbo.get('pbo_strict',1)>.2:reasons.append('unstable_selection_diagnostic')
            if fraction<.75:reasons.append('weak_neighbor_consistency')
            r.update(control=control,paired_difference=paired,reasons=reasons,historical_screen_pass=not reasons)
        checks=[]
        for path in sorted(cache.glob('*.json')):
            x=json.loads(path.read_text());fills=x['fills'];cash=10000+sum(f['realized_pnl']-f['fee'] for f in fills)+sum(f['pnl'] for f in x['funding_events'])
            err=abs(cash-x['daily'][-1]['nav']);poserr=max((abs(f['quantity']-sum(v['quantity']*(1 if v['side']=='buy' else -1) for v in fills if v['ts']<f['ts'])) for f in x['funding_events']),default=0)
            if abs(x['remaining_quantity'])>1e-10 or err>1e-6 or poserr>1e-9:raise ValueError('Ledger identity failed')
            checks.append(dict(run=path.name,nav_error=err,funding_position_error=poserr))
        # Default daily clock must remain bit-identical despite adding optional4H decisions.
        baseline=[]
        for start,end in [('2024-01-01','2025-01-01'),('2025-01-01','2026-01-01'),('2026-01-01','2026-07-01')]:
            original=json.loads((ROOT/f'artifacts/BTC-LOOP-003/runs/P0_{start}_{end}_base.json').read_text())
            replay=replay_cohort3(bars,marks,funding,dict(horizons=[20,60,120],risk_mode='vol_scaled',long_only=False),stamp(start),stamp(end))
            if original['daily']!=replay['daily'] or original['fills']!=replay['fills']:raise ValueError('Default P0 changed')
            baseline.append(dict(start=start,end=end,identical=True))
        audit=dict(cached_runs=len(checks),max_nav_error=max(v['nav_error'] for v in checks),max_funding_position_error=max(v['funding_position_error'] for v in checks),baseline_default_clock=baseline,checks=checks)
        atomic_json(out/'implementation-audit.json',audit)
        summary=dict(experiment=cfg['experiment_id'],completed_at=datetime.now(timezone.utc).isoformat(),results=results,development_pbo=pbo,neighbor_positive_fraction=fraction,event_counts={str(k):len(v) for k,v in events.items()},alpha_candidates=4,controls_count=4,cumulative_alpha_candidates=43,cumulative_controls=16,historical_screen_pass_count=sum(results[c]['historical_screen_pass'] for c in alphaids),research_qualified=0,demo_ready=0)
        atomic_json(out/'summary.json',summary)
        lines=['# BTC-LOOP-008：突破失败后的修复还是延续？','',f"完成：{summary['completed_at']}；4候选+4同事件延续对照，累计43alpha/16对照。",'',
        '主R20_24在收益前固定。20/60个此前完整UTC日高低点冻结为区间；4H收盘新越界，之后3bar内首次收回区间才确认失败。禁止同bar影线推断路径；确认事件固定96H间隔，不按未来收益筛选。',
        'R反向原突破，C沿原突破，持有决策期限24/72H，目标±50%NAV，4H决策/5pp带/首意图TTL12H；每年重新从空仓开始，不承接前一年已开始的事件。','',
        '| ID | 2024 | 2025 | 两年 | 最大回撤 | 2026H1已知 | 压力成本 | 执行8H |','|---|---:|---:|---:|---:|---:|---:|---:|']
        for cid,r in results.items():
            s=r['scenarios'];lines.append(f"| {cid} | {r['years']['2024']['net_return']:.2%} | {r['years']['2025']['net_return']:.2%} | {s['base']['net_return']:.2%} | {s['base']['max_drawdown']:.2%} | {r['challenge']['net_return']:.2%} | {s['stress']['net_return']:.2%} | {s['delay8h']['net_return']:.2%} |")
        lines+=['','每边费用/滑点5+5bps，压力10+10，另计实际funding与mark估值。信号确认+4H最早成交，退出目标在确认+24/72H产生再延迟成交；零量不成交/挂单TTL。无价格止损，合成margin/仓位限额只用于研究，非生产风险验收。', '', '## 完整失败与增量','']
        for cid in alphaids:
            r=results[cid];lines.append(f"- {cid}: {', '.join(r['reasons']) or '历史筛查通过，仍须未知数据/工程'}；成交{r['fills']}，费用{r['fees']:.2f}，funding {r['funding_pnl']:.2f}研究单位。")
            for block,v in r['paired_difference'].get('block_lengths',{}).items():lines.append(f"  - 对{r['control']}，{block}日块，平均日差{v['mean']:.4%}，探索性5/95区间[{v['lower_one_sided_95']:.4%}, {v['upper_95']:.4%}]。")
        lines+=['',f"原始确认事件20日区间{len(events[20])}个、60日{len(events[60])}个（含2023–2026Sep，与两年成交数不同）。开发期PBO={pbo.get('pbo_strict')}；历史筛查{summary['historical_screen_pass_count']}，研究0、Demo0。",'',
        f"工程：{len(checks)}运行账本NAV最大误差{audit['max_nav_error']:.3g}，默认Daily P0三旧窗口逐日NAV/成交精确一致。",'',
        '全部历史已知/适应性，FX止损/获利单研究只提供反驳机制，未证明BTC极值区间就是实际订单聚集。论文作用时段多为小时，不能直接移植成4H/数日利润。当前无真实历史强平tier/报价/账户隔离/场所订单链路；没有交易授权或自动晋级。']
        (ROOT/'research/reports/BTC_LOOP_008.md').write_text('\n'.join(lines)+'\n')
        print('Complete',summary['historical_screen_pass_count'],'screen passed',flush=True)

if __name__=='__main__':main()
