# Personal Mini Quant Fund

面向 BTC / ETH / SOL、Daily / 4H 的长期系统化投资研究项目。

**当前阶段：Phase 0 架构与研究治理。没有已验证 alpha，没有交易接口，没有实盘授权。**

目标：找到有经济解释、样本外证据、扣除可实现成本后仍有价值的策略；允许结论是没有 alpha。

## 从这里恢复

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
公开行情仅完成小样本探测；模拟账户、完整历史与数据管线仍未接入。

## 现在可运行的内容

只包含独立的 CSCV 教学算例，使用人为构造的分块收益评分；不是回测引擎，也不是 alpha 证据。

```sh
python3 examples/cscv_selection_demo.py
python3 -m unittest discover -s tests -v
```

生产代码将按架构文档中的职责逐步建立，不以空目录和未实现接口冒充完成的系统。
阶段推进以验收证据为准，不以日历日期为准。
