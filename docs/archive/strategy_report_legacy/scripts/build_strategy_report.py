"""리텐션 활성화 전략 리포트 생성 (Korean static HTML)."""
from __future__ import annotations

from pathlib import Path
import sys
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import Patch
import pandas as pd
import seaborn as sns
from sklearn.metrics import f1_score, matthews_corrcoef, precision_score, recall_score


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "strategy_report"
ASSETS = OUT / "assets"

FONT_FAMILY = [
    "AppleGothic",
    "Noto Sans CJK KR",
    "Noto Sans KR",
    "Malgun Gothic",
    "Aptos",
    "Inter",
    "Segoe UI",
    "DejaVu Sans",
    "Arial",
    "sans-serif",
]

TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#17202A",
    "muted": "#5F6B7A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}

FAMILIES = {
    "blue": {"xlight": "#EEF2FF", "light": "#D9E1FF", "base": "#A5B4FC", "mid": "#6366F1", "dark": "#4338CA"},
    "gold": {"xlight": "#FFF4C2", "light": "#FFEA8F", "base": "#FFE15B", "mid": "#B8A037", "dark": "#736422"},
    "orange": {"xlight": "#FFEDDE", "light": "#FFBDA1", "base": "#F0986E", "mid": "#CC6F47", "dark": "#804126"},
    "olive": {"xlight": "#D8ECBD", "light": "#BEEB96", "base": "#A3D576", "mid": "#71B436", "dark": "#386411"},
    "pink": {"xlight": "#FCDAD6", "light": "#F5BACC", "base": "#F390CA", "mid": "#BD569B", "dark": "#8A3A6F"},
}

NEUTRAL = {"xlight": "#F4F5F7", "light": "#E2E5EA", "base": "#C5CAD3", "mid": "#7A828F", "dark": "#464C55"}


def use_theme() -> None:
    sns.set_theme(
        style="whitegrid",
        rc={
            "figure.facecolor": TOKENS["surface"],
            "savefig.facecolor": "white",
            "axes.facecolor": TOKENS["panel"],
            "axes.edgecolor": TOKENS["axis"],
            "axes.labelcolor": TOKENS["ink"],
            "axes.grid": True,
            "axes.unicode_minus": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": TOKENS["grid"],
            "grid.linewidth": 0.8,
            "font.family": "sans-serif",
            "font.sans-serif": FONT_FAMILY,
        },
    )


def add_header(fig, ax, title: str, subtitle: str, title_width=56, subtitle_width=82) -> None:
    title = textwrap.fill(title, width=title_width, break_long_words=False)
    subtitle = textwrap.fill(subtitle, width=subtitle_width, break_long_words=False)
    title_lines = title.count("\n") + 1
    subtitle_lines = subtitle.count("\n") + 1
    ax.set_title("")
    fig.subplots_adjust(top=max(0.50, 0.76 - 0.06 * (title_lines - 1) - 0.045 * (subtitle_lines - 1)), bottom=0.16)
    left = ax.get_position().x0
    fig.text(left, 0.985, title, ha="left", va="top", fontsize=13, fontweight="semibold", color=TOKENS["ink"], linespacing=1.12)
    fig.text(left, 0.915 - 0.055 * (title_lines - 1), subtitle, ha="left", va="top", fontsize=9, color=TOKENS["muted"], linespacing=1.24)
    sns.despine(ax=ax)


def save(fig, name: str) -> None:
    fig.savefig(ASSETS / name, dpi=180, bbox_inches="tight")
    plt.close(fig)


