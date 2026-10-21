"""Frozen6-cell downside-volume mechanism study; no alpha selection or orders."""
from datetime import datetime,timezone
import fcntl,hashlib,json,platform,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from miniquant.backtest.replay import aggregate,HOUR,DAY
from miniquant.research.volume_events import detect_events,label_events,calendar_joint_bootstrap
from tools.run_btc_night import stamp
from tools.okx_market_audit import atomic_json


def main():
    out=ROOT/'artifacts/BTC-EVENT-004';out.mkdir(exist_ok=True)
    with (out/'study.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        path=ROOT/'data/market-audit/btc-overnight-20261021/trade_BTC-USDT_1H.json'
        cfgpath=ROOT/'research/experiments/BTC-EVENT-004.json'
        cfg=json.loads(cfgpath.read_text())
        sources=[ROOT/p for p in ('src/miniquant/research/volume_events.py','src/miniquant/backtest/replay.py','src/miniquant/accounting/spot.py','tools/run_btc_volume_events.py','tools/run_btc_night.py','tools/okx_market_audit.py','src/miniquant/data/okx_public.py')]
        manifest=dict(protocol_sha256=hashlib.sha256(cfgpath.read_bytes()).hexdigest(),data_path=str(path.relative_to(ROOT)),data_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),code={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},python=platform.python_version(),numpy=np.__version__)
        manifest['fingerprint']=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
        if (out/'manifest.json').exists():raise ValueError('Preserve completed/partial run; do not overwrite a diagnostic to tune results')
        atomic_json(out/'manifest.json',manifest)
        for p in sources+[cfgpath]:
            saved=out/'source_snapshot'/p.relative_to(ROOT);saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(p.read_bytes())
        hourly=[dict(ts=x['open_time_ms'],o=float(x['open']),h=float(x['high']),l=float(x['low']),c=float(x['close']),v=float(x['volume'])) for x in json.loads(path.read_text()) if x['complete']]
        rows=aggregate(hourly,4*HOUR);volume={}
        for h in hourly:volume[h['ts']//(4*HOUR)*(4*HOUR)]=volume.get(h['ts']//(4*HOUR)*(4*HOUR),0)+h['v']
        for b in rows:b['v']=volume[b['ts']]
        events=detect_events(rows,stamp(cfg['event_start']));labeled=label_events(events,hourly)
        atomic_json(out/'events.json',labeled)
        end=max(hourly[-1]['ts'],max(e['signal_ms'] for e in events))//DAY*DAY+DAY
        bootstrap=calendar_joint_bootstrap(labeled,stamp(cfg['event_start']),end)
        cells={};periods={}
        for group in ('low','normal','high'):
            for horizon in (24,72):
                subset=[e for e in labeled if e['volume_group']==group]
                valid=[e for e in subset if e['labels'][str(horizon)]['status']=='labeled']
                ret=[e['labels'][str(horizon)] for e in valid]
                cells[group+'_'+str(horizon)]=dict(events=len(subset),executable_labels=len(valid),unavailable=len(subset)-len(valid),base_mean=float(np.mean([r['base_net'] for r in ret])) if ret else None,stress_mean=float(np.mean([r['stress_net'] for r in ret])) if ret else None,gross_mean=float(np.mean([r['gross_return'] for r in ret])) if ret else None,minimum30_met=len(valid)>=30)
                periods[group+'_'+str(horizon)]={}
                for label,start,stop in [('2021-2023','2021-01-01','2024-01-01'),('2024-2025','2024-01-01','2026-01-01'),('2026-known','2026-01-01','2027-01-01')]:
                    values=[e['labels'][str(horizon)]['base_net'] for e in valid if stamp(start)<=e['signal_ms']<stamp(stop)]
                    periods[group+'_'+str(horizon)][label]=dict(events=len(values),base_mean=float(np.mean(values)) if values else None)
        summary=dict(id=cfg['experiment_id'],completed_at=datetime.now(timezone.utc).isoformat(),manifest_fingerprint=manifest['fingerprint'],events=len(events),diagnostic_cells=6,cells=cells,subperiods=periods,bootstrap=bootstrap,calendar_end_ms=end,new_alpha_candidates=0,research_qualified=0,demo_ready=0,interpretation='Exploratory conditional event averages, not NAV/strategy returns. Every cell retained; bootstrap bands approximate and cannot correct cross-batch adaptive idea discovery.')
        atomic_json(out/'summary.json',summary)
        lines=['# BTC-EVENT-004：放量下跌后是否修复？','',f"完成：{summary['completed_at']}。预登记6格机制诊断，{len(events)}个不重叠入选事件。",'',
               '全部历史已知且适应性使用；没有新策略、NAV或前瞻盈利证明。事件间隔72h，信号结束后1h市场开盘进入，24/72h后定时开盘退出，费用/滑点每边10+5bps、压力20+10。',
               '相对成交量只用过去8周同星期/UTC4H时段中位数。当前4H跌幅超过此前30收益标准差的1.5倍；不按未来路径挑事件。','',
               '| 量组/持有小时 | 可执行标签数 | 标签缺失 | 平均成本后事件收益 | 压力成本均值 | 至少30事件 |','|---|---:|---:|---:|---:|---|']
        for key,v in cells.items():
            lines.append(f"| {key} | {v['executable_labels']} | {v['unavailable']} | {v['base_mean']:.3%} | {v['stress_mean']:.3%} | {v['minimum30_met']} |")
        lines+=['','## 不确定性','',
                '使用日历日sum/count联合块bootstrap，保留无事件日期，14/30日块各2000次。六格一起重采样，给近似同时区间；不是6次独立检验，也不能清除以前的人工选题。','',
                '| 日历块长 | 量组/小时 | 六格近似同时95%区间 |','|---|---|---|']
        for block,v in bootstrap.items():
            if 'cells' not in v:
                lines.append(f"| {block} | joint | {v['status']} |")
                continue
            for key,cell in v['cells'].items():lines.append(f"| {block} | {key} | [{cell['simultaneous_lower']:.3%}, {cell['simultaneous_upper']:.3%}] |")
        for block,v in bootstrap.items():
            if 'primary_high_minus_normal24' not in v:continue
            diff=v['primary_high_minus_normal24']
            lines+=['',f"预登记主要比较（{block}日块）：高量减正常量24h均值差{diff['observed']:.3%}，探索性5/95区间[{diff['lower5']:.3%}, {diff['upper95']:.3%}]。",'']
        lines+=['## 分时期','', '| 量组/小时 | 2021–2023均值（n） | 2024–2025均值（n） | 2026已知均值（n） |','|---|---:|---:|---:|']
        for key,v in periods.items():
            values=[f"{p['base_mean']:.3%} ({p['events']})" if p['base_mean'] is not None else '无样本' for p in v.values()]
            lines.append('| '+key+' | '+' | '.join(values)+' |')
        lines+=['','## 决定与限制','',
                '正均值可能来自BTC总体漂移、冲击强弱/市场状态差异或少数尾部，不是成交量因果效应。每格全部结果及失败/不可执行标签保留。',
                '事件均值不是资金连续使用的组合收益，不能当年化收益、Sharpe或直接相加；空闲资金、重叠风险、头寸和止损未形成交易策略。',
                '样本不足、同时区间含0或跨时期换号时不能据此挑某格晋级；新策略须另登记并接受未知数据和工程验收。',
                '事件检测不依赖未来标签，尾部缺未来价格记缺失不补0；有量OHLC仍不能认证真实可成交报价。']
        (ROOT/'research/reports/BTC_EVENT_004.md').write_text('\n'.join(lines)+'\n')
        print('Event study complete',len(events),'events',flush=True)


if __name__=='__main__':main()
