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
