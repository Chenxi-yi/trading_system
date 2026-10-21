# 015：当前 REST 定义与历史 CSV 的边界

2026-10-21。人工一手文档审查，不运行收益检验、不增加 alpha。

历史归档的完整性已经由014复核；这不证明字段的经济含义、计数方式或原始发布时间。机器可读结论冻结在 `research/contracts/BINANCE_METRICS_015.json`。

## 已确认的当前接口定义

依据[Binance USD-M 官方市场接口文档](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data)：

| 当前 REST | timestamp 角色 | 本轮接入 |
|---|---|---|
| openInterest | 快照 time | 无认证公开 GET |
| openInterestHist | 区间结束 | 无认证公开 GET |
| globalLongShortAccountRatio | 区间结束 | 无认证公开 GET |
| takerlongshortRatio | 区间开始 | 无认证公开 GET，5分钟结束后才视为闭合 |
| topLongShortAccountRatio / topLongShortPositionRatio | 区间结束 | 当前文档要求 API Key，排除 |

历史接口只提供近期窗口，不能凭这些 REST 说明恢复多年 CSV 的首次可得时间。文档还说明 OI 历史可能省略无成交区间；这不是对本项目133个缺失标签原因的确认。

global ratio 示例中的比例与账户分量不一致，字段文字也有混淆；不能用示例反推归档字段或强行修正原始值。016保留原始数字，只检查有限性、非负及账户份额区间，不据示例建立恒等式。

## 尚未认证

CSV 六个字段与 REST 的对应只登记为假设，不是官方映射。OI 数量单位、单边/双边计数、CSV create_time 与当前 REST 区间标签的对应、历史原始发布延迟均未认证。因此零 OI 仍不能解释为去杠杆，也不能直接与其他交易所成交量比较或检验条件收益。

[官方归档 README](https://github.com/binance/binance-public-data)允许后续更新文件；本次 checksum 匹配只能确认当前文件完整性，不能证明当时能拿到同一版本。[Issue513](https://github.com/binance/binance-public-data/issues/513)中的字段提问未提供可据以认证的官方回答；[Issue484](https://github.com/binance/binance-public-data/issues/484)由提问者关闭，不构成维护方对修复或时间口径的确认。社区描述仅作问题线索。

## 决策

DATA-015保持未验收，不采未经单位认证的成交量来制造数量约束。另冻结016：最多5次公开 GET，实际HTTP接收作为 available_at，按端点区分开始/结束时间，只选择接收时已结束的区间；不回填历史。403/451持久阻断，禁止凭证调用和访问绕路。

下一项可验证产出是实际前瞻原始观测及其时间因果检查，不是新策略或收益证据。此前43 alpha、16固定对照的失败结果不变。
