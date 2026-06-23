"""Offline MerRec-shaped synthetic event log with a KNOWN causal structure.

Why this exists: HuggingFace is network-gated in many environments, and the
g-computation / IPTW code is custom — so we need a fixture with a *planted*
causal effect to verify the impact estimators actually recover truth (and that
the naive, confounded estimate is biased upward). The whole downstream pipeline
(data -> person-period -> survival -> drivers -> impact) runs on this exactly as
it would on real MerRec.

Planted structure (per user):
  a ~ Beta            latent affinity = CONFOUNDER
  early_cart         depends on a (so cart correlates with conversion via a)
  daily conversion hazard logit = BASE + CONF_BETA*a + GAMMA_TRUE*early_cart - DECAY*day
The lever under study is `early_cart` (did the user hit the activation behavior
in the first window). Adjusting for an `a`-proxy (early #views) should recover
~GAMMA_TRUE; the unadjusted estimate should be larger (confounding).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Planted ground truth (read by tests).
GAMMA_TRUE = 0.85         # causal log-odds of early_cart on daily conversion hazard
CONF_BETA = 1.1           # confounder (affinity) effect -> upward bias if unadjusted
BASE = -6.0               # baseline daily conversion log-odds (=> realistic ~5-8% total)
DECAY = 0.04              # mild within-window hazard decay
LAPSE_LOGIT = -2.2        # baseline daily lapse hazard

BASE_DATE = pd.Timestamp("2023-05-01")
_C0 = ["Women", "Men", "Electronics", "Home", "Toys"]
_BRANDS = ["Nike", "Apple", "Zara", "Sony", "Lego", "NoBrand"]


def generate_events(cfg: dict, rng: np.random.Generator | None = None) -> pd.DataFrame:
    """Return a long event-log DataFrame matching the configured MerRec columns."""
    if rng is None:
        rng = np.random.default_rng(cfg.get("seed", 17))
    n_users = int(cfg["data"]["synthetic_n_users"])
    span = 28  # one-month sample
    H = int(cfg["windows"]["horizon_H"])
    W = int(cfg["windows"]["feature_window_W"])
    G = int(cfg["windows"]["embargo_gap_G"])
    lapse_days = int(cfg["person_period"]["lapse_inactive_days"])

    rows: list[dict] = []
    eid = 0
    for u in range(n_users):
        a = float(rng.beta(2.0, 2.0))
        # first observed event day; leave room for the full window for most users
        t0 = int(rng.integers(0, span - 4))
        p_cart = _sigmoid(-0.6 + 2.0 * a)
        early_cart = int(rng.random() < p_cart)
        n_view = int(rng.poisson(1.5 + 5.0 * a))           # a-proxy (confounder signal)
        n_like = int(rng.poisson(0.4 + 1.5 * a))
        n_offer = int(rng.poisson(0.3 * a))

        uid = f"u{u:06d}"
        # ---- feature window [t0, t0+W): emit the early behaviors ----
        for _ in range(max(1, n_view)):
            day = t0 + int(rng.integers(0, max(1, W)))
            rows.append(_ev(uid, day, "item_view", rng, eid)); eid += 1
        for _ in range(n_like):
            day = t0 + int(rng.integers(0, max(1, W)))
            rows.append(_ev(uid, day, "item_like", rng, eid)); eid += 1
        for _ in range(early_cart * max(1, int(rng.poisson(1.5)))):
            day = t0 + int(rng.integers(0, max(1, W)))
            rows.append(_ev(uid, day, "item_add_to_cart_tap", rng, eid)); eid += 1
        for _ in range(n_offer):
            day = t0 + int(rng.integers(0, max(1, W)))
            rows.append(_ev(uid, day, "offer_make", rng, eid)); eid += 1

        # ---- outcome window: daily competing risks (convert vs lapse) ----
        last_active = t0 + W
        converted = False
        start = t0 + W + G
        for day in range(start, min(span, start + H)):
            h_conv = _sigmoid(BASE + CONF_BETA * a + GAMMA_TRUE * early_cart - DECAY * (day - start))
            if rng.random() < h_conv:
                rows.append(_ev(uid, day, "buy_start", rng, eid)); eid += 1
                rows.append(_ev(uid, day, "buy_comp", rng, eid)); eid += 1
                converted = True
                break
            # occasional light browsing keeps them active
            if rng.random() < 0.35:
                rows.append(_ev(uid, day, "item_view", rng, eid)); eid += 1
                last_active = day
            elif day - last_active >= lapse_days:
                break  # lapsed (absorbing) -> no more events
        _ = converted
    df = pd.DataFrame(rows)
    return df.sort_values(["user_id", "stime"]).reset_index(drop=True)


def _ev(uid: str, day: int, etype: str, rng: np.random.Generator, eid: int) -> dict:
    secs = int(rng.integers(0, 86400))
    stime = BASE_DATE + pd.Timedelta(days=int(day), seconds=secs)
    # session id buckets activity into ~half-day sessions
    sess = f"{uid}_s{day}_{secs // 43200}"
    return {
        "user_id": uid,
        "stime": stime,
        "session_id": sess,
        "event_id": eid,
        "item_id": int(rng.integers(0, 50000)),
        "c0_name": _C0[int(rng.integers(0, len(_C0)))],
        "c1_name": "sub" + str(int(rng.integers(0, 20))),
        "brand_name": _BRANDS[int(rng.integers(0, len(_BRANDS)))],
        "price": round(float(rng.gamma(2.0, 15.0)), 2),
        "event": etype,
    }


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-x))
