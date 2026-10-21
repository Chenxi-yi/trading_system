# 013独立有界重试数据来源

012实际捕获SSLEOFError/8，按ADR-0009另建来源，不修改010冻结源码/清单/数据。新路径data/binance-metrics/BTCUSDT-2023-2026-retry-v2，父353日101661行先独立复核再逐文件复制；原始下载metadata/时间不改，父checkpoint及导入manifest独立留存。原缺口、历史失败及统计不洗掉。

仅TLS EOF允许每段最多2次重试，等2/5秒，所有实际尝试含失败计入100GET。其他错误保留原停止/600秒退避，403451不绕过，证书验证保持开启。父退避被继承并已到期后才开始第一次新HTTP。132项测试通过（7新增覆盖重试上限/预算/证书与拒绝不重试/部分ZIP/父损坏/原metadata和退避保留）。

当前0001实际运行中，未证明真实重试成功；多天数据完整不等于历史单位/available_at认证。alpha43/固定对照16、研究0/Demo0不变，无PnL或订单/费用。

013 invocation0001累计402日/115773行，待采967日；transport_errors累计1，last_error=null；旧010父数据不变，无PnL/可得性认证。

013 invocation0002累计452日/130048行，待采917日；transport_errors累计1，last_error=null；旧010父数据不变，无PnL/可得性认证。

013 invocation0003累计502日/144448行，待采867日；transport_errors累计1，last_error=null；旧010父数据不变，无PnL/可得性认证。

013 invocation0004累计552日/158848行，待采817日；transport_errors累计2，last_error=null；旧010父数据不变，无PnL/可得性认证。

013 invocation0005累计602日/173248行，待采767日；transport_errors累计2，last_error=null；旧010父数据不变，无PnL/可得性认证。

013 invocation0006累计652日/187648行，待采717日；transport_errors累计2，last_error=null；旧010父数据不变，无PnL/可得性认证。

013 invocation0007累计702日/202046行，待采667日；transport_errors累计2，last_error=null；旧010父数据不变，无PnL/可得性认证。

013 invocation0008累计751日/216158行，待采618日；transport_errors累计4，last_error=null；旧010父数据不变，无PnL/可得性认证。