def load_candidate_grid() -> pd.DataFrame:
    """Compute actual aha-rule candidates from the persisted MerRec event table."""
    sys.path.insert(0, str(ROOT / "src"))
    from _util import load_config
    from data import build_cohort
    from personperiod import (build_person_period, early_features,
                              full_followup_users, user_retention_label)

    cfg = load_config()
    events_path = ROOT / "data" / "events.parquet"
    if not events_path.exists():
        # 데이터가 없으면 커밋된 candidate_rules.csv를 단일 출처로 사용한다.
        csv = OUT / "candidate_rules.csv"
        return pd.read_csv(csv) if csv.exists() else pd.DataFrame()

    events = pd.read_parquet(events_path)
    cohort = build_cohort(events, cfg)
    feats = early_features(events, cohort, cfg)
    pp = build_person_period(events, cohort, feats, cfg)
    full_users = full_followup_users(events, cohort, cfg)
    label = user_retention_label(pp, full_users)
    t0 = cohort.set_index("user_id")["t0_day"]
    users = label.index
    late = users.map(lambda u: t0.get(u, 0) > t0.median()).to_numpy()
    y = label[late].to_numpy()
    base = float(y.mean())

    ev = events.copy()
    ev["stime"] = pd.to_datetime(ev["stime"])
    data_start = ev["stime"].min().normalize()
    ev["day"] = (ev["stime"].dt.normalize() - data_start).dt.days
    ev = ev.join(t0.rename("t0d"), on="user_id")

    thresholds = {
        "활동일 수": [1, 2, 3],
        "세션 수": [1, 2, 3, 4],
        "조회 수": [3, 5, 10, 20],
        "카테고리 수": [1, 2, 3],
        "카트 수": [1, 2, 3, 5],
    }
    rows = []
    for n in [1, 3]:
        win = ev[(ev["day"] >= ev["t0d"]) & (ev["day"] < ev["t0d"] + n)]
        values = {
            "활동일 수": win.groupby("user_id")["day"].nunique(),
            "세션 수": win.groupby("user_id")["session_id"].nunique(),
            "조회 수": win[win["event"] == "item_view"].groupby("user_id").size(),
            "카테고리 수": win.groupby("user_id")["c0_name"].nunique(),
            "카트 수": win[win["event"] == "item_add_to_cart_tap"].groupby("user_id").size(),
        }
        for metric, ks in thresholds.items():
            series = values[metric].reindex(users).fillna(0)
            for k in ks:
                pred = (series >= k).astype(int).to_numpy()
                ph = pred[late]
                if ph.sum() == 0:
                    continue
                precision = precision_score(y, ph, zero_division=0)
                rows.append(
                    {
                        "metric": metric,
                        "n": n,
                        "k": k,
                        "rule": f"{metric} >= {k} / {n}일",
                        "precision": precision,
                        "recall": recall_score(y, ph, zero_division=0),
                        "f1": f1_score(y, ph, zero_division=0),
                        "mcc": matthews_corrcoef(y, ph),
                        "coverage": float(ph.mean()),
                        "lift": precision / base if base else float("nan"),
                    }
                )
    out = pd.DataFrame(rows).sort_values("mcc", ascending=False).reset_index(drop=True)
    out.to_csv(OUT / "candidate_rules.csv", index=False)
    return out


def build_shap_chart() -> None:
    df = pd.DataFrame(
        [
            ("세션 수", 0.021),
            ("활동일 수", 0.019),
            ("시간 스텝", 0.015),
            ("조회 수", 0.012),
            ("찜 수", 0.005),
            ("브랜드 다양성", 0.005),
            ("카트 활성화", 0.001),
            ("카테고리 다양성", 0.000),
            ("제안 수", 0.000),
        ],
        columns=["feature", "importance"],
    ).sort_values("importance")
    fig, ax = plt.subplots(figsize=(9.5, 6.1))
    colors = [FAMILIES["orange"]["xlight"] if f == "카트 활성화" else FAMILIES["blue"]["base"] for f in df["feature"]]
    edges = [FAMILIES["orange"]["dark"] if f == "카트 활성화" else FAMILIES["blue"]["dark"] for f in df["feature"]]
    bars = ax.barh(df["feature"], df["importance"], color=colors, edgecolor=edges, linewidth=1.0)
    for bar, value in zip(bars, df["importance"]):
        ax.text(value + 0.0007, bar.get_y() + bar.get_height() / 2, f"{value:.3f}", va="center", ha="left", fontsize=8.5, color=TOKENS["ink"])
    ax.set_xlabel("평균 절대 SHAP 중요도")
    ax.set_ylabel("")
    add_header(fig, ax, "SHAP은 행동 X를 좁히는 후보 발굴 장치다", "상위 후보는 세션 수, 활동일 수, 조회 수처럼 초기 활동 폭을 나타낸다. 카트는 후보로 볼 수 있지만 단독 레버로 과대해석하면 안 된다.")
    save(fig, "x_shortlist_shap.png")


def build_aha_chart(grid: pd.DataFrame) -> pd.DataFrame:
    if grid.empty:
        grid = pd.DataFrame(
            [
                {"metric": "활동일 수", "n": 3, "k": 2, "rule": "활동일 수 >= 2 / 3일", "precision": 0.485, "recall": 0.442, "f1": 0.462, "mcc": 0.302, "coverage": 0.220, "lift": 2.008},
                {"metric": "세션 수", "n": 3, "k": 2, "rule": "세션 수 >= 2 / 3일", "precision": 0.419, "recall": 0.557, "f1": 0.479, "mcc": 0.286, "coverage": 0.321, "lift": 1.737},
                {"metric": "카트 수", "n": 3, "k": 1, "rule": "카트 수 >= 1 / 3일", "precision": 0.389, "recall": 0.155, "f1": 0.222, "mcc": 0.113, "coverage": 0.096, "lift": 1.611},
            ]
        )
    top = grid.head(12).sort_values("mcc")
    selected_rule = str(grid.iloc[0]["rule"])
    fig, ax = plt.subplots(figsize=(9.8, 7.2))
    colors = [FAMILIES["olive"]["base"] if r == selected_rule else FAMILIES["gold"]["base"] for r in top["rule"]]
    edges = [FAMILIES["olive"]["dark"] if r == selected_rule else FAMILIES["gold"]["dark"] for r in top["rule"]]
    bars = ax.barh(top["rule"], top["mcc"], color=colors, edgecolor=edges, linewidth=1.0)
    for bar, row in zip(bars, top.itertuples()):
        ax.text(row.mcc + 0.006, bar.get_y() + bar.get_height() / 2, f"MCC {row.mcc:.3f} | P {row.precision:.2f} R {row.recall:.2f} C {row.coverage:.2f}", va="center", ha="left", fontsize=8.0, color=TOKENS["ink"])
    ax.set_xlabel("MCC 점수")
    ax.set_ylabel("조작적 정의 후보")
    add_header(fig, ax, "실제 후보 X grid에서는 활동일 수와 세션 수가 카트보다 앞선다", "첫 3일 안에 활동일 2일 이상이 MCC 0.302로 최상위다. 카트 1회/3일은 운영 마커로는 가능하지만 후보 순위에서 뒤로 밀린다.")
    save(fig, "aha_rule_selection.png")
    return grid


