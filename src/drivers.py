"""Driver discovery + leakage control + aha-moment operational playbook.

- Importance of early behaviours on the retention (return) hazard (SHAP if available, else
  permutation importance — model-agnostic, always runs).
- Embargo gap sweep: rebuild labels at gaps 0..7 and watch holdout PR-AUC fall to a
  plateau = the leakage-controlled "true" performance.
- Aha grid: "X >= k within window n (n<=W)" scored by precision/recall/F1/MCC/lift on a
  temporal holdout. The threshold is an *operational rule*, not the causal evidence.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import (average_precision_score, f1_score,
                             matthews_corrcoef, precision_score, recall_score)

from _util import df_to_md, load_config, write_md
from personperiod import RETAIN, FEATURE_COLS, build_person_period, early_features
from survival import DESIGN_COLS, fit_cause_specific, predict_hazards


def importance(pp: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    bundle = fit_cause_specific(pp, cfg)
    X = pp[DESIGN_COLS]
    y = (pp["event"].to_numpy() == RETAIN).astype(int)
    try:
        import shap  # optional
        expl = shap.Explainer(lambda d: predict_hazards(bundle, pd.DataFrame(d, columns=DESIGN_COLS))[0],
                              X.sample(min(200, len(X)), random_state=0).to_numpy(float))
        vals = np.abs(expl(X.sample(min(500, len(X)), random_state=1).to_numpy(float)).values).mean(0)
        imp = pd.Series(vals, index=DESIGN_COLS)
        method = "shap"
    except Exception:
        class _W:
            def fit(self, *a): return self
            def predict(self, d): return predict_hazards(bundle, pd.DataFrame(d, columns=DESIGN_COLS))[0]
        r = permutation_importance(_W().fit(), X.to_numpy(float), y, n_repeats=8,
                                   random_state=0, scoring=_ap_score)
        imp = pd.Series(r.importances_mean, index=DESIGN_COLS)
        method = "permutation (Δ PR-AUC)"
    out = imp.sort_values(ascending=False).reset_index()
    out.columns = ["feature", "importance"]
    out.attrs["method"] = method
    return out


def _ap_score(est, X, y):
    # drop in PR-AUC when a feature is shuffled = its importance (sensitive to rare events)
    if y.sum() == 0:
        return 0.0
    return average_precision_score(y, est.predict(X))


def gap_sweep(events, cohort, cfg) -> pd.DataFrame:
    t0 = cohort.set_index("user_id")["t0_day"]
    cut = t0.median()
    recs = []
    for g in cfg["windows"]["gap_sweep"]:
        feats = early_features(events, cohort, cfg)
        pp = build_person_period(events, cohort, feats, cfg, gap_override=int(g))
        if pp.empty or (pp["event"] == RETAIN).sum() < 10:
            recs.append({"gap": g, "holdout_pr_auc": np.nan, "n_rows": len(pp)})
            continue
        early = pp[pp["user_id"].map(t0) <= cut]
        late = pp[pp["user_id"].map(t0) > cut]
        if (early["event"] == RETAIN).sum() < 5 or (late["event"] == RETAIN).sum() < 3:
            recs.append({"gap": g, "holdout_pr_auc": np.nan, "n_rows": len(pp)})
            continue
        bundle = fit_cause_specific(early, cfg)
        hc, _ = predict_hazards(bundle, late)
        y = (late["event"].to_numpy() == RETAIN).astype(int)
        recs.append({"gap": g, "holdout_pr_auc": float(average_precision_score(y, hc)),
                     "n_rows": len(pp), "base_rate": float(y.mean())})
    return pd.DataFrame(recs)


def user_retention_label(pp: pd.DataFrame) -> pd.Series:
    return pp.groupby("user_id")["event"].apply(lambda s: int((s == RETAIN).any()))


def aha_grid(events, cohort, pp, cfg) -> pd.DataFrame:
    """Grid over k and window n (n<=W) for the cart lever, scored on temporal holdout."""
    W = int(cfg["windows"]["feature_window_W"])
    label = user_retention_label(pp)
    t0 = cohort.set_index("user_id")["t0_day"]
    cut = t0.median()
    ev = events.copy()
    ev["stime"] = pd.to_datetime(ev["stime"])
    data_start = ev["stime"].min().normalize()
    ev["day"] = (ev["stime"].dt.normalize() - data_start).dt.days
    ev = ev.join(t0.rename("t0d"), on="user_id")

    recs = []
    users = label.index
    is_late = users.map(lambda u: t0.get(u, 0) > cut)
    base = label.mean()
    for n in [x for x in cfg["windows"]["aha_windows_n"] if x <= W]:
        win = ev[(ev["day"] >= ev["t0d"]) & (ev["day"] < ev["t0d"] + n)]
        cart_n = win[win["event"] == "item_add_to_cart_tap"].groupby("user_id").size()
        cart_n = cart_n.reindex(users).fillna(0)
        for k in cfg["aha_grid"]["k_values"]:
            pred = (cart_n >= k).astype(int)
            yh = label[is_late.values].to_numpy()
            ph = pred[is_late.values].to_numpy()
            if ph.sum() == 0 or yh.sum() == 0:
                continue
            prec = precision_score(yh, ph, zero_division=0)
            recs.append({
                "behavior": "n_cart", "n": n, "k": k,
                "precision": prec, "recall": recall_score(yh, ph, zero_division=0),
                "f1": f1_score(yh, ph, zero_division=0), "mcc": matthews_corrcoef(yh, ph),
                "lift": prec / base if base > 0 else np.nan,
                "coverage": float(ph.mean()),
            })
    return pd.DataFrame(recs)


def run(cfg: dict, events, cohort) -> dict:
    feats = early_features(events, cohort, cfg)
    pp = build_person_period(events, cohort, feats, cfg)
    imp = importance(pp, cfg)
    sweep = gap_sweep(events, cohort, cfg)
    aha = aha_grid(events, cohort, pp, cfg)
    _write_report(imp, sweep, aha, cfg)
    return {"importance": imp, "gap_sweep": sweep, "aha": aha, "pp": pp, "feats": feats}


def _write_report(imp, sweep, aha, cfg):
    lines = ["# Drivers, leakage control & aha playbook\n"]
    lines.append(f"## Driver importance (retention hazard) — method: {imp.attrs.get('method','?')}\n")
    lines.append(df_to_md(imp.round(4)))
    lines.append("\n## Embargo gap sweep (holdout PR-AUC -> plateau = leakage-controlled)\n")
    lines.append(df_to_md(sweep.round(4)))
    lines.append("\n## Aha grid: X>=k in window n (operational rule, on temporal holdout)\n")
    if not aha.empty:
        best = aha.sort_values("mcc", ascending=False).head(1).iloc[0]
        lines.append(f"**Selected aha rule:** ≥{int(best['k'])} cart events in first {int(best['n'])}d "
                     f"(MCC={best['mcc']:.3f}, lift={best['lift']:.2f}, coverage={best['coverage']:.1%}).\n")
        lines.append(df_to_md(aha.round(3)))
    else:
        lines.append("_grid empty (insufficient positives on holdout)._")
    write_md("docs/drivers_report.md", "\n".join(lines) + "\n")


def main() -> int:
    cfg = load_config()
    from data import build_cohort, load_events
    events = load_events(cfg)
    cohort = build_cohort(events, cfg)
    run(cfg, events, cohort)
    print("[drivers] wrote docs/drivers_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
