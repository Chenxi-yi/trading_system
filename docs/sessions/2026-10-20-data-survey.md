# Session：R-0001 数据源调研

用户新增背景：OKX Bot，现货/合约/美股，准备提供模拟 API；本轮先研究可用数据并展示画面。

交付：

- research/notes/R-0001-data-source-survey.md：源、用途、端点、授权、历史和限制。
- research/tools/probe_public_sources.py：无凭证 GET-only 探测脚本。
- research/evidence/R-0001-public-probes.json：请求、观察时间、结果与响应哈希。
- 对话交互地图：线程 visualization 目录 okx-data-map.html；可选 19 类数据/工具查看详情。
- ADR-0002、章程与当前状态更新。

证据：

- 20 项公开探测：16 个数据样例成功，1 个档案 checksum 成功，3 个 HTTP 错误。
- OKX 14 项样例成功，包括三类产品、crypto K 线、两类股票产品 K 线、funding/OI/book/mark/index。
- Coinbase 日线与 Coin Metrics PriceUSD 成功。
- Binance 两项 REST 451；Bybit OI 403；不推断账户/国家，不绕过。
- BTC 2020 年初日线可取，不能据此声称完整历史可用。
- Kit 官方配置明确网格不支持 demo；尚未安装和运行。

限制：

- 无 WebSocket 测试、完整历史下载、缺口审计、付费 Key 试用或模拟账户验证。
- 当前网络允许/拒绝状态不等于服务长期可用性。
- 可视化通过浏览器初始渲染和数据集切换检查；不把 UI 验证当数据质量验证。
- 数据模块未实施，下一步是与 PM 讨论产品范围和首批数据。
