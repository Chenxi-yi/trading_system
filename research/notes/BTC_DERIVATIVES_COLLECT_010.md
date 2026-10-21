# BTC 历史衍生品归档采集010

本轮为 DATA-013 数据工程，不新增 alpha、对照或条件收益检验。累计仍43 alpha /16固定对照、10机制比较，研究及Demo准入均0。

## 冻结范围与实际状态

先登记 research/audits/BTC-DERIVATIVES-COLLECT-010.json，固定2023-01-01至2026-10-01（不含）1369日，仅官方 Binance BTCUSDT UM metrics 免费 ZIP及CHECKSUM，每次最多100个新HTTP GET。禁止访问拒绝后绕路、无认证或账户调用。

首个实际调用的第一个GET发生URLError，取得0个日文件、0行；原错误类别、请求次数与10分钟退避保存于 data/binance-metrics/BTCUSDT-2023-2026/checkpoint.json。错误原因未查明，不宣称限区、源站拒绝或数据不存在。最早重试时刻2026-10-21 11:45:21（北京时间）；不得提前忙等重试。首段原日志 runtime/overnight/collect-binance010.log，不可覆盖；独立失败快照 artifacts/BTC-DERIVATIVES-COLLECT-010/invocation-0001.json 保留。

## 已实现的保护

OS独占锁避免重复写入；协议和四份源码指纹冻结，续跑拒绝变更。ZIP与checksum可分段恢复；每个已取得原始文件保存实际下载时间、SHA256和来源。已缓存文件先核验哈希，不把事后恢复时间伪造成原始下载时间；孤立原始文件缺metadata会停止待审。

404/410登记缺失；403/451停止自动重试；其他网络或限频错误有600秒退避。校验和、文件布局、数据schema或缓存完整性失败停止待审。单响应3MB、解压CSV10MB、单CSV布局限制沿用009。原始行序不改，另检查排序后288个5min标签网格与每字段缺失。网格完整不代表历史发布和单位认证通过，research_ready始终false。

五项新增离线测试覆盖请求预算/分段续传、孤立文件、404/451、退避、缓存篡改；统一121项通过。冻结来源129份核验通过。当前只是可恢复采集能力，尚无长期数据覆盖证据，更没有新策略有效性证据。

## 后续

先真实读取共享额度并执行quota gate，再检查退避及锁；允许后使用冻结采集器，每次最多100GET，独立日志和invocation快照。全日期处理后仍需覆盖、缺失/乱序/字段变更、单位和时间可得性审计，另登记下一研究假设后才能进行条件PnL。若持续失败保存事实并转独立工程，不绕过拒绝或靠价格参数搜索凑策略。

## 11:49恢复采集

真实额度允许且退避到期后，invocation-0002完成100GET/50日/14400行，日期2023-01-01至02-19，0不完整标签网格；sum_toptrader_long_short_ratio和count_toptrader_long_short_ratio各1个缺失值，未填充。首URLError及invocation-0001不改。新桶公开观测7项成功/fresh。结束额度主剩余11%、次68%，gate允许续传。尚有1319日待采，不是长期覆盖完成，研究ready=false。

invocation-0003再完成100GET，累计100日/28800行（2023-01-01至04-10），0不完整标签网格，缺失仍两ratio各1。源指纹未变，原始失败与每段快照均保留。真实quota恰10%允许启动下一有限段，结束必须再查；不把当前下载覆盖当point-in-time认证。

## 额度等待与累计采集

本次恢复共3段各100GET，累计150日/43200行（2023-01-01至05-30），0不完整网格；两项ratio仍各缺1值。独立invocation-0002/0003/0004和原失败0001保留，尚有1219日待采。公开新桶7项成功/fresh，非策略PnL。所有有限采集进程已结束。

实际共享主额度剩9%、次68%，gate要求停止新工作；建议今天14:35（北京时间）一次唤醒。checkpoint单独记录quota_wait_until，人工暂停仍false。先保存本地Git，再通过应用工具更新原btc并确认成功；成功证据另附，不提前声称已预约。恢复必须实查额度，允许后恢复15min保险。未购买/使用重置券。累计43alpha/16对照、研究0/Demo0，不运行收益检验。

应用automation_update已成功确认原btc为ACTIVE单次规则 FREQ=DAILY;BYMONTH=10;BYMONTHDAY=21;BYHOUR=14;BYMINUTE=35;BYSECOND=0;COUNT=1；保存配置复核一致，名称/prompt/目标线程沿用原值。已预约北京时间2026-10-21 14:35复核。OPS-006仅真实低额保存/预约阶段通过，刷新后实际唤醒/恢复15min仍待验收；未把端到端标done。当前无活动采集进程，不启动新工作。

010 invocation0006: cumulative 218 days/62784 rows; pending 1151; missing {"sum_toptrader_long_short_ratio": 1, "count_toptrader_long_short_ratio": 9}; last_error null. No publication/unit certification or PnL.

010 invocation0007: cumulative 240 days/69120 rows; pending 1129; missing {"sum_toptrader_long_short_ratio": 2, "count_toptrader_long_short_ratio": 10, "count_long_short_ratio": 1}; last_error {"day": "2023-08-29", "error_type": "URLError"}. No publication/unit certification or PnL.

最终恢复进展：0006完成100GET，0007完成44GET后URLError，累计240日/69120行（2023-01-01..08-28），余1129日，0不完整网格。缺失sum_toptrader_long_short_ratio=2、count_toptrader_long_short_ratio=10、count_long_short_ratio=1。实际下一重试 2026-10-21T15:33:19.632580+08:00，不得提前重复采集。0006/0007快照和日志均保留。共享额度一次返回非JSON导致编排安全停止，未启动下一段；一次有限真实复核恢复93%/66%。原始账户回包不保存。当前无worker，网络退避不冒充额度等待，15min保险已恢复。

010 invocation0008累计290日/83517行，待采1079日；缺失{"sum_toptrader_long_short_ratio": 2, "count_toptrader_long_short_ratio": 10, "count_long_short_ratio": 1}；last_error=null。独立快照/原始失败保留；无PnL/可得性认证。

010 invocation0009累计320日/92157行，待采1049日；缺失{"sum_toptrader_long_short_ratio": 3, "count_toptrader_long_short_ratio": 11, "count_long_short_ratio": 2}；last_error={"day": "2023-11-17", "error_type": "URLError"}。独立快照/原始失败保留；无PnL/可得性认证。

本次07:28UTC恢复最终：额度开始91%/66%，段前88%/65%、结束87%/65%，均实查gate允许。0008完成100GET、0009完成61GET后URLError；本次新增80日，累计320日92157行，1049日待采。09-12仅285条、缺失['2023-09-12 08:40:00', '2023-09-12 08:45:00', '2023-09-12 08:50:00']，0填补；独立011复核640raw/320日一致，不代表无缺失/可得性认证。网络下一重试15:47:04，当前worker结束。133冻结源码、123测试未变；43alpha/16对照、研究0/Demo0不变，无PnL/订单/账户读取/付费。后续先quota/退避/OSlock再0010，保留所有失败。
