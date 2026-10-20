# 项目任务台账（唯一任务状态入口）

更新时间：2026-10-20（Asia/Shanghai）
当前工作包：**W1 账户能力与投资边界**。用户已认可 W1–W3，开始执行准备工作。
本文件记录全部已知工作；新发现的任务在执行前或发现时登记，不能承诺预知所有未来工作。
PROJECT_STATE.md 只概述现状，任务状态以本台账为准。

## 状态与维护规则

- backlog：已知工作，尚未启动；in_progress：正在推进；waiting_input：缺特定用户输入；
  blocked：外部障碍；done：验收证据齐全；rejected/cancelled：保留原因，不删除历史。
- 每项包含 ID、负责人、依赖、验收与证据位置；投入时间或产生文件本身不等于完成。
- 关键步骤完成即落盘；结束时同步状态、交接和 Git。未推送不能写成已远端备份。
- 工作包部分受阻不阻止其余独立任务；资金/凭证缺失不影响公开数据设计。
- 每次恢复读本文件与 PROJECT_STATE.md，检查未提交修改和最新交接，再继续。

## 已完成的基础工作

| ID | 工作 | 状态 | 证据 |
|---|---|---|---|
| F-001 | 章程、架构、研究规范和交接机制 | done | docs/CHARTER.md、docs/ARCHITECTURE.md、docs/RESEARCH_PROTOCOL.md、docs/CONTINUITY.md |
| F-002 | PBO 精读与教学算例 | done | research/notes/001-pbo.md；examples/ 与 tests/；6 项测试通过见启动交接 |
| F-003 | GitHub 关联和首次同步 | done | docs/sessions/2026-10-20-github.md；首次已同步 407a374 |
| F-004 | R-0001 数据源首轮调研 | done | research/notes/R-0001-data-source-survey.md；research/evidence/R-0001-public-probes.json；仅样例可用性，不是完整覆盖审计 |
| F-005 | OKX Global 场景审查与实施路线 | done | docs/SCENARIO_REVIEW_AND_PLAN.md；用户已认可近期工作包 |
| F-006 | 固定任务台账与 W1 执行入口 | done | 本文件、docs/workpackages/W1.md、docs/INVESTMENT_MANDATE.md、docs/ACCOUNT_CAPABILITIES.md |

## W1：当前执行清单

负责人中的 Agent 指本项目助手，PM 指用户。

| ID | 任务 | 状态 | 负责人 | 依赖 | 完成条件与证据 |
|---|---|---|---|---|---|
| W1-01 | 建立投资授权草案 | done | Agent | F-005 | docs/INVESTMENT_MANDATE.md；区分已确认/待定，不编造风险预算 |
| W1-02 | 决定规模、预算与总体亏损口径 | done | PM | W1-01 | 规模/预算与本 Bot 相对初始本金的总体亏损口径已确认；私有记录 config/local/investment-mandate.json；执行阈值尚未实现 |
| W1-03 | 编写模拟凭证本机配置步骤 | done | Agent | F-005 | docs/OKX_DEMO_SETUP.md；只读、Global、demo 明确，不要求聊天发送密钥 |
| W1-04 | 用户在本机配置 demo 只读凭证 | waiting_input | PM | W1-03 | 文件已提供并受 Git 忽略/0600 保护；Demo 认证 50111，待 PM 本机核对 API Key；Key 权限尚未核验 |
| W1-05 | 实现受限只读账户审计器 | done | Agent | W1-03 | tools/okx_demo_audit.py；GET allowlist、显式 demo、无重定向、脱敏；6 项审计器测试通过 |
| W1-06 | 核验账户模式与产品支持 | blocked | Agent | W1-04,W1-05 | 已发只读 config 请求，认证 50111；凭证修正后核验产品。见 docs/sessions/2026-10-20-demo-connection.md |
| W1-07 | 核验费率、单位与保证金/持仓模式 | backlog | Agent | W1-06 | 有对应账户只读证据；不以模拟费率推定未来实盘费率 |
| W1-08 | W1 验收与下一步决定 | backlog | PM+Agent | W1-02,W1-06,W1-07 | 支持/不支持/未知明确；未知项有降级方案；W2 首批产品与范围固定 |

