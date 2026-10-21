# 026：严格输入边界，不改资金或研究政策

独立推进P-001，全部合成数据、零网络/账户/订单。

## 实际复现

旧 `pretrade.assess_spot_order` 使用Python的int/float类型检查，bool也通过。合成cash买单的quantity=True在lot=1/minimum=1时被允许。另一合成输入quantity=1e308、lot=1e-308均为有限数，二者比值溢出，旧函数抛OverflowError。

旧文件及risk包init已被002/003/007/008冻结，不改源码、原记录或历史结果。新增 `pretrade_strict.assess_spot_order`：精确int/float类型（不含bool）、拒绝非有限/无法表示的大整数/不支持类型；除法后检查比值有限；算术/值/类型异常转为拒绝。合法输入继续委托旧规则，所以不改资金、40%初始本金损失、旧币保护或订单限额。

## 检查与边界

4项新测试覆盖每个数字配置字段的bool、数量回归、极端比值/巨大整数/非有限/错误结构，以及正常、初始本金损失停买和旧资产保护不退化。曾因测试模块直接导入旧TestCase导致重复发现4个旧用例，已修正；最终独立总数182，未将重复发现计作新增能力。

026冻结源码后实际合成演练：旧bool允许true、新版拒绝true；旧极端输入OverflowError、新版拒绝true；submission_authorized=false，0HTTP/订单/PnL。

这是可复用纯预检查入口，**尚未接入真实账户/订单，未构成完整风险引擎**。仍沿用旧版浮点数量规则；生产必须结合精确产品数量、原子预算预留、真实抵押品/库存基线、对账和场所模式验收。不能用它补签W1-09或策略准入。

后续新集成显式使用 `from miniquant.risk.pretrade_strict import assess_spot_order`，历史研究仍用其冻结版本。PaperStore的精确整数账本与自身检查不变。未来永续/组合风险另行实现，不因现货预检查通过而放开。

43alpha/16固定对照、研究0/Demo0不变；本项没有策略搜索或模型真实评分。
