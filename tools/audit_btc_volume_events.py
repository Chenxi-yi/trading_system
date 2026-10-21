"""Tail concentration diagnostics on all preserved event-study cells."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from tools.okx_market_audit import atomic_json


def main():
    out=ROOT/'artifacts/BTC-EVENT-004';events=json.loads((out/'events.json').read_text());cells={}
    for group in ('low','normal','high'):
        for horizon in ('24','72'):
            subset=[e for e in events if e['volume_group']==group and e['labels'][horizon]['status']=='labeled']
            values=np.array([e['labels'][horizon]['base_net'] for e in subset]);ordered=np.sort(values)
            cells[group+'_'+horizon]=dict(n=len(values),median=float(np.median(values)),worst=float(values.min()),best=float(values.max()),mean_excluding_best5=float(ordered[:-5].mean()) if len(values)>5 else None,
                 best5_fraction_of_positive_payoffs=float(np.maximum(ordered[-5:],0).sum()/np.maximum(values,0).sum()) if np.maximum(values,0).sum()>0 else None,
                 median_shock_sigma=float(np.median([-e['shock_log_return']/e['prior_sigma'] for e in subset])))
    cfg=ROOT/'research/experiments/BTC-EVENT-004-AUDIT.json'
    atomic_json(out/'concentration-audit.json',dict(protocol_sha256=hashlib.sha256(cfg.read_bytes()).hexdigest(),events_sha256=hashlib.sha256((out/'events.json').read_bytes()).hexdigest(),code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cells=cells,new_alpha_candidates=0,note='After-result all-cell descriptive audit. Trimming best future outcomes is NOT an ex-ante strategy.'))
    report=ROOT/'research/notes/BTC_EVENT_004_AUDIT.md'
    lines=['# BTC-EVENT-004：尾部与替代解释审计','', '主结果已知后另登记描述性审计，全部六格保留。不是新确认/新策略，不把剔除未来赢家变成交易规则。','',
           '| 量组/小时 | 中位数 | 最差事件 | 最好事件 | 剔除最好5事件后的均值 | 最好5占正事件收益 | 冲击σ中位数 |','|---|---:|---:|---:|---:|---:|---:|']
    for key,v in cells.items():lines.append(f"| {key} | {v['median']:.3%} | {v['worst']:.2%} | {v['best']:.2%} | {v['mean_excluding_best5']:.3%} | {v['best5_fraction_of_positive_payoffs']:.1%} | {v['median_shock_sigma']:.2f} |")
    lines+=['','六格联合置信带均包含0；高量72h的正均值不是已证实优势。冲击程度/市场状态与成交量共同变化，比较不是因果识别。',
            '若正均值主要由少数未来赢家贡献，不能事后过滤后再宣称稳健；下一阶段要先解释谁提供流动性、在何种可观察状态下可能有净补偿。',
            '保持当前无达标结论，不按72h收益最好去改阈值/期限；原主要24h比较没有排除无增量。']
    report.write_text('\n'.join(lines)+'\n')
    print(json.dumps(cells,indent=2))


if __name__=='__main__':main()
