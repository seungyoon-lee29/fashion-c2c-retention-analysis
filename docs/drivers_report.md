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

**Selected aha rule:** ≥1 cart events in first 3d (MCC=0.113, lift=1.14, coverage=9.6%).

| behavior | n | k | precision | recall | f1 | mcc | lift | coverage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| n_cart | 1 | 1 | 0.358 | 0.118 | 0.178 | 0.080 | 1.052 | 0.080 |
| n_cart | 1 | 2 | 0.414 | 0.053 | 0.094 | 0.072 | 1.216 | 0.031 |
| n_cart | 1 | 3 | 0.423 | 0.024 | 0.045 | 0.050 | 1.241 | 0.014 |
| n_cart | 1 | 5 | 0.520 | 0.012 | 0.023 | 0.049 | 1.528 | 0.006 |
| n_cart | 3 | 1 | 0.389 | 0.155 | 0.222 | 0.113 | 1.142 | 0.096 |
| n_cart | 3 | 2 | 0.455 | 0.078 | 0.133 | 0.104 | 1.336 | 0.041 |
| n_cart | 3 | 3 | 0.484 | 0.040 | 0.074 | 0.081 | 1.422 | 0.020 |
| n_cart | 3 | 5 | 0.577 | 0.021 | 0.041 | 0.074 | 1.694 | 0.009 |
