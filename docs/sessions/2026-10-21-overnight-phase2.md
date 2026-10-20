# 通宵交接：20配置首轮已运行，细频/工程复核继续

PM已同意通宵，用户睡眠中勿问常规问题。heartbeat btc ACTIVE，03:20续跑；caffeinate session25107。
当前风险/资金操作未授权，未下任何订单。Git/数据以实际磁盘为准。

## 活动进程与恢复

- 原采集器66204已完成第一轮500页后退出；续采worker工具session6392仍在活动，日志runtime/overnight/worker.log。
- worker持runtime/overnight/worker.lock；它继续collect_btc_overnight，完整后物化15m，等mark，再perp研究、grid细频、报告。
  若主机/app中断可重启 tools/btc_night_worker.py，有锁则退出，不重复写。
- 独立mark采集session98617已完成；独立资金费归档session40162已完成；具体任务/锁以实际状态为准。
- 真实研究已执行：spot tools/run_btc_night.py、perp tools/run_btc_perpetual_night.py，结果缓存不可当未知数据重复调参。

## 已保存结果

artifacts/BTC-NIGHT-001/summary.json：16个现货配置+时序选参，spot四族均未过冻结门槛。
2024–2025合并净收益：趋势48.74%、回归11.30%、网格29.60%、再平衡22.11%；
2026H1封存：分别-16.16%、-19.90%、-22.54%、-16.76%。部分WF年份为负、bootstrap均值下界非正/PBO不稳等。
95%BTC连续持有基准同窗+99.79%/回撤-31.46%；不可只看正收益而不看风险/暴露。

artifacts/BTC-NIGHT-001-PERP/summary.json：四个额外已预算突破配置，WF2024–25+15.41%，回撤-34.99%；
2026H1+24.66%，压力成本+13.31%；仍因一个WF年份负、均值不确定、PBO不稳而未通过。
合约模型含实际funding、mark、张数、费用/滑点；maintenance10%只是合成压力，非OKX历史tier/强平实现，demo_ready=false。
目前研究全门槛通过0，Demo准入0。不能称找到五个有效策略，不以参数近邻凑数，不追加未登记搜索。

初步中文报告 research/reports/BTC_OVERNIGHT_2026-10-21.md 已生成（会被worker更新）；图在artifacts。
原spot源代码hash与配置在artifact/source_snapshot已核对保存；sealed_access_log标第一次访问已发生。

## 数据新发现

官方monthly market-data-history endpoint存在（完整www官方docs在ignored数据目录已保存）；
PublicClient增加archive只读白名单。tools/collect_okx_funding_archive.py取得55个月、5025事件，REST重叠216项一致无冲突。
档案有2022Dec一处偏移2.9h、一处+1秒，不取整/零填；perp分支在任何其PnL前已把开始收紧到2023，2024选参使用2023一年。
见research/experiments/BTC-NIGHT-001-PERP.json，明确它不是spot历史封存之后的独立全新确认。
数据归档manifest data/funding-archive/BTC-USDT-SWAP/manifest.json，源URL/ZIP哈希、异常与REST核对均保留。

## 代码与检查

现货回放增加15m base支持、仍固定1h信号延迟、每格每小时最多一次fill；4族选中参数的小时2024–25结果逐一复算，与旧缓存数值完全一致。
原mainrunner因代码hash变化拒绝原缓存重用是设计行为；不要为复用随便删manifest或封存访问日志。
细频工具 tools/check_btc_grid_resolution.py 用旧WF参数，不重新选；worker会在15m完整后调用。
新增perp账本/回放、funding解析与覆盖测试；当前43项测试通过，runtime/overnight/tests-phase7.log。
matplotlib图已人工查看；可选依赖numpy1.26.4、matplotlib3.8.0，已在本机，无新增付费。

## 继续事项

优先等worker完成细频敏感性和报告，复核所有代码/数据/结果、补保护/风险/执行的可测试实现，完整记录未完成门槛。
不应因5个结果未达标就立刻停在一份回测报告，也不得重调已访问封存样本以制造5个通过。
本轮候选预算20已用完，后续新研究需明确登记新波次及已知数据限制；用户批准的本夜计划不允许无限搜索到凑数。
额度00:46左右5h已用86%（时间粗略以工具实际为准）；03:16重置，03:20heartbeat已创建，必要时保存并用它续跑。

后补：纯spot交易前风控src/miniquant/risk/pretrade.py已实现，检查初始本金损失口径、策略/Bot/账户可用预算、
预存资产保护、过期快照和环境；passing仍submission_authorized=false，未做原子资金预留/真实订单。
新增4项风险测试，统一47项通过。报告工具已加入15m完成后自动运行细频检查的钩子，
因此当前worker虽在修改前加载旧函数，最终调用新报告脚本仍会补上grid-resolution。
