# Impact: g-computation + cross-checks

## Retention risk difference under the activation lever (by horizon)

- **naive (confounded)**: Δ=+0.2704  (r1=0.5263, r0=0.2559)
- **g-formula (standardised)**: Δ=+0.2366  (CIF lever1=0.5382, lever0=0.3016)
- **IPTW/MSM (cross-check)**: Δ=+0.2598
- **risk ratio**=1.785 → **E-value**=2.97 (unmeasured confounder assoc. needed to explain it away)

**Positivity**: e∈[0.082,0.969], frac extreme=2.6%, max weight=6.7

## Out-of-time validation (fit early-t0 cohort → score later cohort)

- retain-hazard holdout PR-AUC=0.168, ROC-AUC=0.609 (late base rate=0.126, n_early=4634, n_late=3248)

## Memoryless Markov approximation (absorbing chain, NOT the headline)

- expected retentions per 1000 (eventual): **480** [90% CI 464–499]  (row-sum check=1.000)

## Identification diagnosis (g-formula vs IPTW)

- **AGREE**: g-formula and IPTW within thresholds (abs diff 2.3pp).

## Lever ledger (per 1000 new-observed users)

- conservative: 420
- base: 538
- optimistic: 657

> Honesty: g-formula identification rests on sequential exchangeability + positivity + consistency. These are assumptions, not facts — the E-value bounds their fragility. No randomised experiment is present in MerRec, so this is a defensible *conditional* estimate, not proof of causation.
