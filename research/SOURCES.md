# 文献索引

核对日期：2026-10-20。以下是阅读路线，不能将未精读项表述为已复现。
全文/版本与行业迁移适用性在每篇研究笔记中继续核查。

| ID | 文献与来源 | 阶段 / 状态 |
|---|---|---|
| P01 | Bailey, Borwein, López de Prado, Zhu, The Probability of Backtest Overfitting；[作者全文](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) | Phase 0/3；本轮重点阅读定义与 CSCV 算法；不把作者稿日期与期刊版混同 |
| P02 | Moskowitz, Ooi, Pedersen, Time Series Momentum (2012)；[AQR](https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum) | Phase 2；作为趋势入门，待逐节精读 |
| P03 | Hurst, Ooi, Pedersen, A Century of Evidence on Trend-Following Investing (2017)；[AQR](https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing) | Phase 2；长期跨资产证据，不能直接外推到三个币 |
| P04 | Frazzini, Israel, Moskowitz, Trading Costs of Asset Pricing Anomalies；[作者站全文](https://pages.stern.nyu.edu/~afrazzin/pdf/Trading%20Cost%20of%20Asset%20Pricing%20Anomalies%20-%20Frazzini%2C%20Israel%20and%20Moskowitz.pdf) | Phase 1/5；多个稿本，实施前固定所用版本；机构股票成本不能直接套 crypto |
| P05 | Almgren, Chriss, Optimal Execution of Portfolio Transactions；[2000 年 12 月作者稿镜像](https://www.smallake.kr/wp-content/uploads/2016/03/optliq.pdf) | Phase 5；执行风险与临时/永久冲击的权衡；待精读 |
| P06 | Kelly, Malamud, Pourmohammadi, Trojani, Universal Portfolio Shrinkage；[NBER w32004](https://www.nber.org/papers/w32004)；[SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4660670) | Phase 4 进阶；已核对题名/作者检索结果，全文抓取失败；尚未精读，不给具体结论 |
| P07 | Lim, Zohren, Roberts, Enhancing Time Series Momentum Strategies Using Deep Neural Networks；[作者 arXiv](https://arxiv.org/abs/1904.04912) | Phase 7；Deep Momentum Networks 的实际论文题名；待精读 |
| P08 | Bailey, López de Prado, The Deflated Sharpe Ratio (2014)；[作者全文](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf) | Phase 3；试验选择偏差与非正态；待精读 |
| P09 | Ledoit, Wolf, Honey, I Shrunk the Sample Covariance Matrix；[作者全文](https://ledoit.net/honey.pdf) | Phase 4；先理解估计误差与收缩，再研究 Universal Portfolio Shrinkage |

教材用于按问题查阅，不按章节授课：

- Grinold & Kahn, Active Portfolio Management：预测、主动收益、风险预算和组合。
- Larry Harris, Trading and Exchanges：交易机制、流动性和实施成本。
- Antti Ilmanen, Expected Returns：风险溢价、收益来源与组合视角。
- Ernest Chan, Algorithmic Trading：个人系统研究与实施的补充，不替代统计验证。

论文笔记模板：问题 → 关键词 → 经济机制 → 数据/假设 → 方法 → 发现与证据 →
失败边界 → 对本项目意义 → 可实现项 → 复现差异 → PM 决策。

补充首批 BTC 合约/网格研究入口（2026-10-21）：

- [BIS Working Paper 1087: Crypto carry](https://www.bis.org/publications/working-paper-1087-crypto-carry)：基差经济机制与风险，待全文精读/复现。
- [OKX Spot grid FAQ](https://www.okx.com/help/spot-grid-bot-faq)：产品行为、费用与库存风险参考；产品说明不作为 alpha 实证。

## 持续循环新增文献（2026-10-21）

P10 Liu/Tsyvinski crypto动量与注意力；P11 Moreira/Muir波动管理及P12 Cederburg等对实施稳健性的反证；
P13 Hansen/Kim/Kimbrough crypto量/波动时段结构；P14 Shen/Urquhart/Wang BTC日内动量。
完整来源、实际阅读范围/访问失败与迁移限制见research/notes/BTC_LOOP_LITERATURE.md，未声明全部精读或复现。

市场状态方向：2026-10-21重读Moreira/Muir Yale作者稿引言p1–6，非全篇复现；AQR Century网页已读。Ang/Bekaert How Regimes Affect Asset Allocation与Ang/Timmermann综述仅检索摘要，NBER403，未精读。边界与本轮用途见research/notes/BTC_REGIME_RESEARCH_029_032.md。
