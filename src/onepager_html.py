"""Build the recruiter-facing portfolio one-pager.

The one-pager is a 60-second scan layer above the detailed reports. Headline
metrics are computed from the current event cache so the HTML does not drift
from regenerated reports.
"""

from __future__ import annotations

import base64
import html
from pathlib import Path

import pandas as pd

from _util import ROOT, load_config
from ab_design import run as ab_run


REPO = "https://github.com/seungyoon-lee29/fashion-c2c-retention-analysis"
GITHUB_PROFILE = "https://github.com/seungyoon-lee29"
EMAIL = "sy3097@gmail.com"
HF = "https://huggingface.co/datasets/mercari-us/merrec"
AUTHOR = "이승윤"
ROLE = "Product Data Analyst"

EVENTS = ROOT / "data" / "events.parquet"
FIGURE_DIR = ROOT / "docs" / "figures"

FLOW = [
    (
        "1",
        "퍼널",
        "조회·찜·카트·구매의 도달률에서 최대 유출 구간(조회→찜)을 짚고, 희소한 구매 대신 재방문을 주지표로 삼았다. 오퍼·즉시구매는 병렬 경로다.",
    ),
    (
        "2",
        "코호트",
        "D7 재방문 기준선과 첫날 활동 폭별 차이를 계산해 실험 후보를 좁혔다.",
    ),
    (
        "3",
        "식별 진단",
        "카트·찜 같은 행동 신호를 인과효과로 과대해석하지 않도록 보정 추정과 한계를 분리했다.",
    ),
    (
        "4",
        "실험",
        "첫날 탐색 폭 넛지의 주지표, 가드레일, MDE, 표본수, 성공/중단 규칙을 설계했다.",
    ),
]

SKILLS = [
    ("KPI 재정의", "구매완료율이 낮은 상황에서 신규 유저 경험의 의사결정 KPI를 D7 재방문으로 전환"),
    ("SQL 데이터 QA", "required fields, event vocabulary, timestamp, price, denominator를 DuckDB로 검증"),
    ("퍼널/코호트", "최대 유출 구간과 첫날 활동 폭별 D7 재방문 차이를 연결"),
    ("인과 정직성", "관측 상관, 보정 추정, 실험 필요성을 분리해 결론을 제한"),
    ("실험 설계", "주지표, 가드레일, MDE, 표본수, 기간, 성공/중단 판정표 제안"),
]

FIGURES = [
    ("drivers_importance.png", "행동 강도(세션·활동일)가 재방문을 가장 잘 '예측'한다 — 단, 예측일 뿐 인과는 아니다."),
    ("impact_estimators.png", "같은 활동량을 보정하면 카트 효과는 naive +16pp → 0 근처/음수로 붕괴 (naive·g-formula·IPTW)."),
]

DOCS = [
    ("README.md", "프로젝트 입구와 읽는 순서"),
    ("onepager.html", "채용담당자용 60초 요약"),
    ("docs/portfolio_report.md", "면접용 메인 분석 리포트"),
    ("docs/data_quality_report.md", "DuckDB SQL 데이터 QA"),
    ("docs/ab_test_design.md", "실험 설계와 표본수"),
]


