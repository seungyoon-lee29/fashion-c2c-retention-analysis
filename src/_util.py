"""Shared helpers: config loading, paths, deterministic RNG, markdown writing."""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_config(path: str | None = None) -> dict:
    path = path or os.environ.get("GA_CONFIG", str(ROOT / "config" / "config.yaml"))
    with open(path) as f:
        return yaml.safe_load(f)


def rng_from(cfg: dict) -> np.random.Generator:
    return np.random.default_rng(int(cfg.get("seed", 17)))


def data_dir() -> Path:
    d = ROOT / "data"
    d.mkdir(exist_ok=True)
    return d


def write_md(rel_path: str, text: str) -> Path:
    p = ROOT / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def df_to_md(df, index: bool = False, float_digits: int = 3, na_rep: str = "nan") -> str:
    """Minimal markdown table (avoids the optional `tabulate` dependency)."""
    if index:
        df = df.reset_index()
    cols = list(df.columns)
    head = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = ["| " + " | ".join(_fmt(v, float_digits, na_rep) for v in row) + " |"
            for row in df.itertuples(index=False, name=None)]
    return "\n".join([head, sep, *rows])


def _fmt(v, float_digits: int = 3, na_rep: str = "nan"):
    try:
        if np.isnan(v):
            return na_rep
    except (TypeError, ValueError):
        pass
    if isinstance(v, (float, np.floating)):
        return f"{v:.{float_digits}f}"
    return str(v)
