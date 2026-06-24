"""Impact estimation: reuse the survival spine as a g-computation engine.

Three estimators of the SAME estimand (risk difference in retention by horizon H
under the activation lever `aha_cart`):
  - naive      : unadjusted CIF(lever=1) - CIF(lever=0)         [confounded, upper-biased]
  - g-formula  : standardisation via the cause-specific hazards [adjusts for features]
  - IPTW/MSM   : stabilised inverse-propensity weighting        [cross-check, different model]
Plus: E-value (confounding robustness), a memoryless Markov approximation with a
Dirichlet posterior band, a lever ledger (conservative/base/optimistic), and a
pre-registered disagreement check between g-formula and IPTW.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from _util import load_config, write_md
from personperiod import (CONFOUNDER_COLS, RETAIN, build_person_period,
                          early_features)
from survival import (DESIGN_COLS, fit_cause_specific, oot_validation,
                      predict_hazards)


def _h_steps(cfg: dict) -> int:
    return max(1, int(cfg["windows"]["horizon_H"]) // int(cfg["person_period"]["step_days"]))


def gformula_cif(bundle: dict, feats: pd.DataFrame, x: int, cfg: dict) -> float:
    """Population CIF of retention (return) by horizon under do(aha_cart=x), standardising over features."""
    base = feats[CONFOUNDER_COLS].copy()
    base["aha_cart"] = int(x)
    n = len(base)
    S = np.ones(n); cif = np.zeros(n)
    for t in range(_h_steps(cfg)):
        d = base.copy(); d["t"] = t
        hc, hl = predict_hazards(bundle, d[DESIGN_COLS])
        cif += S * hc
        S *= (1 - hc - hl)
    return float(cif.mean())


def naive_delta(pp: pd.DataFrame) -> tuple[float, float, float]:
    lab = pp.groupby("user_id").agg(conv=("event", lambda s: int((s == RETAIN).any())),
                                    aha=("aha_cart", "first"))
    r1 = lab.loc[lab["aha"] == 1, "conv"].mean()
    r0 = lab.loc[lab["aha"] == 0, "conv"].mean()
    return float(r1 - r0), float(r1), float(r0)


def iptw_delta(pp: pd.DataFrame, feats: pd.DataFrame, cfg: dict) -> dict:
    lab = pp.groupby("user_id").agg(conv=("event", lambda s: int((s == RETAIN).any()))).reset_index()
    f = feats.merge(lab, on="user_id")
    X = f[CONFOUNDER_COLS].to_numpy(float)
    a = f["aha_cart"].to_numpy(int)
    if a.sum() < 10 or a.sum() == len(a):
        return {"delta": np.nan, "positivity": None, "note": "degenerate treatment"}
    e = LogisticRegression(max_iter=1000).fit(X, a).predict_proba(X)[:, 1]
    clip = float(cfg["impact"]["iptw"]["clip_quantile"])
    lo, hi = np.quantile(e, 1 - clip), np.quantile(e, clip)
    e = np.clip(e, max(1e-3, lo), min(1 - 1e-3, hi))
    pmarg = a.mean()
    w = np.where(a == 1, pmarg / e, (1 - pmarg) / (1 - e))
    y = f["conv"].to_numpy(float)
    r1 = np.average(y[a == 1], weights=w[a == 1])
    r0 = np.average(y[a == 0], weights=w[a == 0])
    return {"delta": float(r1 - r0), "r1": float(r1), "r0": float(r0),
            "positivity": {"e_min": float(e.min()), "e_max": float(e.max()),
                           "frac_extreme": float(np.mean((e < 0.05) | (e > 0.95)))},
            "weight_max": float(w.max())}


def e_value(rr: float) -> float:
    rr = max(rr, 1.0 / max(rr, 1e-9))  # work on the >=1 side
    return float(rr + np.sqrt(rr * (rr - 1)))


def markov_absorbing(pp: pd.DataFrame, cfg: dict) -> dict:
    """Memoryless approximation: pooled per-step hazards -> absorbing chain B=N R, with Dirichlet band."""
    n = len(pp)
    d_c = int((pp["event"] == RETAIN).sum())
    d_l = int((pp["event"] == 2).sum())
    stay = n - d_c - d_l
    counts = np.array([stay, d_c, d_l], float)
    h_c, h_l = d_c / n, d_l / n
    q = 1 - h_c - h_l                       # P(stay at risk)
    N = 1.0 / max(1e-9, 1 - q)              # fundamental matrix (scalar)
    b_retain = N * h_c                      # absorption prob into retention (return)
    # Dirichlet posterior band
    prior = float(cfg["impact"]["dirichlet_prior"])
    rng = np.random.default_rng(int(cfg.get("seed", 17)))
    draws = rng.dirichlet(counts + prior, size=int(cfg["impact"]["n_sims"]))
    b_draws = draws[:, 1] / np.clip(draws[:, 1] + draws[:, 2], 1e-9, None)
    return {"per1000_point": float(1000 * b_retain),
            "per1000_lo": float(1000 * np.quantile(b_draws, 0.05)),
            "per1000_hi": float(1000 * np.quantile(b_draws, 0.95)),
            "row_sum_check": float((counts / counts.sum()).sum())}


def run(cfg: dict, events, cohort, feats=None, pp=None) -> dict:
    if feats is None:
        feats = early_features(events, cohort, cfg)
    if pp is None:
        pp = build_person_period(events, cohort, feats, cfg)
    feats_kept = feats[feats["user_id"].isin(pp["user_id"].unique())].reset_index(drop=True)

    bundle = fit_cause_specific(pp, cfg)
    oot = oot_validation(pp, cohort, cfg)
    cif1 = gformula_cif(bundle, feats_kept, 1, cfg)
    cif0 = gformula_cif(bundle, feats_kept, 0, cfg)
    g_delta = cif1 - cif0
    nd, nr1, nr0 = naive_delta(pp)
    iptw = iptw_delta(pp, feats_kept, cfg)
    rr = cif1 / cif0 if cif0 > 0 else np.nan
    ev = e_value(rr) if np.isfinite(rr) and rr > 0 else np.nan
    mk = markov_absorbing(pp, cfg)

    # lever ledger scenarios on the anchored (g-formula) lever
    base1000 = 1000 * cif0
    ledger = {name: {"per1000": float(base1000 + 1000 * mult * g_delta)}
              for name, mult in cfg["impact"]["lever_ledger"].items()}

    # pre-registered disagreement check (g-formula vs IPTW)
    thr = float(cfg["impact"]["disagreement_threshold_pct"]) / 100
    diverge = None
    if iptw.get("delta") is not None and np.isfinite(iptw["delta"]) and abs(g_delta) > 1e-6:
        rel = abs(g_delta - iptw["delta"]) / abs(g_delta)
        diverge = {"rel_diff": float(rel), "exceeds": bool(rel > thr)}

    res = {
        "cif_lever1": cif1, "cif_lever0": cif0, "gformula_delta": g_delta,
        "naive_delta": nd, "naive_r1": nr1, "naive_r0": nr0,
        "iptw": iptw, "risk_ratio": rr, "e_value": ev,
        "markov": mk, "ledger": ledger, "disagreement": diverge, "oot": oot,
    }
    _write_report(res, cfg)
    return res


def _write_report(r: dict, cfg: dict):
    L = ["# Impact: g-computation + cross-checks\n"]
    L.append("## Retention risk difference under the activation lever (by horizon)\n")
    L.append(f"- **naive (confounded)**: Δ={r['naive_delta']:+.4f}  (r1={r['naive_r1']:.4f}, r0={r['naive_r0']:.4f})")
    L.append(f"- **g-formula (standardised)**: Δ={r['gformula_delta']:+.4f}  "
             f"(CIF lever1={r['cif_lever1']:.4f}, lever0={r['cif_lever0']:.4f})")
    idl = r["iptw"].get("delta")
    L.append(f"- **IPTW/MSM (cross-check)**: Δ={idl:+.4f}" if idl is not None and np.isfinite(idl)
             else f"- **IPTW/MSM**: n/a ({r['iptw'].get('note','')})")
    L.append(f"- **risk ratio**={r['risk_ratio']:.3f} → **E-value**={r['e_value']:.2f} "
             "(unmeasured confounder assoc. needed to explain it away)\n")
    if r["iptw"].get("positivity"):
        p = r["iptw"]["positivity"]
        L.append(f"**Positivity**: e∈[{p['e_min']:.3f},{p['e_max']:.3f}], "
                 f"frac extreme={p['frac_extreme']:.1%}, max weight={r['iptw'].get('weight_max',float('nan')):.1f}\n")
    oot = r.get("oot") or {}
    if oot.get("oot_pr_auc") is not None:
        L.append("## Out-of-time validation (fit early-t0 cohort → score later cohort)\n")
        L.append(f"- retain-hazard holdout PR-AUC={oot['oot_pr_auc']:.3f}"
                 + (f", ROC-AUC={oot['oot_roc_auc']:.3f}" if oot.get('oot_roc_auc') is not None else "")
                 + f" (late base rate={oot['base_rate_late']:.3f}, "
                 f"n_early={oot['n_early_rows']}, n_late={oot['n_late_rows']})\n")
    elif oot.get("note"):
        L.append(f"## Out-of-time validation\n- skipped: {oot['note']}\n")
    L.append("## Memoryless Markov approximation (absorbing chain, NOT the headline)\n")
    mk = r["markov"]
    L.append(f"- expected retentions per 1000 (eventual): **{mk['per1000_point']:.0f}** "
             f"[90% CI {mk['per1000_lo']:.0f}–{mk['per1000_hi']:.0f}]  (row-sum check={mk['row_sum_check']:.3f})\n")
    L.append("## Lever ledger (per 1000 new-observed users)\n")
    for name, d in r["ledger"].items():
        L.append(f"- {name}: {d['per1000']:.0f}")
    if r["disagreement"]:
        dv = r["disagreement"]
        L.append(f"\n## Disagreement protocol\n- g-formula vs IPTW rel-diff={dv['rel_diff']:.1%} "
                 f"→ {'DIVERGE: diagnose which assumption binds' if dv['exceeds'] else 'agree within threshold'}")
    L.append("\n> Honesty: g-formula identification rests on sequential exchangeability + positivity + "
             "consistency. These are assumptions, not facts — the E-value bounds their fragility. "
             "No randomised experiment is present in MerRec, so this is a defensible *conditional* estimate, "
             "not proof of causation.")
    write_md("docs/impact_report.md", "\n".join(L) + "\n")


def main() -> int:
    cfg = load_config()
    from data import build_cohort, load_events
    events = load_events(cfg)
    cohort = build_cohort(events, cfg)
    run(cfg, events, cohort)
    print("[impact] wrote docs/impact_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
