# BTC持续研究循环：第二批历史探索

更新：2026-10-21T01:38:21.793429+00:00。旧实验保持原样；新8配置+4对照，累计28个alpha候选与6对照。

全部历史属于已知/适应性探索，任何正收益不构成新的独立样本外或前瞻证据。主配置T0/R0事前固定，无事后选最好版本。

| 主候选 | 2024–2025净收益 | 最大回撤 | 2026H1已知挑战 | 压力成本 | 4H执行延迟 | 历史筛查 |
|---|---:|---:|---:|---:|---:|---|
| multiscale_trend | 24.77% | -13.10% | -1.08% | 18.51% | 25.48% | nonpositive_year, nonpositive_known_challenge, uncertain_mean, unstable_selection_diagnostic |
| confirmed_pullback | -14.86% | -15.99% | -0.17% | -17.71% | -7.52% | nonpositive_year, nonpositive_known_challenge, nonpositive_stress, uncertain_mean, fragile_neighbors |

费用/滑点每边10+5bps，压力20+10；所有结果非年化。
两族均为现货long/flat，无funding或借贷；新执行器传播volume并禁止零量bar成交，等待意图固定截止/到期。
历史筛查与前瞻/真实工程准入分离，当前研究达标0、Demo准入0。跨批次多重选择未被单批PBO消除。

## 固定对照

| 对照 | 2024–2025净收益 | 2026H1已知挑战 |
|---|---:|---:|
| cash | 0.00% | 0.00% |
| hold_75pct | 78.78% | -25.16% |
| vol_only20pct_cap75pct | 35.51% | -20.82% |
| multiscale_T0_no_vol_cap75pct | 30.18% | -0.67% |

## 下一步

逐笔解释风险缩放/确认修复相对消融对照的差异，检查状态与交易成本，而非继续挑最优参数。
下一家族优先实际永续多周期双向趋势、量价条件与流动性/持仓机制；先补数据、检验替代解释并另登记。
前瞻shadow与账户保护工程继续推进，不用历史回测替代等待新数据。
