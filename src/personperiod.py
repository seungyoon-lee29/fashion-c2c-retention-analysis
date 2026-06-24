"""Build early-window features and the discrete-time competing-risks person-period table.

Time axis per user:  [t0, t0+W) feature window | [t0+W, t0+W+G) embargo | [t0+W+G, +H) outcome.
The person-period table has one row per (user, step) from delayed entry to event/censor,
with competing outcomes per step: 0=continue (at risk), 1=retain (returned/active), 2=lapse (absorbing churn).
The spine models RETENTION: in MerRec first purchase is immediate (median 0 days from first
observation), so it is acquisition, not retention; the leakage-safe outcome window therefore
models whether a user RETURNS after the embargo. Covariates are measured strictly in the
feature window (past-only -> no immortal-time/reflexivity).
"""
from __future__ import annotations

import pandas as pd

CONTINUE, RETAIN, LAPSE = 0, 1, 2
FEATURE_COLS = ["n_view", "n_like", "n_cart", "n_offer", "n_session",
                "cat_diversity", "brand_diversity", "active_days"]
# Confounder/adjustment set EXCLUDES n_cart: the lever `aha_cart` already encodes the
# cart behaviour, so keeping both would (a) let a tree attribute the effect to n_cart so
# toggling the lever does nothing, and (b) make the IPTW propensity perfectly predict
# treatment (positivity violation). n_cart stays available for reporting only.
CONFOUNDER_COLS = [c for c in FEATURE_COLS if c != "n_cart"]


def early_features(events: pd.DataFrame, cohort: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Time-fixed behaviour in [t0, t0+W). `aha_cart` is the lever under study."""
    W = int(cfg["windows"]["feature_window_W"])
    ev = events.copy()
    ev["stime"] = pd.to_datetime(ev["stime"])
    data_start = ev["stime"].min().normalize()
    ev["day"] = (ev["stime"].dt.normalize() - data_start).dt.days
    t0 = cohort.set_index("user_id")["t0_day"]
    ev = ev.join(t0, on="user_id")
    win = ev[(ev["day"] >= ev["t0_day"]) & (ev["day"] < ev["t0_day"] + W)]

    def agg(g: pd.DataFrame) -> pd.Series:
        ev_types = g["event"]
        return pd.Series({
            "n_view": int((ev_types == "item_view").sum()),
            "n_like": int((ev_types == "item_like").sum()),
            "n_cart": int((ev_types == "item_add_to_cart_tap").sum()),
            "n_offer": int((ev_types == "offer_make").sum()),
            "n_session": int(g["session_id"].nunique()),
            "cat_diversity": int(g["c0_name"].nunique()),
            "brand_diversity": int(g["brand_name"].nunique()),
            "active_days": int(g["day"].nunique()),
        })

    feats = win.groupby("user_id").apply(agg, include_groups=False)
    feats = feats.reindex(cohort["user_id"].values).fillna(0).astype(int)
    feats["aha_cart"] = (feats["n_cart"] >= 1).astype(int)   # lever
    return feats.reset_index().rename(columns={"index": "user_id"})


def build_person_period(events: pd.DataFrame, cohort: pd.DataFrame,
                        feats: pd.DataFrame, cfg: dict,
                        gap_override: int | None = None) -> pd.DataFrame:
    W = int(cfg["windows"]["feature_window_W"])
    G = int(cfg["windows"]["embargo_gap_G"] if gap_override is None else gap_override)
    H = int(cfg["windows"]["horizon_H"])
    step = int(cfg["person_period"]["step_days"])
    lapse_days = int(cfg["person_period"]["lapse_inactive_days"])

    ev = events.copy()
    ev["stime"] = pd.to_datetime(ev["stime"])
    data_start = ev["stime"].min().normalize()
    ev["day"] = (ev["stime"].dt.normalize() - data_start).dt.days
    span = int(ev["day"].max()) + 1

    acts = ev.groupby("user_id")["day"].apply(lambda s: set(s.tolist()))
    t0 = cohort.set_index("user_id")
    fidx = feats.set_index("user_id")

    rows: list[dict] = []
    kept = cohort[cohort["kept"]]["user_id"].values
    for uid in kept:
        entry = int(t0.loc[uid, "t0_day"]) + W + G
        if entry >= span:
            continue
        win_end = min(span - 1, entry + H - 1)
        uacts = acts.get(uid, set())
        # lapse clock starts from the user's last activity before the outcome window
        pre = [d for d in uacts if d < entry]
        last_active = max(pre) if pre else entry - 1
        # competing risks in [entry, win_end]: first return = RETAIN, inactivity gap = LAPSE
        event_day, event_code = None, CONTINUE
        for d in range(entry, win_end + 1):
            if d in uacts:
                event_day, event_code = d, RETAIN     # returned/active post-embargo
                break
            if d - last_active >= lapse_days:
                event_day, event_code = d, LAPSE      # churned (absorbing)
                break
        if event_day is None:
            event_day, event_code = win_end, CONTINUE  # right-censored
        duration = event_day - entry
        S = duration // step
        frow = fidx.loc[uid]
        base = {c: int(frow[c]) for c in FEATURE_COLS}
        base["aha_cart"] = int(frow["aha_cart"])
        for s in range(S + 1):
            code = event_code if (s == S and event_code != CONTINUE) else CONTINUE
            rows.append({"user_id": uid, "t": s, "event": code, **base})
    pp = pd.DataFrame(rows)
    return pp
