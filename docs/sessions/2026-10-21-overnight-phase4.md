# BTC通宵首轮汇总与03:20续跑交接

PM已批准通宵自主研究；本次03:20 heartbeat实际触发。额度恢复（开始时5h窗口已用1%），
worker此前已research_runs_finished，无采集/研究活动进程，未重复启动。未下单/转账/改模式/新增付费。

## 不可误读的结论

五族20配置已用完登记预算；研究全门槛通过0、Demo准入0。目标五个未实现，不放宽门槛补齐。
报告 research/reports/BTC_OVERNIGHT_2026-10-21.md；原数据、缓存、manifest、访问日志与源码快照未改写。
四个现货族封存2026H1均负；永续该段+24.66%，但2025为-26.77%、均值不确定与PBO不稳。
过去的正收益不是可保证未来收益，原保守政策未通过也不证明整类策略永久无效。

## 本次新增与证据

1. tools/audit_btc_night.py：103份缓存从成交/费用/funding重算NAV，最大差4.18e-11；
   funding金额/结算前头寸一致；manifest原列7份源码快照哈希一致。
   现货12个零量小时（9个集中2022Dec18），永续1个零量4H，没有缓存成交发生其起点。
   跨频两差异：2022Dec18 00UTC close16735.6 vs16729.2；16UTC open16729.2 vs16749。
   后者前两小时零量、首次有量开盘16749，与原生吻合；前者未解释。无静默修补或择优选源。
   listTime/历史规则未认证；原perp manifest漏列导入replay/validation哈希，记录为来源缺陷。
2. 两项黑盒因果测试：未来价格/mark/funding改变不影响历史交易，五现货表达做截断一致性。
3. ADR-0005：本机paper SQLite预留与订单日志，12项并发/部分成交/重复/unknown/保护库存/
   重启对账/损失限额/未提交进程退出回滚测试。paper-only，无场所连接，真实保护未验收。
4. 事后延迟审计另登记BTC-NIGHT-001-DELAY-AUDIT，仅固定旧WF选择、无重选。
   默认10个年度回放与原daily一致（perp也逐fill一致）。4H/8H现货与8H/12Hperp压力已完成。
   回归对调度敏感（原WF+11.30%，延迟场景约+48–50%），不能择更赚钱延迟晋级。
   新信号覆盖等待意图；网格只延迟初始化/重锚，不模拟挂撤网络延迟，边界已写报告。
   source_snapshot原证据不动，代码扩展前另存delay-audit/before-source。
5. 同步收益相关描述：趋势/固定比例0.843，网格/固定比例0.832，突破/固定比例0.820。
   未事后优化权重。README/CHARTER/OPERATING_MODEL/状态台账中的“尚未冻结/待同意”等旧现状已清理；历史session不改。

统一61项离线测试通过，日志runtime/overnight/tests-continuation.log。
初版paper INSERT占位数量错误、初版perp因果合成数据无成交（测试无力）均已发现修正后重跑通过；
未隐藏这些工程失败，不涉及删除研究失败或修改已知留出。

## 保存与收尾

此检查点先本地提交，再执行tools/bundle_btc_research.py：显式公开数据根目录+Git源码，
不含config.toml/config/local/runtime/账户账本；校验全部归档字节、恢复61测试和选中真实BTC回放。
本机包不构成异地备份。最终包校验/远端限时push/automation关闭结果在本交接末尾追加，不预称成功。
原spot/perp runner因代码指纹变化会拒绝旧缓存，这是正确保护，禁止删manifest绕过。
再次执行延迟审计会拒绝覆盖已完成summary；不要无意义重复搜索。

## 下一步与未验收

W1-09真实只读资金/旧库存保护对账 → 不下单shadow时钟/行情/日志/告警/恢复闭环。
N-025无成交/无报价状态传播及等待意图TTL；N-026完整传递依赖/环境manifest。
历史强平tier、真实队列、完整组合Risk和降仓kill switch、WS及长时间前瞻仍未完成。
新研究另登记假设/预算/未知观察期，不能把本轮已知历史继续称干净OOS；carry收益仍取消。
无需向睡眠中的PM再问常规问题；不自动启动新策略搜索或真实/Demo订单。

## 最终收尾核验（2026-10-21T03:36:22.348013+08:00）

- 本地研究/工程提交：7adaaad；打包时工作树干净。
- 公开研究复现包：`artifacts/recovery/BTC-NIGHT-001-7adaaad44493.tar.gz`，29009190字节，0600。
- SHA256：`9dee70c0c3c422bdcf3c7cf44fc89f62b3845a0e3cfd7d125621be016c2a5798`。全部成员逐字节哈希核验、临时目录恢复61测试通过，
  真实BTC趋势90日2024–2025回放daily NAV与缓存完全一致。包绑定7adaaad代码；本条收尾文档在之后Git提交，不伪称包含在旧包。
- `git push origin main`本次20秒超时，远端未确认；当时main领先7提交。后续状态以Git为准，未强推或反复无限重试。
- automation_update返回btc状态PAUSED，已从本机automation.toml再次验证，不再自动继续本夜研究。
- 原临时防休眠进程96977已确认是本任务caffeinate；收尾停止。没有其他研究/采集进程需要继续。
- 当前留出全已访问、0研究/0Demo准入，新一轮不沿已知历史追逐赢家。