CSS = """
:root{
  --font-body:'Pretendard Variable','Pretendard',-apple-system,BlinkMacSystemFont,system-ui,sans-serif;
  --font-display:'Fraunces','Pretendard',Georgia,serif;
  --font-mono:'IBM Plex Mono','Pretendard',ui-monospace,monospace;
  --paper:#F4EFE6;--paper-deep:#ECE4D5;--surface:#FBF8F2;
  --ink:#1C1916;--ink-soft:#4A443B;--muted:#8A8173;
  --rule:#D9D1C0;--rule-strong:#B6AC97;
  --oxblood:#7B2E2C;--pine:#3E6B4F;--ochre:#A9792A;
  --shadow:0 1px 2px rgba(28,25,22,.04),0 10px 30px rgba(28,25,22,.07)
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:var(--font-body);font-size:15.5px;line-height:1.62;
  -webkit-font-smoothing:antialiased;font-feature-settings:"ss01"}
a{color:var(--oxblood);text-underline-offset:2px}
main{max-width:1040px;margin:0 auto;padding:30px 22px 76px}
section{margin:0 0 16px}

/* hero — editorial masthead on paper */
.hero{background:var(--surface);border:1px solid var(--rule);border-top:3px solid var(--oxblood);
  border-radius:4px;padding:34px 38px 30px;box-shadow:var(--shadow)}
.eyebrow{margin:0 0 16px;color:var(--oxblood);font-family:var(--font-mono);
  font-size:11px;font-weight:600;letter-spacing:.22em;text-transform:uppercase}
.hero h1{margin:0;max-width:880px;font-size:clamp(28px,4.2vw,44px);line-height:1.1;
  font-weight:800;letter-spacing:-.02em;color:var(--ink)}
.hero h1 .ac{color:var(--oxblood)}
.sub{max-width:820px;margin:14px 0 0;color:var(--ink-soft);font-size:17px;line-height:1.55}
.profile{display:flex;flex-wrap:wrap;gap:8px;margin-top:20px}
.profile span{font-family:var(--font-mono);font-size:12px;color:var(--ink-soft);
  background:var(--paper-deep);border:1px solid var(--rule);border-radius:4px;padding:6px 10px}
.profile b{font-family:var(--font-body)}
.profile a{color:var(--oxblood)}

/* panels */
.panel{background:var(--surface);border:1px solid var(--rule);border-radius:4px;
  padding:22px 24px;box-shadow:var(--shadow)}
h2{font-size:19px;margin:0 0 16px;font-weight:800;letter-spacing:-.01em;color:var(--ink);
  padding-bottom:11px;border-bottom:1px solid var(--rule)}
h3{font-size:15px;margin:8px 0 6px;font-weight:700;color:var(--ink)}
.lead{font-size:16.5px;margin:0 0 16px;color:var(--ink-soft);line-height:1.6}
.lead b,p b,td b{color:var(--ink);font-weight:700}

/* metrics */
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.metric{border:1px solid var(--rule);border-radius:4px;padding:15px 16px;background:var(--paper)}
.metric .v{font-size:30px;font-weight:800;letter-spacing:-.02em;color:var(--ink);font-variant-numeric:tabular-nums}
.metric.warn .v{color:var(--ochre)} .metric.ok .v{color:var(--oxblood)}
.metric p{margin:6px 0 0;color:var(--muted);font-size:12.5px;line-height:1.45}

/* flow */
.flow{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.step{background:var(--paper);border:1px solid var(--rule);border-top:2px solid var(--oxblood);
  border-radius:4px;padding:14px}
.step .num{font-family:var(--font-display);color:var(--oxblood);font-weight:600;font-size:19px}
.step h3{margin:6px 0 4px}
.step p{margin:4px 0 0;color:var(--ink-soft);font-size:13px;line-height:1.5}

/* table */
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;border-bottom:1px solid var(--rule);padding:11px 8px;vertical-align:top;color:var(--ink-soft)}
th{font-family:var(--font-mono);font-size:11px;text-transform:uppercase;letter-spacing:.1em;
  color:var(--muted);border-bottom:1.5px solid var(--rule-strong)}
td:first-child{color:var(--ink);font-weight:700;white-space:nowrap}
tr:last-child td{border-bottom:none}

/* figures */
.figs{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
figure{margin:0;border:1px solid var(--rule);border-radius:4px;overflow:hidden;background:var(--surface)}
figure img{display:block;width:100%;height:auto}
figcaption{font-family:var(--font-mono);font-size:11.5px;color:var(--ink-soft);
  padding:10px 12px;border-top:1px solid var(--rule);line-height:1.5}

/* next / scope / docs */
.next{display:grid;grid-template-columns:1.15fr .85fr;gap:16px}
.experiment{border-left:3px solid var(--oxblood)}
.experiment p{font-size:14.5px;color:var(--ink-soft);margin:0 0 10px}
.scope ul{margin:0;padding-left:18px;color:var(--ink-soft)}
.scope li{margin:0 0 6px}
.doclist{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}
.doc{border:1px solid var(--rule);border-radius:4px;background:var(--paper);padding:12px}
.doc b{display:block;font-size:12.5px;color:var(--ink);font-family:var(--font-mono)}
.doc span{color:var(--muted);font-size:12px}

.foot{color:var(--muted);font-size:11.5px;margin:18px 2px 0;font-family:var(--font-mono);line-height:1.6}
.foot a{color:var(--oxblood)}
.foot code{background:var(--paper-deep);padding:1px 5px;border-radius:3px}

@media (max-width:860px){
  .metrics,.flow,.figs,.next,.doclist{grid-template-columns:1fr}
  .hero{padding:28px 22px}
}
"""


