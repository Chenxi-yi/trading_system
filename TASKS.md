# 项目任务台账（唯一任务状态入口）

更新时间：2026-10-21（Asia/Shanghai）
当前工作包：**持续BTC研究循环 + W2/W3数据执行能力 + V-001验证**。PM 最新决定首批聚焦 BTC 多策略（含网格），见 research/plans/BTC_FIRST_COHORT.md；W1 交易前保护尚未验收。
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

## 合作执行约定

PM 与 Agent 的责任、从选题到上线的十一环节及交付见 docs/OPERATING_MODEL.md。
Agent 主动承担授权内研究/实现/验证/风险与执行准备；PM 决定预算、重大风险变更与实盘启动。
角色复核不冒充独立团队，拒绝/证据不足均可为有效结论，不以保证盈利作验收。

## W1：当前执行清单

负责人中的 Agent 指本项目助手，PM 指用户。

| ID | 任务 | 状态 | 负责人 | 依赖 | 完成条件与证据 |
|---|---|---|---|---|---|
| W1-01 | 建立投资授权草案 | done | Agent | F-005 | docs/INVESTMENT_MANDATE.md；区分已确认/待定，不编造风险预算 |
| W1-02 | 决定规模、预算与总体亏损口径 | done | PM | W1-01 | 规模/预算与本 Bot 相对初始本金的总体亏损口径已确认；私有记录 config/local/investment-mandate.json；执行阈值尚未实现 |
| W1-03 | 编写模拟凭证本机配置步骤 | done | Agent | F-005 | docs/OKX_DEMO_SETUP.md；只读、Global、demo 明确，不要求聊天发送密钥 |
| W1-04 | 本机模拟凭证只读接入 | done | PM+Agent | W1-03 | PM 修正后显式 demo 认证、config/balance GET 成功；config.toml 忽略/0600；客户端只读，不推定 Key 仅有 Read 权限 |
| W1-05 | 实现受限只读账户审计器 | done | Agent | W1-03 | tools/okx_demo_audit.py；GET allowlist、显式 demo、无重定向、脱敏；6 项审计器测试通过 |
| W1-06 | 核验账户模式与产品支持 | done | Agent | W1-04,W1-05 | docs/ACCOUNT_CAPABILITIES.md；六个 crypto USDT 产品可见；四个股票样例未返回；可见性不代表订单验证 |
| W1-07 | 核验费率、单位与保证金/持仓模式 | done | Agent | W1-06 | 六产品按 feeGroup 精确匹配费率；合约张数、乘数及账户模式已读；实际杠杆和逐单保证金路径仍是交易前门槛；见 W1_REVIEW.md |
| W1-08 | W1 验收与下一步决定 | in_progress | PM+Agent | W1-02,W1-06,W1-07,W1-09 | docs/workpackages/W1_REVIEW.md：可开始 W2 数据工作；W1-09 未完成，尚无交易晋级 |
| W1-09 | USDT-only 保证金与旧资产保护审查 | in_progress | Agent | W1-06 | 只读初审为条件可行；抵押品/自动划转/费用抵扣路径及旧库存保护尚未穷尽，不能据此下单；见 W1_REVIEW.md、ADR-0003 |

W1-05 可以在等待凭证时独立完成；规模/预算与总体亏损口径已确认。
W1-04/05/06/07 已完成；14 项 GET 检查成功，离线测试合计 16 项通过，没有发单。
W1-09 的交易前隔离审查未完成；不阻塞公开数据契约与历史覆盖审计。

## 后续完整工作分解

