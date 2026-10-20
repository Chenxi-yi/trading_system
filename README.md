# Personal Mini Quant Fund

面向 BTC / ETH / SOL、Daily / 4H 的长期系统化投资研究项目；第一批策略聚焦 BTC。

**当前阶段：首轮BTC历史研究与本机paper工程。没有已验证 alpha、自动下单接口或实盘授权。**

目标：找到有经济解释、样本外证据、扣除可实现成本后仍有价值的策略；允许结论是没有 alpha。

## 从这里恢复

**固定任务入口：[TASKS.md](TASKS.md)**。当前工作包：[W2 研究数据](docs/workpackages/W2.md)。
每次进入读取任务台账与 PROJECT_STATE，完成时更新任务状态、验收证据和交接。
[PM 与研究/工程负责人合作协议](docs/OPERATING_MODEL.md)规定从选题到验证、上线准备与运营的责任。

1. [项目指令](AGENTS.md)
2. [当前状态](PROJECT_STATE.md)
3. [项目章程](docs/CHARTER.md)
4. [系统架构](docs/ARCHITECTURE.md)
5. [路线图](docs/ROADMAP.md)
6. [研究与验证规范](docs/RESEARCH_PROTOCOL.md)
7. [PBO 精读与原创算例](research/notes/001-pbo.md)
8. [文献索引](research/SOURCES.md)
9. [决策记录](docs/decisions/0001-foundation.md)
10. [交接协议](docs/CONTINUITY.md)
11. [R-0001：OKX 数据源地图与实测](research/notes/R-0001-data-source-survey.md)
12. [OKX Global 框架审查与逐步验收路线（建议稿）](docs/SCENARIO_REVIEW_AND_PLAN.md)

运行场所已确定为 OKX Global；美股范围为股票永续与 x-stock 现货。
模拟账户已只读接入；[数据契约](docs/DATA_CONTRACT.md)与[首轮覆盖审计](research/notes/W2-first-coverage.md)已完成，
持续采集与历史规则仍待补齐。[BTC 区间观察](research/notes/R-0003-btc-range-observation.md)与[首批多策略计划](research/plans/BTC_FIRST_COHORT.md)已登记，含网格，首轮回测已运行，尚无通过全部研究和模拟准入门槛的策略。

## 现在可运行的内容

包含独立 CSCV 教学算例及 Demo 只读连接审计器。统一检查需要 Python 3.11+ 与可选research依赖（numpy、matplotlib）；只读审计器本身使用标准库。
教学算例使用人为构造的分块收益评分；不是回测引擎，也不是 alpha 证据。

```sh
python3.11 examples/cscv_selection_demo.py
python3.11 -m unittest discover -s tests -v
python3.11 tools/okx_demo_audit.py
python3.11 -m tools.okx_capabilities
python3.11 tools/okx_market_audit.py --page-budget 120
```

审计器固定读取根目录已忽略的 config.toml 中 profiles.demo，不使用 default_profile。
仅向 Global 官方域名发出模拟环境 GET 请求，不下单、不跟随重定向；报告在 ignored runtime/。
最近结果：14 项 GET 检查成功，六个 crypto USDT 现货/永续产品可见且费用/单位已读；四个股票样例未返回。
详见 docs/ACCOUNT_CAPABILITIES.md 与 docs/workpackages/W1_REVIEW.md。61 项统一离线测试通过；WS、真实交易链路和账户资金/库存保护尚未验收。

生产代码将按架构文档中的职责逐步建立，不以空目录和未实现接口冒充完成的系统。
阶段推进以验收证据为准，不以日历日期为准。

首轮通宵结果：[BTC-NIGHT-001 报告](research/reports/BTC_OVERNIGHT_2026-10-21.md)。
当前61项测试通过。研究测试包含numpy，可使用Python3.11环境安装可选依赖 `pip install -e ".[research]"`；
已下载数据和研究缓存不在Git内，重现需对应manifest数据；报告不表示Demo或实盘就绪。

本机paper预算与订单故障语义见[ADR-0005](docs/decisions/0005-local-paper-order-journal.md)。
公开研究复现包工具为 `tools/bundle_btc_research.py`，需干净Git检查点与已下载数据；仅本机备份，不含账户/密钥。
