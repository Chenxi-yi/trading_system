# 免费衍生品数据可行性009

先登记BTC-DERIVATIVES-DATA-009数据审计，再用10个无认证GET取5个官方ZIP及CHECKSUM；全部SHA256一致，无收益测试/新候选。

官方归档提供历史公开市场数据及校验文件，也说明归档可在发现问题后修订；当前下载的历史副本不是当年的数据版本。[官方仓库](https://github.com/binance/binance-public-data)。
普通OI统计REST只提供最近一个月，不能用该API的短窗口推断ZIP不存在长期数据。API字段timestamp的说明也不能直接作为归档create_time所有列的语义证明。[官方接口文档](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data#open-interest-statistics)。

| 样本日期 | 行数 | 原行序倒退次数 | 排序后完整5min日网格 | 数值缺失 |
|---|---:|---:|---|---|
| 2022-01-01 | 288 | 0 | True | {'sum_toptrader_long_short_ratio': 288, 'sum_taker_long_short_vol_ratio': 288, 'count_long_short_ratio': 288, 'count_toptrader_long_short_ratio': 288} |
| 2024-01-01 | 288 | 0 | True | 无 |
| 2026-06-24 | 288 | 0 | True | 无 |
| 2026-06-25 | 288 | 0 | True | 无 |
| 2026-09-30 | 288 | 29 | True | 无 |

## 能带来的新信息

- sum_open_interest / sum_open_interest_value：可望研究未平仓规模及去杠杆状态。OI包含多空双方，增加不自动等于看多；报价价值受价格变化影响，单位/估值口径未由归档说明完全认证。
- count_toptrader_long_short_ratio、sum_toptrader_long_short_ratio、count_long_short_ratio：可望研究账户/头部持仓聚集。具体分类/覆盖与历史口径不能只从字段名推断，也不等于全部市场净仓位。
- sum_taker_long_short_vol_ratio：可望研究主动交易方向倾斜。只有比率不能把多根bar直接求和当买卖净流量；需核实窗口及底层量，不能把今日ratio回填过去。

## 验收边界

当前5个样本全部有288个唯一日内时间标签；9月30日原行序有29次时间倒退，排序后仍完整。原ZIP/顺序保留，另存label-sorted-inspection，不静默把它变成可用特征表。2022样本4项ratio整日NaN，不填零；OI可读不等于这些比率自2022起都可用。
发现用户在官方repo issue491报告6月24/25时间标记问题，本次固定两个日期作为质量探针；当前下载版本未见跨日重复标签。不能因此判定历史当时没有问题，更不能把用户报告当官方确认。历史标签是区间起点/终点/快照时点及原始发布延迟仍不充分确定。
available_at保持未知；ZIP中的create_time仅是源标签。真实下载时间/原始SHA256/官方checksum都保存。数据来自Binance，与OKX产品/成交/费用不可混同；即使可作跨所信号，执行与成本仍须用OKX实际数据。
因此这里只证明5个日期可免费获取与解析，未认证全历史覆盖、时间语义或alpha。下一步应单独冻结有界/可恢复的历史采集与完整性扫描，再决定可用特征/保守延迟假设；本轮不得测试条件PnL。

工程：新增3项ZIP校验/路径布局/缺失NaN/重复标签/错误产品/负值/时间口径改变测试，统一116项通过。源码与原始数据快照在artifacts/BTC-DERIVATIVES-DATA-009，原研究43alpha/16对照与0晋级结论不变。
