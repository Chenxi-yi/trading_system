# Roadmap：按证据晋级

OKX Global 场景下的具体推进顺序和逐步验收见 [v0.2 实施路线建议](SCENARIO_REVIEW_AND_PLAN.md)。
下面保留原有能力/阅读分期；实际工作采用研究与运行两条线并进，不需完成所有市场或 ML 才开始合格策略的模拟运行。

阶段编号表达能力顺序，不要求先完成所有研究才开始模拟交易。
Phase 8 可在 Phase 5 后先启动简单 baseline；Phase 6/7 可在影子环境并行迭代。
风控、成本和验证从第一条回测就有最低可用版本，不能拖到对应阶段才考虑。

| Phase | 学什么 / 研究问题 | 阅读 | 实现与产出 | 验收条件 |
|---|---|---|---|---|
| 0 Architecture | 信号如何转化为可审计 PnL；职责、治理、授权 | PBO；Grinold & Kahn《Active Portfolio Management》选章 | 章程、架构、ADR、状态与交接、研究规范 | 能解释数据→交易→对账；区分设计和实现 |
| 1 Research Framework | 时间因果、产品定义、数据偏差、成本与可复现性 | Harris《Trading and Exchanges》选章；PBO 方法部分 | 数据审计、raw/clean/features 清单、实验登记、时钟、账本最小案例、环境锁定 | 同一快照可复现；缺失/重复/时间泄漏失败关闭；人工核对一个交易案例 |
| 2 Trend/Momentum baseline | 趋势方向、持仓尺度、beta 与择时 | Time Series Momentum；A Century of Evidence | Daily 简单趋势；现金、买入持有、等权、风险匹配基准；限制参数试验族；净值/换手/成本报告 | 按预注册计划运行；收盘信号延后成交；无同 bar 偷看；4H 后续独立试验 |
| 3 Validation | 选择偏差、序列依赖、不稳定性 | PBO；Deflated Sharpe Ratio | walk-forward、最终留出、block bootstrap、PBO、适用时 purging/embargo；失败档案 | 完整试验族；边界/并列/缺失处理透明；不只报最高 Sharpe；结论可为拒绝 |
| 4 Portfolio & Risk | 风险预算、协方差误差、相关性、杠杆 | Honey, I Shrunk the Sample Covariance Matrix；随后 Universal Portfolio Shrinkage | 等权/逆波动基准、组合波动目标、约束优化候选、压力测试、VaR/ES、kill switch | 优化器不优于简单方法则保留简单方法；所有目标组合过风险层 |
| 5 Execution | 实现亏损、冲击、订单状态与恢复 | Trading Costs of Asset Pricing Anomalies；Almgren–Chriss | 成本校准、模拟 broker、场所 adapter、订单状态机、幂等、恢复与对账 | 部分成交/超时/断连/重启演练；模拟与账本一致；低资金不强行复杂拆单 |
| 6 Crypto-specific Alpha | funding/basis 的来源；微观数据是否增加净收益 | 场所官方产品/资金费率规则；经核验后加入 crypto microstructure 论文 | funding/OI/basis 后续到清算/订单流；逐类加入、做增量实验 | 可得时间与历史覆盖可信；与原 baseline 同成本/同风险比较；不称 carry 无风险 |
| 7 ML | 复杂模型是否提供增量价值 | Gu/Kelly/Xiu 资产定价研究待精读；Deep Momentum Networks | linear→logistic→tree→boosting→regime→DL；标签/特征/训练隔离 | 同一外层 walk-forward、搜索预算与成本下比较；无净改善不晋级 |
| 8 Paper Trading | 研究→线上偏差、运行可靠性 | 本项目运行/事故手册；复核执行文献 | 常驻调度、虚拟账本、告警、实时影子决策、每日对账、故障演练 | 覆盖足够决策/订单事件及运行场景；预先定义窗口；paper 不证明真实成交或 alpha |
| 9 Small-capital Live | 真实费用/成交/资金风险 | 交易场所最新规则与实盘审查材料 | PM 批准资金/限额；专用低权限账户；受控发布；实盘归因/事故复盘 | 数据、验证、风险、运行四项审查通过；明确停机/恢复责任；扩容需新证据 |

未设盈利、Sharpe 或完成日期保证。数据许可证、资金和可用场所可能改变实现范围。
每一阶段产出一份 decision memo：通过 / 拒绝 / 证据不足 / 延后，而不是只产出代码。
