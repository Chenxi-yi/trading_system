# 交接：W2 数据实现与 BTC 均值回归研究入口

PM 指示“开动”，补充 BTC 近期在 8 万附近震荡，要求考虑首个策略。
行动：推进 W2，登记 R-0003 草案，核实真实行情，不发任何订单。

## 代码与检查

src/miniquant/data/okx_public.py 实现无签名公共 GET、固定官方主机/路径/参数、无重定向、有限重试，
严格 OHLC/volume/时间/完成 bar 与 funding 校验；历史 available_at 保持未知。
tools/okx_market_audit.py 实现原始页+哈希、原子 checkpoint、失败不推进游标、恢复与覆盖报告。
research/tools/describe_btc_range.py 描述冻结快照，没有信号或策略 PnL。
pyproject.toml 为 stdlib 项目定义 Python>=3.11 与 src 包；未安装第三方运行依赖或声称环境已锁定。
新增 7 项有意义数据/故障测试，统一 23 项通过。已完成运行 --resume 为 0 页，无重复网络请求。

## 实际证据

本机 www.okx.com 公共端点 403；openapi.okx.com 无签名 GET 成功，明确记录主机，不换交易所。
运行 data/market-audit/20261020T154059431686Z：75 历史页+4快照，16,690 标准化记录。
公开可提交摘要 research/evidence/W2-first-coverage.json；详细结论 research/notes/W2-first-coverage.md。
原始数据未进 Git，备份仍待实现；重采可能有修订，不能承诺仅靠 Git 恢复相同数据。
该早期运行未在启动时捕获 code dirty hash，后续正式研究 manifest 仍需补 Git+dirty/环境/数据/成本完整血缘。

BTC snapshot 约 82,592 USDT；7/30 日确有区间表现，90 条日线首尾收盘变化约 +23.94%。
记录精确窗口与“收盘变化跨 N-1 间隔”，不把描述性区间称为 alpha。
R-0003 只登记一个主观候选草案，未冻结、未回测、未筛参，近期讨论样本不作干净留出。
引用 NBER 原文入口，均值回归/crypto 动量论文尚未全文精读，不冒充已复现。

## 任务状态与下一步

W2-01 done；W2-02/03 in_progress；A-002 R-0003 in_progress。
优先查明现货当前 listTime 比历史日线起点晚的问题，再扩 mark/index 和长期 funding 来源；
不能将缺 funding 填零，不能按当前规则认证全部过去历史。随后补跨运行增量与补洞。
数据边界明确后冻结趋势/均值回归计划，进入 W3 最小账本与因果回放。
W1-09 旧库存/费用抵扣/保证金保护尚未通过，不下单，不动非 USDT 库存。
Git 提交/推送状态以实际 git status/log 为准，之前三提交可能尚未同步。
