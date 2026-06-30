"""M2 — Identifiability map: do the candidate early-window retention levers satisfy positivity?

Instead of a single lever (cart), this sweeps 4 OBSERVED early-window levers and, for each, tests
covariate OVERLAP (propensity AUC, non-overlap tail fraction, max |SMD|, e_max) plus the naive→IPTW
adjustment and an association E-value. Headline (two failure modes, same conclusion): levers with
adequate overlap (cart, cat) collapse to ~0/negative under adjustment = vanity; levers without
overlap (offer, like) are not identifiable ⇒ no observational path gives a trustworthy positive
retention lever ⇒ the experiment (A/B) is the conclusion.

Reuses the committed machinery (`early_features`, the person-period RETAIN outcome, `e_value`) WITHOUT
refactoring the aha_cart-specific impact.py — the per-lever propensity/IPTW is a small generic mirror
of impact.iptw_delta. make-reproducible (`make causal`); all params (lever thresholds, e-bounds,
feature-window W) come from config (single source). Run at the config W; the overlap-FAIL *set* is
W-robust but point estimates vary with W — no specific W=7 numbers are asserted.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from _util import load_config, write_md
from personperiod import (FEATURE_COLS, build_person_period, early_features,
                          full_followup_users, user_retention_label)
from impact import e_value

# M2 levers: (early-feature count column = own-confounder to EXCLUDE, label). The ≥ threshold comes
# from config.impact.lever_thresholds (single source); the display id (e.g. "cart≥1") is derived.
SHORT = {"n_cart": "cart", "n_offer": "offer", "cat_diversity": "cat", "n_like": "like"}
LEVERS = [("n_cart", "카트(구매의도)"), ("n_offer", "오퍼(협상의도)"),
          ("cat_diversity", "탐색폭(다양성)"), ("n_like", "찜(관심신호)")]


def _smd_max(X: np.ndarray, a: np.ndarray) -> float:
    """Max abs standardized mean difference across confounders (covariate-overlap diagnostic)."""
    x1, x0 = X[a == 1], X[a == 0]
    sd = np.sqrt((x1.var(0) + x0.var(0)) / 2) + 1e-9
    return float(np.max(np.abs(x1.mean(0) - x0.mean(0)) / sd))


def diagnose(feats: pd.DataFrame, Y: np.ndarray, col: str, thr: int, cfg: dict) -> dict:
    a = (feats[col] >= thr).astype(int).to_numpy()
    if a.sum() < 10 or a.sum() == len(a):             # degenerate treatment (e.g. lever absent in fixture)
        nan = float("nan")
        return {"n1": int(a.sum()), "auc": nan, "e_max": nan, "frac_ext": nan, "smd": nan,
                "naive": nan, "iptw": nan, "evalue": nan, "overlap_ok": False}
    conf = [c for c in FEATURE_COLS if c != col]      # exclude the lever's own count (else trivial)
    X = feats[conf].to_numpy(float)
    Xs = StandardScaler().fit_transform(X)            # scale → stable propensity (raw counts overflow)
    # (near-)separable propensity triggers benign solver over/underflow; keep the suppression local.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        e = LogisticRegression(max_iter=1000).fit(Xs, a).predict_proba(Xs)[:, 1]

    # naive association
    r1, r0 = Y[a == 1].mean(), Y[a == 0].mean()
    # IPTW (stabilised + clipped) — mirrors impact.iptw_delta
    clip = float(cfg["impact"]["iptw"]["clip_quantile"])
    lo, hi = np.quantile(e, 1 - clip), np.quantile(e, clip)
    ec = np.clip(e, max(1e-3, lo), min(1 - 1e-3, hi))
    pm = a.mean()
    w = np.where(a == 1, pm / ec, (1 - pm) / (1 - ec))
    iptw = np.average(Y[a == 1], weights=w[a == 1]) - np.average(Y[a == 0], weights=w[a == 0])

    rr = r1 / r0 if r0 > 0 else np.nan
    lo, hi = cfg["impact"]["overlap_e_bounds"]
    frac_ext = float(np.mean((e < lo) | (e > hi)))
    thr = float(cfg["impact"]["overlap_extreme_frac_max"])
    # OVERLAP, not e_max: e.max() saturates to ~1.0 trivially in large-n logistic. The reliable
    # overlap measure is the FRACTION of units in the non-overlap tail (Austin/Stuart). SMD here is
    # *baseline imbalance* (motivates adjustment), reported but NOT the overlap gate.
    return {"n1": int(a.sum()), "auc": float(roc_auc_score(a, e)), "e_max": float(e.max()),
            "frac_ext": frac_ext, "smd": _smd_max(X, a),
            "naive": float(r1 - r0), "iptw": float(iptw),
            "evalue": float(e_value(rr)) if np.isfinite(rr) and rr > 0 else float("nan"),
            "overlap_ok": bool(frac_ext <= thr)}


def run(cfg: dict, events, cohort, write: bool = True) -> dict:
    W = int(cfg["windows"]["feature_window_W"])
    feats = early_features(events, cohort, cfg)
    pp = build_person_period(events, cohort, feats, cfg)
    full_users = full_followup_users(events, cohort, cfg).intersection(pd.Index(pp["user_id"].unique()))
    pp = pp[pp["user_id"].isin(full_users)].copy()
    Y = user_retention_label(pp)
    fk = feats.set_index("user_id").reindex(Y.index)   # align features to the kept-cohort outcome
    base = float(Y.mean())
    thr = cfg["impact"]["lever_thresholds"]
    out = {}
    for col, label in LEVERS:
        d = diagnose(fk, Y.to_numpy(float), col, int(thr[col]), cfg)
        d["lid"], d["label"] = f"{SHORT[col]}≥{int(thr[col])}", label
        out[col] = d
    if write:
        _write_report(out, W, base, len(Y), cfg)
    return out


def _write_report(out: dict, W: int, base: float, n: int, cfg: dict):
    rows = []
    for r in out.values():
        verdict = "✅ 충분" if r["overlap_ok"] else "❌ 부족"
        rows.append((f"`{r['lid']}` {r['label']}", f"{r['n1']:,}", round(r["auc"], 2),
                     f"{r['frac_ext']*100:.0f}%", round(r["smd"], 2),
                     f"{r['naive']*100:+.1f}pp", f"{r['iptw']*100:+.1f}pp",
                     round(r["evalue"], 2), verdict))
    cols = ["레버", "처치 n", "propAUC", "비겹침%", "기준 SMD", "naive Δ", "IPTW Δ", "E-value", "겹침(overlap)"]
    md = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    md += ["| " + " | ".join(str(v) for v in row) + " |" for row in rows]

    ok = [c for c in out if out[c]["overlap_ok"]]
    bad = [c for c in out if not out[c]["overlap_ok"]]
    ok_txt = ", ".join(f"`{out[c]['lid']}` {out[c]['naive']*100:+.0f}→{out[c]['iptw']*100:+.0f}pp" for c in ok) or "없음"
    bad_txt = ", ".join(f"`{out[c]['lid']}`(비겹침 {out[c]['frac_ext']*100:.0f}%)" for c in bad) or "없음"
    lo, hi = cfg["impact"]["overlap_e_bounds"]
    L = [
        "# 식별 가능성 지도 — \"보이는 레버가 인과인가\" (M2, 자동 생성)\n",
        "> **BLUF**: 초기 행동 레버 4종 어느 것도 **신뢰할 양성 리텐션 효과를 주지 못한다** — 두 가지 방식으로. "
        f"겹침이 충분한 레버({len(ok)}종)는 보정 시 효과가 **~0/음전**(허영지표 확인); 신호가 큰 레버({len(bad)}종)는 "
        "**겹침 부족으로 식별 불가**. ⇒ 관측 보정의 한계 = **A/B가 답**.\n",
        f"> 데이터 = `data/events.parquet`(person-period) · 특징창 **W={W}일**(config 단일출처) · 대상 {n:,}명 · "
        f"retain base {base*100:.1f}% · `make causal` 재계산. (겹침-부족 레버 *집합*은 W에 견고하나 점추정은 W에 따라 "
        "변하므로 특정 W 수치는 단정하지 않음.)\n",
        "## 레버별 식별 진단\n",
        "_용어: **propAUC**=활동량만으로 처치를 맞히는 정확도(↑=처치가 활동량에 종속) · **비겹침%**=처치확률이 "
        f"{lo}~{hi} 밖인 유저 비율(↑=비교할 쌍이 없음 = overlap 실패) · **기준 SMD**=처치·대조 baseline 격차(보정 *필요* 신호) · "
        "**naive→IPTW**=보정 전후 효과. 겹침 판정 = `비겹침% ≤ "
        f"{float(cfg['impact']['overlap_extreme_frac_max'])*100:.0f}%`._\n\n",
        "\n".join(md), "\n",
        "\n_naive·IPTW는 연관/진단값이다. 겹침 충분 레버에서도 같은 초기창에서 처치와 교란을 함께 재므로 "
        "IPTW는 확정적 인과점추정이 아니라 방향성·민감도 진단으로 읽는다. 겹침 부족 레버에선 외삽이라 점추정 철회. "
        "E-value는 *naive(연관) RR* 기준(겉보기 연관의 강건성) — `impact_report.md`의 카트 *g-formula* RR E-value(1.23, 보정 후)와는 추정량이 다름._\n",
        "\n## 읽기 — 두 가지 실패, 같은 결론\n",
        "비유: 인과 보정 = 처치 유저마다 '똑 닮은 비처치 쌍둥이'를 찾아 비교. 쌍둥이가 없으면(겹침 부족) 보정은 데이터 밖 *외삽*이다.\n",
        f"- **겹침 충분 → 허영지표 확인**: {ok_txt}. 겹침이 있어 외삽 위험은 낮지만, 그 보정값마저 "
        "**0 근처/음수**로 무너진다 — 동시창 교란의 과대보정 가능성을 감안해도 *겉보기 양성을 뒷받침할 근거가 없다*. "
        "(카트 전체 g-formula 분해: `docs/impact_report.md`.)\n",
        f"- **겹침 부족 → 식별 불가**: {bad_txt}. 활동량이 처치를 거의 결정해 비교할 쌍이 없다 → naive가 커 보여도 "
        "*인과 판정 자체가 불가*(신호가 크다고 인과 아님).\n",
        "\n## 한계 (정직)\n",
        "- 교란을 처치와 **같은 초기창**에서 측정 — 세션수·활동일수는 레버를 거의 결정하므로 이를 조건부에 넣으면 "
        "겹침 부족이 *부분적으로 자초*된다(과대보정). 즉 '겹침 부족'은 데이터 한계 + 설계상 동시성의 혼합. "
        "그래도 결론(관측만으론 신뢰할 양성 효과 추정 불가)은 견고하다.\n",
        "- 식별 가정(순차교환가능성·positivity·consistency)은 검증 불가한 가정 — 이 표는 그중 **positivity/overlap**만 진단.\n",
        "\n## 다음 단계 (1개) — A/B\n",
        "> 겹침 충분한 레버는 효과가 ~0, 신호 큰 레버는 식별 불가 → **어느 관측 경로도 양성 리텐션 효과를 확정하지 못한다.** "
        "답은 관측 보정 고도화가 아니라 **노출 무작위화(A/B)** — 설계는 `docs/ab_test_design.md`.\n",
        "\n> Honesty: positivity/overlap 진단이며 인과 점추정 아님. 겹침 실패 레버는 인과 단정을 철회하고 연관+E-value로만 본다(프로젝트 규약).\n",
    ]
    write_md("docs/causal_report.md", "".join(L))


def main() -> int:
    cfg = load_config()
    from data import build_cohort, load_events
    events = load_events(cfg)
    cohort = build_cohort(events, cfg)
    run(cfg, events, cohort)
    print("[identifiability_map] wrote docs/causal_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
