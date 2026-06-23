# Drivers, leakage control & aha playbook

## Driver importance (conversion hazard) — method: permutation (Δ PR-AUC)

| feature | importance |
| --- | --- |
| aha_cart | 0.006 |
| t | 0.005 |
| n_session | 0.004 |
| n_view | 0.004 |
| brand_diversity | 0.003 |
| cat_diversity | 0.002 |
| active_days | 0.001 |
| n_offer | 0.000 |
| n_like | 0.000 |

## Embargo gap sweep (holdout PR-AUC -> plateau = leakage-controlled)

| gap | holdout_pr_auc | n_rows | base_rate |
| --- | --- | --- | --- |
| 0 | 0.016 | 37986 | 0.006 |
| 1 | 0.014 | 35614 | 0.007 |
| 2 | 0.015 | 33099 | 0.008 |
| 3 | 0.014 | 30847 | 0.008 |
| 5 | 0.011 | 26400 | 0.008 |
| 7 | 0.011 | 22095 | 0.008 |

## Aha grid: X>=k in window n (operational rule, on temporal holdout)

**Selected aha rule:** ≥1 cart events in first 3d (MCC=0.099, lift=0.93, coverage=58.7%).

| behavior | n | k | precision | recall | f1 | mcc | lift | coverage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| n_cart | 1 | 1 | 0.053 | 0.380 | 0.093 | 0.033 | 0.825 | 0.310 |
| n_cart | 1 | 2 | 0.080 | 0.127 | 0.098 | 0.049 | 1.234 | 0.069 |
| n_cart | 1 | 3 | 0.091 | 0.014 | 0.024 | 0.019 | 1.409 | 0.007 |
| n_cart | 3 | 1 | 0.060 | 0.817 | 0.112 | 0.099 | 0.934 | 0.587 |
| n_cart | 3 | 2 | 0.072 | 0.451 | 0.124 | 0.086 | 1.117 | 0.271 |
| n_cart | 3 | 3 | 0.062 | 0.183 | 0.093 | 0.035 | 0.964 | 0.128 |
| n_cart | 3 | 5 | 0.000 | 0.000 | 0.000 | -0.023 | 0.000 | 0.012 |
