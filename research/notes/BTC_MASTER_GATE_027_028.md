# 027主数据与028研究入口保护

先冻结027采集/变化处理，再实现并实际请求公开time与SWAP instruments，共2GET。沿用既有PublicClient的域名、UA和TLS；不碰016/019被阻断路径。每日先保留reservation，失败/崩溃也不再次启动当天采集，所有底层尝试计入6GET上限，跨UTC日期停止；403/451持久停止。

旧基线与本次实际收到的规格均为线性USDT、ctVal=.01 BTC、ctMult=1。2份主数据版本与20个OI点按available_at匹配，0币数/张数换算差异、0面值/执行字段变化。重复prepare前后当天attempt文件SHA相同，没有新增HTTP。历史规格生效时间未知；一致性不认证单双边定义或历史恒定面值。

OI只能使用此前已收到的master，不以未来规格回填。研究开始后面值/结算变化或单位不一致持久标记整项研究失效；不重缩放、不删除不利区间。tick/lot等变化标记执行复核；主数据超过26小时或非live/不支持状态阻断。最新时效使用latest_quality，不能把不可变首次unit_checks的freshness当永久结论。

028作为批准入口，先刷新027并要求study_supported严格为true且无持久失效，才运行原022/024。evaluate先检查固定终点，未到期不调用刷新或读取真实结果；到期仍须通过master保护后运行原025。实际prepare成功，40 raw/3个截止后桶，0完整特征/标签/预测；实际evaluate返回not_due、真实结果未加载或评分。

保护是在第一条完整特征、真实标签、预测和拟合之前加入；未查看结果，没有修改两模型、窗口、阈值。原022/024/025源码不改且每次核验父manifest。6项master检查+3项dispatch检查，统一191测试通过。到期真实评价、长期采集连续性与真实规格漂移尚未验收。43alpha/16对照/0研究准入/0Demo保持，无订单、账户读取或新增付费。

恢复顺序：真实quota→既有public/pressure观测→python3.11 tools/run_oi_study.py --mode prepare；只看质量summary，禁看internal_samples_no_peek。最终固定终点2026-12-20T10:15Z后才用同入口--mode evaluate。等待数据期间选TASKS中独立工程/审计工作，不重复空清单或优化已知历史。
