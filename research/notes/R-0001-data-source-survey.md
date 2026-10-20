# R-0001：OKX Bot 数据源地图与可用性调查

调研日期：2026-10-20（Asia/Shanghai）。状态：数据源选型调研，尚未批准数据模块实现。
用户已指定 OKX 为运行场所，范围为现货、合约、美股；准备提供模拟盘 API。
当前没有接收密钥、连接私有账户、安装 Kit 或发单。

## 结论

1. OKX 原生数据作为目标交易产品的价格、成本和产品规则事实来源。
2. 外部交易所数据是参考/交叉检验，不替代 OKX 缺失交易价格，不混成一条无来源价格序列。
3. “美股”拆成传统股票、OKX 股票永续、OKX Unified Tokenized Stocks。
   实测有 AAPL-USDT-SWAP 和 XAAPL-USDT；用户已确认 Global 站点，交易范围是股票永续与 x-stock 现货，模拟权限待测。
4. 研究使用真实公开行情；模拟盘用于验证订单/账户/账本链路。模拟盘口和成交不证明实盘容量。
5. 第一批应选产品主数据、Daily/4H OHLCV、mark/index、funding、基础盘口、账户费率/流水。
   OI、清算、链上与新闻分阶段加入，不因“能取得”就进入特征库。

## 证据等级

- 文档支持：官方说明有此数据，不表示已能下载。
- 样例已通：此环境一次小样本 GET 成功，不表示全历史完整、持续稳定或账户可交易。
- 网络受限：当前请求失败；403/451 不能推断你的账户权限，也不通过代理绕过。
- 待 Key/订阅：本轮未实测；不承诺免费计划覆盖所有所需字段。
- 完整覆盖审计：尚未执行；需要逐产品起止、缺口、重复、修订、时间单位、单位口径与许可检查。

## 数据源目录

