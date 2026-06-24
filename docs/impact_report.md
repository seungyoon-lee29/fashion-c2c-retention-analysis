# Impact: g-computation + cross-checks

## Retention risk difference under the activation lever (by horizon)

- **naive (confounded)**: Δ=+0.1505  (r1=0.4770, r0=0.3265)
- **g-formula (standardised)**: Δ=-0.0120  (CIF lever1=0.3389, lever0=0.3509)
- **IPTW/MSM (cross-check)**: Δ=+0.0272
- **risk ratio**=0.966 → **E-value**=1.23 (unmeasured confounder assoc. needed to explain it away)

**Positivity**: e∈[0.056,0.587], frac extreme=0.0%, max weight=2.2

## Out-of-time validation (fit early-t0 cohort → score later cohort)

- retain-hazard holdout PR-AUC=0.184, ROC-AUC=0.658 (late base rate=0.080, n_early=40000, n_late=53259)

## Memoryless Markov approximation (absorbing chain, NOT the headline)

- expected retentions per 1000 (eventual): **357** [90% CI 352–361]  (row-sum check=1.000)

## Identification diagnosis (g-formula vs IPTW)

- **NULL effect**: both estimators within ±3pp of zero (g-formula -1.2pp, IPTW +2.7pp; abs diff 3.9pp). The 326% relative gap is a null-scale artifact (tiny denominator), **not** a genuine divergence — the effect's sign is not identified. Practical read: the activation lever has no reliable retention effect.

## Lever ledger (per 1000 new-observed users)

- _omitted: no positively-identified lever effect to project (g-formula Δ ≤ 0 / null). Projecting conservative/base/optimistic on a non-positive effect would invert the scenarios._

> Honesty: g-formula identification rests on sequential exchangeability + positivity + consistency. These are assumptions, not facts — the E-value bounds their fragility. No randomised experiment is present in MerRec, so this is a defensible *conditional* estimate, not proof of causation.
