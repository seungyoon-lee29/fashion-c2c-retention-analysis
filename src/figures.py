"""Generate the report figures (matplotlib, no seaborn). All saved under docs/figures/."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from _util import ROOT, load_config
from personperiod import build_person_period, early_features
from survival import empirical_cif


def _outdir(cfg) -> Path:
    d = ROOT / cfg["figures"]["dir"]; d.mkdir(parents=True, exist_ok=True)
    return d


def fig_cif(pp, out: Path, dpi):
    c = empirical_cif(pp)
    plt.figure(figsize=(6, 4))
    plt.plot(c["t"], c["cif_retain"], label="retain (return)", color="#2a7")
    plt.plot(c["t"], c["cif_lapse"], label="lapse (churn)", color="#c44")
    plt.xlabel("step (since delayed entry)"); plt.ylabel("cumulative incidence")
    plt.title("Competing-risks CIF: retention vs churn"); plt.legend(); plt.tight_layout()
    plt.savefig(out / "cif_competing_risks.png", dpi=dpi); plt.close()


def fig_cif_by_aha(pp, out: Path, dpi):
    plt.figure(figsize=(6, 4))
    for x, col in [(1, "#2a7"), (0, "#888")]:
        sub = pp[pp["aha_cart"] == x]
        if sub.empty:
            continue
        c = empirical_cif(sub)
        plt.plot(c["t"], c["cif_retain"], color=col, label=f"aha_cart={x}")
    plt.xlabel("step"); plt.ylabel("CIF retain"); plt.title("Retention CIF by activation")
    plt.legend(); plt.tight_layout(); plt.savefig(out / "cif_by_aha.png", dpi=dpi); plt.close()


def fig_gap(sweep, out: Path, dpi):
    plt.figure(figsize=(6, 4))
    plt.plot(sweep["gap"], sweep["holdout_pr_auc"], "o-", color="#36c")
    plt.xlabel("embargo gap (days)"); plt.ylabel("holdout PR-AUC")
    plt.title("Leakage control: gap sweep → plateau"); plt.tight_layout()
    plt.savefig(out / "gap_sweep.png", dpi=dpi); plt.close()


def fig_importance(imp, out: Path, dpi):
    plt.figure(figsize=(6, 4))
    plt.barh(imp["feature"][::-1], imp["importance"][::-1], color="#759")
    plt.xlabel(f"importance ({imp.attrs.get('method','?')})"); plt.title("Retention predictors")
    plt.tight_layout(); plt.savefig(out / "drivers_importance.png", dpi=dpi); plt.close()


def fig_impact(res, out: Path, dpi):
    plt.figure(figsize=(6, 4))
    labels, vals = ["naive", "g-formula", "IPTW"], [
        res["naive_delta"], res["gformula_delta"],
        res["iptw"].get("delta", np.nan)]
    colors = ["#c93", "#2a7", "#39c"]
    plt.bar(labels, vals, color=colors)
    plt.ylabel("Δ retention (return) prob"); plt.axhline(0, color="k", lw=0.6)
    plt.title("Lever impact: confounded vs adjusted"); plt.tight_layout()
    plt.savefig(out / "impact_estimators.png", dpi=dpi); plt.close()


def fig_markov(res, out: Path, dpi):
    mk = res["markov"]
    plt.figure(figsize=(5, 4))
    plt.bar(["per 1000"], [mk["per1000_point"]], color="#593",
            yerr=[[mk["per1000_point"] - mk["per1000_lo"]], [mk["per1000_hi"] - mk["per1000_point"]]],
            capsize=6)
    plt.ylabel("expected retentions / 1000"); plt.title("Markov approx (90% CI)")
    plt.tight_layout(); plt.savefig(out / "markov_per1000.png", dpi=dpi); plt.close()


def main() -> int:
    cfg = load_config()
    dpi = int(cfg["figures"]["dpi"])
    out = _outdir(cfg)
    from data import build_cohort, load_events
    from drivers import run as drivers_run
    from impact import run as impact_run
    events = load_events(cfg)
    cohort = build_cohort(events, cfg)
    dr = drivers_run(cfg, events, cohort)
    res = impact_run(cfg, events, cohort, feats=dr["feats"], pp=dr["pp"])
    fig_cif(dr["pp"], out, dpi)
    fig_cif_by_aha(dr["pp"], out, dpi)
    fig_gap(dr["gap_sweep"], out, dpi)
    fig_importance(dr["importance"], out, dpi)
    fig_impact(res, out, dpi)
    fig_markov(res, out, dpi)
    print(f"[figures] wrote 6 PNGs to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