| 数据集 | 用途（项目建议） | 如何获取 | 历史/限制与当前证据 |
|---|---|---|---|
| OKX 产品主数据 | 产品映射、最小量、合约乘数、上市/到期、有效交易范围 | `GET /api/v5/public/instruments?instType=SPOT/SWAP/FUTURES` | 三类实测成功；当前列表不是历史退市全集；不能用今日 universe 代表历史 |
| OKX 交易 OHLCV | 趋势、波动、均值回归、基准 | `GET /api/v5/market/history-candles`，`bar=1Dutc` 或 `4H`；REST 回补、WS 增量待测 | BTC Daily、ETH/SOL 4H 样例成功；BTC 2020 年初样例成功，不代表全区间完整 |
| OKX mark/index | 估值、强平风险参考、基差 | `GET /api/v5/public/mark-price`；`GET /api/v5/market/index-tickers` | BTC 样例成功；历史及计算规则仍待逐产品核验。mark/index 不是可成交价 |
| OKX funding | 永续真实持有成本、carry 候选 | `GET /api/v5/public/funding-rate-history`；长期补充官方历史文件 | 样例成功；普通历史接口约三个月。严格区分预测与实际结算费率 |
| OKX OI | 仓位增长、杠杆拥挤度候选 | `GET /api/v5/public/open-interest`；实时频道后续录制 | 当前快照成功；长历史尚未审计。contracts / coin / USD 单位不得混用 |
| OKX 盘口/成交 | spread、滑点、流动性、订单流 | `GET /api/v5/market/books`；trades/WS；历史 L2 走档案或供应商 | 五档快照成功；增量 WS 未测。不能从当前快照恢复过去盘口 |
| OKX 历史下载 | 大批量回补、研究长期成本和微观结构 | 官方 historical-data 页面；下载按产品/日期选择 | 页面称 trades 自 2021-09、candles 自 2023-07、funding 自 2022-03、L2 自 2023-03；均为门户总体范围，未逐文件验证 |
| OKX 模拟账户 | 费率、仓位、余额、订单、成交、资金流水、对账 | 私有 REST/WS，模拟凭证；`x-simulated-trading: 1`；域名按账户实体选择 | 未提供 Key，未测；账户产品列表与公开市场列表可能不同 |
| Binance | 跨所价格/funding 对照、长历史参考 | `/api/v3/klines`、`/fapi/v1/fundingRate`；data.binance.vision 日/月文件 | 两个 REST 实测 451；2025-01 BTC 日线档案 checksum 可取，但未下载 ZIP/校验内容；现货文件自 2025-01 起注意微秒时间戳 |
| Bybit | 跨所 funding / OI 对照 | `/v5/market/funding/history`、`/v5/market/open-interest`，按 symbol/category 分页 | OI 请求实测 403；历史上限与产品上市时间需逐项核验，不能假定无限回溯 |
| Coinbase Exchange | USD 现货价格交叉核验 | `/products/BTC-USD/candles?granularity=86400` | 单次最多 300 candles；无成交时可能缺 bar；4H 需从较小周期聚合。实测结果见 evidence |
| Alpaca Market Data | 真实美股参考价、成交量、基准；不承担本项目执行 | `data.alpaca.markets/v2/stocks/{symbol}/bars`，指定 `feed`，需数据 Key | 免费实时 IEX 不等于全市场 SIP；FAQ 允许无订阅查询至少延迟 15 分钟的历史 SIP；实时/最新 SIP 需相应权限；未测 |
| Massive | 美股历史 OHLC、交易/报价、拆股分红、产品参考 | REST / WebSocket / S3-compatible flat files；API Key/套餐 | 方案与历史年限相关；flat files 原始未复权，REST 默认拆股调整不等于分红总回报；未测 |
| SEC EDGAR | 公司披露、财报、事件发布时间 | `data.sec.gov/submissions/CIK….json`；`/api/xbrl/companyfacts/CIK….json` | 免费公开 JSON；遵守识别 User-Agent / Fair Access；用提交/接受时间而非财报期末构建可得信息；未测 |
| FRED / ALFRED | 宏观状态、利率、风险环境 | `/fred/series/observations` + Key；指定 vintage/realtime period | 不同序列覆盖不同；ALFRED 查当时版本以控制修订泄漏；未测 |
| Coin Metrics Community | 链上/网络指标及参考价格 | `community-api.coinmetrics.io/v4/timeseries/asset-metrics`；先查 catalog | BTC PriceUSD 样例成功；仅证明该字段，不证明 BTC/ETH/SOL 所有链上指标免费；免费子集且有许可边界 |
| CoinGlass | 多所 OI、funding、清算、ETF 流量候选 | `open-api-v4.coinglass.com`；Key 和端点对应订阅 | 未测；不同历史粒度/范围按套餐；模型化清算热图与真实清算成交事件分开 |
| Tardis | 需要时补长期逐笔、L2、funding、liquidation | HTTP replay / 下载 / API Key；OKX spot/swap/futures 分数据集 | 文档覆盖 OKX；付费和样本范围按产品查；未测。当前 Daily/4H 不优先购入全量 L2 |

普通 K 线 API 与历史下载门户覆盖可以不同。不能用门户 2023 年起点否定 REST 能返回更早日线，
也不能用一笔 2020 年记录承诺中间没有缺口。

## 美股必须分开建模

