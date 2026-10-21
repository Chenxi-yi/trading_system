"""Price-only coverage audit, never select a state definition by expert PnL."""
from pathlib import Path
import json,sys,hashlib
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.okx_market_audit import atomic_json


def quantile(values,p):
    v=sorted(values);pos=(len(v)-1)*p;i=int(pos);f=pos-i
    return v[i]*(1-f)+v[min(i+1,len(v)-1)]*f


def main():
    out=ROOT/'artifacts/BTC-STATE-COVERAGE-031';out.mkdir(exist_ok=True)
    protocol=ROOT/'research/audits/BTC-STATE-COVERAGE-031.json';cfg=json.loads(protocol.read_text())
    paths=[ROOT/p for p in cfg['inputs']];code=[Path(__file__).resolve(),ROOT/'tools/okx_market_audit.py']
    manifest=dict(protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},code={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in code})
    mp=out/'manifest.json'
    if mp.exists() and json.loads(mp.read_text())!=manifest:raise ValueError('Frozen inputs changed')
    if not mp.exists():
        atomic_json(mp,manifest)
        for p in code+[protocol]:
            dest=out/'source_snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    states=json.loads(paths[0].read_text());years={}
    for year in range(2021,2027):
        rows=[r for r in states if datetime.fromtimestamp(r['available_at']/1000,timezone.utc).year==year and r['available_at']<1782864000000]
        if not rows:continue
        names=sorted(set(r['state'] for r in rows));eff=[r['efficiency'] for r in rows if r['efficiency'] is not None]
        years[str(year)]=dict(days=len(rows),state_days={k:sum(r['state']==k for r in rows) for k in names},efficiency_quantiles={str(p):quantile(eff,p) for p in (.1,.5,.9,.95)} if eff else None,confirmed_vs_raw_mismatch_days=sum(r['state']!=r['raw_state'] for r in rows),transitions=sum(a['state']!=b['state'] for a,b in zip(rows,rows[1:])))
    last=states[-1];payload=dict(years=years,last_historical_state=dict(state=last['state'],available_at_utc=datetime.fromtimestamp(last['available_at']/1000,timezone.utc).isoformat()),current_state_established=False,pnl_tests=0,orders=0)
    atomic_json(out/'summary.json',payload)
    lines=['# 031：固定状态检测器覆盖审计','', '仅读取029价格状态，不读取策略收益，不挑阈值。按状态available_at日期统计，与029按收益日开始归因日期可能差1天。','', '| 年 | 天数 | 状态天数 | 方向效率中位数 | 方向效率90分位 | 确认与原始不同天数 |','|---|---:|---|---:|---:|---:|']
    for year,v in years.items():
        q=v['efficiency_quantiles'];lines.append(f"| {year} | {v['days']} | {json.dumps(v['state_days'],ensure_ascii=False)} | {q['0.5']:.3f} | {q['0.9']:.3f} | {v['confirmed_vs_raw_mismatch_days']} |")
    lines+=['', '60日方向效率是净位移/总绝对位移，0.35要求相当连续的路径。普通有噪声上涨/下跌仍可能低于阈值，因此range只是弱路径效率，不是收益平稳、边界可靠或适合网格的认证。3日确认减少切换也造成延迟；标签不能替代其经济解释。','', f"最新历史标签{payload['last_historical_state']}；没有刷新完整bar，不宣称已判断当前BTC阶段。",'', '下一步应将趋势方向/强弱、波动水平/变化、区间边界可靠性拆成可解释维度，再独立冻结新检测器；不根据029/030收益改分界。新的状态估计必须是filtered/实时可得而非全样本smoothed，逐段未知数据验证并与连续配权比较。此为后续机制方向，不是已实现新模型。']
    (ROOT/'research/notes/BTC_STATE_COVERAGE_031.md').write_text('\n'.join(lines)+'\n');print(json.dumps(payload,ensure_ascii=False))
if __name__=='__main__':main()