def _pct(x: float) -> str:
    return f"{x:.1f}%"


def _pp(x: float) -> str:
    sign = "+" if x >= 0 else ""
    return f"{sign}{x:.0f}pp"


def _portfolio_metrics(cfg: dict) -> dict[str, str]:
    if not EVENTS.exists():
        raise SystemExit("data/events.parquet missing. Run `make eda` first.")

    h = int(cfg["da_reports"]["retention_days"][-1])
    nq = int(cfg["da_reports"]["breadth_quantiles"])
    df = pd.read_parquet(EVENTS, columns=["user_id", "stime", "event"])
    df["day"] = pd.to_datetime(df["stime"]).dt.normalize()

    users = df["user_id"].nunique()
    buyers = df.loc[df["event"].eq("buy_comp"), "user_id"].nunique()
    buy_reach = 100 * buyers / users

    first = df.groupby("user_id")["day"].min()
    days = df.groupby("user_id")["day"].apply(set)
    data_start, data_end = df["day"].min(), df["day"].max()
    eligible = first[(first > data_start) & (first <= data_end - pd.Timedelta(days=h))].index

    retained = pd.Series(
        {
            user: any(
                first[user] < day <= first[user] + pd.Timedelta(days=h)
                for day in days[user]
            )
            for user in eligible
        }
    )
    d7_base = 100 * retained.mean()

    first_day_events = df[df["day"].eq(df["user_id"].map(first))]
    first_day_counts = first_day_events.groupby("user_id").size().reindex(eligible)
    bins = pd.qcut(first_day_counts.rank(method="first"), nq, labels=False)
    bottom = retained.loc[bins[bins == 0].index].mean()
    top = retained.loc[bins[bins == nq - 1].index].mean()
    breadth_gap = 100 * (top - bottom)

    return {
        "buy_reach": _pct(buy_reach),
        "d7_base": _pct(d7_base),
        "breadth_gap": _pp(breadth_gap),
    }


def _experiment(cfg: dict) -> dict[str, str]:
    res = ab_run(cfg, write=False)
    primary = res["primary"]
    row = next(r for r in res["rows"] if abs(r[0] - primary) < 1e-9)
    return {
        "base": f"{res['base'] * 100:.1f}",
        "mde": f"{primary:.1f}",
        "narm": f"{row[1]:,}",
        "weeks": f"{row[3]:.1f}",
    }


def _metric_cards(metrics: dict[str, str], experiment: dict[str, str]) -> str:
    cards = [
        (
            metrics["buy_reach"],
            "구매완료율. 구매 전환만으로는 의사결정 표본이 작다.",
            "warn",
        ),
        (
            metrics["d7_base"],
            "D7 재방문 기준선. 실험의 주지표로 사용했다.",
            "ok",
        ),
        (
            metrics["breadth_gap"],
            "첫날 활동 폭 상위 코호트와 하위 코호트의 D7 재방문 차이.",
            "ok",
        ),
        (
            experiment["narm"],
            "MDE 2.0pp 검정을 위한 arm당 표본수.",
            "",
        ),
    ]
    return "".join(
        f'<div class="metric {css}"><div class="v">{html.escape(value)}</div><p>{html.escape(text)}</p></div>'
        for value, text, css in cards
    )


def _flow_cards() -> str:
    return "".join(
        f'<div class="step"><span class="num">{num}</span><h3>{html.escape(title)}</h3><p>{html.escape(text)}</p></div>'
        for num, title, text in FLOW
    )


def _skill_rows() -> str:
    return "".join(
        f"<tr><td>{html.escape(skill)}</td><td>{html.escape(text)}</td></tr>"
        for skill, text in SKILLS
    )


def _img(name: str) -> str:
    p = FIGURE_DIR / name
    if not p.exists():
        return ""
    encoded = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _figures() -> str:
    parts = []
    for name, caption in FIGURES:
        src = _img(name)
        if not src:
            continue
        parts.append(
            f'<figure><img src="{src}" alt=""><figcaption>{html.escape(caption)}</figcaption></figure>'
        )
    return "".join(parts)


def _doc_cards() -> str:
    return "".join(
        f'<div class="doc"><b>{html.escape(path)}</b><span>{html.escape(desc)}</span></div>'
        for path, desc in DOCS
    )


