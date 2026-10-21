# BTC-LOOP-003：实际永续双向多周期探索

完成：2026-10-21T01:56:02.623057+00:00；8候选+4对照，累计36alpha+10对照。

所有历史均为已知适应性探索；无独立新OOS/前瞻，没有交易所订单。P0/F0在收益前固定，其他为敏感性，不事后选最佳。

| 候选 | 2024净收益 | 2025净收益 | 两年净收益 | 最大回撤 | 2026H1已知挑战 | 压力成本两年 | 8H延迟两年 |
|---|---:|---:|---:|---:|---:|---:|---:|
| P0 | 13.54% | -1.26% | 12.11% | -19.97% | 13.21% | 6.22% | 4.98% |
| P1 | 4.56% | -4.21% | 0.15% | -24.33% | 17.95% | -6.22% | -3.45% |
| P2 | 5.08% | -0.99% | 4.04% | -23.26% | 13.25% | -1.06% | -1.64% |
| P3 | -2.12% | 4.03% | 1.82% | -28.82% | 7.40% | -2.34% | 2.36% |
| F0 | 4.33% | -8.87% | -4.93% | -38.79% | 17.39% | -12.42% | -13.70% |
| F1 | -2.05% | -8.13% | -10.01% | -41.27% | 16.98% | -18.63% | -16.08% |
| F2 | -0.53% | -3.00% | -3.51% | -39.15% | 15.41% | -10.36% | -11.42% |
| F3 | -5.90% | 5.10% | -1.10% | -42.48% | 8.89% | -6.64% | -1.23% |

净收益非年化；P组20%年化风险目标/75%上限，F组75%固定名义乘信号强度。基准费/滑点每边5+5bps、压力10+10，另含实际funding费率/时点。
保证金仅合成10%最坏mark压力，绝非真实OKX历史强平认证；4Hmark边界估算funding名义金额；当前合同粒度为研究情景。

## 消融对照

| 对照 | 两年净收益 | 2026H1已知挑战 |
|---|---:|---:|
| long_only_scaled | 21.09% | -0.98% |
| long_only_fixed | 22.44% | -0.42% |
| passive_long_fixed | 48.07% | -26.85% |
| passive_long_scaled | 24.36% | -21.64% |

## 否决与不确定性

- P0: nonpositive_year, uncertain_mean, unstable_selection_diagnostic；PBO=0.2857142857142857，funding两年=-511.00研究单位，费用=275.16。
- P1: nonpositive_year, nonpositive_stress, uncertain_mean, unstable_selection_diagnostic；PBO=0.2857142857142857，funding两年=-459.46研究单位，费用=318.27。
- P2: nonpositive_year, nonpositive_stress, uncertain_mean, unstable_selection_diagnostic；PBO=0.2857142857142857，funding两年=-552.29研究单位，费用=257.58。
- P3: nonpositive_year, nonpositive_stress, uncertain_mean, unstable_selection_diagnostic；PBO=0.2857142857142857，funding两年=-567.97研究单位，费用=209.97。
- F0: nonpositive_year, nonpositive_stress, drawdown_limit, uncertain_mean, unstable_selection_diagnostic, fragile_neighbors；PBO=0.3，funding两年=-900.54研究单位，费用=380.02。
- F1: nonpositive_year, nonpositive_stress, drawdown_limit, uncertain_mean, unstable_selection_diagnostic, fragile_neighbors；PBO=0.3，funding两年=-806.43研究单位，费用=439.80。
- F2: nonpositive_year, nonpositive_stress, drawdown_limit, uncertain_mean, unstable_selection_diagnostic, fragile_neighbors；PBO=0.3，funding两年=-979.83研究单位，费用=364.67。
- F3: nonpositive_year, nonpositive_stress, drawdown_limit, uncertain_mean, unstable_selection_diagnostic, fragile_neighbors；PBO=0.3，funding两年=-1005.98研究单位，费用=279.75。

历史筛查通过0，研究达标0、Demo准入0。PBO只诊断本族开发期排名，不能消除跨批自适应选择。

下一步不是挑表里最赚钱的参数，而是核查空头/波动缩放的配对差异、对市场时期与交易成本的依赖，并完成三批研究过程审计。