def build_impact_chart() -> None:
    df = pd.DataFrame(
        [
            ("단순 비교", 15.1),
            ("IPTW/MSM", 2.7),
            ("g-formula", -1.2),
        ],
        columns=["estimator", "delta_pp"],
    ).sort_values("delta_pp")
    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    colors = [FAMILIES["olive"]["base"] if v >= 0 else FAMILIES["orange"]["base"] for v in df["delta_pp"]]
    edges = [FAMILIES["olive"]["dark"] if v >= 0 else FAMILIES["orange"]["dark"] for v in df["delta_pp"]]
    bars = ax.barh(df["estimator"], df["delta_pp"], color=colors, edgecolor=edges, linewidth=1.0)
    ax.axvspan(-3, 3, color=NEUTRAL["xlight"], zorder=0)
    ax.axvline(0, color=TOKENS["ink"], linewidth=1.0)
    for bar, value in zip(bars, df["delta_pp"]):
        ax.text(value + (0.45 if value >= 0 else -0.45), bar.get_y() + bar.get_height() / 2, f"{value:+.1f}pp", ha="left" if value >= 0 else "right", va="center", fontsize=9, color=TOKENS["ink"])
    ax.set_xlabel("재방문 확률 차이")
    ax.set_ylabel("")
    ax.xaxis.set_major_formatter(mticker.StrMethodFormatter("{x:.0f}pp"))
    ax.legend(
        handles=[
            Patch(facecolor=NEUTRAL["xlight"], edgecolor=NEUTRAL["light"], label="실질적 0 구간 +/-3pp"),
            Patch(facecolor=FAMILIES["olive"]["base"], edgecolor=FAMILIES["olive"]["dark"], label="양의 추정치"),
            Patch(facecolor=FAMILIES["orange"]["base"], edgecolor=FAMILIES["orange"]["dark"], label="음의 추정치"),
        ],
        loc="upper left",
        frameon=False,
        ncol=1,
        fontsize=8,
    )
    add_header(fig, ax, "임팩트 추정은 후보 지표가 아니라 인과 게이트를 통과한 레버에만 붙인다", "Markov는 1,000명당 기대 재방문 같은 회사 언어로 번역하는 레이어다. 현재 카트 레버는 보정 후 null이라 lever ledger를 공개하지 않는다.")
    save(fig, "impact_logic.png")


