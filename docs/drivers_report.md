# Drivers, leakage control & aha playbook

## Driver importance (retention hazard) — method: shap

| feature | importance |
| --- | --- |
| n_session | 0.021 |
| active_days | 0.019 |
| t | 0.015 |
| n_view | 0.012 |
| n_like | 0.005 |
| brand_diversity | 0.005 |
| aha_cart | 0.001 |
| cat_diversity | 0.000 |
| n_offer | 0.000 |

## Embargo gap sweep (holdout PR-AUC -> plateau = leakage-controlled)

| gap | holdout_pr_auc | n_rows | base_rate |
| --- | --- | --- | --- |
| 0 | 0.196 | 128645 | 0.072 |
| 1 | 0.189 | 110785 | 0.075 |
| 2 | 0.184 | 93259 | 0.080 |
| 3 | 0.197 | 75732 | 0.090 |
| 5 | 0.191 | 56943 | 0.104 |
| 7 | 0.181 | 54048 | 0.101 |

## Aha grid: X>=k in window n (operational rule, on temporal holdout)

**Selected aha rule:** ≥1 cart events in first 3d (MCC=0.119, lift=1.15, coverage=9.2%).

| behavior | n | k | precision | recall | f1 | mcc | lift | coverage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| n_cart | 1 | 1 | 0.415 | 0.105 | 0.168 | 0.077 | 1.035 | 0.074 |
| n_cart | 1 | 2 | 0.496 | 0.050 | 0.091 | 0.079 | 1.237 | 0.030 |
| n_cart | 1 | 3 | 0.485 | 0.020 | 0.039 | 0.047 | 1.211 | 0.012 |
| n_cart | 1 | 5 | 0.605 | 0.009 | 0.018 | 0.046 | 1.510 | 0.004 |
| n_cart | 3 | 1 | 0.462 | 0.146 | 0.221 | 0.119 | 1.153 | 0.092 |
| n_cart | 3 | 2 | 0.549 | 0.075 | 0.131 | 0.115 | 1.370 | 0.040 |
| n_cart | 3 | 3 | 0.551 | 0.035 | 0.066 | 0.078 | 1.375 | 0.018 |
| n_cart | 3 | 5 | 0.639 | 0.019 | 0.036 | 0.071 | 1.594 | 0.009 |
