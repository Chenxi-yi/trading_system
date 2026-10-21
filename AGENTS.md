# 项目工作约定

## 每次进入项目

先读 TASKS.md、PROJECT_STATE.md、当前工作包文档、docs/CHARTER.md、docs/ARCHITECTURE.md、
docs/RESEARCH_PROTOCOL.md、docs/decisions/ 中相关决策及最近一份 docs/sessions/ 交接。
检查 git status 与近期提交；有未提交修改时先理解归属，不覆盖用户工作。
按需读取 roadmap、文献和实验记录，不把全部历史塞进上下文。

## 永久原则

- 用户是 PM；用问题、证据、决策沟通。中文解释，代码标识符英文。
- 合作责任遵循 docs/OPERATING_MODEL.md：Agent 承担研究/工程全链路推进与反证；PM 决定目标、资金风险和重大晋级。
  授权内主动执行，不把常规下一步逐项交回 PM；角色分工不冒充独立团队，盈利不作为可承诺结果。
- Prediction、alpha、strategy、portfolio、PnL 不混用。盈利不保证。
- TASKS.md 是唯一任务状态入口：所有已知工作、依赖、阻塞和验收证据集中登记；新增工作及时登记。
- 用户已接受 W1–W3，已指示启动 W2 并研究 BTC 近期震荡候选；工作包认可不等于资金风险数值或实盘授权。
- Phase 0：架构与研究治理；策略、数据、风控和交易能力是否实现必须据实报告。
- 首批策略聚焦 BTC（PM 最新决定）：趋势、均值回归、有限现货网格、永续突破与恒定比例再平衡；PM已取消carry收益研究。
  系统总体范围仍含 BTC/ETH/SOL 与股票相关产品；保留已有数据。Daily/4H 按研究族区分，不默认多个 BTC 策略构成分散。
  首批研究计划见 research/plans/BTC_FIRST_COHORT.md；先简单可解释 baseline，再 crypto 数据，再 ML。
- 用户已指定 OKX 运行，范围现货/合约/美股相关产品；模拟 API 已只读接入。
  已确认 Global 站点，美股为股票永续与 x-stock 现货。数据源调研后先与 PM 讨论，再实现数据模块。
- 任何研究都记录失败、试验族、参数搜索和人工筛选；不能删除失败以美化结果。
- 时间语义是契约：event_time / available_at / ingested_at，决策只能使用当时可得数据。
- 先冻结研究计划、成本口径、基准和样本切分，再观察结果。测试集一旦影响修改即已污染。
- 真正的最终留出集不参与 CSCV、特征筛选或阈值优化。
- PBO 是选择过程的相对排名诊断，不是未来亏损概率、p 值或 alpha 存在概率。
- 风控独立于策略；策略不得直接下单。所有订单（包括手工调整）必须经过风控。
- PM 指定只使用 USDT 作为投入/保证金，保护预存非 USDT 资产；新买现货仓位单独归属。
  多策略共用已定 Bot 总预算，不随账户余额自动扩容；先验证抵押品模式与资金/库存隔离（ADR-0003）。
- 交易本金、杠杆、交易场所、司法辖区和实盘参数未由 PM 决定前，不自行假设。
- 未获得明确实盘授权，不发送真实订单、不转账、不索要密钥明文。
- 数据、密钥、账户信息不得进入 Git；忽略规则不等于安全扫描或备份。
- 根目录 config.toml 为用户私有凭证文件：已忽略并设为 0600；禁止打印内容或加入提交。
  连接测试显式使用 profiles.demo，忽略 default_profile；修正后 Demo REST 的 config/balance 只读认证已成功，产品/费率已完成六个 crypto 样例的只读审计；WS/交易未验证，隔离保护尚未验收。
- 先模块化单体；没有可验证需求，不引入微服务、复杂模型或大量占位代码。

## 每个有实质进展的工作单元结束

更新 TASKS.md（任务、依赖、证据和状态）、PROJECT_STATE.md（状态与下一步）；新增 docs/sessions/ 交接（事实与证据）；
重要架构/研究规则变更写 ADR；更新受影响文档。
记录执行过的检查、失败和未检查项。检查 diff；只提交本次相关、无敏感信息的文件。
提交可恢复的本地 Git 检查点；没有配置身份时报告，不伪造身份。
远端发布、实盘部署及风险预算变更须在相应授权范围内进行。
最终告诉 PM：新增能力、证据、局限、下一步理由。

## 当前可用检查

