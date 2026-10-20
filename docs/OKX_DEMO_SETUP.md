# W1：本机模拟凭证配置准备

W1 只做账户只读审计。使用 OKX Global 的模拟交易 API，不使用实盘 Key。

## 当前实际配置与测试

用户已采用项目根目录 config.toml（Git 忽略，0600），作为本轮唯一凭证来源；无需另外复制到 JSON。
审计器固定选择 profiles.demo 并要求 demo=true，即使默认 profile 指向其他环境也不会使用。
API Key、Secret、Passphrase 分别填写 api_key、secret_key、passphrase。
最近在 openapi.okx.com 与 www.okx.com 的模拟 GET 检查中，公共 time 成功，账户 config 返回 HTTP 401 / 50111。
请在本机核对模拟盘 API Key，排查复制不完整或字段填反，再复测；没有成功认证之前不查询后续账户能力。

运行：`python3.11 tools/okx_demo_audit.py`。Python 3.11+ 标准库实现，无需安装 Kit。
签名与密码均不输出；JSON 报告保存于 ignored runtime/okx-demo-audit/，只包含状态与耗时。
官方错误码：https://www.okx.com/docs-v5/en/ （50111 = Invalid OK-ACCESS-KEY）。

## PM 操作

1. 在 Global 账户的模拟交易区域创建专用 API Key；W1 只需要 Read 权限，不开启 Trade 或 Withdraw。
2. 凭证包括 API Key、Secret、Passphrase；由 PM 在本机保存，不发进聊天、不粘到 GitHub。
3. 若使用文件配置，使用项目已忽略的 `config/local/okx-demo.json`；父目录仅本人可访问（0700），文件仅本人可读写（0600）。
   这是本机明文文件的访问权限，不是加密存储；后续可迁移到系统凭证管理器。
4. 配置完成后仅告知“模拟只读配置已准备好”和采用的存储方式，不提供凭证内容。

## 可选 JSON 方案（当前审计器只读取 TOML）

`environment=demo`、`site=global`、`api_key`、`secret_key`、`passphrase`。
暂不要求填写 REST/WS 域名；由审计器按核验后的 Global 文档固定并检查，避免误连。
这个配置不会自行启动服务或交易。不要用 shell 命令把实际密钥写入历史记录。

## Agent 后续工作

受限只读审计器已实现并完成离线检查；用户更新本机配置后可复测。
不能把完整配置文件打印出来；不得把 Secret/Passphrase 放在进程命令行、日志或异常文本中。
私有响应写入 ignored runtime/，仓库只保存脱敏结论与校验信息。
当前不安装 Agent Trade Kit，不改变账户模式；未来如需模拟交易权限，按具体测试范围单独配置。

参考：OKX API 的 Demo Trading、Account instruments/config/trade-fee 文档。
https://www.okx.com/docs-v5/en/
