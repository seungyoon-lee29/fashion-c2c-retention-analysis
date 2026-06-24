# Drivers, leakage control & aha playbook

## Driver importance (retention hazard) — method: shap

| feature | importance |
| --- | --- |
| aha_cart | 0.041 |
| n_session | 0.014 |
| brand_diversity | 0.012 |
| cat_diversity | 0.010 |
| n_view | 0.009 |
| n_like | 0.009 |
| active_days | 0.008 |
| n_offer | 0.005 |
| t | 0.005 |

## Embargo gap sweep (holdout PR-AUC -> plateau = leakage-controlled)

| gap | holdout_pr_auc | n_rows | base_rate |
| --- | --- | --- | --- |
| 0 | 0.169 | 12417 | 0.079 |
| 1 | 0.169 | 10046 | 0.099 |
| 2 | 0.168 | 7882 | 0.126 |
| 3 | 0.142 | 7232 | 0.104 |
| 5 | 0.086 | 5514 | 0.063 |
| 7 | 0.048 | 4372 | 0.021 |

## Aha grid: X>=k in window n (operational rule, on temporal holdout)

**Selected aha rule:** ≥1 cart events in first 3d (MCC=0.229, lift=1.14, coverage=60.5%).

| behavior | n | k | precision | recall | f1 | mcc | lift | coverage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| n_cart | 1 | 1 | 0.467 | 0.400 | 0.431 | 0.113 | 1.109 | 0.333 |
| n_cart | 1 | 2 | 0.444 | 0.088 | 0.147 | 0.033 | 1.055 | 0.077 |
| n_cart | 1 | 3 | 0.375 | 0.007 | 0.014 | -0.003 | 0.890 | 0.008 |
| n_cart | 3 | 1 | 0.479 | 0.745 | 0.583 | 0.229 | 1.139 | 0.605 |
| n_cart | 3 | 2 | 0.492 | 0.363 | 0.417 | 0.133 | 1.168 | 0.287 |
| n_cart | 3 | 3 | 0.453 | 0.130 | 0.202 | 0.046 | 1.076 | 0.112 |
| n_cart | 3 | 5 | 0.455 | 0.012 | 0.024 | 0.014 | 1.079 | 0.010 |