python3.11 -m unittest discover -s tests -v
python3.11 examples/cscv_selection_demo.py
python3.11 tools/okx_demo_audit.py
python3.11 -m tools.okx_capabilities
python3.11 tools/okx_market_audit.py --page-budget 120

离线测试覆盖教学算例及审计器只读/脱敏/模拟环境控制；实际脚本检查 Demo REST 能力与无签名公开市场历史，均为 GET；共 85 项离线测试。
数据契约见 docs/DATA_CONTRACT.md；覆盖与研究入口见 docs/workpackages/W2.md。本夜已获PM批准，冻结实验 research/experiments/BTC-NIGHT-001.json；先读本夜最新交接，保护封存历史样本。
生产模块建立时再加入对应的数值、时间因果、账本和故障测试。

当前通宵20配置与续跑审计已完成，最新恢复读docs/sessions/2026-10-21-overnight-phase4.md。
历史研究全门槛0通过、Demo准入0；禁止凑5个修改已访问样本或超预算搜索。
固定原WF参数的延迟诊断与paper工程不改变原结论；原runner指纹拒绝是保护，不删除manifest绕过。
worker已完成；恢复时仍先检查进程与锁，避免重复采集/写入；本夜heartbeat关闭状态见最新交接。

## 2026-10-21持续循环新授权

PM已明确要求失败后继续提出新机制并研究，见ADR-0006和research/plans/BTC_RESEARCH_LOOP.md。
旧20配置预算/结果不改；允许独立冻结后续批次，当前累计28alpha+6固定对照、68测试。
最新恢复入口docs/sessions/2026-10-21-research-loop.md与research/loop/checkpoint.json；先运行tools/research_loop_status.py。
btc现每4小时ACTIVE；单次最多1批、每天最多2新批，每批8alpha+4对照，每3批做方法审计。
所有已看历史只作适应性探索，不以累计搜索/PBO冒充独立新OOS；无交易/新增付费授权。

## 最新调度纠正（ADR-0007）

PM要求资源可用立即推进，不等定时；取消Agent自设每日2批节奏，单批预算和证据门槛不改。
btc为15分钟中断恢复保险；前台顺序继续有意义研究/数据/工程，不能把ACTIVE说成在计算。
当前36alpha+10对照，79测试；最新交接2026-10-21-foreground-loop003.md。
下一步量价事件诊断/公开前瞻观测，累计登记与三批方法审计保留；无资金操作授权。

最新恢复交接2026-10-21-event004.md；004六格365事件机制诊断已完成，不新增alpha配置（仍36+10），85测试。
主24h比较不确定，高量72h不能凭均值晋级；下一步匹配机制对照，保持原历史已知属性。

最新恢复交接2026-10-21-pressure006.md；005匹配诊断/006压力数据审计已完成，93测试，累计36alpha+10固定对照、10机制格；0研究/0Demo。长期指数8214条已补，funding另建4107笔新快照；下一步先登记压力过滤增量研究，禁止把历史可得时点假设当真实观测。

最新恢复2026-10-21-loop007.md；007三候选+2对照全失败，累计39alpha/12对照，101测试。三新批审计BTC_ADAPTIVE_LOOP_REVIEW_007.md；恢复额外运行tools/observe_btc_pressure.py保存实际压力观测。不得看8H较好就改主结果；无模拟晋级。

PM已解除人工暂停，ADR-0008额度调度已批准：每次恢复/每批前后先真实读get_usage_limits，脱敏stdin送tools/research_quota_gate.py，低于10%保存并通过应用工具预约刷新后复核；不买/不用重置券，人工暂停优先。最新2026-10-21-loop008.md；43alpha/16对照、113测试，008全失败。下一步免费历史衍生品增量数据审计，勿挑R20_72优化。

009免费衍生品样例审计已完成，116测试，43alpha/16对照不变；恢复读2026-10-21-derivatives009.md。官方5日文件可取≠全历史可用，ratio缺失/乱序/时间单位未认证保留。先查真实额度，再独立冻结有界采集，不做条件PnL。

010有界归档采集已冻结/实现，121测试；首1GET发生URLError、0日0行，600秒退避，不绕路/不猜原因。最新恢复2026-10-21-collect010.md，先quota gate和data/binance-metrics/BTCUSDT-2023-2026/checkpoint.json的retry_after_epoch；源指纹不可静默改，下一段独立日志/invocation快照。累计43alpha/16对照，研究0/Demo0。
