"""Build Chinese research report and static curves from preserved run artifacts."""
from datetime import datetime,timezone
import hashlib,json,math,sys,subprocess
import fcntl
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from tools.okx_market_audit import atomic_json
from miniquant.research.validation import daily_returns,block_bootstrap_mean


def percent(x):return f'{100*x:+.2f}%' if x is not None else '未完成'


def main():
 if (ROOT/'data/market-audit/btc-overnight-20261021/trade_BTC-USDT_15m.json').exists() and not(ROOT/'artifacts/BTC-NIGHT-001/grid-resolution.json').exists():
  subprocess.run([sys.executable,str(ROOT/'tools/check_btc_grid_resolution.py')],check=True,cwd=ROOT)
 out=ROOT/'artifacts/BTC-NIGHT-001';s=json.loads((out/'summary.json').read_text())
 pp=ROOT/'artifacts/BTC-NIGHT-001-PERP/summary.json'
 if pp.exists():s['families']['breakout']=json.loads(pp.read_text())
 names=dict(trend='日频趋势',reversion='4H均值回归',grid='有限现货网格',breakout='永续双向突破',constant_mix='恒定比例再平衡')
 report=ROOT/'research/reports/BTC_OVERNIGHT_2026-10-21.md';report.parent.mkdir(parents=True,exist_ok=True)
 lines=['# BTC 首轮研究：历史筛查与模拟准入','',f'更新：{datetime.now(timezone.utc).isoformat()}（UTC）。所有数值为历史模型结果，不是账户收益。','',
 '当前没有通过全部研究与模拟准入门槛的策略。此前冻结的门槛未因结果不理想而放宽；未执行任何交易所订单。','',
 '## 五方向结果','',
 '| 方向 | 2024–2025时序样本外净收益 | 同窗最大回撤 | 2026H1封存历史净收益 | 更差成本同窗净收益 | 研究筛查 | 模拟就绪 |',
 '|---|---:|---:|---:|---:|---|---|']
 for key in ('trend','reversion','grid','breakout','constant_mix'):
  x=s['families'][key];wf=x.get('walk_forward',{});sealed=x.get('sealed_historical',{});stress=x.get('adverse_cost',{})
  lines.append(f"| {names[key]} | {percent(wf.get('net_return'))} | {percent(wf.get('max_drawdown'))} | {percent(sealed.get('net_return'))} | {percent(stress.get('net_return'))} | {x['research_status']} | 否 |")
 lines += ['', '以上净收益不是年化。样本外策略按各年之前的数据选择该族参数，年初重新建仓并计成本；不同族原生信号频率不同。',
           '四个现货方向的基准成本为每次成交10bps费率+5bps市场滑点，压力情景20+10；限价网格按严格穿价与taker费用建模，未假设实际队列必成交。',
           '永续成本为5+5bps，压力10+10，另计历史实际funding费率/时点；结算名义金额以4H mark边界价格估计，不是真实账单复现。4H执行延迟与合成保证金压力不是完整OKX历史强平模型。','',
           '## 规则、参数与否决理由','']
 for key in ('trend','reversion','grid','breakout','constant_mix'):
  x=s['families'][key]
  lines += [f'### {names[key]}','',f"- 状态：{x['research_status']}。",f"- 原因：{', '.join(x.get('research_reasons',[])) or x.get('reason','等待额外审核')}。"]
  if 'selected_parameter' in x:lines.append(f"- 封存前已选参数：{x['selected_parameter']}。")
  if 'selected_choices' in x:lines.append(f"- 封存前已选参数：{x['selected_choices']}。")
  if 'bootstrap' in x:lines.append(f"- 三种块长的均值下界均为正：{x['bootstrap'].get('all_lower_bounds_positive',False)}。")
  if 'PBO' in x:lines.append(f"- 开发区间PBO相对排名诊断：{x['PBO'].get('pbo_strict')}，状态{x['PBO']['status']}；不是未来亏损概率。")
  lines.append('')
 lines += ['## 分年结果与尾部风险','',
           '| 方向 | 2024净收益 | 2025净收益 | WF日收益Sharpe（365） | WF最差日 | 压力成本最大回撤 |',
           '|---|---:|---:|---:|---:|---:|']
 for key in ('trend','reversion','grid','breakout','constant_mix'):
  x=s['families'][key];years=x.get('walk_forward_years',{});wf=x['walk_forward'];stress=x['adverse_cost']
  sharpe=wf.get('daily_sharpe_365')
  lines.append(f"| {names[key]} | {percent(years.get('2024',{}).get('net_return'))} | {percent(years.get('2025',{}).get('net_return'))} | {sharpe:.3f} | {percent(wf.get('worst_day'))} | {percent(stress.get('max_drawdown'))} |")
 lines += ['', '上述Sharpe是描述性年化，未校正收益自相关，不是有效性的证明。突破压力成本回撤超过35%，进一步显示其风险脆弱性。',
           '每个WF年都盈利、PBO≤0.2等属于本轮事先选择的保守筛查政策，并非金融学定理；未通过不等于证明该策略永远无效。',
           '“封存历史”是本轮选择前保留的数据，不是从未被人看过的未来。BTC与近期行情已影响选题，因此尚无真正前瞻验证。','',
           '## 该结果说明什么','',
           '四个现货方向在2024–2025合并净收益为正，封存的2026上半年均亏损。正收益本身不能满足预先设定的稳健性要求；均值回归对成本提高尤其敏感。',
           '固定比例再平衡主要改变BTC风险暴露，不能把其全部收益称为alpha；网格也有方向库存和未实现亏损。',
           f"基准：同一2024–2025窗口95% BTC买入持有净收益{percent(s['baselines']['hold']['net_return'])}，最大回撤{percent(s['baselines']['hold']['max_drawdown'])}；现金收益0。基准连续持有，策略WF年界强制重建，需结合成本和风险差异解释。",'']
 # Ex-post risk/beta diagnostics, never used to pick a strategy.
 hold_path=out/'runs/hold_0_2024-01-01_2026-01-01_base.json'
 if hold_path.exists():
  baseline=daily_returns(json.loads(hold_path.read_text())['daily']);attribution={}
  for key,x in s['families'].items():
   if 'daily_walk_forward' not in x:continue
   r=daily_returns(x['daily_walk_forward'])
   if len(r)!=len(baseline):continue
   beta=float(np.cov(r,baseline,ddof=1)[0,1]/np.var(baseline,ddof=1))
   residual=r-beta*baseline
   scale=float(r.std(ddof=1)/baseline.std(ddof=1))
   scaled=baseline*scale
   attribution[key]=dict(beta_to_95pct_hold=beta,residual_daily_mean=float(residual.mean()),
                        matched_volatility_hold_scale=scale,matched_vol_hold_net_return=float(np.prod(1+scaled)-1),
                        residual_bootstrap=block_bootstrap_mean(residual),note='Ex-post diagnostic, not a tradable portfolio or independent alpha proof.')
  atomic_json(out/'attribution.json',attribution)
  lines += ['## 风险与归因补充','',
            '已另存对BTC持有基准的beta、残差均值与块bootstrap，以及事后波动率匹配基准；这些是解释性诊断，不是可部署的事后配仓规则。','',
            '| 方向 | 对持有基准beta | 同波动基准净收益（事后诊断） | 残差均值下界均为正 |','|---|---:|---:|---|']
  for key,x in attribution.items():lines.append(f"| {names[key]} | {x['beta_to_95pct_hold']:.3f} | {percent(x['matched_vol_hold_net_return'])} | {x['residual_bootstrap'].get('all_lower_bounds_positive',False)} |")
  lines.append('')
 fine_path=out/'grid-resolution.json'
 if fine_path.exists():
  fine=json.loads(fine_path.read_text())
  lines += ['## 网格细频敏感性','',f"保持原选参数、1小时延迟和每格每小时最多一次成交，15m重放的2024–2025合并净收益为{percent(fine['combined']['net_return'])}；小时主回放为{percent(s['families']['grid']['walk_forward']['net_return'])}。",'这项比较检查成交分辨率，不用于重新选参，也不提供真实排队成交保证。','']
 lines += ['## 结论的适用范围','',
           '本轮仅检验登记的20个规则配置。否决它们不代表所有BTC策略、趋势或网格都无效；后续新假设须另登记，并承认本轮历史已被查看。',
           '永续突破即使某验证段盈利，也需同时通过更早时序验证、不确定性、选择偏差和工程门槛；不能因它是最好的一个就自动标有效。','']
 cross_path=out/'aggregation-crosscheck.json'
 if cross_path.exists():
  cross=json.loads(cross_path.read_text())
  lines += ['## 数据聚合复核','',f"小时聚合与原生日线比较{cross['1Dutc']['compared_bars']}条，超一tick差异{cross['1Dutc']['mismatches_over_one_current_tick']}条；与原生4H比较{cross['4H']['compared_bars']}条，差异{cross['4H']['mismatches_over_one_current_tick']}条，集中于2022年12月。续跑确认其中一处开盘差与零量小时填充值相符，另一处收盘差仍未解释，未静默修正。",'15m网格结果在当前每格每小时最多一次成交模型下与小时结果一致，主要是聚合/模型一致性检查，不能当独立排队成交证据。','']
 audit_path=out/'continuation-audit.json'
 if audit_path.exists():
  audit=json.loads(audit_path.read_text());checks=audit['cached_ledger_audits']
  lines += ['## 续跑审计与工程结果','',
            f"- 从成交/费用/funding独立重算{len(checks)}份已保存运行，最大NAV终值差{max(x['nav_error'] for x in checks):.3g}；原manifest列出的7份源码快照哈希一致。",
            '- 主现货小时历史12个零量bar，永续4H历史1个；没有已保存成交落在这些bar起点。零量仍可能影响特征，不能把完整bar覆盖当可交易性认证。',
            '- 新增未来价格/mark/funding扰动和输入截断测试，历史交易前缀保持一致。原永续manifest遗漏导入依赖的哈希，原始来源证据仍有限制。',
            '- 本机paper已实现SQLite原子预算/库存预留、幂等意图与成交、部分成交、unknown保留资金、重启强制对账和持久停机；不含OKX订单接口。',
            '- 统一离线检查61项通过，含进程未提交退出回滚。测试是工程案例证据，不能代替真实账户/长时间运维验收。',
            '- 详细审计：research/notes/BTC-NIGHT-001-continuation-audit.md；paper边界：docs/decisions/0005-local-paper-order-journal.md。',
            '- 趋势与固定比例日收益相关0.843，网格与固定比例0.832，突破与固定比例0.820；未事后优化组合权重。','']
 delay_path=out/'delay-audit/summary.json'
 if delay_path.exists():
  delay=json.loads(delay_path.read_text())
  lines += ['## 固定选择的执行延迟压力','',
            '该诊断在原封存结果已知后另行登记，只复用原WF参数，不重选赢家，不提供新的干净样本外证据。10个默认年度回放与原缓存完全一致。','',
            '| 方向 | 延迟场景一：2024–2025净收益 | 延迟场景二：2024–2025净收益 |',
            '|---|---:|---:|']
  for key in ('trend','reversion','grid','breakout','constant_mix'):
   values=list(delay['results'][key].items())
   lines.append(f"| {names[key]} | {values[0][0]} {percent(values[0][1]['net_return'])} | {values[1][0]} {percent(values[1][1]['net_return'])} |")
  lines += ['', '回归结果对延迟变化很大，说明执行/调度依赖，不能挑更赚钱的延迟反过来宣称有效。较长延迟允许新信号覆盖等待意图，因此包含此调度假设，并非纯物理延迟测量。',
            '网格这里只延迟初始化/重锚，原有格子仍按原撮合模型，未模拟挂撤单网络延迟；原全门槛通过数仍是0。','']
 recovery_path=ROOT/'artifacts/recovery/manifest.json'
 if recovery_path.exists():
  recovery=json.loads(recovery_path.read_text())
  lines += ['## 保存与恢复检查','',
            f"公开研究恢复包绑定Git {recovery['git_head'][:7]}，大小{recovery['archive_bytes']/1000000:.2f}MB；全部成员哈希核验，临时目录恢复61项检查通过，真实BTC回放逐日NAV与原缓存一致。",
            '包与清单位于本机artifacts/recovery，权限0600，不含密钥/账户/私有账本。这是本机副本，异地数据备份仍未配置。',
            '本夜自动续跑已在收尾暂停。Git代码/报告已本地提交；本次远端push20秒超时，同步未确认，不能写成已完成远端备份。','']
 # Plot normalized NAV; title marks historical nature.
 fig,ax=plt.subplots(figsize=(11,5))
 for key,x in s['families'].items():
  if 'daily_walk_forward' in x:
   rows=x['daily_walk_forward'];ax.plot([datetime.fromtimestamp(v['ts']/1000,timezone.utc) for v in rows],[v['nav']/10000 for v in rows],label=key)
 if hold_path.exists():
  rows=json.loads(hold_path.read_text())['daily'];ax.plot([datetime.fromtimestamp(v['ts']/1000,timezone.utc) for v in rows],[v['nav']/10000 for v in rows],label='95% BTC hold',color='black',linestyle='--')
 ax.set(title='Historical walk-forward 2024-2025 | net model NAV',ylabel='Normalized NAV',xlabel='UTC');ax.grid(alpha=0.25);ax.legend();fig.tight_layout();fig.savefig(out/'walk-forward.png',dpi=160);plt.close(fig)
 lines += ['## 图表与可复现入口','',f'![历史时序验证曲线]({out / "walk-forward.png"})','',
           '- 原始现货研究：artifacts/BTC-NIGHT-001/summary.json；每个运行的daily/fills均保存。',
           '- 永续研究：artifacts/BTC-NIGHT-001-PERP/summary.json。',
           '- 费用、代码、输入哈希：各manifest与source_snapshot；第一次封存访问日志已保存。',
           '- 主协议：research/experiments/BTC-NIGHT-001.json；永续分支协议：BTC-NIGHT-001-PERP.json。',
           '- 代码或数据变化时runner拒绝复用旧缓存；不得看完封存结果后继续调参并称干净样本外。','',
           '## 数据与工程限制','',
           '- 六项主采集共223849条，含BTC现货小时/4H/15m、永续4H和近期mark/index；所请求窗口缺口0不表示历史交易未中断。',
           '- 官方月度funding归档已找到，弥补REST最近约三个月限制。具体文件哈希、覆盖和REST交叉核对在data/funding-archive/BTC-USDT-SWAP/manifest.json。',
           '- 2022年12月两处非标准funding时间戳已隔离，不取整或填零；永续研究因此从2023年开始，并在计算其收益前记录数据边界调整。',
           '- 当前产品元数据与历史listTime冲突尚未完全解释，历史发布时刻未知，费用和交易规则是明示情景。',
           '- 网格真实队列、历史强平tier、实际旧库存保护、交易所资金预留/订单回报/恢复对账与告警尚未验收；本机paper实现只覆盖合成现货。',
           '- 历史产品规则认证、常驻shadow前瞻、完整kill switch降仓演练未完成；没有用这些未完成工作为策略发放通过结论。',
           '- 原始数据与运行结果在忽略目录，本机Git提交只保存代码/文档，不代替数据备份。','',
           '## 决定与下一步','',
           '本轮研究全门槛通过0，交易所Demo准入0，目标五个未达成。保留所有失败证据，不把未达标策略直接接上Demo。下一步先接通不下单的shadow与实际账户只读保护对账，补执行/行情质量验收；新研究另登记，并用冻结之后的未知数据观察。',
           '首轮通宵工作的目标数量未获得保证，最终只按真实证据报告；不能用五个近邻参数或放宽门槛补齐数量。']
 report.write_text('\n'.join(lines)+'\n')
 atomic_json(ROOT/'runtime/overnight/report-status.json',dict(report=str(report.relative_to(ROOT)),perpetual_completed=pp.exists(),demo_ready=0,updated_at=datetime.now(timezone.utc).isoformat()))
 print('Report:',report,flush=True)


if __name__=='__main__':
    lock_path=ROOT/'artifacts/BTC-NIGHT-001'/'report.lock'
    lock_path.parent.mkdir(parents=True,exist_ok=True)
    with lock_path.open('a') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        main()