CSS = """
:root {
  --bg: #eef1f7;
  --paper: #ffffff;
  --ink: #14181f;
  --muted: #5a6472;
  --faint: #8b94a3;
  --line: #e4e8f0;
  --line-strong: #cfd6e2;
  --brand: #4f46e5;
  --brand-2: #6366f1;
  --brand-ink: #312e81;
  --pos: #15803d;
  --neg: #c2410c;
  --red: #be4b3b;
  --amber: #b45309;
  --blue-soft: #eef2ff;
  --green-soft: #ecfdf3;
  --amber-soft: #fff7e6;
  --red-soft: #fef0ed;
  --olive-soft: #f0f7e7;
  --shadow: 0 1px 2px rgba(20,24,31,.04), 0 8px 24px rgba(20,24,31,.06);
  --shadow-lg: 0 18px 48px rgba(31,27,75,.22);
  --radius: 16px;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background: radial-gradient(1100px 560px at 82% -12%, #e6eafc 0%, transparent 60%), var(--bg);
  color: var(--ink);
  font: 15.5px/1.65 "Pretendard", -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Segoe UI", "Noto Sans KR", sans-serif;
  -webkit-font-smoothing: antialiased;
}
main { max-width: 1080px; margin: 0 auto; padding: 34px 22px 96px; }
section { margin-bottom: 18px; }

header.hero {
  position: relative; overflow: hidden; color: #eef1ff;
  background: linear-gradient(135deg, #1e1b4b 0%, #312e81 46%, #4338ca 100%);
  border-radius: 22px; padding: 46px 46px 40px; margin-bottom: 22px;
  box-shadow: var(--shadow-lg);
}
header.hero::after {
  content: ""; position: absolute; right: -130px; top: -130px;
  width: 400px; height: 400px; border-radius: 50%;
  background: radial-gradient(circle, rgba(129,140,248,.45), transparent 65%);
}
.eyebrow {
  display: inline-block; color: #c7d0ff;
  background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.18);
  font-size: 12px; font-weight: 700; letter-spacing: .05em;
  padding: 6px 13px; border-radius: 999px; margin: 0 0 18px; position: relative;
}
header.hero h1 { margin: 0; font-size: clamp(30px, 4.6vw, 46px); line-height: 1.12; font-weight: 800; letter-spacing: -.01em; max-width: 880px; color: #fff; }
.subtitle { max-width: 760px; color: #c4ccf2; font-size: 17px; margin: 16px 0 0; position: relative; }
.meta { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 24px; position: relative; }
.meta span { font-size: 12.5px; color: #d7ddff; background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.15); padding: 6px 12px; border-radius: 8px; }
.meta b { color: #fff; font-weight: 700; }

.panel { background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius); padding: 26px 28px; box-shadow: var(--shadow); }
h2 { position: relative; margin: 0 0 14px; padding-left: 15px; font-size: 22px; line-height: 1.3; font-weight: 750; letter-spacing: -.01em; }
h2::before { content: ""; position: absolute; left: 0; top: .18em; bottom: .18em; width: 5px; border-radius: 6px; background: linear-gradient(180deg, var(--brand-2), var(--brand)); }
h3 { margin: 0 0 8px; font-size: 16px; }
p { margin: 10px 0; color: #2b333f; }
ul, ol { padding-left: 20px; margin: 10px 0 0; }
li { margin: 6px 0; }
code { background: #eef1f8; color: #3b3f6b; border-radius: 5px; padding: 1.5px 6px; font-size: 13px; font-family: "SF Mono", ui-monospace, Menlo, monospace; }

.verdict { display: grid; grid-template-columns: 1.25fr .75fr; gap: 18px; align-items: stretch; }
.callout { background: linear-gradient(180deg, #f7f8ff, #fff); border-color: #dfe3ff; }
.callout h2::before { background: linear-gradient(180deg, #818cf8, #4338ca); }
.decision { background: linear-gradient(180deg, var(--green-soft), #fff); border-color: #c8eed5; }
.decision h2::before { background: linear-gradient(180deg, #34d399, #15803d); }
.lede { font-size: 18px; line-height: 1.6; color: #1d2530; }
.lede strong { color: var(--brand-ink); }

.metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-top: 18px; }
.metric { position: relative; border: 1px solid var(--line); border-radius: 14px; padding: 18px 16px 15px; background: #fff; overflow: hidden; transition: transform .15s ease, box-shadow .15s ease; }
.metric::before { content: ""; position: absolute; left: 0; top: 0; height: 4px; width: 100%; background: linear-gradient(90deg, var(--brand-2), var(--brand)); }
.metric:hover { transform: translateY(-3px); box-shadow: var(--shadow); }
.metric .v { font-size: 30px; font-weight: 820; line-height: 1.05; color: var(--brand-ink); letter-spacing: -.02em; }
.metric .l { color: var(--muted); font-size: 12.5px; line-height: 1.4; margin-top: 8px; }
.metric.neg::before { background: linear-gradient(90deg, #fb923c, #c2410c); }
.metric.neg .v { color: var(--neg); }
.metric.pos::before { background: linear-gradient(90deg, #34d399, #15803d); }
.metric.pos .v { color: var(--pos); }

.strip { display: grid; grid-template-columns: repeat(5, 1fr); gap: 11px; margin-top: 22px; counter-reset: step; }
.strip div { position: relative; padding: 17px 14px 14px; background: linear-gradient(180deg, #f7f8ff, #fff); border: 1px solid var(--line); border-radius: 12px; font-size: 13px; color: var(--muted); }
.strip div::before { counter-increment: step; content: counter(step); position: absolute; top: -11px; left: 14px; width: 23px; height: 23px; border-radius: 50%; background: var(--brand); color: #fff; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; box-shadow: 0 3px 8px rgba(79,70,229,.40); }
.strip strong { display: block; color: var(--ink); margin: 7px 0 4px; font-size: 14px; }

.flow-title { margin: 24px 0 0; font-size: 14.5px; font-weight: 700; color: var(--brand-ink); }
.flow { display: grid; grid-template-columns: repeat(6, 1fr); gap: 9px; margin-top: 22px; }
.flow-step { position: relative; padding: 31px 12px 15px; border: 1px solid var(--line); border-radius: 13px; background: linear-gradient(180deg, #f5f6ff, #fff); text-align: center; transition: transform .15s ease, box-shadow .15s ease; }
.flow-step:hover { transform: translateY(-3px); box-shadow: var(--shadow); }
.flow-step .n { position: absolute; top: -14px; left: 50%; transform: translateX(-50%); width: 29px; height: 29px; border-radius: 50%; background: linear-gradient(135deg, var(--brand-2), var(--brand)); color: #fff; font-weight: 700; font-size: 13px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 11px rgba(79,70,229,.42); }
.flow-step b { display: block; font-size: 13.5px; color: var(--ink); margin-bottom: 6px; }
.flow-step p { margin: 0; font-size: 11.5px; line-height: 1.45; color: var(--muted); }
.flow-step:not(:last-child)::after { content: ""; position: absolute; top: 50%; right: -7px; width: 8px; height: 8px; border-top: 2px solid var(--line-strong); border-right: 2px solid var(--line-strong); transform: translateY(-50%) rotate(45deg); z-index: 2; }
@media (max-width: 820px) { .flow { grid-template-columns: repeat(2, 1fr); gap: 18px 12px; } .flow-step:not(:last-child)::after { display: none; } }

.grid2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 16px; }
.grid3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin-top: 16px; }
.card { border: 1px solid var(--line); border-radius: 13px; padding: 16px 17px; background: #fff; transition: transform .15s ease, box-shadow .15s ease; }
.card:hover { transform: translateY(-2px); box-shadow: var(--shadow); }
.card strong { color: var(--ink); display: inline-block; margin-bottom: 2px; }
.card.blue { background: var(--blue-soft); border-color: #d9e1ff; }
.card.green { background: var(--green-soft); border-color: #c8eed5; }
.card.amber { background: var(--amber-soft); border-color: #ffe6b0; }
.card.red { background: var(--red-soft); border-color: #f8cabf; }
.card.olive { background: var(--olive-soft); border-color: #d7ebbb; box-shadow: 0 0 0 2px rgba(113,180,54,.18); }

.scorecard { width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 16px; font-size: 14px; border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.scorecard th, .scorecard td { padding: 13px 14px; vertical-align: top; text-align: left; border-bottom: 1px solid var(--line); }
.scorecard thead th { background: #f4f6fc; font-weight: 750; color: var(--brand-ink); font-size: 12px; letter-spacing: .03em; text-transform: uppercase; }
.scorecard tbody tr:last-child td { border-bottom: 0; }
.scorecard tbody tr:nth-child(even) td { background: #fafbfe; }
.badge { display: inline-block; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 999px; white-space: nowrap; }
.badge.ok { background: #e7f0ff; color: #2d49b8; }
.badge.null { background: #fbe4db; color: #b4451f; }
.badge.warn { background: #fff2d6; color: #8a5a08; }
.badge.good { background: #e3f6ea; color: #167c3c; }

figure { margin: 18px 0 4px; }
figure img { display: block; width: 100%; height: auto; border: 1px solid var(--line); border-radius: 14px; background: #fff; box-shadow: var(--shadow); }
figcaption { color: var(--muted); font-size: 12.5px; margin-top: 10px; padding-left: 2px; }

.step-list { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-top: 16px; }
.step { position: relative; border: 1px solid var(--line); border-radius: 13px; padding: 16px 15px; background: linear-gradient(180deg, #fffaf2, #fff); }
.step b { display: block; color: var(--amber); margin-bottom: 6px; font-size: 13.5px; }
.action { background: linear-gradient(180deg, #fffdf8, #fff); }
.action h2::before { background: linear-gradient(180deg, #f59e0b, #b45309); }
.assumption { background: #fbfcfe; }
.assumption h2::before { background: linear-gradient(180deg, #cbd2df, #9aa4b5); }
.assumption p { color: var(--muted); font-size: 14px; }

.footer { border-top: 1px solid var(--line); padding-top: 18px; color: var(--faint); font-size: 12.5px; margin-top: 40px; }

@media (max-width: 820px) {
  .verdict, .metric-grid, .strip, .grid2, .grid3, .step-list { grid-template-columns: 1fr; }
  header.hero { padding: 32px 24px; border-radius: 18px; }
  .panel { padding: 20px; }
  .strip { gap: 18px; }
}
@media print {
  body { background: white; }
  main { padding: 0; max-width: none; }
  header.hero, .panel { break-inside: avoid; box-shadow: none; }
}
"""


