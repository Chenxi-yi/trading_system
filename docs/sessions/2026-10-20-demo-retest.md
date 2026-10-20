# Session：Demo 凭证修正后复测成功

PM 表示已重新复制配置，授权再做只读连接测试。
固定读取根目录 ignored config.toml 的 profiles.demo，强制模拟 header=1，不使用默认 profile。

结果（2026-10-20 22:57 Asia/Shanghai）：
- Global openapi.okx.com 公共 /api/v5/public/time 成功。
- 签名 /api/v5/account/config 成功。
- 签名 /api/v5/account/balance 成功。
- 状态 demo_authenticated；无下单、无账户模式/资金修改、无 live 请求。

脱敏报告：runtime/okx-demo-audit/20261020T145743558580Z.json（本机忽略目录，0600）。
未输出/提交凭证、身份或余额。config.toml 仍被 Git 忽略；本轮未修改审计代码，无需重跑离线测试。

W1-04 完成：本机凭证只读连接已验证；不据此声称 API Key 仅有 Read 权限或已验证交易权限。
W1-06 认证障碍解除，下一步核验账户模式、可用产品清单；W1-07 费率仍待执行。
WS 和订单链路未测试，W1 整体未验收。
