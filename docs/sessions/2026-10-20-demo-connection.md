# Session：保护 config.toml 并测试 Demo REST

用户授权读取项目根目录 config.toml，配置 Git ignore，并测试 Demo 连接。

完成：
- /config.toml 和其备份后缀加入忽略；核验索引/历史未跟踪该文件；0600 文件权限。
- 仅在本机解析配置并显式选择 profiles.demo，确认 demo=true。默认 profile 未采用，其他 profile 未请求。
- 实现 tools/okx_demo_audit.py：Global 主机白名单、GET 路径/查询白名单、强制模拟 header、拒绝重定向、报告脱敏。
- Python 3.11+ 标准库，无需安装第三方包；当前系统 python3 为 3.9，使用已有 python3.11。
- 全部 12 项测试通过（6 项 CSCV + 6 项审计器控制）。

实测：
- openapi.okx.com：公共 /api/v5/public/time 成功；签名 /api/v5/account/config 返回 HTTP 401 / 50111。
- www.okx.com：同样公共接口成功，账户认证 HTTP 401 / 50111。
- 认证失败后停止该轮；balance 未请求；无产品/费用/订单测试，无账户改动，无实盘请求。
- OKX 官方错误码定义 50111 为 Invalid OK-ACCESS-KEY；不是凭据已验证、也不是可交易性证明。
- 本地格式诊断：demo API Key 不符合常见 UUID 形态；不自动替换、互换或猜测凭据。

证据：ignored runtime/okx-demo-audit/ 下两份 JSON，仅保存状态/时间/端点，不保存原始配置、身份、余额或凭证。
关键调用与错误码已记本交接，可在修正本机 Key 后用同一脚本复测。

后续：PM 本机核对 profiles.demo 的 API Key 与模拟交易创建来源；无需在聊天发送凭证。
W1-04 等待凭证更正，W1-05 完成，W1-06 认证受阻，W1-07 未执行。
文档：OKX API REST Authentication / Demo Trading / API Class error codes。
https://www.okx.com/docs-v5/en/

GitHub 本轮推送成功，远端从 292a48c 前进至 ae5f423，所有此前积压已同步；config.toml 与 runtime/ 未上传。
