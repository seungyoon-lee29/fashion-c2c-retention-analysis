# Impact: g-computation + cross-checks

## Retention risk difference under the activation lever (by horizon)

_User-level naive/IPTW contrasts and g-formula standardisation use full-follow-up users only (n=22,165) so right-censored users are not counted as non-retained._

- **naive (confounded)**: Δ=+0.1603  (r1=0.5467, r0=0.3864)
- **g-formula (standardised)**: Δ=-0.0123  (CIF lever1=0.3533, lever0=0.3656)
- **IPTW/MSM (cross-check)**: Δ=+0.0323
- **risk ratio**=0.966 → **E-value**=1.23 (unmeasured confounder assoc. needed to explain it away)

**Positivity**: e∈[0.053,0.568], frac extreme=0.0%, max weight=2.1

## Out-of-time validation (fit early-t0 cohort → score later cohort)

- retain-hazard holdout PR-AUC=0.184, ROC-AUC=0.658 (late base rate=0.080, n_early=40000, n_late=53259)

## Memoryless Markov approximation (absorbing chain, NOT the headline)

- expected retentions per 1000 (eventual): **357** [90% CI 352–361]  (row-sum check=1.000)

## Identification diagnosis (g-formula vs IPTW)

- **DIVERGE**: rel-diff=362% and abs-diff=4.5pp exceed thresholds → diagnose which assumption binds (hazard-model misspecification vs propensity/positivity), do not average.

## Lever ledger (per 1000 new-observed users)

- _omitted: no positively-identified lever effect to project (g-formula Δ ≤ 0 / null). Projecting conservative/base/optimistic on a non-positive effect would invert the scenarios._

> Honesty: g-formula identification rests on sequential exchangeability + positivity + consistency. These are assumptions, not facts — the E-value bounds their fragility. No randomised experiment is present in MerRec, so this is a defensible *conditional* estimate, not proof of causation.
