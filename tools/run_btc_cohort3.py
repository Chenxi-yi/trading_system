"""Frozen cohort3 research on actual perpetual candles/mark/realized funding."""
from datetime import datetime,timezone
import fcntl,hashlib,json,platform,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from miniquant.backtest.cohort3 import replay_cohort3
from miniquant.research.validation import metrics,daily_returns,block_bootstrap_mean,cscv_sharpe
from tools.run_btc_night import stamp
from tools.okx_market_audit import atomic_json


def stitch(values):
    rows=[];nav=10000
    for v in values:
        for row,r in zip(v['daily'],daily_returns(v['daily'])):
            nav*=1+float(r);rows.append(dict(ts=row['ts'],nav=nav))
    return rows


def main():
    out=ROOT/'artifacts/BTC-LOOP-003';out.mkdir(exist_ok=True)
    with (out/'study.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        paths=dict(protocol='research/experiments/BTC-LOOP-003.json',trade='data/market-audit/btc-overnight-20261021/trade_BTC-USDT-SWAP_4H.json',mark='data/market-audit/btc-perp-mark-20261021/mark_BTC-USDT-SWAP_4H.json',funding='data/funding-archive/BTC-USDT-SWAP/normalized.json')
        sources=list((ROOT/'src').rglob('*.py'))+[Path(__file__).resolve(),ROOT/'tools/run_btc_night.py',ROOT/'tools/okx_market_audit.py',ROOT/'pyproject.toml']
        manifest=dict(inputs={k:dict(path=p,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()) for k,p in paths.items()},code={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},python=platform.python_version(),numpy=np.__version__)
        fp=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest();manifest['fingerprint']=fp
        target=out/'manifest.json'
        if target.exists() and json.loads(target.read_text())['fingerprint']!=fp:raise ValueError('Frozen code/input changed; retain prior lineage')
        if not target.exists():
            atomic_json(target,manifest)
            for p in sources+[ROOT/paths['protocol']]:
                saved=out/'source_snapshot'/p.relative_to(ROOT);saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(p.read_bytes())
        cfg=json.loads((ROOT/paths['protocol']).read_text())
        def load(p,volume=False):
            return [dict(ts=x['open_time_ms'],o=float(x['open']),h=float(x['high']),l=float(x['low']),c=float(x['close']),**(dict(v=float(x['volume'])) if volume else {})) for x in json.loads((ROOT/p).read_text()) if x['complete']]
        bars=load(paths['trade'],True);marks=load(paths['mark']);funding=json.loads((ROOT/paths['funding']).read_text())
        cache=out/'runs';cache.mkdir(exist_ok=True)
        def evaluate(param,start,end,scenario='base'):
            p=cache/f"{param['id']}_{start}_{end}_{scenario}.json"
            if p.exists():return json.loads(p.read_text())
            r=replay_cohort3(bars,marks,funding,param,stamp(start),stamp(end),fee_bps=10 if scenario=='stress' else 5,slip_bps=10 if scenario=='stress' else 5,lag_hours=8 if scenario=='delay8h' else 4)
            r.update(stats=metrics(r['daily']),id=param['id'],start=start,end=end,scenario=scenario)
            atomic_json(p,r);print(p.name,flush=True);return r
        all_results={};dev={};neighbors={}
        for param in cfg['variants']:
            cid=param['id'];dev[cid]=evaluate(param,'2023-01-01','2024-01-01')
            years=[evaluate(param,f'{y}-01-01',f'{y+1}-01-01') for y in (2024,2025)]
            challenge=evaluate(param,'2026-01-01','2026-07-01')
            stress=[evaluate(param,f'{y}-01-01',f'{y+1}-01-01','stress') for y in (2024,2025)]
            delay=[evaluate(param,f'{y}-01-01',f'{y+1}-01-01','delay8h') for y in (2024,2025)]
            daily=stitch(years);boot=block_bootstrap_mean(daily_returns(daily));stats=metrics(daily);stressed=metrics(stitch(stress));reasons=[]
            if any(v['stats']['net_return']<=0 for v in years):reasons.append('nonpositive_year')
            if challenge['stats']['net_return']<=0:reasons.append('nonpositive_known_challenge')
            if stressed['net_return']<=0:reasons.append('nonpositive_stress')
            if min(stats['max_drawdown'],challenge['stats']['max_drawdown'])<-.35:reasons.append('drawdown_limit')
            if sum(len(v['fills']) for v in years)<20:reasons.append('insufficient_fills')
            if not boot.get('all_lower_bounds_positive'):reasons.append('uncertain_mean')
            if any(v['synthetic_margin_breaches'] for v in years+[challenge]):reasons.append('synthetic_margin_breach')
            all_results[cid]=dict(parameters=param,historical_replay=stats,years={str(y):v['stats'] for y,v in zip((2024,2025),years)},known_challenge=challenge['stats'],stress=stressed,delay8h=metrics(stitch(delay)),fills=sum(len(v['fills']) for v in years),fees=sum(v['fees'] for v in years),funding_pnl=sum(v['funding_pnl'] for v in years),mean_absolute_exposure=float(np.mean([v['mean_absolute_exposure'] for v in years])),bootstrap=boot,reasons=reasons,daily=daily,historical_screen_pass=False,research_qualified=False,demo_ready=False)
        for prefix in ('P','F'):
            ids=[f'{prefix}{i}' for i in range(4)]
            pbo=cscv_sharpe(np.asarray([daily_returns(dev[c]['daily']) for c in ids]).T)
            fraction=sum(all_results[c]['historical_replay']['net_return']>0 for c in ids)/4
            for cid in ids:
                r=all_results[cid];r['PBO']=pbo;r['neighbor_positive_fraction']=fraction
                if pbo.get('status')!='diagnostic' or pbo.get('pbo_strict',1)>.2:r['reasons'].append('unstable_selection_diagnostic')
                if fraction<.75:r['reasons'].append('fragile_neighbors')
                r['historical_screen_pass']=not r['reasons']
        controls={}
        for param in cfg['controls']:
            years=[evaluate(param,f'{y}-01-01',f'{y+1}-01-01') for y in (2024,2025)]
            challenge=evaluate(param,'2026-01-01','2026-07-01')
            controls[param['id']]=dict(historical_replay=metrics(stitch(years)),known_challenge=challenge['stats'],funding_pnl=sum(v['funding_pnl'] for v in years))
        summary=dict(experiment=cfg['experiment_id'],completed_at=datetime.now(timezone.utc).isoformat(),manifest_fingerprint=fp,variants=all_results,controls=controls,alpha_candidates=8,controls_count=4,cumulative_alpha_candidates=36,cumulative_controls=10,research_qualified=0,demo_ready=0,historical_screen_pass_count=sum(v['historical_screen_pass'] for v in all_results.values()))
        atomic_json(out/'summary.json',summary)
        lines=['# BTC-LOOP-003：实际永续双向多周期探索','',f"完成：{summary['completed_at']}；8候选+4对照，累计36alpha+10对照。",'',
               '所有历史均为已知适应性探索；无独立新OOS/前瞻，没有交易所订单。P0/F0在收益前固定，其他为敏感性，不事后选最佳。','',
               '| 候选 | 2024净收益 | 2025净收益 | 两年净收益 | 最大回撤 | 2026H1已知挑战 | 压力成本两年 | 8H延迟两年 |','|---|---:|---:|---:|---:|---:|---:|---:|']
        for cid,r in all_results.items():
            lines.append(f"| {cid} | {r['years']['2024']['net_return']:.2%} | {r['years']['2025']['net_return']:.2%} | {r['historical_replay']['net_return']:.2%} | {r['historical_replay']['max_drawdown']:.2%} | {r['known_challenge']['net_return']:.2%} | {r['stress']['net_return']:.2%} | {r['delay8h']['net_return']:.2%} |")
        lines+=['','净收益非年化；P组20%年化风险目标/75%上限，F组75%固定名义乘信号强度。基准费/滑点每边5+5bps、压力10+10，另含实际funding费率/时点。',
                '保证金仅合成10%最坏mark压力，绝非真实OKX历史强平认证；4Hmark边界估算funding名义金额；当前合同粒度为研究情景。','',
                '## 消融对照','', '| 对照 | 两年净收益 | 2026H1已知挑战 |', '|---|---:|---:|']
        for cid,r in controls.items():lines.append(f"| {cid} | {r['historical_replay']['net_return']:.2%} | {r['known_challenge']['net_return']:.2%} |")
        lines+=['','## 否决与不确定性','']
        for cid,r in all_results.items():lines.append(f"- {cid}: {', '.join(r['reasons']) or '历史筛查通过，仍待独立前瞻/工程'}；PBO={r['PBO'].get('pbo_strict')}，funding两年={r['funding_pnl']:.2f}研究单位，费用={r['fees']:.2f}。")
        lines+=['',f"历史筛查通过{summary['historical_screen_pass_count']}，研究达标0、Demo准入0。PBO只诊断本族开发期排名，不能消除跨批自适应选择。",'',
                '下一步不是挑表里最赚钱的参数，而是核查空头/波动缩放的配对差异、对市场时期与交易成本的依赖，并完成三批研究过程审计。']
        (ROOT/'research/reports/BTC_LOOP_003.md').write_text('\n'.join(lines)+'\n')
        print('Complete',flush=True)


if __name__=='__main__':main()
