# PM批准额度感知续跑并恢复研究

PM明确“按照这个来，你继续”，解除人工暂停。先读checkpoint/policy/Git及原btc配置；工作树干净、main领先21提交。只读额度查询允许工作。未用购买/重置券；未把原始账户ID/额度回包加入Git。

新增quota_policy.py及stdin gate，任一窗口剩余<10%时取受限窗口最晚刷新+120秒向上整分钟，输出单次唤醒建议；unknown/past-reset/usage-disallowed保存复查。6项针对阈值、双窗口、空值、到期和脱敏的测试通过，统一107测试。runtime只保存脱敏决策0600。

通过automation_update更新现有btc完整配置：ACTIVE，保留15min、名称/原prompt/目标线程，新增每恢复/每批前后的真实额度API调用、低额先保存后应用工具确认单次唤醒、恢复后重查与改回15min规则。工具回执ACTIVE。单次低额分支尚未实触发，OPS-006保留待验收；建议输出不等于已预约。人工暂停永远优先。

ADR-0008、policy/checkpoint/TASKS/PROJECT_STATE已同步。不是保证准点恢复；本地电脑/应用/网络/共享额度仍决定可执行性。研究继续原检查点的突破失败机制审查，尚未在此工作单元新增试验或下单。