def format_top_rules(grid: pd.DataFrame) -> str:
    top = grid.head(4) if not grid.empty else pd.DataFrame()
    if top.empty:
        return ""
    cards = []
    for i, row in enumerate(top.itertuples(), start=1):
        cards.append(
            f"""<div class="card {'olive' if i == 1 else ''}"><strong>{i}. {row.rule}</strong><br>
            precision {row.precision:.3f} · recall {row.recall:.3f} · MCC {row.mcc:.3f} · coverage {row.coverage:.1%}</div>"""
        )
    return "\n".join(cards)


def build_html(grid: pd.DataFrame) -> str:
    best = grid.iloc[0] if not grid.empty else None
    best_rule = str(best["rule"]) if best is not None else "활동일 수 >= 2 / 3일"
    best_mcc = float(best["mcc"]) if best is not None else 0.302
    best_precision = float(best["precision"]) if best is not None else 0.485
    best_recall = float(best["recall"]) if best is not None else 0.442
    best_coverage = float(best["coverage"]) if best is not None else 0.220
    best_lift = float(best["lift"]) if best is not None else 2.008
    top_rule_cards = format_top_rules(grid)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>리텐션 활성화 전략: 무엇이 신규 유저를 다시 오게 하는가</title>
  <style>{CSS}</style>
