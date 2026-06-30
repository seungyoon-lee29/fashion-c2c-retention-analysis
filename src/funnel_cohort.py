"""M1 reports: user-level funnel and cohort retention.

The reports are intentionally DA-readable: headline numbers are computed
from `data/events.parquet`, not copied from narrative notes.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

from _util import ROOT, df_to_md, load_config


EVENTS = ROOT / "data" / "events.parquet"
DOCS = ROOT / "docs"

FUNNEL = [
    "item_view",
    "item_like",
    "item_add_to_cart_tap",
    "offer_make",
    "buy_start",
    "buy_comp",
]

LABEL = {
    "item_view": "조회 view",
    "item_like": "찜 like",
    "item_add_to_cart_tap": "카트 cart",
    "offer_make": "오퍼 offer",
    "buy_start": "구매시작 buy_start",
    "buy_comp": "구매완료 buy_comp",
}


def load() -> pd.DataFrame:
    if not EVENTS.exists():
        sys.exit("data/events.parquet not found. Run `make eda` first.")
    df = pd.read_parquet(EVENTS, columns=["user_id", "stime", "session_id", "event", "c0_name"])
    df["day"] = pd.to_datetime(df["stime"]).dt.normalize()
    return df


def _wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return float("nan"), float("nan")
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return 100 * (centre - half), 100 * (centre + half)


def _ci_text(successes: int, n: int) -> str:
    lo, hi = _wilson(successes, n)
    return f"{lo:.1f}-{hi:.1f}%"


def funnel_report(df: pd.DataFrame, cfg: dict) -> None:
    users = set(df["user_id"].unique())
    n_users = len(users)
    sets = {event: set(df.loc[df["event"] == event, "user_id"]) for event in FUNNEL}
    counts = {event: len(sets[event]) for event in FUNNEL}

    rows = []
    prev_event = None
    for event in FUNNEL:
        count = counts[event]
        if prev_event is None:
            step_reach = ""
            lost = ""
        else:
            step_reach = f"{100 * count / max(counts[prev_event], 1):.1f}%"
            lost = f"{len(sets[prev_event] - sets[event]):,}"
        rows.append((LABEL[event], f"{count:,}", round(100 * count / n_users, 1), step_reach, lost))
        prev_event = event

    table = pd.DataFrame(rows, columns=["단계", "도달 유저수", "도달률%", "직전 단계 대비 reach%", "직전→해당 미도달"])

    losses = [
        (
            f"{LABEL[FUNNEL[i - 1]].split()[0]}→{LABEL[FUNNEL[i]].split()[0]}",
            100 * counts[FUNNEL[i]] / max(counts[FUNNEL[i - 1]], 1),
            len(sets[FUNNEL[i - 1]] - sets[FUNNEL[i]]),
        )
        for i in range(1, len(FUNNEL))
    ]
    leak = max(losses, key=lambda x: x[2])
    buy_reach = 100 * counts["buy_comp"] / n_users

    sessions = df.groupby("user_id")["session_id"].nunique()
    buyers = sets["buy_comp"]
    multi_rate = 100 * len(buyers & set(sessions[sessions >= 2].index)) / max((sessions >= 2).sum(), 1)
    single_rate = 100 * len(buyers & set(sessions[sessions == 1].index)) / max((sessions == 1).sum(), 1)
    direction = "높다" if multi_rate > single_rate else "오히려 낮다"

    cat_users = df.groupby("c0_name")["user_id"].nunique()
    cat_rate = (100 * df[df["event"] == "buy_comp"].groupby("c0_name")["user_id"].nunique() / cat_users).dropna()
    floor = int(cfg["da_reports"]["category_min_users"])
    cat_rate = cat_rate[cat_users[cat_rate.index] >= floor].sort_values(ascending=False).head(6)

    lines = [
        '# 퍼널 분석 "어디서 새는가" (M1, 자동 생성)\n',
        f"> **BLUF**: 전체 유저 {n_users:,}명 중 구매완료 도달 **{buy_reach:.1f}%**. "
        f"최대 유출은 **{leak[0]}**(직전 도달 후 미도달 {leak[2]:,}명). "
        "전환이 희소하므로 북극성은 전환이 아니라 **D7 재방문**이다.\n\n",
        "데이터 `data/events.parquet` · 전 수치 `make funnel` 재계산.\n\n",
        "## 1. 전체 유저 퍼널\n\n",
        "_도달률은 이벤트를 1회 이상 일으킨 유저 비율이다. MerRec은 오퍼/즉시구매가 병렬 경로라 "
        "직전 단계 대비 reach%는 순차 전환율이 아니라 비순차 reach 비율이다._\n\n",
        df_to_md(table, index=False, float_digits=1, na_rep=""),
        "\n\n## 2. 세그먼트 구매완료 도달률\n\n",
        f"- 멀티세션(>=2 세션) **{multi_rate:.2f}%** vs 단일세션 **{single_rate:.2f}%**. "
        f"멀티세션 쪽이 {direction}. 세션을 많이 쓴다고 더 사는 것은 아니므로 전환과 리텐션은 별개 축이다.\n",
        "- 카테고리(c0)별 구매완료 도달률 (유저 >=500):\n\n",
        df_to_md(cat_rate.round(1).to_frame("buy_comp 도달률%"), index=True, float_digits=1, na_rep=""),
        "\n\n## 3. 양성 권고\n\n",
        f"> **{leak[0]} 구간**은 직전 단계 도달자 중 {leak[2]:,}명이 다음 단계로 가지 않는 최대 유출이다. "
        "조회 직후 찜 후보 또는 인접 카테고리 노출은 최종 실험인 **첫날 탐색 폭 넛지**의 구현 예시로 묶는다. "
        "성공지표는 구매 전환이 아니라 D7 재방문으로 둔다.\n",
    ]
    (DOCS / "funnel_report.md").write_text("".join(lines), encoding="utf-8")
    print("wrote docs/funnel_report.md")


def _retention_series(first: pd.Series, days: pd.Series, eligible: pd.Index, k: int) -> pd.Series:
    values = {
        user: int(any(first[user] < day <= first[user] + pd.Timedelta(days=k) for day in days[user]))
        for user in eligible
    }
    return pd.Series(values, dtype=int)


def cohort_report(df: pd.DataFrame, cfg: dict) -> None:
    horizons = list(cfg["da_reports"]["retention_days"])
    h = horizons[-1]
    nq = int(cfg["da_reports"]["breadth_quantiles"])

    first = df.groupby("user_id")["day"].min()
    days = df.groupby("user_id")["day"].apply(set)
    data_start, data_end = df["day"].min(), df["day"].max()

    truncated = first[first == data_start].index
    new_users = first.index.difference(truncated)
    first_new = first.loc[new_users]

    retention = {}
    eligible_by_horizon = {}
    for k in horizons:
        eligible = first_new[first_new <= data_end - pd.Timedelta(days=k)].index
        eligible_by_horizon[k] = eligible
        retention[k] = _retention_series(first, days, eligible, k)

    overall_rows = []
    for k in horizons:
        series = retention[k]
        successes = int(series.sum())
        n = int(len(series))
        overall_rows.append((f"D{k}", n, round(100 * successes / n, 1), _ci_text(successes, n)))
    overall = pd.DataFrame(overall_rows, columns=["horizon", "eligible users", "revisit%", "Wilson 95% CI"])

    eligible_h = retention[h].index
    weeks = first.loc[eligible_h].dt.isocalendar().week.astype(int)
    week_rows = []
    for week, users in weeks.groupby(weeks).groups.items():
        row = [str(week), len(users)]
        for k in horizons:
            users_k = retention[k].index.intersection(users)
            if len(users_k) == 0:
                row.extend(["—", "—"])
                continue
            s = retention[k].loc[users_k]
            successes = int(s.sum())
            n = int(len(s))
            row.extend([round(100 * successes / n, 1), _ci_text(successes, n)])
        week_rows.append(tuple(row))
    week_cols = ["cohort week", "users"]
    for k in horizons:
        week_cols.extend([f"D{k}%", f"D{k} 95% CI"])
    week_table = pd.DataFrame(week_rows, columns=week_cols)

    first_day_events = df[df["day"].eq(df["user_id"].map(first))]
    fd_counts = first_day_events.groupby("user_id").size().reindex(eligible_h)
    labels = [f"Q{i + 1}" for i in range(nq)]
    labels[0] += "(첫날 최소)"
    labels[-1] += "(첫날 최다)"
    quantile = pd.qcut(fd_counts.rank(method="first"), nq, labels=labels)

    breadth_rows = []
    for label, users in quantile.groupby(quantile, observed=True).groups.items():
        s = retention[h].loc[users]
        successes = int(s.sum())
        n = int(len(s))
        breadth_rows.append((str(label), n, round(100 * successes / n, 1), _ci_text(successes, n)))
    breadth = pd.DataFrame(breadth_rows, columns=["첫날 활동 분위", "users", f"D{h}%", "Wilson 95% CI"])
    gap_pp = float(breadth.iloc[-1][f"D{h}%"] - breadth.iloc[0][f"D{h}%"])

    first_day_carters = set(first_day_events.loc[first_day_events["event"] == "item_add_to_cart_tap", "user_id"])
    cart_users = [u for u in eligible_h if u in first_day_carters]
    no_cart_users = [u for u in eligible_h if u not in first_day_carters]
    cart_ret = 100 * retention[h].loc[cart_users].mean()
    no_cart_ret = 100 * retention[h].loc[no_cart_users].mean()
    d_h = 100 * retention[h].mean()

    lines = [
        '# 코호트 리텐션 "누가 돌아오는가" (M1, 자동 생성)\n',
        f"> **BLUF**: 신규 관측 유저 D{h} 재방문 **{d_h:.1f}%**. "
        f"첫날 활동량 최상위 코호트는 최하위보다 **+{gap_pp:.0f}pp** 더 돌아온다. "
        "A/B 후보는 단일 행동이 아니라 **첫날 경험의 폭**이다.\n\n",
        f"데이터 `data/events.parquet` · `make cohort` 재계산. "
        f"좌측절단 보정: 데이터 시작일({data_start.date()}) 유저 **{len(truncated):,}명**은 신규 코호트에서 제외.\n\n",
        "## 1. 전체 재방문율 (full-window 신규 관측 유저)\n\n",
        df_to_md(overall, index=False, float_digits=1, na_rep="—"),
        "\n\n## 2. 코호트 주차별 재방문율\n\n",
        "_관측창이 부족한 마지막 주는 직접 비교하지 않는다._\n\n",
        df_to_md(week_table, index=False, float_digits=1, na_rep="—"),
        "\n\n## 3. 첫날 경험 폭 후보\n\n",
        df_to_md(breadth, index=False, float_digits=1, na_rep="—"),
        "\n\n",
        f"- 비교: 첫날 카트 유저 D{h} {cart_ret:.1f}% vs 미카트 {no_cart_ret:.1f}% "
        f"({cart_ret - no_cart_ret:+.1f}pp). 카트도 상관은 있으나 첫날 활동량의 상관물일 수 있다. "
        "카트가 마커인지 레버인지는 식별 진단이 필요하다.\n\n",
        "## 4. 양성 권고\n\n",
        f"> **실험 후보: 첫날 경험을 풍부하게 하는 온보딩.** 첫날 활동량 최상위가 최하위보다 "
        f"D{h} 재방문이 **{gap_pp:.0f}pp** 높다. 신규 유저 첫 세션을 한 아이템에 가두지 않고 "
        "인접 카테고리와 저장 후보로 탐색 폭을 넓히는 넛지를 건다. 단, 이 상관을 인과로 단정하지 않으며 "
        "검증은 A/B로 넘긴다(`docs/ab_test_design.md`).\n",
    ]
    (DOCS / "cohort_report.md").write_text("".join(lines), encoding="utf-8")
    print("wrote docs/cohort_report.md")


def main() -> int:
    cfg = load_config()
    df = load()
    funnel_report(df, cfg)
    cohort_report(df, cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
