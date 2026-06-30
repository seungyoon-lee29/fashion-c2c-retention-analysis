"""M3 A/B test design for the first-session exploration-width nudge."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
from scipy.stats import norm

from _util import ROOT, load_config


EVENTS = ROOT / "data" / "events.parquet"
DOCS = ROOT / "docs"


def base_and_arrival(cfg: dict) -> tuple[float, int, int, float, float, float]:
    """Return D-H revisit base and p25/p50/p75 daily eligible arrivals."""
    if not EVENTS.exists():
        raise SystemExit("data/events.parquet missing. Run `make eda` first.")
    df = pd.read_parquet(EVENTS, columns=["user_id", "stime"])
    df["day"] = pd.to_datetime(df["stime"]).dt.normalize()
    first = df.groupby("user_id")["day"].min()
    days = df.groupby("user_id")["day"].apply(set)
    data_start, data_end = df["day"].min(), df["day"].max()
    h = int(cfg["da_reports"]["retention_days"][-1])

    new_users = first[first > data_start]
    eligible = new_users[new_users <= data_end - pd.Timedelta(days=h)].index
    retained = sum(
        int(any(first[user] < day <= first[user] + pd.Timedelta(days=h) for day in days[user]))
        for user in eligible
    )
    base = retained / len(eligible)

    daily = new_users.groupby(new_users).size()
    p25 = float(daily.quantile(0.25))
    p50 = float(daily.quantile(0.50))
    p75 = float(daily.quantile(0.75))
    return base, h, len(new_users), p25, p50, p75


def n_per_arm(p: float, mde: float, alpha: float, power: float) -> int:
    """Two-sample normal approximation for equal allocation proportion test."""
    p1 = p
    p2 = min(max(p + mde, 1e-6), 1 - 1e-6)
    pooled = (p1 + p2) / 2
    z_alpha = norm.ppf(1 - alpha / 2)
    z_beta = norm.ppf(power)
    numerator = (
        z_alpha * math.sqrt(2 * pooled * (1 - pooled))
        + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    ) ** 2
    return math.ceil(numerator / (p2 - p1) ** 2)


def _duration(total_n: int, daily_arrivals: float, h: int) -> tuple[int, float]:
    enroll_days = math.ceil(total_n / max(daily_arrivals, 1))
    return enroll_days, (enroll_days + h) / 7


def run(cfg: dict, write: bool = True) -> dict:
    base, h, n_new, p25, p50, p75 = base_and_arrival(cfg)
    ab = cfg["ab_test"]
    alpha = float(ab["alpha"])
    power = float(ab["power"])
    primary = float(ab["primary_mde_pp"])

    rows = []
    for mde_pp in ab["mde_grid_pp"]:
        n_arm = n_per_arm(base, float(mde_pp) / 100, alpha, power)
        enroll_days, weeks = _duration(2 * n_arm, p50, h)
        rows.append((float(mde_pp), n_arm, enroll_days, weeks))

    primary_row = next(row for row in rows if abs(row[0] - primary) < 1e-9)
    arrival_rows = []
    for label, arrivals in [("p25", p25), ("p50", p50), ("p75", p75)]:
        enroll_days, weeks = _duration(2 * primary_row[1], arrivals, h)
        arrival_rows.append((label, round(arrivals, 1), enroll_days, weeks))

    res = {
        "base": base,
        "H": h,
        "n_new": n_new,
        "arrivals": p50,
        "arrival_p25": p25,
        "arrival_p75": p75,
        "rows": rows,
        "arrival_rows": arrival_rows,
        "primary": primary,
        "alpha": alpha,
        "power": power,
    }
    if write:
        _write_report(res, cfg)
    return res


def _mde_table(rows: list[tuple[float, int, int, float]], h: int) -> str:
    head = ["MDE(절대)", "표본/arm", "총 표본", "모집 일수", f"총 기간(모집+D{h})"]
    out = ["| " + " | ".join(head) + " |", "| " + " | ".join("---" for _ in head) + " |"]
    for mde_pp, n_arm, enroll_days, weeks in rows:
        out.append(f"| {mde_pp:.1f}pp | {n_arm:,} | {2 * n_arm:,} | {enroll_days}일 | {weeks:.1f}주 |")
    return "\n".join(out)


def _arrival_table(rows: list[tuple[str, float, int, float]], h: int) -> str:
    head = ["유입 가정", "일별 신규 유저", "모집 일수", f"총 기간(모집+D{h})"]
    out = ["| " + " | ".join(head) + " |", "| " + " | ".join("---" for _ in head) + " |"]
    for label, arrivals, enroll_days, weeks in rows:
        out.append(f"| {label} | {arrivals:,.1f} | {enroll_days}일 | {weeks:.1f}주 |")
    return "\n".join(out)


def _write_report(res: dict, cfg: dict) -> None:
    base = float(res["base"])
    h = int(res["H"])
    primary = float(res["primary"])
    primary_row = next(row for row in res["rows"] if abs(row[0] - primary) < 1e-9)
    n_arm = int(primary_row[1])
    weeks = float(primary_row[3])

    lines = [
        f"# A/B 설계 — 첫날 경험 폭 넓히기 넛지 -> D{h} 재방문 (M3, 자동 생성)\n\n",
        f"> **BLUF**: 관측 로그만으로는 양성 리텐션 효과를 확정할 수 없다. "
        f"따라서 첫날 탐색 폭 넛지를 유저 단위 A/B로 검증한다. "
        f"주지표 D{h} 재방문(base **{base * 100:.1f}%**), MDE **{primary:.1f}pp**, "
        f"표본 **{n_arm:,}명/arm**, 예상 **{weeks:.1f}주**.\n\n",
        "## 1. 왜 실험인가\n\n",
        "- 코호트 신호: 첫날 활동량 상위군은 하위군보다 D7 재방문이 높다.\n",
        "- 식별 진단: 카트와 탐색 폭은 좋아 보이지만 같은 초기창 활동량을 보정하면 효과가 0 근처 또는 음수로 불안정하다.\n",
        "- 결론: 관측 추정치를 더 단정하지 않고, 전향 무작위화로 하나의 실험 estimand를 새로 정의한다.\n\n",
        "## 2. 가설\n\n",
        f"- **H1**: 신규 유저의 첫 세션에서 탐색 폭을 넓히는 넛지가 D{h} 재방문을 높인다.\n",
        "- 조회 직후 찜 후보와 인접 카테고리 노출은 별도 실험이 아니라 같은 탐색 폭 넛지의 구현 예시다.\n\n",
        "## 3. 설계\n\n",
        "- **랜덤화 단위**: 유저. 첫 세션 진입 시 1회 배정하고 고정한다.\n",
        "- **대상 모집단**: 신규 관측 유저. 프로덕션에서는 가입 후 첫 세션 유저로 고정하는 것이 더 좋다.\n",
        "- **처치**: 첫 세션에 인접 카테고리와 저장 후보를 노출한다.\n",
        f"- **주지표**: D{h} 재방문율.\n",
        "- **보조지표**: first-session categories, like reach, view depth, D1 session count.\n",
        "- **가드레일**: 구매완료율, 즉시이탈, 세션 품질, SRM.\n\n",
        f"## 4. 표본수·MDE·기간 (base {base * 100:.1f}%, alpha {res['alpha']}, power {res['power']})\n\n",
        _mde_table(res["rows"], h),
        "\n\n",
        f"## 5. 모집 속도 민감도 (MDE {primary:.1f}pp 기준)\n\n",
        _arrival_table(res["arrival_rows"], h),
        "\n\n",
        "## 6. 성공/중단 판정표\n\n",
        "| Decision | Rule |\n",
        "|---|---|\n",
        f"| Ship / scale | D{h} 재방문 lift >= {primary:.1f}pp이고 가드레일 악화 없음 |\n",
        f"| Iterate | D{h} lift가 0~{primary:.1f}pp 사이이며 보조지표가 개선됨 |\n",
        "| Stop | D7 재방문 lift <= 0 또는 즉시이탈 +1.0pp 초과 |\n",
        "| Invalidate | SRM p<0.001, 로깅 결측, 처치 오염 발견 |\n",
        "| Revenue follow-up | D7 lift가 확인되면 D14/D30 재방문과 repeat purchase 또는 GMV/AOV 로그로 후속 검증 |\n\n",
        "Guardrail margin은 실제 서비스 리스크 허용도에 맞춰 사전등록해야 한다. 현재 데이터에서는 구매완료율이 4.4%로 낮아 "
        "작은 구매 악화는 underpowered일 수 있으므로, 구매완료율은 단독 stop rule보다 모니터링 가드레일로 둔다.\n\n",
        "## 7. 실험이 답하는 것 / 못 하는 것\n\n",
        f"- **답함**: 첫날 탐색 폭 넛지의 D{h} 재방문 인과 효과.\n",
        f"- **못함**: 장기(>D{h}) 효과, 매출 효과, 구현 방식별 차이, 신규 외 유저 효과.\n\n",
        "> Honesty: 가설, 주지표, MDE, 성공/중단 규칙은 실험 전 사전등록 대상이다. 사후 지표/MDE 변경은 금지한다.\n",
    ]
    (DOCS / "ab_test_design.md").write_text("".join(lines), encoding="utf-8")
    print("wrote docs/ab_test_design.md")


def main() -> int:
    cfg = load_config()
    run(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
