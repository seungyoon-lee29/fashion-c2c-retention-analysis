"""Discrete-time competing-risks survival: cause-specific hazards, CIF, OOT validation.

- Empirical CIF via the Aalen-Johansen product-limit estimator (model-free description).
- Cause-specific hazard models h_convert, h_lapse (logistic or GBM) used by the
  g-computation impact stage. Competing risks => lapse is modelled, not treated as
  non-informative censoring.
- Out-of-time validation: fit on early cohorts, score later cohorts (the credibility core).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

from personperiod import CONFOUNDER_COLS, CONVERT, LAPSE

DESIGN_COLS = CONFOUNDER_COLS + ["aha_cart", "t"]


def _make_clf(cfg: dict):
    kind = cfg["hazard"]["model"]
    if kind == "logistic":
        return LogisticRegression(max_iter=1000, C=1.0)
    return HistGradientBoostingClassifier(max_depth=3, max_iter=150,
                                          learning_rate=0.08, random_state=cfg.get("seed", 17))


def _fit_one(pp: pd.DataFrame, target_code: int, cfg: dict):
    X = pp[DESIGN_COLS].to_numpy(float)
    y = (pp["event"].to_numpy() == target_code).astype(int)
    clf = _make_clf(cfg)
    if y.sum() < 5 or y.sum() == len(y):
        # degenerate: fall back to a constant-rate predictor
        rate = float(y.mean())
        return _ConstHazard(rate)
    clf.fit(X, y)
    if cfg["hazard"].get("calibrate", False) and y.sum() >= 30:
        try:
            clf = CalibratedClassifierCV(clf, method="isotonic", cv=3).fit(X, y)
        except Exception:
            pass
    return clf


class _ConstHazard:
    def __init__(self, rate: float):
        self.rate = max(1e-6, min(1 - 1e-6, rate))

    def predict_proba(self, X):
        p = np.full(len(X), self.rate)
        return np.column_stack([1 - p, p])


def fit_cause_specific(pp: pd.DataFrame, cfg: dict) -> dict:
    """Return fitted hazard models for convert and lapse."""
    return {
        "convert": _fit_one(pp, CONVERT, cfg),
        "lapse": _fit_one(pp, LAPSE, cfg),
        "cols": DESIGN_COLS,
    }


def predict_hazards(bundle: dict, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    Xa = X[bundle["cols"]].to_numpy(float)
    hc = bundle["convert"].predict_proba(Xa)[:, 1]
    hl = bundle["lapse"].predict_proba(Xa)[:, 1]
    # keep total absorbing hazard < 1
    tot = hc + hl
    scale = np.where(tot > 0.999, 0.999 / np.maximum(tot, 1e-9), 1.0)
    return hc * scale, hl * scale


def empirical_cif(pp: pd.DataFrame, max_t: int | None = None) -> dict:
    """Aalen-Johansen CIF for convert & lapse, plus overall survival."""
    if max_t is None:
        max_t = int(pp["t"].max())
    S_prev = 1.0
    cif_c = cif_l = 0.0
    out = {"t": [], "cif_convert": [], "cif_lapse": [], "survival": []}
    for t in range(max_t + 1):
        at = pp[pp["t"] == t]
        n = len(at)
        if n == 0:
            out["t"].append(t); out["cif_convert"].append(cif_c)
            out["cif_lapse"].append(cif_l); out["survival"].append(S_prev)
            continue
        d_c = int((at["event"] == CONVERT).sum())
        d_l = int((at["event"] == LAPSE).sum())
        h_c, h_l = d_c / n, d_l / n
        cif_c += S_prev * h_c
        cif_l += S_prev * h_l
        S_prev = S_prev * (1 - h_c - h_l)
        out["t"].append(t); out["cif_convert"].append(cif_c)
        out["cif_lapse"].append(cif_l); out["survival"].append(S_prev)
    return {k: np.array(v) for k, v in out.items()}


def oot_validation(pp: pd.DataFrame, cohort: pd.DataFrame, cfg: dict) -> dict:
    """Temporal split: fit on early-t0 cohort, score later cohort (per-step convert hazard)."""
    t0 = cohort.set_index("user_id")["t0_day"]
    cut = t0.median()
    early = pp[pp["user_id"].map(t0) <= cut]
    late = pp[pp["user_id"].map(t0) > cut]
    if early["event"].eq(CONVERT).sum() < 10 or late["event"].eq(CONVERT).sum() < 5:
        return {"note": "insufficient events for OOT split", "n_early": len(early), "n_late": len(late)}
    bundle = fit_cause_specific(early, cfg)
    hc, _ = predict_hazards(bundle, late)
    y = (late["event"].to_numpy() == CONVERT).astype(int)
    return {
        "n_early_rows": int(len(early)), "n_late_rows": int(len(late)),
        "oot_pr_auc": float(average_precision_score(y, hc)) if y.sum() else None,
        "oot_roc_auc": float(roc_auc_score(y, hc)) if 0 < y.sum() < len(y) else None,
        "base_rate_late": float(y.mean()),
    }
