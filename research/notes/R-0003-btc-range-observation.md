# BTC 围绕 8 万震荡：首轮观察，不是 alpha 结论

观察时间：2026-10-20 15:41 UTC（北京时间 23:41）。OKX BTC-USDT 最新成交约 82,591.5 USDT。
数据来自无签名 Global 公开市场，不是 Demo 账户成交；快照不代表阅读本文时的实时价格。

| 完整 UTC 日线窗口（右边界不含） | 盘中最低–最高 USDT | 首条至末条收盘价变化 |
|---|---|---|
| 2026-10-13 → 2026-10-20，7 条 | 79,775.1–84,166.3 | -1.48% |
| 2026-09-20 → 2026-10-20，30 条 | 79,775.1–87,399.0 | +0.94% |
| 2026-07-22 → 2026-10-20，90 条 | 62,268.5–87,399.0 | +23.94% |

收盘变化跨 N-1 个间隔；高低覆盖 N 条完整 bar。今日未完成日线没有加入统计。
短窗口确实符合近期横盘描述；长窗口含明显上涨。选窗口本身已有人工选择，
不能把上述变化当作均值回归显著性、平稳性或未来盈利证据。

## 怎样把 PM 的观察变成可检验策略

已登记一个草案：[R-0003 研究计划](../proposals/R-0003-btc-range-reversion.md)。
先做 BTC 现货 long/flat，近期标准化偏离较低时考虑买入、回到近期中心或超时退出。
止损阈值、单次入场、不加杠杆和禁止越跌越加仓是草案约束；细节仍待冻结和因果回放。
不用绝对 80,000 锚点，不事后画固定上下界，不因横盘看着适合就启动无限网格。

真正检验：在当时可得的数据下，入场后反弹是否超过双边费用与滑点？
趋势行情的亏损是否吞掉震荡期利润？是否优于相同风险的现金/买入持有/简单趋势基线？
近期行情已经讨论过，只能作探索样本，后续需要冻结后的样本外和前瞻证据。

## 阅读线索与反证

- [Poterba–Summers：Mean Reversion in Stock Prices](https://www.nber.org/papers/w2343)：
  用于理解回归检验与检验力；研究的是股票、且期限不同，不能迁移成 BTC 4H 盈利证明。
- [Liu–Tsyvinski：Risks and Returns of Cryptocurrency](https://www.nber.org/papers/w24877)：
  报告 crypto 的时间序列动量证据，提醒我们趋势延续是必须正视的对立解释；
  旧样本发现也不保证当前能赚钱。这里仅核验论文入口与研究问题，尚未完成全文精读/复现。

## 复现

```sh
python3.11 research/tools/describe_btc_range.py --run data/market-audit/20261020T154059431686Z
```

原始与描述产物保存在该 ignored 目录；btc_range_observation.json 内附标准化输入哈希。
原始数据未由 Git 备份；离开本机后需另行恢复数据/重采，重采可能存在修订。
公开接口：[BTC ticker](https://openapi.okx.com/api/v5/market/ticker?instId=BTC-USDT)、
[历史日线](https://openapi.okx.com/api/v5/market/history-candles?instId=BTC-USDT&bar=1Dutc&limit=100)。
