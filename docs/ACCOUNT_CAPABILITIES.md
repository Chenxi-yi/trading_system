# OKX Global 账户能力矩阵

当前：已尝试模拟只读认证，HTTP 401 / 50111（Invalid OK-ACCESS-KEY）；未取得私有账户配置或产品结果。
只记录能力与脱敏证据引用，不保存账户身份、资产金额或凭证。

| 产品 | 公开行情样例 | 账户可用清单 | 模拟费率/单位核验 | 模拟订单链路 |
|---|---|---|---|---|
| Crypto SPOT | BTC/ETH 样例已取；BTC/ETH/SOL 产品可见 | 未测 | 未测 | 未测 |
| Crypto SWAP | SOL 4H、BTC funding/OI 等样例已取 | 未测 | 未测 | 未测 |
| Expiry FUTURES | 产品列表样例已取 | 未测 | 未测 | 未测 |
| Equity SWAP | AAPL-USDT-SWAP K 线样例已取 | 未测 | 未测 | 未测 |
| x-stock SPOT | XAAPL-USDT K 线样例已取 | 未测 | 未测 | 未测 |

公开样例证据：research/evidence/R-0001-public-probes.json。
实际审计后需补观察时间、环境、读接口、支持/不支持/未知、限制及私有证据位置。

## 账户级检查项

Global 公共时间接口成功；显式 profiles.demo、demo header=1 的账户 config 查询失败。
openapi.okx.com 与 www.okx.com 结果一致；报告在 ignored runtime/okx-demo-audit/。
认证和权限尚未通过，下面账户模式等项目均未核验。

认证与时钟偏差；demo 环境；账户模式；net/long-short；cross/isolated 可用性；
账户 instruments；tick/lot/合约单位；fee group；各产品费率；私有数据返回一致性。
账户可见产品不代表已验证下单，更不代表相同产品可用真实资金交易。

文档入口：https://www.okx.com/docs-v5/en/ 。执行前核验 Global 当前接口/域名及字段。
