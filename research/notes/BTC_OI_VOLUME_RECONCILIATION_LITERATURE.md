# OI与成交量自洽：增量数据进入研究前的检查

一手来源：[Giagkiozis & Said, Reconciling Open Interest with Traded Volume in Perpetual Swaps, Ledger 9 (2024), v2](https://arxiv.org/html/2310.14973v2)。已读第2–4节方法、数据与表格；并非只读摘要。

论文以2023年两段逐笔数据比较多场所。开仓、换手、平仓使每笔OI变化为增加、不变或减少，数量变化受成交量约束：同一市场/同一数量单位下，绝对OI变化≤区间成交量；累加绝对变化给出最低所需成交量。作者报告不一致，但无法仅凭此识别错误发生在OI还是成交报告；消息时间不同步也是解释线索。它研究数据质量，不证明可交易收益。

## 本项目决策与尚未执行的审计

010的checksum/完整网格只证明所取副本与文件结构，不能认证经济量。先确认archive的sum_open_interest单位、一边或两边计数、区间标签及历史更改，才能做数量约束。必须使用同场所、同BTCUSDT线性永续的成交数据；OKX成交量不能拿来约束Binance OI。不能拿随价格变化的OI名义美元价值直接套数量不变量。

将DATA-015列为backlog：固定日期/请求预算后，取得相同市场成交量，再冻结时间边界、容差和缺失处理做独立质量审计。若只能作时间/单位假设，结果标记假设下诊断，不能定性造假或认证有效；宽区间不违例也不证明细粒度数据完整。此处未取新成交数据、未算条件收益、未增加alpha配置。

备选论文[Cheng et al., Liquidation, Leverage and Optimal Margin in Bitcoin Futures Markets](https://arxiv.org/abs/2102.04591)本次只检索摘要，尚未精读，不据此设置OKX风险或杠杆参数。PM取消carry收益不变。

## 本次官方口径检索边界

[Binance USD-M REST市场文档](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data#open-interest-statistics)把openInterestHist的timestamp描述为区间结束毫秒时刻，并说明仅最近1月。这认证该REST字段的当前文档语义，不自动认证archive的create_time及其历史版本。数值示例不足以证明数量单位。

[官方repo issue211](https://github.com/binance/binance-public-data/issues/211)有协作者2023年提供更细粒度数据的计划；计划不是已上线验收。[issue513](https://github.com/binance/binance-public-data/issues/513)是社区用户要求澄清archive映射/时间口径的问题，本次可读页没有提供可引用的权威映射答案，不以用户提问作官方定义。未向外发issue/评论或请求服务。