官方 [股票永续说明](https://www.okx.com/en-us/help/stock-perpetuals)：
跟踪股票价格、USDT 保证金、存在 funding/强平，不持有真实股份。
[Unified Tokenized Stocks](https://www.okx.com/stock)：
X 前缀的代币化股票价格敞口，不等于公司实际股权；适用自己的公司行动规则。
[上市公告](https://www.okx.com/en-gb/help/okx-to-list-unified-tokenized-stocks-for-spot-trading)
说明产品从 2026 年 7 月开始上市，产品历史很短。

设计影响（我们的判断）：

- AAPL、XAAPL-USDT、AAPL-USDT-SWAP 是三个不同 instrument，记录 underlying 关联而非合并。
- 真实股票长期价格能用于研究信号，但不能当作 OKX 合约过去的成交、funding 或流动性历史。
- 储存 calendar/session、America/New_York 时区、DST、holiday、公司行动、参考价陈旧程度。
- 传统市场休市时，OKX 产品仍可能交易；必须记录参考来源的停更和周末基差风险。
- 股票 4H bar 要明确跨哪些 session，不默认与 crypto 24/7 4H 是相同统计对象。
- 代币化产品的股息处理可能影响持仓数量；需要 ledger 的 corporate-action 事件。
- 不默认 ticker 前缀足以分类，产品元数据及官方规则要共同核验。

## Agent Trade Kit

已核对 [官方仓库](https://github.com/okx/agent-trade-kit)、
[配置](https://github.com/okx/agent-trade-kit/blob/github-main/docs/configuration.md)、
[Bot 模块](https://github.com/okx/agent-trade-kit/blob/github-main/docs/modules/bot.md)。

它是把 CEX API 暴露为 CLI/MCP 工具的接口层，包含行情、账户、交易、条件订单、网格/DCA。
不是独立基础行情源，也不是已验证 alpha 库。CEX Kit 与 OnchainOS/DApp 钱包工具不能混用。
配置文档支持 demo profile 与 read-only；明确指出网格 bot 端点不支持 demo。
不能外推所有 DCA/特殊产品均可模拟；需逐端点测试。
仓库说明和不同版本文档的工具数量、包名存在差异；实施时固定 tag/SHA/包版本，
使用当前配置文档的 scoped 包并核对实际 release，不在这次调研中安装最新版或执行远程脚本。

建议：

- Kit：交互查询、排障、受控模拟操作。
- REST/WS/文件采集：可重放研究与长期采集主路径。
- 我们的 Risk / accounting / experiment registry 不外包给 Kit。
- 原生网格 bot 在场所自行产生子订单，不能声称每个子订单已过本地风控；
  如未来采用，需要单独的委托资本上限、子订单监控、停止与持仓回收协议。
- 现成 Martingale/DCA 会改变尾部风险，不能因“自带策略”绕过验证。

## 数据模块讨论草案（尚未实施）

建议先落以下六张逻辑表：

1. instrument_versions：场所/环境/产品/underlying/合约单位/生效时间。
2. bars：trade/mark/index 分开，bar 时区、confirm、event_time、available_at、ingested_at。
3. funding_events：预测快照与实际结算分开；实际 interval，不固定 8h。
4. liquidity_snapshots：bid/ask/spread/可成交深度，来源与采样时间。
5. account_events：demo/live 隔离；订单、成交、手续费、现金流和公司行动。
6. source_manifests：覆盖、字段单位、许可、修订/哈希、缺口、网络状态和采集版本。

有需要再加 OI、公司行动日历、宏观 vintage、链上和第三方派生指标表。
不自动用外所价格填补 OKX 缺失；应标记不可用或改变研究区间。
所有访问能力为时间相关的状态，不把一次 200 等同生产 SLA。

## 下一步决策

产品类型及站点已确认：股票永续 + x-stock 现货，OKX Global。用户在本机安全配置模拟 Key 后，
只读核对账户模式/可交易产品/费率；再讨论是否开始 data adapter，实现前冻结数据契约。
不要求用户把 Secret/Passphrase 发进聊天或 Git。

## 官方来源

- [OKX API](https://app.okx.com/docs-v5/en/)（所打开页面含区域化域名，不能直接套给用户）
- [OKX 历史数据](https://www.okx.com/historical-data)
- [Binance 公共档案与校验和说明](https://github.com/binance/binance-public-data)
- [Binance OI 历史窗口](https://developers.binance.info/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data)
- [Bybit funding](https://bybit-exchange.github.io/docs/v5/market/history-fund-rate)
- [Bybit OI](https://bybit-exchange.github.io/docs/v5/market/open-interest)
- [Coinbase candles](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles)
- [Alpaca 市场数据 FAQ](https://docs.alpaca.markets/us/docs/market-data-faq)
- [Massive flat files](https://massive.com/docs/flat-files/stocks/overview)
- [Massive 公司行动](https://massive.com/blog/new-splits-and-dividends-endpoints)
- [Massive 复权口径](https://massive.com/knowledge-base/article/is-massives-stock-data-adjusted-for-splits-or-dividends)
- [SEC 数据访问](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
- [ALFRED 可得版本](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html)
- [Coin Metrics API](https://docs.coinmetrics.io/api/v4/)
- [Coin Metrics 许可](https://github.com/coinmetrics/product-docs/blob/master/docs/access-our-data/api/README.md)
- [CoinGlass 端点](https://docs.coinglass.com/reference/endpoint-overview)
- [Tardis OKX Swap](https://docs.tardis.dev/historical-data-details/okex-swap.md)

实测脚本：research/tools/probe_public_sources.py。
原始响应仅保存在忽略目录 data/source-audit/，不上传市场原始数据。
版本化证据摘要：research/evidence/R-0001-public-probes.json，包含请求、时间、状态、哈希与少量元数据。
