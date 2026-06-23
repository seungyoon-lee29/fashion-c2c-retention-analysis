# Impact: g-computation + cross-checks

## Conversion risk difference under the activation lever (by horizon)

- **naive (confounded)**: Δ=+0.0515  (r1=0.0853, r0=0.0339)
- **g-formula (standardised)**: Δ=+0.0404  (CIF lever1=0.1028, lever0=0.0625)
- **IPTW/MSM (cross-check)**: Δ=+0.0496
- **risk ratio**=1.646 → **E-value**=2.68 (unmeasured confounder assoc. needed to explain it away)

**Positivity**: e∈[0.055,0.975], frac extreme=3.9%, max weight=10.8

## Memoryless Markov approximation (absorbing chain, NOT the headline)

- expected conversions per 1000 (eventual): **370** [90% CI 341–403]  (row-sum check=1.000)

## Lever ledger (per 1000 new-observed users)

- conservative: 83
- base: 103
- optimistic: 123

## Disagreement protocol
- g-formula vs IPTW rel-diff=22.9% → agree within threshold

> Honesty: g-formula identification rests on sequential exchangeability + positivity + consistency. These are assumptions, not facts — the E-value bounds their fragility. No randomised experiment is present in MerRec, so this is a defensible *conditional* estimate, not proof of causation.
