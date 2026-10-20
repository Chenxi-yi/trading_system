# W1：本机模拟凭证配置准备

W1 只做账户只读审计。使用 OKX Global 的模拟交易 API，不使用实盘 Key。

## PM 操作

1. 在 Global 账户的模拟交易区域创建专用 API Key；W1 只需要 Read 权限，不开启 Trade 或 Withdraw。
2. 凭证包括 API Key、Secret、Passphrase；由 PM 在本机保存，不发进聊天、不粘到 GitHub。
3. 若使用文件配置，使用项目已忽略的 `config/local/okx-demo.json`；父目录仅本人可访问（0700），文件仅本人可读写（0600）。
   这是本机明文文件的访问权限，不是加密存储；后续可迁移到系统凭证管理器。
4. 配置完成后仅告知“模拟只读配置已准备好”和采用的存储方式，不提供凭证内容。

## 预定配置字段（审计器尚未实现）

`environment=demo`、`site=global`、`api_key`、`secret_key`、`passphrase`。
暂不要求填写 REST/WS 域名；由审计器按核验后的 Global 文档固定并检查，避免误连。
这个配置不会自行启动服务或交易。不要用 shell 命令把实际密钥写入历史记录。

## Agent 后续工作

先实现并检查受限只读审计器，再在用户确认已配置后进行签名查询。
不能把完整配置文件打印出来；不得把 Secret/Passphrase 放在进程命令行、日志或异常文本中。
私有响应写入 ignored runtime/，仓库只保存脱敏结论与校验信息。
当前不安装 Agent Trade Kit，不改变账户模式；未来如需模拟交易权限，按具体测试范围单独配置。

参考：OKX API 的 Demo Trading、Account instruments/config/trade-fee 文档。
https://www.okx.com/docs-v5/en/
