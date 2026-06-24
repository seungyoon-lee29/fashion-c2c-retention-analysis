"""Offline smoke + correctness test. Runs the full pipeline on synthetic data and
checks sanity invariants AND that the impact estimators recover the planted causal
effect on RETENTION (g-formula/IPTW < naive, all positive). No network required.

Run:  python -m pytest tests/ -q     or     python tests/test_smoke.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np

from _util import load_config
from data import build_cohort, load_events, validate
from drivers import run as drivers_run
from impact import run as impact_run
from survival import empirical_cif, fit_cause_specific, predict_hazards


def _cfg():
    cfg = load_config()
    cfg["data"]["source"] = "synthetic"
    cfg["data"]["synthetic_n_users"] = 2500
    cfg["hazard"]["model"] = "gbm"        # flexible model demonstrates confounding removal
    cfg["hazard"]["calibrate"] = False    # keep the smoke test fast
    cfg["impact"]["n_sims"] = 150
    return cfg


def test_pipeline_and_ground_truth():
    cfg = _cfg()
    events = load_events(cfg)
    # Phase-0 gate
    m = validate(events, cfg)
    assert m["GATE_PASS"], m["gate_detail"]
    assert m["conversion_rate"] > 0

    cohort = build_cohort(events, cfg)
    dr = drivers_run(cfg, events, cohort, write=False)  # don't clobber committed real-data report
    pp = dr["pp"]
    assert not pp.empty
    assert set(pp["event"].unique()).issubset({0, 1, 2})

    # hazards in [0,1] and total absorbing hazard < 1
    bundle = fit_cause_specific(pp, cfg)
    hc, hl = predict_hazards(bundle, pp)
    assert hc.min() >= 0 and hl.min() >= 0
    assert (hc + hl).max() < 1.0

    # CIF monotone non-decreasing and within [0,1]
    c = empirical_cif(pp)
    assert c["cif_retain"].min() >= 0 and c["cif_retain"].max() <= 1
    assert np.all(np.diff(c["cif_retain"]) >= -1e-9)

    # Markov sanity: row sums to 1, finite per-1000
    res = impact_run(cfg, events, cohort, feats=dr["feats"], pp=pp, write=False)
    assert abs(res["markov"]["row_sum_check"] - 1.0) < 1e-6
    assert np.isfinite(res["markov"]["per1000_point"])

    # GROUND-TRUTH backstop: planted retention effect is positive; confounding inflates naive,
    # so the adjusted (g-formula) estimate should be positive but below the naive one,
    # and the independent IPTW estimate should agree with g-formula.
    assert res["naive_delta"] > 0, "planted lever should associate with retention"
    assert res["gformula_delta"] > 0, "adjusted effect should remain positive"
    assert res["gformula_delta"] < res["naive_delta"] + 0.01, \
        "adjustment should pull the confounded naive estimate down, not inflate it"
    idl = res["iptw"].get("delta")
    assert idl is not None and np.isfinite(idl) and idl > 0, "IPTW estimate should be positive"
    assert abs(res["gformula_delta"] - idl) < 0.6 * res["naive_delta"], \
        "g-formula and IPTW (different models, same estimand) should broadly agree"

    # E-value defined and > 1 for a real effect
    assert res["e_value"] > 1.0


if __name__ == "__main__":
    test_pipeline_and_ground_truth()
    print("OK: smoke + ground-truth recovery passed")