def build() -> str:
    cfg = load_config()
    metrics = _portfolio_metrics(cfg)
    ex = _experiment(cfg)
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>패션 C2C 신규 유저 리텐션 분석 | Portfolio One-Pager</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.css">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400..700&display=swap">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>{CSS}</style>
</head>
<body>
<main>
  <section class="hero">
    <p class="eyebrow">PRODUCT DATA ANALYSIS PORTFOLIO</p>
    <h1>패션 C2C 신규 유저 <span class="ac">리텐션 분석</span></h1>
    <p class="sub">카트가 아니라 <b>첫날 경험 폭</b>을 실험한다. Mercari 행동 로그로 퍼널, 코호트, 인과 진단, A/B 설계를 한 흐름으로 연결했다.</p>
    <div class="profile">
      <span>작성자 <b>{html.escape(AUTHOR)}</b></span>
      <span>목표 직무 <b>{html.escape(ROLE)}</b></span>
      <span>연락 <a href="mailto:{EMAIL}">{EMAIL}</a></span>
      <span>GitHub <a href="{GITHUB_PROFILE}">seungyoon-lee29</a></span>
      <span>저장소 <a href="{REPO}">repository</a></span>
    </div>
  </section>

  <section class="panel">
    <h2>10초 결론</h2>
    <p class="lead">구매완료율은 <b>{metrics["buy_reach"]}</b>로 낮아 구매 최적화보다 재방문 실험이 더 현실적이었다. 첫날 활동 폭은 D7 재방문과 <b>{metrics["breadth_gap"]}</b> 연관됐지만, 관측 데이터만으로 인과효과를 단정하지 않았다. 결론은 <b>첫날 탐색 폭 넛지 A/B</b>다.</p>
    <div class="metrics">{_metric_cards(metrics, ex)}</div>
  </section>

  <section class="panel">
    <h2>분석 흐름</h2>
    <div class="flow">{_flow_cards()}</div>
  </section>

  <section class="panel">
    <h2>보여준 역량</h2>
    <table>
      <tr><th>역량</th><th>이 프로젝트에서 한 일</th></tr>
      {_skill_rows()}
    </table>
  </section>

  <section class="panel">
    <h2>핵심 근거</h2>
    <p class="lead">행동 강도(세션·활동일)가 D7 재방문을 가장 잘 <b>예측</b>하지만, 같은 초기 활동량을 보정하면 카트 효과는 0 근처/음수로 사라진다. <b>예측력 ≠ 인과</b> — 그래서 관측 추정을 단정하지 않고 실험으로 넘긴다.</p>
    <div class="figs">{_figures()}</div>
  </section>

  <section class="next">
    <div class="panel experiment">
      <h2>실험 Handoff</h2>
      <p><strong>가설.</strong> 신규 유저의 첫 세션에서 인접 카테고리, 저장 후보, 탐색 경로를 넓히면 D7 재방문이 오른다.</p>
      <p><strong>설계.</strong> 유저 단위 무작위 배정, 주지표 D7 재방문, 기준선 {ex['base']}%, MDE {ex['mde']}pp, 표본 {ex['narm']}/arm, 예상 {ex['weeks']}주.</p>
      <p><strong>판정.</strong> D7 재방문 +{ex['mde']}pp 이상, 구매완료율 비악화, 즉시이탈 및 SRM 이상 없음이면 다음 단계로 진행한다.</p>
    </div>
    <div class="panel scope">
      <h2>범위</h2>
      <ul>
        <li>리텐션은 재방문 행동이다. 매출 효과는 후속 검증이다.</li>
        <li>관측 데이터만으로 양성 인과 효과를 확정하지 않는다.</li>
        <li>30일 로그라 장기 churn은 다루지 않는다.</li>
      </ul>
    </div>
  </section>

  <section class="panel">
    <h2>읽는 순서</h2>
    <div class="doclist">{_doc_cards()}</div>
  </section>

  <p class="foot">
    데이터: MerRec © Mercari, Inc., HuggingFace <a href="{HF}">mercari-us/merrec</a>, CC BY-NC 4.0.
    공개용 정본은 <code>README.md</code>, <code>onepager.html</code>, <code>docs/portfolio_report.md</code>다.
    저장소: <a href="{REPO}">{REPO}</a>.
  </p>
</main>
</body>
</html>
"""


def main() -> int:
    out = ROOT / "onepager.html"
    out.write_text(build(), encoding="utf-8")
    print(f"[onepager_html] wrote {out} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
