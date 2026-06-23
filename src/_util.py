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


def docs_dir() -> Path:
    d = ROOT / "docs"
    d.mkdir(exist_ok=True)
    return d


def write_md(rel_path: str, text: str) -> Path:
    p = ROOT / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def df_to_md(df) -> str:
    """Minimal markdown table (avoids the optional `tabulate` dependency)."""
    cols = list(df.columns)
    head = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = ["| " + " | ".join(_fmt(v) for v in row) + " |"
            for row in df.itertuples(index=False, name=None)]
    return "\n".join([head, sep, *rows])


def _fmt(v):
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)