| ID | 工作包/里程碑 | 状态 | 主要依赖 | 交付与验收 |
|---|---|---|---|---|
| W2-01 | 核心数据契约 | done | W1 能力证据；公开部分可提前 | docs/DATA_CONTRACT.md；src/miniquant/data/okx_public.py；时间/单位/未知可得时刻、质量规则已实现；23 项统一测试通过 |
| W2-02 | 历史覆盖和成本数据审计 | in_progress | W2-01 | 主数据223849条，funding55月/5025事件及REST216匹配；103运行审计见BTC-NIGHT-001-continuation-audit.md；历史listTime/交易规则与2022Dec收盘差仍未解决 |
| W2-03 | 持续数据采集与恢复 | in_progress | W2-01 | tools/okx_market_audit.py 已有页快照、哈希、检查点恢复/去重质量报告；尚缺跨运行增量合并、补洞调度/告警、股票前瞻及 WS 验证 |
| W3-01 | 领域对象与最小账本 | in_progress | W2-01；合成案例不依赖完整行情 | 现货/线性永续账本已实现，现金库存/费用/funding守恒有测试；通用领域事件/资金流与真实账户对账仍待补 |
| W3-02 | 因果回放与模拟 broker | in_progress | W3-01,W2-02 | 已实现五族因果研究回放、15m网格检查、未来扰动/截断测试；本机paper broker单独实现，未接成完整生产链路 |
| W3-03 | R-0002 BTC Daily 趋势 baseline 预注册与运行 | done | W3-02 | BTC-NIGHT-001预注册并完成趋势4配置/WF/封存；结论rejected_or_insufficient，非alpha通过；报告BTC_OVERNIGHT_2026-10-21.md |
| W3-04 | 策略子账本与预存库存保护 | in_progress | W3-01,W1-09 | paper_store合成策略子账本/旧BTC不可卖与对账已测；真实库存基线及W1-09保护未验收，见ADR-0005 |
| V-001 | 样本外与选择偏差验证 | in_progress | W3-03 | 首轮20配置WF/封存/块bootstrap/PBO完成，0全门槛通过；DSR条件不足未估计；新研究未知样本与完整引擎待续 |
| P-001 | 最小组合与完整风险规则 | in_progress | W3；投入资本前需 V-001 | 纯预检查与paper初始本金损失/订单限额/停机已测；完整gross/net/集中度/保证金/降仓与场所验证待续 |
| P-002 | 多策略 USDT 预算分配与统一执行归属 | in_progress | W3-04,P-001 | paper固定总预算分配、SQLite原子挂单/费用/库存预留已测；真实共享保证金、动态分配及合并订单归属未实现 |
| O-001 | Shadow / OKX demo 常驻运行 | in_progress | W3,P-001 | 本机paper订单/幂等/部分成交/unknown/重启/进程退出演练完成，12项案例；常驻shadow、场所Demo、真实回报恢复/告警仍未验收 |
| E-001 | x-stock / 股票永续专门验收 | backlog | W2,W3；可提前记录数据 | 日历/陈旧参考价/公司行动/份额变化/保护恢复；逐产品晋级 |
| A-002 | R-0003 BTC 区间均值回归研究 | done | W2,W3-01/02,V-001 | 本轮R-0003四配置已冻结/回测，封存-19.90%、压力成本WF为负，拒绝/证据不足；延迟敏感，不晋级 |
| A-003 | R-0004 BTC 有限现货网格研究 | done | W2,W3-01/02/04,V-001 | 本轮R-0004四配置与15m一致性已完成，封存-22.54%、真实队列未证实；拒绝/证据不足，不晋级 |
| A-004 | R-0005 BTC carry 候选与双腿风险 | cancelled | PM 2026-10-21 决定 | PM取消本轮资金费收益策略，保留历史；合约 funding 成本仍须计入 |
| A-005 | R-0006 BTC USDT 永续波动压缩后突破 | done | W2-02,W3,P-001,V-001 | 本轮R-0006四配置含实际funding/mark完成，封存+24.66%但2025亏损、统计不稳；合成margin非真实强平，不晋级 |
| A-006 | R-0007 BTC/USDT 恒定比例再平衡候选 | done | W3,V-001；本夜已获PM批准 | 本轮R-0007四比例完成，封存-16.76%、交易数及稳定性不足；属于风险暴露管理候选，不证明alpha |
| A-001 | Carry/funding/basis 等增量 alpha | cancelled | 可信 baseline 与验证 | PM取消本轮carry/funding收益研究；仅保留合约funding成本/风险数据，不擅自重启收益策略 |
| L-001 | 小额 live 上线审查与校准 | backlog | V-001,P-001,O-001；对应产品验收 | PM 明确资金和权限；真实费用/成交/账差证据；短期盈亏不证明 alpha |
| L-002 | 证据驱动扩容 | backlog | L-001 | 容量/尾部/场所风险与经济利润审查；每档单独决定 |
| R-001 | 归因、策略复核与退役 | backlog | 首个运行策略 | 固定复核节奏、变更记录、隔离/恢复/退役；允许不交易 |
| ML-001 | 复杂模型增量研究 | backlog | 成熟 baseline、验证和成本数据 | 统一外层样本/风险/搜索预算的净增益，无增益不采用 |

## 项目级运行事项