W1-05 可以在等待凭证时独立完成；规模/预算与总体亏损口径已确认。
W1-05 已完成；W1-06 首次认证测试受阻，W1-07 尚未执行，没有发单。

## 后续完整工作分解

| ID | 工作包/里程碑 | 状态 | 主要依赖 | 交付与验收 |
|---|---|---|---|---|
| W2-01 | 核心数据契约 | backlog | W1 能力证据；公开部分可提前 | 产品/时间/单位/日历/版本字典及质量规则 |
| W2-02 | 历史覆盖和成本数据审计 | backlog | W2-01 | BTC/ETH/SOL 起止、缺口、funding 覆盖、费用来源；不将外所价格静默补入 |
| W2-03 | 持续数据采集与恢复 | backlog | W2-01 | 有状态采集、去重、补洞、质量告警；股票前瞻留存；单独验证 WS |
| W3-01 | 领域对象与最小账本 | backlog | W2-01 | 单位和现金/持仓守恒手算案例；资金流与收益区分 |
| W3-02 | 因果回放与模拟 broker | backlog | W3-01,W2-02 | 信号→目标→最小 Risk→订单→成交→NAV；无同 bar 偷看 |
| W3-03 | R-0002 Daily baseline 预注册与运行 | backlog | W3-02 | 假设、候选预算、基准、样本切分冻结；保存全部有效候选及失败 |
| V-001 | 样本外与选择偏差验证 | backlog | W3-03 | Walk-forward、留出、适用的 bootstrap/PBO/DSR；通过/拒绝/证据不足报告 |
| P-001 | 最小组合与完整风险规则 | backlog | W3；投入资本前需 V-001 | underlying 汇总、gross/net、现金/抵押品、压力情景、拒单和降险规则 |
| O-001 | Shadow / OKX demo 常驻运行 | backlog | W3,P-001 | 日常对账、告警、订单状态机、超时/部分成交/重启恢复演练；工程测试与投资证据分开 |
| E-001 | x-stock / 股票永续专门验收 | backlog | W2,W3；可提前记录数据 | 日历/陈旧参考价/公司行动/份额变化/保护恢复；逐产品晋级 |
| A-001 | Carry/funding/basis 等增量 alpha | backlog | 可信 baseline 与验证 | 相对已有组合的成本后增益；双腿失败和保证金单独审查 |
| L-001 | 小额 live 上线审查与校准 | backlog | V-001,P-001,O-001；对应产品验收 | PM 明确资金和权限；真实费用/成交/账差证据；短期盈亏不证明 alpha |
| L-002 | 证据驱动扩容 | backlog | L-001 | 容量/尾部/场所风险与经济利润审查；每档单独决定 |
| R-001 | 归因、策略复核与退役 | backlog | 首个运行策略 | 固定复核节奏、变更记录、隔离/恢复/退役；允许不交易 |
| ML-001 | 复杂模型增量研究 | backlog | 成熟 baseline、验证和成本数据 | 统一外层样本/风险/搜索预算的净增益，无增益不采用 |

## 项目级运行事项

| ID | 工作 | 状态 | 完成条件 |
|---|---|---|---|
| OPS-001 | 补齐 GitHub 远端同步 | blocked | 台账/W1 准备已同步至 292a48c；随后 6ad8109 起因 GitHub 443 再次超时，保留本地提交待网络恢复后补推 |
| OPS-002 | 环境锁定、CI 与恢复演练 | backlog | 随首个可运行模块建立依赖锁与相应检查；干净 checkout 可复现指定产物 |
| OPS-003 | 数据与私有运行状态备份 | backlog | 明确存储、校验和、保留与恢复验证；Git 仅备份代码/文档不代替数据备份 |
| OPS-004 | 常驻运行责任与告警渠道 | backlog | 启动常驻任务前明确运行主机、响应人、维护/更新窗口与告警路径 |

## 本次下一动作

按 W1.md 推进：等待 PM 在本机核对 profiles.demo.api_key，随后复测认证，再核验产品与费率。
后续新增子任务使用稳定 ID，保留变更与失败证据，不悄悄从台账删除。
