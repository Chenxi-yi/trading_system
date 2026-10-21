# 核心行情数据契约 v1

日期：2026-10-20；W2-01。实现：src/miniquant/data/okx_public.py；采集工具：tools/okx_market_audit.py。
本契约覆盖首批行情，不代表回测、特征库、交易或 point-in-time 历史已完成。

## 产品身份、来源与范围

键必须包含 venue、source_environment、kind、inst_id、bar 与事件时间。
六个执行候选产品为 BTC/ETH/SOL 的 *-USDT 现货、*-USDT-SWAP 线性永续，分别记账。
BTC/ETH/SOL-USDT 的 index 记录属于参考指数，不能因同名误作可成交现货。
source_environment=public_market 表示无签名真实市场公开数据；不读取账户配置或混入模拟成交。
Global 目标公开主机固定 openapi.okx.com；www 域名本机返回 403，本次不静默换交易所。

当前 Instrument 快照至少保存 instId、产品类型、币种/结算、ctVal/ctValCcy/ctMult、
minSz/lotSz/tickSz、listTime/expTime/state 与抓取时间。原始产品列表留存并哈希。
这只是当前观察；不能将今天的合约规格回填成过去的真实规格。
股票类产品本轮不采入执行宇宙，不修改总体研究范围。

## 时间

- 所有时间 UTC；Unix 毫秒。1Dutc 为 [00:00,次日00:00)，4H 为 UTC 00/04/08/12/16/20 开始。
- 原始 ts 为 bar 开始，open_time_ms=ts，end_time_ms=ts+周期；bar 的 event_time 表示结束边界。
- ingested_at 为本机接收时间；lineage_id 指向原始 body SHA-256。
- 历史原始数据没有真实发布时间，available_at=null，availability_basis 明确为未知。
  未来回放必须显式另设“可得延迟假设”并做敏感性测试；不能把 ingested_at 或 bar 结束当作已证实发布时刻。
- confirm=0 不进入完成 bar 集；confirm=1 却尚未到结束时间则拒绝。未来/非周期边界的 bar 拒绝。
- 信号不得使用未完成 bar；信号之后的可执行成交时点另由回放引擎定义。

## 值与单位

| 数据类型 | 规范与用途 |
|---|---|
| trade OHLCV | 成交价格和换手，价格为 USDT/base；正有限 OHLC 且 low <= open/close <= high；量非负 |
| 现货 volume | vol 为 base 数量；volCcy、volCcyQuote 为 quote 数量 |
| USDT 永续 volume | vol 为合约张数；volCcy 为 base 数量，volCcyQuote 为 USDT 数量；不可直接用张数当币数 |
| mark OHLC | 独立序列，用于衍生品估值/风险；不当作可成交报价，无伪造 volume |
| index OHLC | 独立参考指数序列，用于 basis/风险；不当作可成交报价，无伪造 volume |
| funding | fundingTime 为结算事件；realizedRate 为实际率，fundingRate 为预测字段；缺实际率保留 null，不以预测替代 |
| fees | 独立私有快照，按产品与 feeGroup、环境、观察时间版本化；正 cost_bps 表成本，不回填历史/live |

价格、量与费率均用 Decimal 校验，以字符串持久化，拒绝 NaN/Infinity，不以浮点强行修正异常。
Funding 正实际率通常表示多方向空方支付；账本按当时实际持仓和名义金额计提，不假设固定每日次数。
历史最终 funding 不能作为结算前可知的预测特征。

## 分页、存储与质量

只读 GET、固定路径/参数白名单、无认证材料、禁止重定向、有限超时/响应尺寸与重试。
每页保存请求 URL、开始/接收时间、原始 body_text 和 SHA-256；标准化前校验哈希。
解析整页成功才提交更早的 after 游标；异常不推进，恢复重试同一个游标。
原始文件先持久化，再原子替换 checkpoint；中断产生的孤儿页不作为已完成抓取。
去重与冲突按逻辑键检测；保留原始修订，存在冲突则不能标记窗口完整。
输出的第一版本标准化列表仅便于审计；冲突时不能直接拿第一条去回测。

窗口为显式 [start,end)，只计算该窗口完成数据。报告首末、条数、重复、冲突、未完成排除、
总缺失/内部缺口；缺失不填成零或复制相邻行情。
请求边界 2020-01-01 仅是此次覆盖探测范围，不是冻结研究起点，也不承诺该日已有所有产品上市。
窗口头部缺失与产品上市边界需分别核验；当前 metadata 的 listTime 不构成完整历史证据。
Funding 间隔直方图用于提示异常，不假定每 8 小时固定；无完整历史 schedule 则缺事件数未知。
所有 coverage 产物的 research_ready=false：窗口无缺口不代替因果/成本/账本验收。

## 恢复与版本

原始与标准化数据在 ignored data/market-audit/<run-id>/；覆盖报告引用运行位置。
checkpoint 冻结工作窗口与分页状态；--resume 继续该窗口。后续新行情另建新运行，
跨运行增量合并、定时调度、告警及备份仍属 W2-03 未完成项。
研究 manifest 必须绑定代码提交、原始页哈希、契约版本、成本和延迟假设；不能仅写“最新数据”。
当前 schema_version=1；字段变化需显式新版本或解析失败，不静默接受。

## 实际接收观测的as-of查询（020）

仅对实际保存的公开OI与永续盘口构建接收时点快照，不回填历史可得性。
以每个盘口HTTP接收时刻为决策时间，选择此前最近收到的OI；OI接收及数据返回标签距决策均不超过60秒，盘口标签距接收不超过30秒。
源标签不能晚于自身接收，时间必须带时区；同类同接收时刻冲突拒绝，相同副本去重。
未来才接收的OI即使标签较早也不可加入；缺失/陈旧输出不可用，不跨缺口填值。
OI REST ts只按官方数据返回时间解释，不认证为精确交易事件。盘口实际接收时刻是此工程查询的时钟，不代表策略下单或成交时刻。
020绑定32个既有raw哈希，结果只属离线时间对齐；追加观测不得改写其冻结输入，生产增量须另建快照manifest。
16个可对齐时点不等于连续采样、独立试验或前瞻策略PnL；质量报告必须同时列出观测间最大间隔。

接口依据：[OKX 官方 API](https://app.okx.com/docs-v5/en/)，本轮核验成交/mark/index 历史及 funding 字段。
