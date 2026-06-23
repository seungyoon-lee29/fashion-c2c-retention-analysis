"""Phase 0: load MerRec (or synthetic), reconstruct user timelines, validate().

Real MerRec is downloaded lazily via urllib and cached under data/raw. That host
is network-gated in many environments, so `source: synthetic` is the default and
always works. Either way the output is the same long event-log schema, so every
downstream stage is identical on synthetic and real data.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from _util import data_dir, load_config, rng_from


def load_events(cfg: dict) -> pd.DataFrame:
    src = cfg["data"]["source"]
    if src == "synthetic":
        from _synth import generate_events
        return generate_events(cfg, rng_from(cfg))
    if src == "merrec":
        return _load_merrec(cfg)
    raise ValueError(f"unknown data.source={src!r}")


def _load_merrec(cfg: dict) -> pd.DataFrame:
    """Best-effort cached download of N MerRec files for one date partition.

    Raises a clear error (rather than hanging) when the HF host is blocked, so
    the caller can fall back to synthetic.
    """
    import urllib.request

    date = cfg["data"]["merrec_date"]
    n_files = int(cfg["data"]["merrec_n_files"])
    cache = Path(cfg["data"]["cache_dir"]); cache.mkdir(parents=True, exist_ok=True)
    base = f"https://huggingface.co/datasets/mercari-us/merrec/resolve/main/{date}"
    cols = cfg["data"]["columns"]
    frames = []
    for i in range(n_files):
        fname = f"{i:012d}.parquet"
        local = cache / f"{date}_{fname}"
        if not local.exists():
            url = f"{base}/{fname}?download=true"
            try:
                urllib.request.urlretrieve(url, local)  # noqa: S310
            except Exception as e:  # network-gated environments
                raise RuntimeError(
                    f"MerRec download failed ({e}). HF is likely network-gated here; "
                    "set data.source=synthetic in config.yaml."
                ) from e
        df = pd.read_parquet(local)
        keep = [c for c in cols if c in df.columns]
        frames.append(df[keep])
    out = pd.concat(frames, ignore_index=True)
    if "event" not in out.columns and "name" in out.columns:
        out = out.rename(columns={"name": "event"})
    return out


def build_cohort(events: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """One row per user: anchor t0 (first observed event), with left-truncation buffer."""
    w = cfg["windows"]
    ev = events.copy()
    ev["stime"] = pd.to_datetime(ev["stime"])
    data_start = ev["stime"].min().normalize()
    g = ev.groupby("user_id")["stime"]
    cohort = pd.DataFrame({"t0": g.min(), "t_last": g.max(), "n_events": g.size()})
    cohort["t0_day"] = (cohort["t0"].dt.normalize() - data_start).dt.days
    buf = int(w["truncation_buffer_days"])
    cohort["kept"] = cohort["t0_day"] >= buf  # mitigate left truncation
    cohort = cohort.reset_index()
    return cohort


def validate(events: pd.DataFrame, cfg: dict) -> dict:
    """Sanity metrics + the Phase-0 go/no-go gate."""
    ev = events.copy()
    ev["stime"] = pd.to_datetime(ev["stime"])
    cohort = build_cohort(ev, cfg)
    conv = cfg["events"]["conversion"]
    per_user = ev.groupby("user_id").size()
    converters = ev.loc[ev["event"] == conv, "user_id"].nunique()
    n_users = ev["user_id"].nunique()
    span_days = (ev["stime"].max() - ev["stime"].min()).days
    m = {
        "n_events": int(len(ev)),
        "n_users": int(n_users),
        "median_events_per_user": float(per_user.median()),
        "span_days": int(span_days),
        "n_converters": int(converters),
        "conversion_rate": float(converters / max(1, n_users)),
        "kept_after_truncation": int(cohort["kept"].sum()),
        "event_types": sorted(ev["event"].unique().tolist()),
    }
    # go/no-go gate
    gate = {
        "timeline_reconstructable": "user_id" in ev and "stime" in ev,
        "enough_converters": converters >= 50,
        "enough_observed_users": int(cohort["kept"].sum()) >= 200,
        "conversion_event_present": conv in m["event_types"],
    }
    m["GATE_PASS"] = bool(all(gate.values()))
    m["gate_detail"] = gate
    return m


def main() -> int:
    cfg = load_config()
    try:
        events = load_events(cfg)
    except RuntimeError as e:
        print(f"[data] {e}", file=sys.stderr)
        return 2
    m = validate(events, cfg)
    lines = ["# EDA / Phase-0 feasibility gate\n"]
    for k in ["n_events", "n_users", "median_events_per_user", "span_days",
              "n_converters", "conversion_rate", "kept_after_truncation"]:
        lines.append(f"- **{k}**: {m[k]}")
    lines.append(f"- **event_types**: {m['event_types']}")
    lines.append(f"\n## GATE: {'PASS ✅' if m['GATE_PASS'] else 'FAIL ❌'}")
    for k, v in m["gate_detail"].items():
        lines.append(f"- {k}: {v}")
    from _util import write_md
    write_md("docs/eda_findings.md", "\n".join(lines) + "\n")
    print("\n".join(lines))
    # also persist the raw events for downstream stages
    out = data_dir() / "events.parquet"
    events.to_parquet(out)
    print(f"\n[data] wrote {out} ; GATE_PASS={m['GATE_PASS']}")
    return 0 if m["GATE_PASS"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
