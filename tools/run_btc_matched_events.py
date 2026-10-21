"""BTC-MATCH-005, immutable descriptive four-cell matching diagnostic."""
from datetime import datetime,timezone
from collections import Counter
import fcntl,hashlib,json,platform,sys
from pathlib import Path
from statistics import mean,median
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from miniquant.research.matched_events import features,ordinary_events,match_events
from miniquant.research.volume_events import label_events
from miniquant.backtest.replay import aggregate,HOUR
from tools.run_btc_night import stamp
from tools.okx_market_audit import atomic_json


def main():
    cfgpath=ROOT/'research/experiments/BTC-MATCH-005.json'
    cfg=json.loads(cfgpath.read_text());out=ROOT/'artifacts/BTC-MATCH-005';out.mkdir(exist_ok=True)
    with (out/'study.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (out/'manifest.json').exists():raise ValueError('Never overwrite partial/completed frozen study')
        path=ROOT/'data/market-audit/btc-overnight-20261021/trade_BTC-USDT_1H.json'
        parent=ROOT/'artifacts/BTC-EVENT-004/events.json'
        source_names=['src/miniquant/research/matched_events.py','tools/run_btc_matched_events.py','src/miniquant/research/volume_events.py','src/miniquant/backtest/replay.py','src/miniquant/accounting/spot.py','tools/run_btc_night.py','tools/okx_market_audit.py','src/miniquant/data/okx_public.py']
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        manifest=dict(protocol_sha256=sha(cfgpath),code={p:sha(ROOT/p) for p in source_names},inputs={str(p.relative_to(ROOT)):sha(p) for p in [path,parent]},python=platform.python_version())
        atomic_json(out/'manifest.json',manifest)
        for p in [ROOT/n for n in source_names]+[cfgpath]:
            saved=out/'source_snapshot'/p.relative_to(ROOT);saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(p.read_bytes())
        hourly=[dict(ts=x['open_time_ms'],o=float(x['open']),h=float(x['high']),l=float(x['low']),c=float(x['close']),v=float(x['volume'])) for x in json.loads(path.read_text()) if x['complete']]
        rows=aggregate(hourly,4*HOUR);volume={}
        for h in hourly:
            t=h['ts']//(4*HOUR)*(4*HOUR);volume[t]=volume.get(t,0)+h['v']
        for b in rows:b['v']=volume[b['ts']]
        events=features(rows,json.loads(parent.read_text()))
        treated=[e for e in events if e['volume_group']=='high']
        normal=[e for e in events if e['volume_group']=='normal']
        ordinary=features(rows,ordinary_events(rows,stamp('2021-01-01')))
        pools={'normal_shock':normal,'ordinary_decline':ordinary};pairs={};cells={}
        for name,pool in pools.items():
            pairs[name]=match_events(treated,pool,name=='normal_shock')
            # Outcome labels are loaded only after the donor choices are fixed.
            donor_labels={e['signal_ms']:e for e in label_events(pool,hourly)}
            treated_labels={e['signal_ms']:e for e in treated}
            matched=[p for p in pairs[name] if p['status']=='matched']
            reuse=Counter(p['donor_ms'] for p in matched)
            for horizon in (24,72):
                key=name+'_'+str(horizon);valid=[]
                for pair in matched:
                    t=treated_labels[pair['treated_ms']]['labels'][str(horizon)]
                    d=donor_labels[pair['donor_ms']]['labels'][str(horizon)]
                    if t['status']!='labeled' or d['status']!='labeled':continue
                    valid.append(dict(pair,treated_base=t['base_net'],donor_base=d['base_net'],difference=t['base_net']-d['base_net'],stress_difference=t['stress_net']-d['stress_net']))
                periods={}
                for label,start,stop in [('2021-2023','2021-01-01','2024-01-01'),('2024-2025','2024-01-01','2026-01-01'),('2026-known','2026-01-01','2027-01-01')]:
                    v=[p['difference'] for p in valid if stamp(start)<=p['treated_ms']<stamp(stop)]
                    periods[label]=dict(n=len(v),mean_difference=mean(v) if v else None)
                avg=lambda field:mean(p[field] for p in valid) if valid else None
                cells[key]=dict(treated_total=len(treated),matched=len(matched),unmatched=len(treated)-len(matched),usable=len(valid),missing_labels=len(matched)-len(valid),unique_donors=len(reuse),maximum_donor_reuse=max(reuse.values(),default=0),treated_mean=avg('treated_base'),donor_mean=avg('donor_base'),mean_difference=avg('difference'),median_difference=median(p['difference'] for p in valid) if valid else None,stress_difference=avg('stress_difference'),severity_gap=avg('severity_gap'),trend_z_gap=avg('trend_z_gap'),log_sigma_ratio=avg('log_sigma_ratio'),subperiods=periods)
                atomic_json(out/(key+'-pairs.json'),valid)
        atomic_json(out/'matches.json',pairs)
        summary=dict(id=cfg['experiment_id'],completed_at=datetime.now(timezone.utc).isoformat(),cells=cells,ordinary_pool=len(ordinary),new_alpha_candidates=0,research_qualified=0,demo_ready=0,interpretation='Adaptive historical descriptive matching; reused donors and residual confounding preclude iid significance or causal interpretation. Ordinary baseline not severity matched.')
        atomic_json(out/'summary.json',summary)
        lines=['# BTC-MATCH-005：相近冲击与市场状态对照','',f"完成：{summary['completed_at']}。先冻结规则，再生成匹配结果。全部历史已知，4个描述比较，无策略晋级。",'',
        '高量下跌事件沿用004。正常量冲击对照要求：同此前30日趋势方向，趋势标准化距离≤1，此前波动比≤2，冲击强度差≤0.5σ。普通下跌参照只匹配趋势与波动，故不能隔离冲击强度。',
        '候选对照必须发生在处理事件前73小时至365日内，最长72小时标签在决策时已经成熟；固定最近距离、平局取较新事件。匹配不读取未来收益，也不因标签缺失重新选对照。允许重复使用，但明确披露。','',
        '| 对照/小时 | 匹配/179 | 可用 | 唯一对照/最多复用 | 高量均值 | 对照均值 | 配对均差 | 压力均差 |','|---|---:|---:|---:|---:|---:|---:|---:|']
        for key,c in cells.items():
            lines.append(f"| {key} | {c['matched']} | {c['usable']} | {c['unique_donors']}/{c['maximum_donor_reuse']} | {c['treated_mean']:.3%} | {c['donor_mean']:.3%} | {c['mean_difference']:.3%} | {c['stress_difference']:.3%} |")
        lines+=['','| 对照/小时 | 未匹配 | 标签缺失 | 冲击σ平均差 | 趋势z平均差 | log波动比均值 |','|---|---:|---:|---:|---:|---:|']
        for key,c in cells.items():lines.append(f"| {key} | {c['unmatched']} | {c['missing_labels']} | {c['severity_gap']:.3f} | {c['trend_z_gap']:.3f} | {c['log_sigma_ratio']:.3f} |")
        lines+=['','| 对照/小时 | 2021–2023均差(n) | 2024–2025均差(n) | 2026已知均差(n) |','|---|---:|---:|---:|']
        for key,c in cells.items():
            values=[f"{v['mean_difference']:.3%} ({v['n']})" if v['n'] else '无样本' for v in c['subperiods'].values()]
            lines.append('| '+key+' | '+' | '.join(values)+' |')
        lines+=['','## 判断边界','',
        '配对均差是两个事件的收益差，不是可执行多空组合收益或NAV。复用对照使配对相关，跨日期链接可达一年；本研究不报告假设配对独立的置信区间或显著性。',
        '只对成功匹配的事件有效，不能把其高量均值直接和004全体高量均值比较。正常量对照仅覆盖有限共同支持，未匹配事件全部保留；阈值不为提高样本数而放宽。',
        '普通下跌刻意不匹配冲击强度，仅作状态参照；观察差异仍可能来自冲击、市场漂移、遗漏变量及跨批选题。历史公开OHLC仍不等于可成交报价。',
        '本研究没有新增交易策略、资金操作或模拟准入。后续若形成候选，须单独冻结交易规则，并在真实未知观测与工程验收后由PM决定晋级。']
        (ROOT/'research/reports/BTC_MATCH_005.md').write_text('\n'.join(lines)+'\n')
        print(json.dumps(cells,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
