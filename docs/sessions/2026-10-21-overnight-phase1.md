# 通宵执行交接：批准后第一阶段

PM已明确同意开动，授权按本夜计划自主研究，不再提常规问题；无资金操作或live授权。
应用heartbeat btc 已创建 ACTIVE，绑定本对话，计划2026-10-21 03:20 Asia/Shanghai，COUNT1。
第一次创建因缺destination返回参数错误，已以destination=thread成功修正；不创建重复任务。
临时 caffeinate -i -t28800 已运行（工具session25107）；只防空闲系统休眠，合盖仍有可能停止。

活动采集：工具session66204，日志 runtime/overnight/collector.log，OS锁在对应data运行目录。
工具 tools/collect_btc_overnight.py 固定输出 data/market-audit/btc-overnight-20261021，
扩展现货/永续4H、现货1H/15m、近期mark/index4H；每次最多500页，可再次执行恢复。
当前两项4H已完成各14908根/无缺口，小时数据继续；具体以checkpoint为准。
tools/materialize_btc_overnight.py 可安全读取原子checkpoint，单独物化已完成作业而不改采集游标。

冻结：research/experiments/BTC-NIGHT-001.json，在任何真实策略PnL计算前落盘；
2021-2023开发，2024/2025按前两年选参做walk-forward，2026H1封存历史验证，2026H2已知探索。
五族各四个参数，预算20；四个现货族先实现，永续突破数据/模型未完成不得声称净收益。
研究最大回撤35%等阈值是预先声明的筛查假设，不是PM live限额；bootstrap/PBO均有适用边界。

实现：accounting/spot.py、backtest/replay.py、research/validation.py；35项统一测试通过，日志runtime/overnight/tests-phase2.log。
Spot手续费买入扣base、卖出扣quote，资金/库存有限；按完成bar生成信号，延后1h执行。
网格为独立资金单元、每格每小时最多一次fill、严格穿越2bps；初始建仓小时不再触发限价；真实排队/细频验证仍缺。
成本基准每边10bps费用+5bps市场滑点，压力20+10；限价按level成交，严格穿越不等于真实成交保证。
回放使用当前产品规则作为研究情景，历史listTime/规格仍未认证，不给demo准入。

研究runner tools/run_btc_night.py 已写但尚未运行：需先物化完整 trade_BTC-USDT_1H.json。
缓存每个窗口/参数/情景，持有OS锁；先持久化最终参数选择再计算封存结果。
代码/输入变化时拒绝复用旧cache，必须归档并记录修复/留出访问污染；不能看结果改门槛。
研究可选依赖numpy1.26.4、matplotlib3.8.0已在本机存在，pyproject加入research optional；未安装新付费服务。
下一步：继续测试/复核新runner，1H完成后启动真实研究；补永续/funding证据、风险/执行与报告。
如额度耗尽先保存当前状态，03:20续跑检查活动进程，不重复写或重跑已访问的封存结果。