| ID | 工作 | 状态 | 完成条件 |
|---|---|---|---|
| OPS-001 | 补齐 GitHub 远端同步 | blocked | 本次push再次20秒超时；代码/报告本地Git已保存，远端未确认，不无限重试；恢复网络后补推main |
| OPS-002 | 环境锁定、CI 与恢复演练 | in_progress | Python3.11、research依赖版本与85测试已建立；干净研究包恢复检查由N-023记录，CI和完整依赖锁未完成 |
| OPS-003 | 数据与私有运行状态备份 | in_progress | N-023创建显式公开研究复现包并哈希恢复检查；仅本机副本，不含凭证/账户，异地数据与私有状态备份尚未配置 |
| OPS-004 | 常驻运行责任与告警渠道 | backlog | 启动常驻任务前明确运行主机、响应人、维护/更新窗口与告警路径 |

## 本夜首轮结果与下一动作

PM已批准并已执行；五族20配置研究完成，全门槛通过0，Demo准入0，未下单。
结果入口 research/reports/BTC_OVERNIGHT_2026-10-21.md，固定协议 research/experiments/BTC-NIGHT-001*.json。
历史未通过/不足结论保留；DSR未估计，真实强平/队列/前瞻工程等未验收，不放宽门槛凑赢家。

下一步先W1-09实际保护对账，再不下单shadow数据/时钟/日志/恢复闭环。
新研究另登记未知观察期；不能在本轮已访问历史反复优化后继续叫干净OOS。
新增任务 N-025：无成交/无报价状态传播与信号等待意图TTL，避免把零量bar当流动性；
N-026：补全每次研究manifest的传递依赖/环境与恢复契约；不追溯伪造旧证据。
这些工作分别归属W2-03/W3-02和OPS-002，未实施，保持backlog。

## 本夜运行检查点

主worker已完成，六项主行情223849条；官方funding55月5025事件，2022异常时间戳隔离。
03:20已实际恢复，未重复启动旧采集或研究进程。默认WF10年度回放与旧缓存一致；
追加延迟审计只是固定选择的事后压力，不额外搜索或推翻原结论。
统一61项测试通过，完整研究报告与数据审计、paper边界见最新phase4交接。

## 03:20 续跑工作单元（已批准范围）

| ID | 工作 | 状态 | 依赖/验收 |
|---|---|---|---|
| N-021 | 2022Dec 聚合差异、零量 bar 与历史成交审计 | done | 103份成交/费用/funding重算终值误差≤4.19e-11，原7源码快照匹配；零量bar无缓存成交，2处跨频差保留；审计note与JSON |
| N-022 | 本机 paper 资金预留与持久订单故障演练 | done | paper_store及12项并发/故障/恢复/库存测试通过；ADR-0005明确合成现货边界，无交易所连接 |
| N-023 | 因果截断与研究复现包恢复检查 | done | 公开研究包约29MB，全部成员哈希核验、首轮恢复61测试及真实BTC默认回放NAV逐日完全一致；artifacts/recovery/manifest.json；仅本机副本 |
| N-024 | 晨间总结、统一状态与关闭本夜续跑 | done | 报告/任务/交接已保存，btc已PAUSED；本地检查点7adaaad，push20秒超时，远端未确认；完整未验收项保留 |
| N-025 | 无报价/零量状态与等待意图TTL | backlog | W2-03/W3-02；传播volume/venue状态，禁止无依据成交，长延迟覆盖政策显式化 |
| N-026 | 研究传递依赖/环境manifest完整性 | backlog | OPS-002；原perp未记导入依赖，下一次冻结必须递归绑定代码与环境 |

## 持续研究循环（PM于2026-10-21明确授权新想法与后续迭代）

| ID | 工作 | 状态 | 依赖/验收 |
|---|---|---|---|
| LOOP-001 | 有记忆的研究循环、累计尝试与定时续跑 | done | ADR-0006、research/loop注册表/资源策略/检查点、research_loop_status.py；btc已ACTIVE，后由ADR-0007改15分钟恢复；新批不改旧20配置 |
| LOOP-002 | BTC相关论文与失败机制复盘 | done | BTC_LOOP_LITERATURE.md；5篇原始文献入口、方法/反证与迁移限制；部分全文访问失败，不称全部精读 |
| LOOP-003 | BTC-LOOP-002首批8配置+4固定对照 | done | 38个窗口/成本/延迟评估已保存，0历史筛查通过；累计28alpha+6对照；68测试；BTC_LOOP_002.md |