</head>
<body>
  <main>
    <header class="hero">
      <p class="eyebrow">그로스 데이터 분석 · 리텐션 인과추론</p>
      <h1>초기 활동 폭이 재방문을 만든다: 카트 허영지표를 걷어낸 리텐션 실험 제안</h1>
      <p class="subtitle">Mercari 행동 로그를 사용해 신규 관측 유저의 재방문 후보 행동을 찾고, 관측 상관과 인과 추정을 분리해 실제 A/B 테스트 후보로 번역한 분석 케이스.</p>
      <div class="meta">
        <span>데이터 <b>MerRec (Mercari C2C)</b></span>
        <span>규모 <b>277만 이벤트 · 43k 유저</b></span>
        <span>스파인 <b>경쟁위험 생존 + g-computation</b></span>
        <span>라이선스 <b>CC BY-NC 4.0</b></span>
      </div>
    </header>

    <section class="verdict">
      <div class="panel callout">
        <h2>핵심 결론</h2>
        <p class="lede"><strong>카트는 리텐션 레버가 아니라 이미 인게이지된 유저의 마커다.</strong> 단순 비교에서는 카트 유저의 재방문이 +15.1pp 높지만, 인게이지먼트 폭을 보정하면 g-formula -1.2pp, IPTW +2.7pp로 실질적 0 구간에 들어온다.</p>
        <p>따라서 이 프로젝트의 실행 제안은 카트 유도가 아니라 <strong>{best_rule}</strong>을 늘리는 제품 실험이다. 첫날 이후 다시 올 이유를 만들어 두 번째 활동일을 확보하는 것이 더 방어 가능한 리텐션 가설이다.</p>
      </div>
      <div class="panel decision">
        <h2>실행 결정</h2>
        <p><strong>프로덕션이 아니라 실험으로 넘긴다.</strong></p>
        <ul>
          <li>주 KPI: 엠바고 이후 14일 재방문</li>
          <li>실험 후보: {best_rule}</li>
          <li>처치 방향: 저장검색, 관심 카테고리 팔로우, 다음날 추천 피드, 가격변동 알림</li>
          <li>Guardrail: 구매의도 지표와 알림 피로도</li>
        </ul>
      </div>
    </section>

    <section class="panel">
      <h2>한눈에 보는 핵심 수치</h2>
      <div class="metric-grid">
        <div class="metric pos"><div class="v">{best_mcc:.3f}</div><div class="l">확장 후보 grid 1위 MCC<br>{best_rule}</div></div>
        <div class="metric"><div class="v">{best_precision:.1%}</div><div class="l">후보 X precision<br>리텐션 유저 타겟 정확도</div></div>
        <div class="metric neg"><div class="v">-1.2pp</div><div class="l">카트 g-formula 효과<br>보정 후 null</div></div>
        <div class="metric"><div class="v">0.184</div><div class="l">late cohort PR-AUC<br>base 0.080 대비 2배 이상</div></div>
      </div>
      <div class="strip">
        <div><strong>문제</strong>신규 관측 유저의 재방문을 높일 행동 찾기</div>
        <div><strong>가설</strong>초기 활동 폭이 리텐션을 예고한다</div>
        <div><strong>데이터</strong>MerRec 행동 로그, 검열·누수 통제</div>
        <div><strong>결론</strong>카트는 마커, 활동일 수가 후보</div>
        <div><strong>액션</strong>두 번째 활동일 A/B 테스트</div>
      </div>
    </section>

    <section class="panel">
      <h2>구매가 아니라 재방문을 묻는다</h2>
      <p>Mercari 로그에서 첫 구매는 첫 관측 시점 근처에 몰려 있어 리텐션 타깃으로 부적합했다. 그래서 분석 질문을 “누가 바로 구매하는가?”가 아니라 <strong>“초기 경험 후 다시 돌아오는 유저를 어떤 행동으로 만들 수 있는가?”</strong>로 재정의했다.</p>
      <table class="scorecard" aria-label="리텐션 전략 KPI 스코어카드">
        <thead><tr><th>KPI</th><th>정의/비교</th><th>현재 판정</th><th>운영 의미</th></tr></thead>
        <tbody>
          <tr><td>주 KPI</td><td>피처 3일 + 엠바고 2일 이후 14일(t0+5~t0+19일) 안의 재방문</td><td><span class="badge ok">분석 타깃 확정</span></td><td>A/B 테스트의 최종 성공 지표</td></tr>
          <tr><td>후보 X</td><td>{best_rule}</td><td><span class="badge good">MCC {best_mcc:.3f} · lift {best_lift:.2f}</span></td><td>첫 실험 후보. 단, 관측 우위이므로 인과 확정 아님</td></tr>
          <tr><td>배제 후보</td><td>첫 3일 내 카트 1회 이상</td><td><span class="badge null">보정 후 null</span></td><td>구매의도/획득 지표로 분리하고 리텐션 레버로 보고하지 않음</td></tr>
          <tr><td>검증 기준</td><td>late cohort holdout</td><td><span class="badge warn">PR-AUC 0.184</span></td><td>후보 발굴은 가능하나 실험으로 최종 검증 필요</td></tr>
        </tbody>
      </table>
    </section>

    <section class="panel">
      <h2>리텐션 분석에서 자주 틀리는 지점을 먼저 막았다</h2>
      <p>이 리포트는 모델 성능 보고서가 아니라 의사결정 문서다. 그래서 카트의 큰 단순 lift를 그대로 실행하지 않고, 보정 후 null이라는 결론까지 끌고 간다. 분석은 다음 세 가지 함정을 먼저 통제했다.</p>
      <div class="grid3">
        <div class="card blue"><strong>누수 통제</strong><br>피처 3일과 결과 14일 사이에 엠바고를 두고, gap sweep으로 PR-AUC plateau를 확인했다.</div>
        <div class="card green"><strong>검열 처리</strong><br>재방문과 이탈을 경쟁위험으로 모델링해 이탈 유저를 단순 비정보 검열로 취급하지 않았다.</div>
        <div class="card amber"><strong>인과 과장 방지</strong><br>SHAP과 아하 규칙은 후보 발굴용, g-formula/IPTW는 보정 진단용, 최종 효과는 A/B 테스트용으로 역할을 분리했다.</div>
      </div>
      <h3 class="flow-title">전략 프레임워크 — 지표를 고르는 분석이 아니라 실행 의사결정 시스템</h3>
      <div class="flow">
        <div class="flow-step"><span class="n">1</span><b>목표 Y 정의</b><p>엠바고 이후 재방문</p></div>
        <div class="flow-step"><span class="n">2</span><b>후보 X 발굴</b><p>SHAP으로 행동 후보 축소</p></div>
        <div class="flow-step"><span class="n">3</span><b>조작적 정의</b><p>X ≥ k within n days</p></div>
        <div class="flow-step"><span class="n">4</span><b>아하 규칙 선택</b><p>precision · recall · MCC · coverage</p></div>
        <div class="flow-step"><span class="n">5</span><b>임팩트 추정</b><p>g-formula · IPTW · Markov 번역</p></div>
        <div class="flow-step"><span class="n">6</span><b>실험 설계</b><p>A/B 후보와 측정 계획</p></div>
      </div>
      <p>후보 X grid는 원본 임팩트 분석의 카트-only grid가 아니라, 원본 이벤트 테이블에서 활동일 수·세션 수·조회 수·카테고리 수·카트 수 5개 행동지표를 <code>X &gt;= k within n days</code>로 다시 계산한 확장 grid다(아래 “운영 후보” 섹션). 따라서 카트 null 결론은 원본 인과 분석에서, 후보 1위 결론은 이 확장 grid에서 온다.</p>
    </section>

    <section class="panel">
      <h2>리텐션 신호는 카트가 아니라 초기 활동 폭이다</h2>
      <p>해저드 모델의 중요도는 카트보다 세션 수, 활동일 수, 조회 수에 집중된다. 이 결과는 “구매 의도가 있는 유저가 카트도 하고 다시 오는 것”과 “카트를 시키면 다시 온다”를 구분해야 한다는 신호다.</p>
      <figure>
        <img src="assets/x_shortlist_shap.png" alt="SHAP으로 행동 X 후보를 좁히는 차트">
        <figcaption>카트 활성화는 상위 드라이버가 아니다. 초기 탐색 폭을 나타내는 신호가 재방문 예측에 더 강하다.</figcaption>
      </figure>
      <div class="grid2">
        <div class="card"><strong>분석 해석</strong><br>SHAP은 원인 증명이 아니라 후보 압축 장치다. 여기서 도출한 후보는 반드시 조작 가능한 제품 개입으로 다시 정의해야 한다.</div>
        <div class="card"><strong>제품 해석</strong><br>“첫날 한 번 담기”보다 “다음 날 다시 들어와 둘러볼 이유 만들기”가 리텐션 실험으로 더 자연스럽다.</div>
      </div>
    </section>

    <section class="panel">
      <h2>운영 후보는 {best_rule}이다</h2>
      <p>후보 행동을 `X >= k within n days`로 바꿔 비교했다. 불균형 라벨에서 precision, recall, coverage 중 하나만 고르면 왜곡되므로 MCC를 정렬 기준으로 사용했다.</p>
      <figure>
        <img src="assets/aha_rule_selection.png" alt="아하 규칙 후보의 MCC, precision, recall 비교 차트">
        <figcaption>{best_rule}이 MCC {best_mcc:.3f}로 가장 균형이 좋다. 세션 수 규칙은 recall이 더 높지만, 후보 X의 제품 해석과 타겟 정확도까지 고려하면 활동일 수가 더 명확하다.</figcaption>
      </figure>
      <div class="grid2">
        {top_rule_cards}
      </div>
    </section>

    <section class="panel">
      <h2>카트 lift는 실행하면 안 되는 허영지표다</h2>
      <p>카트는 단순 비교에서 +15.1pp로 좋아 보인다. 하지만 인게이지먼트 폭을 보정하면 효과가 0 근처로 붕괴한다. 이 차이를 보여주는 것이 이 프로젝트의 핵심 가치다.</p>
      <figure>
        <img src="assets/impact_logic.png" alt="단순 비교와 인과 보정 추정치를 비교한 임팩트 게이트 차트">
        <figcaption>카트는 “좋은 유저가 이미 하는 행동”일 가능성이 크다. 리텐션 레버로 보고하지 않고, 구매의도/획득 지표로 분리한다.</figcaption>
      </figure>
      <div class="grid2">
        <div class="card red"><strong>중단할 주장</strong><br>“카트율을 올리면 재방문이 오른다”는 주장은 현재 데이터로 방어할 수 없다.</div>
        <div class="card green"><strong>유지할 주장</strong><br>“초기 활동 폭이 넓은 유저는 재방문 가능성이 높다. 이를 실험 후보로 검증하자”는 주장은 방어 가능하다.</div>
      </div>
    </section>

    <section class="panel action">
      <h2>두 번째 활동일을 만드는 실험</h2>
      <p>분석 결과를 제품 과제로 번역하면 “첫날 이후 다시 방문할 이유를 심는 것”이다. 실험은 지표를 올리는지보다 <strong>재방문을 실제로 올리는지</strong>를 봐야 한다.</p>
      <div class="step-list">
        <div class="step"><b>1. Target</b>신규 관측 유저 중 첫날 탐색 신호가 있는 유저</div>
        <div class="step"><b>2. Treatment</b>저장검색, 관심 카테고리 팔로우, 다음날 추천 피드</div>
        <div class="step"><b>3. Primary KPI</b>엠바고 이후 14일 재방문</div>
        <div class="step"><b>4. Secondary KPI</b>{best_rule} 달성률, 세션 수, 조회 수</div>
        <div class="step"><b>5. Guardrail</b>구매의도, 알림 피로도, opt-out</div>
      </div>
    </section>

    <section class="panel assumption">
      <h2>한계와 가정</h2>
      <p>MerRec은 관측 데이터라 실제 A/B 테스트를 수행한 데이터셋이 아니다. 따라서 이 보고서의 완성 지점은 “효과 확정”이 아니라 “A/B 테스트로 검증할 후보 X와 측정 설계”다. g-formula와 IPTW는 순차적 교환가능성, positivity, consistency 가정에 의존하므로 실험을 대체하지 못한다. Markov 체인도 임팩트 번역에는 유용하지만 인과 식별 장치가 아니다.</p>
      <p>또한 원본 드라이버 리포트의 카트 grid와 이 보고서의 확장 후보 grid는 역할이 다르다. 카트 null 결론은 원본 임팩트 분석에서, {best_rule} 후보 결론은 원본 이벤트 테이블에서 재계산한 확장 grid에서 온다.</p>
    </section>

    <p class="footer">근거: `docs/drivers_report.md`, `docs/impact_report.md`, `docs/limitations.md`, `PLAN.md`, `src/drivers.py`, `src/impact.py`, `strategy_report/candidate_rules.csv`. 생성 스크립트: `strategy_report/scripts/build_strategy_report.py`.</p>
  </main>
</body>
</html>
"""


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    use_theme()
    grid = load_candidate_grid()
    build_shap_chart()
    grid = build_aha_chart(grid)
    build_impact_chart()
    (OUT / "index.html").write_text(build_html(grid), encoding="utf-8")
    print(f"wrote {(OUT / 'index.html').relative_to(ROOT)}")
    for path in sorted(ASSETS.glob("*.png")):
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
