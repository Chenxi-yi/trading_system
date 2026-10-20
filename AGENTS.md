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

离线测试覆盖教学算例及审计器只读/脱敏/模拟环境控制；实际脚本检查 Demo REST 能力与无签名公开市场历史，均为 GET；共 47 项离线测试。
数据契约见 docs/DATA_CONTRACT.md；覆盖与研究入口见 docs/workpackages/W2.md。本夜已获PM批准，冻结实验 research/experiments/BTC-NIGHT-001.json；先读本夜最新交接，保护封存历史样本。
生产模块建立时再加入对应的数值、时间因果、账本和故障测试。

当前通宵已批准且已运行20配置，最新恢复读docs/sessions/2026-10-21-overnight-phase2.md。
历史研究未过全门槛，禁止为凑5个修改已访问封存样本或超预算搜索；先完成细频/实现复核和工程验收。
heartbeat btc 在03:20续跑；worker持OS锁，恢复时先检查进程与日志，避免重复采集/写入。