| LOOP-004 | 持续推进后续批次与前瞻证据 | in_progress | btc ACTIVE每15分钟恢复；ADR-0006资源约束，下一批实际永续双向/消融；前轮包恢复68测试，当前79测试；push仍待同步；无自动交易 |

| LOOP-005 | 立即执行BTC-LOOP-003实际永续双向多周期与消融 | done | 8候选+4对照/76窗口情景均完成，主P0两年+12.11%、挑战+13.21%但未达标；76账本复核；累计36alpha+10对照 |
| LOOP-006 | 三批后的方法/信息审计与不中断推进 | done | BTC_FIRST_THREE_COHORT_REVIEW.md；配对bootstrap增量不确定；ADR-0007取消时间闲置，恢复15min |

| LOOP-007 | 前瞻公开OI/盘口/行情快照观测 | in_progress | 首次5种快照GET成功且fresh，实际first-observed时刻；observer可恢复，每15min稀疏观测，非连续WS/策略前瞻PnL |

| LOOP-008 | 放量/缩量下跌后的路径机制诊断 | done | 004预登记6格/365事件，联合日历bootstrap主比较含0，未晋级；完整report/尾部审计/源码快照保留 |

| DATA-009 | 公开观测原始哈希与重放验真 | done | SHA256验证+篡改拒绝测试；10个实际raw重放规范结果一致，不覆盖；85统一测试 |

| LOOP-009 | 相近冲击/市场状态的匹配机制对照 | done | BTC-MATCH-005预登记4比较；相近冲击匹配112/179，72h净事件均值+0.058%、2026配对差负；复用/缺失全保留，89测试，未晋级 |

| LOOP-010 | 永续压力变量的数据与时点审计 | done | BTC_PRESSURE_DATA_006.md；8个有界GET、原funding缺末端1笔并以38重叠精确核对后补新快照；93测试，无PnL检验 |

| DATA-010 | 独立补采2023–2026Sep BTC指数4H | done | 83页/8214条完整4H，缺口重复冲突0；原样本重叠426条无差异；旧544条冻结不改 |

| LOOP-011 | 拥挤压力对既有趋势的增量减险研究 | done | 007预登记3候选+2对照，50运行、3真实数据因果扰动，主P+3.70%低于P0+12.11%，全失败；累计39+12；三新批方法审计完成 |

| DATA-011 | 压力变量真实首次观测 | in_progress | 首个独立funding/premium桶2项成功且fresh，真实HTTP接收时间/哈希/来源快照；后续每次恢复运行observe_btc_pressure.py，不是策略前瞻PnL |

| LOOP-012 | 突破失败/临时价格冲击的机制审查 | done | 008预登记4alpha+4延续对照/64运行全失败，4真实未来扰动与默认P0重放通过；累计43+16，113测试，报告/原始论文边界保留 |

| OPS-005 | PM人工暂停与额度调度讨论 | done | PM已恢复；ADR-0008/额度策略6测试通过，btc应用回执ACTIVE；按边界实际查额度、低于10%保存并预约复核 |

| OPS-006 | 真实低额度单次唤醒验收 | in_progress | 主额度9%已真实触发；应用更新原btc为14:35一次ACTIVE且配置一致；PM15:09唤醒后实查已恢复100%/67%，应用已恢复15min；14:35未带来实际续跑，自动唤醒端到端仍未通过 |

| DATA-012 | 免费长期衍生品增量信息可行性 | done | 009官方5日ZIP/CHECKSUM共10GET全部匹配；2022四ratio缺失、Sep30乱序29次/排序后完整；只证明样例可得，未认证长期覆盖/时间语义；116测试 |

| DATA-013 | 免费衍生品归档有界采集与历史覆盖审计 | in_progress | 010已冻结1369日/每次100GET，断点/哈希/锁/拒绝保护已实现，121测试；首URLError保留，退避后三段共300GET取得150日/43200行、2个字段各1缺失；15:09实际额度恢复，已续传第0005段；报告BTC_DERIVATIVES_COLLECT_010.md；完成前不做条件PnL |

| OPS-007 | 14:35额度恢复预约未实际续跑的调度诊断 | in_progress | 预约回执成功但检查点至PM15:09消息仍未恢复；原因未知，不冒充已修复；恢复15min应用成功，需后续实际触发证据 |

| DATA-014 | 已完成日文件独立完整性复核 | done | 011预登记；337raw/168完成日哈希/官方checksum/统计复核一致；2损坏/统计改写测试，统一123通过；不新增PnL或可得性认证 |
