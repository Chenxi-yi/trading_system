"""Fixed past-price descriptors and simulation calibration, never strategy PnL."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys,hashlib,platform,math,fcntl
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from tools.okx_market_audit import atomic_json
from miniquant.research.range_features import variance_ratio,past_features
from miniquant.backtest.replay import aggregate,DAY,HOUR


def stamp(s):return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()*1000)


def simulate(case,rng,n,burnin):
    if case=='iid':return rng.normal(0,.02,n+burnin)[burnin:]
    innovations=rng.normal(0,1 if case=='garch' else .02,n+burnin);returns=np.empty(n+burnin);previous=0.;variance=.000004/(1-.08-.90)
    for i,shock in enumerate(innovations):
        if case=='garch':
            value=math.sqrt(variance)*shock;variance=.000004+.08*value*value+.90*variance
        else:value=(.2 if case=='ar_pos' else -.2)*previous+shock
        returns[i]=value;previous=value
    return returns[burnin:]


def calibration_summary(records):
    valid=[r for r in records if r['status']=='descriptive'];n=len(valid)
    def describe(k):
        values=np.array([r[k] for r in valid]);return {str(p):float(np.quantile(values,p)) for p in (.05,.5,.95)} if n else None
    rejected=sum(abs(r['z_hetero'])>1.96 for r in valid);p=rejected/n if n else None
    if n:
        d=1+1.96**2/n;center=(p+1.96**2/(2*n))/d;half=1.96*math.sqrt(p*(1-p)/n+1.96**2/(4*n*n))/d;ci=[center-half,center+half]
    else:ci=None
    return dict(total_paths=len(records),valid_paths=n,undefined_paths=len(records)-n,rejected_paths=rejected,abs_z_gt1_96_rate=p,montecarlo_independent_path_wilson95=ci,vr_quantiles=describe('vr'),z_quantiles=describe('z_hetero'))


def main():
    out=ROOT/'artifacts/BTC-RANGE-FEATURES-038';out.mkdir(exist_ok=True)
    with (out/'study.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        protocol=ROOT/'research/audits/BTC-RANGE-FEATURES-038.json';contract=ROOT/'research/contracts/BTC_RANGE_FEATURES_038.json';cfg=json.loads(contract.read_text());data=ROOT/'data/market-audit/btc-overnight-20261021/trade_BTC-USDT_1H.json'
        paths=[data,contract,ROOT/'artifacts/BTC-REGIME-METHODS-037/manifest.json'];imported=[]
        for mod in list(sys.modules.values()):
            name=getattr(mod,'__file__',None)
            if name:
                p=Path(name).resolve()
                if ROOT in p.parents and p.suffix=='.py':imported.append(p)
        code=sorted(set(list((ROOT/'src').rglob('*.py'))+imported+[Path(__file__).resolve(),ROOT/'tests/test_range_features.py',ROOT/'pyproject.toml']))
        manifest=dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},code={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in code},python=platform.python_version(),numpy=np.__version__)
        mp=out/'manifest.json'
        if mp.exists() and json.loads(mp.read_text())!=manifest:raise ValueError('Frozen source/input changed')
        if not mp.exists():
            atomic_json(mp,manifest)
            for p in code+[protocol]:
                dest=out/'source_snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
        rng=np.random.default_rng(cfg['simulation']['seed']);simulated={};rawsim={}
        for case in ('iid','garch','ar_pos','ar_neg'):
            entries={str(q):[] for q in cfg['horizons_q']}
            for i in range(cfg['simulation']['paths_per_process']):
                returns=simulate(case,rng,cfg['window_returns'],cfg['simulation']['burnin'])
                for q in cfg['horizons_q']:entries[str(q)].append(variance_ratio(returns,q))
            rawsim[case]=entries;simulated[case]={q:calibration_summary(v) for q,v in entries.items()}
            print(case,'fixed simulations complete',flush=True)
        atomic_json(out/'simulations.json',rawsim)
        raw=json.loads(data.read_text());bars=[dict(ts=x['open_time_ms'],o=float(x['open']),h=float(x['high']),l=float(x['low']),c=float(x['close'])) for x in raw if x['complete']]
        four=[dict(x,complete=True) for x in aggregate(bars,4*HOUR)];features=[];missing=[]
        for i,row in enumerate(four):
            if row['end']%DAY or not stamp('2021-01-01')<=row['end']<stamp('2026-07-01'):continue
            value=past_features(four[:i+1])
            if value['status']!='descriptive_only':missing.append(dict(end=row['end'],status=value['status']))
            else:features.append(value)
        atomic_json(out/'historical_price_features.json',features);atomic_json(out/'coverage_failures.json',missing)
        for row in features:
            if row['trade_state']is not None or row['historical_publication_certified']:raise ValueError('Descriptor mislabeled as trade evidence')
        expected=(stamp('2026-07-01')-stamp('2021-01-01'))//DAY
        distribution={}
        for q in ('6','42'):
            values=[r['variance_ratios'][q] for r in features];valid=[r for r in values if r['status']=='descriptive']
            distribution[q]=dict(total=len(values),undefined=len(values)-len(valid),vr_quantiles={str(p):float(np.quantile([r['vr'] for r in valid],p)) for p in (.05,.5,.95)},fraction_vr_below1=float(np.mean([r['vr']<1 for r in valid])),overlap_not_independent=True)
        cut=stamp('2025-01-01');before=[r for r in four if r['end']<=cut];original=past_features(before)
        changed=[dict(x,c=x['c']*1.5,o=x['o']*1.5,h=x['h']*1.5,l=x['l']*1.5) if x['ts']>=cut else x for x in bars];altered=[dict(x,complete=True) for x in aggregate(changed,4*HOUR) if x['end']<=cut]
        if original!=past_features(altered):raise ValueError('Future price changed past features')
        summary=dict(simulation=simulated,historical_expected_daily_anchors=expected,historical_features=len(features),coverage_failures=missing,descriptive_distributions=distribution,latest_archived_feature_end_ms=four[-1]['end'],actual_future_perturbation_invariant=True,alpha_candidates=0,controls=0,pnl_tests=0,current_market_state_established=False,research_qualified=0,demo_ready=0)
        atomic_json(out/'summary.json',summary)
        lines=['# 038：价格回复特征与有限样本校准','', '037契约在实现/计算前已冻结；过去720个完整4H收益，q6/42去漂移重叠方差比与异方差稳健z。只看价格特征，未读策略收益/未来OI标签或拟合盈利状态。没有交易状态或alpha标签。','', '| 模拟过程 | q | 有效/总路径 | VR5/50/95分位 | abs(z)>1.96比例 | 独立模拟路径95%Wilson区间 |','|---|---:|---:|---|---:|---|']
        for case,groups in simulated.items():
            for q,r in groups.items():lines.append(f"| {case} | {q} | {r['valid_paths']}/{r['total_paths']} | {json.dumps(r['vr_quantiles'])} | {r['abs_z_gt1_96_rate']:.1%} | {json.dumps(r['montecarlo_independent_path_wilson95'])} |")
        lines+=['', f"历史完整日锚{len(features)}/{expected}，不足/失败{len(missing)}，所有状态保留；此为价格覆盖，不认证可交易性。",'', '| q | 历史VR5/50/95分位 | VR<1占比 |','|---|---|---:|']
        for q,r in distribution.items():lines.append(f"| {q} | {json.dumps(r['vr_quantiles'])} | {r['fraction_vr_below1']:.1%} |")
        lines+=['', 'IID/GARCH为无收益序列相关的模拟零假设，正负AR1只作敏感性；这些是独立模拟路径，历史滚动锚高度重叠，不使用普通二项区间假装独立市场证据。有限样本假警报/功效会偏离渐近理论；不按本次结果改q、窗口、种子或判定阈值。','', 'VR<1不等于价格平稳、固定中心/边界可靠或扣成本后有alpha。60日方向、20日波动独立记录，不把低效率/高波动当均值回复。尚无交易门控、信号、预测收益、样本外净利润或当前BTC阶段结论。历史available_at为完成bar结束假设，非真实原始发布时间，前瞻需真实收到时间。','', f"最新存档4H结束{datetime.fromtimestamp(four[-1]['end']/1000,timezone.utc).isoformat()}，不冒充当前市场。实际未来扰动不改过去特征。",'', '下一项要先解释模拟校准/有限样本与价差机制，之后另冻真正状态适配研究，不能将这张分布表直接阈值化挑收益。研究0/Demo0，无策略配置增量。']
        (ROOT/'research/notes/BTC_RANGE_FEATURES_038.md').write_text('\n'.join(lines)+'\n');print('Completed descriptors and fixed calibration; no strategy returns read',flush=True)
if __name__=='__main__':main()
