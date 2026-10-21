"""Bounded, checkpointed cohort. No adaptive reranking or exchange operations."""
from datetime import datetime,timezone
import fcntl
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from miniquant.backtest.cohort2 import replay_cohort2
from miniquant.research.validation import metrics,daily_returns,block_bootstrap_mean,cscv_sharpe
from tools.run_btc_night import stamp
from tools.okx_market_audit import atomic_json


def stitch(values):
    rows=[];nav=10000
    for value in values:
        for row,r in zip(value['daily'],daily_returns(value['daily'])):
            nav*=1+float(r);rows.append(dict(ts=row['ts'],nav=nav))
    return rows


def main():
    out=ROOT/'artifacts/BTC-LOOP-002';out.mkdir(exist_ok=True)
    with (out/'study.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        protocol=ROOT/'research/experiments/BTC-LOOP-002.json'
        path=ROOT/'data/market-audit/btc-overnight-20261021/trade_BTC-USDT_1H.json'
        cfg=json.loads(protocol.read_text())
        sources=list((ROOT/'src').rglob('*.py'))+[Path(__file__).resolve(),ROOT/'tools/run_btc_night.py',ROOT/'tools/okx_market_audit.py',ROOT/'pyproject.toml']
        manifest=dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),data_path=str(path.relative_to(ROOT)),data_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                      code={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},python=platform.python_version(),numpy=np.__version__,git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
        fp=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest();manifest['fingerprint']=fp
        mp=out/'manifest.json'
        if mp.exists() and json.loads(mp.read_text())['fingerprint']!=fp:
            raise ValueError('Inputs/code changed: preserve prior run and register repair')
        if not mp.exists():
            atomic_json(mp,manifest)
            for p in sources+[protocol]:
                target=out/'source_snapshot'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
        data=json.loads(path.read_text())
        bars=[dict(ts=x['open_time_ms'],o=float(x['open']),h=float(x['high']),l=float(x['low']),c=float(x['close']),v=float(x['volume'])) for x in data if x['complete']]
        cache=out/'runs';cache.mkdir(exist_ok=True)
        def evaluate(family,param,start,end,scenario='base'):
            cid=param.get('id',family);tag=f'{cid}_{start}_{end}_{scenario}'
            target=cache/(tag+'.json')
            if target.exists():return json.loads(target.read_text())
            result=replay_cohort2(bars,family,param,stamp(start),stamp(end),fee_bps=20 if scenario=='stress' else 10,slip_bps=10 if scenario=='stress' else 5,lag_hours=4 if scenario=='delay4h' else 1)
            result.update(stats=metrics(result['daily']),id=cid,family=family,scenario=scenario,start=start,end=end)
            atomic_json(target,result);print(tag,flush=True);return result
        families={}
        for family,rule in cfg['families'].items():
            variants=rule['variants'];dev=[evaluate(family,p,'2021-01-01','2024-01-01') for p in variants]
            # Every variant is retained. Primary was fixed BEFORE any new returns.
            primary=next(p for p in variants if p['id']==rule['primary'])
            neighbors=[evaluate(family,p,'2024-01-01','2026-01-01') for p in variants]
            years=[evaluate(family,primary,f'{y}-01-01',f'{y+1}-01-01') for y in (2024,2025)]
            challenge=evaluate(family,primary,'2026-01-01','2026-07-01')
            stressed=[evaluate(family,primary,f'{y}-01-01',f'{y+1}-01-01','stress') for y in (2024,2025)]
            delayed=[evaluate(family,primary,f'{y}-01-01',f'{y+1}-01-01','delay4h') for y in (2024,2025)]
            daily=stitch(years);stats=metrics(daily);stress=metrics(stitch(stressed));boot=block_bootstrap_mean(daily_returns(daily))
            pbo=cscv_sharpe(np.asarray([daily_returns(x['daily']) for x in dev]).T)
            reasons=[]
            if any(y['stats']['net_return']<=0 for y in years):reasons.append('nonpositive_year')
            if challenge['stats']['net_return']<=0:reasons.append('nonpositive_known_challenge')
            if stress['net_return']<=0:reasons.append('nonpositive_stress')
            if min(stats['max_drawdown'],challenge['stats']['max_drawdown'])<-.35:reasons.append('drawdown_limit')
            if sum(len(x['fills']) for x in years)<20:reasons.append('insufficient_fills')
            if not boot.get('all_lower_bounds_positive'):reasons.append('uncertain_mean')
            if pbo.get('status')!='diagnostic' or pbo.get('pbo_strict',1)>.2:reasons.append('unstable_selection_diagnostic')
            if sum(v['stats']['net_return']>0 for v in neighbors)/len(neighbors)<.75:reasons.append('fragile_neighbors')
            families[family]=dict(primary=primary,historical_replay=stats,years={str(y):v['stats'] for y,v in zip((2024,2025),years)},known_challenge=challenge['stats'],stress=stress,delay4h=metrics(stitch(delayed)),
                                  fills=sum(len(x['fills']) for x in years),fees=sum(x['fees'] for x in years),PBO=pbo,bootstrap=boot,reasons=reasons,historical_screen_pass=not reasons,
                                  research_qualified=False,demo_ready=False,daily=daily)
        controls={}
        for cid,family,param in [('cash','cash',{}),('hold_75pct','hold',{}),('vol_only20pct_cap75pct','vol_only',{}),('multiscale_T0_no_vol_cap75pct','trend_unscaled',dict(horizons=[20,60,120]))]:
            param=dict(param,id=cid)
            result=evaluate(family,param,'2024-01-01','2026-01-01')
            challenge=evaluate(family,param,'2026-01-01','2026-07-01')
            controls[cid]=dict(historical_replay=result['stats'],known_challenge=challenge['stats'])
        summary=dict(experiment=cfg['experiment_id'],manifest_fingerprint=fp,completed_at=datetime.now(timezone.utc).isoformat(),families=families,controls=controls,
                     alpha_candidates=8,controls_count=4,cumulative_alpha_candidates=28,cumulative_controls=6,research_qualified=0,demo_ready=0,
                     interpretation='Adaptive historical exploration only. No fresh OOS or prospective qualification. Historical failures do not authorize changing gates or selecting another delay.')
        atomic_json(out/'summary.json',summary)
        lines=['# BTC持续研究循环：第二批历史探索','',f"更新：{summary['completed_at']}。旧实验保持原样；新8配置+4对照，累计28个alpha候选与6对照。",'',
               '全部历史属于已知/适应性探索，任何正收益不构成新的独立样本外或前瞻证据。主配置T0/R0事前固定，无事后选最好版本。','',
               '| 主候选 | 2024–2025净收益 | 最大回撤 | 2026H1已知挑战 | 压力成本 | 4H执行延迟 | 历史筛查 |',
               '|---|---:|---:|---:|---:|---:|---|']
        for family,v in families.items():
            lines.append(f"| {family} | {v['historical_replay']['net_return']:.2%} | {v['historical_replay']['max_drawdown']:.2%} | {v['known_challenge']['net_return']:.2%} | {v['stress']['net_return']:.2%} | {v['delay4h']['net_return']:.2%} | {'通过，但待前瞻' if v['historical_screen_pass'] else ', '.join(v['reasons'])} |")
        lines+=['','费用/滑点每边10+5bps，压力20+10；所有结果非年化。',
                '两族均为现货long/flat，无funding或借贷；新执行器传播volume并禁止零量bar成交，等待意图固定截止/到期。',
                '历史筛查与前瞻/真实工程准入分离，当前研究达标0、Demo准入0。跨批次多重选择未被单批PBO消除。','',
                '## 固定对照','', '| 对照 | 2024–2025净收益 | 2026H1已知挑战 |','|---|---:|---:|']
        for key,v in controls.items():lines.append(f"| {key} | {v['historical_replay']['net_return']:.2%} | {v['known_challenge']['net_return']:.2%} |")
        lines+=['','## 下一步','',
                '逐笔解释风险缩放/确认修复相对消融对照的差异，检查状态与交易成本，而非继续挑最优参数。',
                '下一家族优先实际永续多周期双向趋势、量价条件与流动性/持仓机制；先补数据、检验替代解释并另登记。',
                '前瞻shadow与账户保护工程继续推进，不用历史回测替代等待新数据。']
        (ROOT/'research/reports/BTC_LOOP_002.md').write_text('\n'.join(lines)+'\n')
        print('Summary complete; no exchange operations',flush=True)


if __name__=='__main__':main()
