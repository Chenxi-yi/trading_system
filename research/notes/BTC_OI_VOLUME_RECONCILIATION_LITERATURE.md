# OI与成交量自洽：增量数据进入研究前的检查

一手来源：[Giagkiozis & Said, Reconciling Open Interest with Traded Volume in Perpetual Swaps, Ledger 9 (2024), v2](https://arxiv.org/html/2310.14973v2)。已读第2–4节方法、数据与表格；并非只读摘要。

论文以2023年两段逐笔数据比较多场所。开仓、换手、平仓使每笔OI变化为增加、不变或减少，数量变化受成交量约束：同一市场/同一数量单位下，绝对OI变化≤区间成交量；累加绝对变化给出最低所需成交量。作者报告不一致，但无法仅凭此识别错误发生在OI还是成交报告；消息时间不同步也是解释线索。它研究数据质量，不证明可交易收益。

## 本项目决策与尚未执行的审计

010的checksum/完整网格只证明所取副本与文件结构，不能认证经济量。先确认archive的sum_open_interest单位、一边或两边计数、区间标签及历史更改，才能做数量约束。必须使用同场所、同BTCUSDT线性永续的成交数据；OKX成交量不能拿来约束Binance OI。不能拿随价格变化的OI名义美元价值直接套数量不变量。

将DATA-015列为backlog：固定日期/请求预算后，取得相同市场成交量，再冻结时间边界、容差和缺失处理做独立质量审计。若只能作时间/单位假设，结果标记假设下诊断，不能定性造假或认证有效；宽区间不违例也不证明细粒度数据完整。此处未取新成交数据、未算条件收益、未增加alpha配置。

备选论文[Cheng et al., Liquidation, Leverage and Optimal Margin in Bitcoin Futures Markets](https://arxiv.org/abs/2102.04591)本次只检索摘要，尚未精读，不据此设置OKX风险或杠杆参数。PM取消carry收益不变。
