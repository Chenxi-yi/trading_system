# OKX Global 账户能力矩阵

观察：2026-10-20 15:09 UTC 附近；Global、显式 profiles.demo、模拟 header=1。
完成 14 项 GET 检查，没有发单或修改设置。只记录能力与脱敏证据引用；不保存账户身份、资产金额或凭证。

| 产品 | 公开行情样例 | 当前 Demo 账户清单 | 模拟费率/单位核验 | 模拟订单链路 |
|---|---|---|---|---|
| Crypto SPOT | BTC/ETH/SOL 产品可见 | BTC/ETH/SOL-USDT 均返回 live | 六产品中的三项已核验 | 未测 |
| Crypto SWAP | K 线、funding/OI 等样例已取 | BTC/ETH/SOL-USDT-SWAP 均返回 live | 三项已核验；线性、USDT 结算 | 未测 |
| Expiry FUTURES | 产品列表样例已取 | 返回列表中未找到 BTC-USDT-*、USDT 结算样例 | 不据其他结算币合约推定 | 未测 |
| Equity SWAP | AAPL-USDT-SWAP K 线已取 | AAPL/TSLA-USDT-SWAP 未返回 | 未核验 | 未测 |
| x-stock SPOT | XAAPL-USDT K 线已取 | XAAPL/XTSLA-USDT 未返回 | 未核验 | 未测 |

“未返回”仅指上述账户、时点与具体样例，不等于所有股票产品不支持，也不证明实盘权限。
“live”是产品状态字段，不表示已连接实盘。账户可见性不代替订单验证。

## 产品单位快照

以下为查询时返回的产品元数据；下单前须刷新，不能永久硬编码。

| 产品 | 数量单位 | 最小量 minSz | 步长 lotSz | 价格步长 tickSz | 合约面值 |
|---|---|---|---|---|---|
| BTC-USDT | BTC | 0.00002 | 0.00000001 | 0.1 | 不适用 |
| ETH-USDT | ETH | 0.00073 | 0.000001 | 0.01 | 不适用 |
| SOL-USDT | SOL | 0.001 | 0.000001 | 0.01 | 不适用 |
| BTC-USDT-SWAP | 张 | 0.01 | 0.01 | 0.01 | 每张 0.01 BTC |
| ETH-USDT-SWAP | 张 | 0.01 | 0.01 | 0.01 | 每张 0.1 ETH |
| SOL-USDT-SWAP | 张 | 0.01 | 0.01 | 0.01 | 每张 1 SOL |

衍生品 sz 是张数，不能直接当作币数。乘数与单位必须一起进入 Instrument 版本。

## 账户模式、费用与保护

账户模式、持仓模式、借贷开关、费用币种路径及自动划转字段已读取，具体值留在私有报告。
当前 USDT-only 初审结论为 `conditionally_feasible_not_trade_ready`，不是已完成隔离，也不是下单许可。
未发现当前持仓和普通挂单；未穷尽原生 Bot/条件单等其他路径。

费用按精确产品请求，并匹配该产品的 feeGroup.groupId；保留原始费率符号，
转换为正成本、负返佣的 cost_bps。缺失、非有限值或分组不匹配均不当作零费率。
衍生品缺少 feeGroup 时拒绝从含混的旧字段推定。Demo 费率不作为实盘费率承诺。
实际费用快照仅存私有报告，不进入公开仓库。

实际杠杆、逐单 tdMode、自动划转和费用抵扣路径、受保护库存与预算预留需要在交易前补齐检查。
WS 连续性、订单生命周期、账本与故障恢复均未验证。

## 证据与复现

- 公共样例：research/evidence/R-0001-public-probes.json。
- 私有能力报告：runtime/okx-demo-audit/20261020T150936572517Z.json（Git 忽略、0600）。
- 工具：`python3.11 -m tools.okx_capabilities`；统一离线测试 16 项通过。
- 评审与下一步：docs/workpackages/W1_REVIEW.md。
- 字段与接口：[OKX API 官方文档](https://www.okx.com/docs-v5/en/)、[账户与交易模式指南](https://www.okx.com/docs-v5/trick_en/)。
