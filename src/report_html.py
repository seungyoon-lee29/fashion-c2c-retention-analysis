"""Build a single self-contained portfolio one-pager (report.html) with figures embedded.

Curated presentation layer: headline numbers are the locked real-MerRec results
(see docs/impact_report.md, docs/eda_findings.md). Figures are embedded as base64 so
the file is shareable on its own. Run: `python src/report_html.py` (or `make report`).
"""
from __future__ import annotations

import base64

from _util import ROOT

FIGS = [
    ("cif_competing_risks.png", "경쟁위험 CIF — 재방문(리텐션) vs 이탈(churn)"),
    ("cif_by_aha.png", "활성화(초기 카트)별 리텐션 CIF — 보정 전 격차"),
    ("drivers_importance.png", "리텐션 드라이버 (SHAP) — 인게이지먼트 폭이 상위"),
    ("gap_sweep.png", "누수 통제: embargo gap sweep PR-AUC plateau"),
    ("impact_estimators.png", "임팩트: naive(교란) vs g-formula·IPTW(보정)"),
    ("markov_per1000.png", "무기억 Markov 근사 (90% CI) — 헤드라인 아님"),
]


def _img(name: str) -> str:
    p = ROOT / "docs" / "figures" / name
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f"data:image/png;base64,{b64}"


def build() -> str:
    cards = "\n".join(
        f'<figure><img src="{_img(n)}" alt="{c}"><figcaption>{c}</figcaption></figure>'
        for n, c in FIGS
    )
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>활성화→리텐션 생존분석 + g-계산 임팩트</title>
<style>
:root{{--ink:#1a1a1a;--mut:#666;--line:#e4e4e7;--acc:#2a7;--bad:#c44;--bg:#fafafa}}
*{{box-sizing:border-box}}
body{{font:16px/1.65 -apple-system,Segoe UI,Roboto,'Noto Sans KR',sans-serif;color:var(--ink);
background:var(--bg);margin:0;padding:0 20px}}
main{{max-width:900px;margin:0 auto;padding:48px 0 80px}}
h1{{font-size:30px;line-height:1.25;margin:0 0 6px}}
.sub{{color:var(--mut);font-size:17px;margin:0 0 28px}}
h2{{font-size:21px;margin:40px 0 12px;padding-bottom:6px;border-bottom:2px solid var(--line)}}
p{{margin:10px 0}}
.callout{{background:#fff;border:1px solid var(--line);border-left:4px solid var(--acc);
border-radius:8px;padding:14px 18px;margin:18px 0}}
.callout.warn{{border-left-color:var(--bad)}}
table{{width:100%;border-collapse:collapse;margin:14px 0;background:#fff}}
th,td{{padding:9px 12px;border:1px solid var(--line);text-align:left}}
th{{background:#f4f4f5;font-weight:600}}
.pos{{color:var(--acc);font-weight:600}}.neg{{color:var(--bad);font-weight:600}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:18px;margin:18px 0}}
figure{{margin:0;background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px}}
figure img{{width:100%;height:auto;border-radius:4px}}
figcaption{{color:var(--mut);font-size:13px;margin-top:8px}}
code{{background:#f0f0f1;padding:1px 5px;border-radius:4px;font-size:13.5px}}
.foot{{color:var(--mut);font-size:13px;margin-top:48px;border-top:1px solid var(--line);padding-top:14px}}
ul{{margin:10px 0;padding-left:22px}}li{{margin:4px 0}}
</style></head>
<body><main>

<h1>활성화 → 리텐션 생존분석 + g-계산 임팩트</h1>
<p class="sub">리텐션을 <b>인과적으로 정직하게</b> 다루고(검열·누수·교란을 <i>방법으로</i> 처리),
모던 추정기를 헤드라인이 아니라 <b>정밀 계측기</b>로 쓰는 그로스 데이터 분석.</p>

<div class="callout"><b>한 줄 결론.</b> 초기 카트는 리텐션과 큰 <i>연관</i>(+15pp)을 보이지만,
인게이지먼트를 인과 보정하면 효과가 <b>~0으로 붕괴</b>한다 — 카트는 리텐션 <i>레버</i>가 아니라 이미
인게이지된 유저의 <b>마커</b>(허영지표)다. 방법론은 이 null을 정직하게 드러내고 검증한다.</div>

<h2>데이터 & Phase-0 핵심 발견</h2>
<p><b>MerRec</b>(Mercari 공식 C2C 행동 로그, KDD 2025) 5개 파티션 — 277만 이벤트·43,311 유저·30일.
가입 필드 없음 → t0=첫 관측, 좌측절단을 생존모델 <b>지연진입</b>으로 처리.</p>
<div class="callout warn"><b>발견 → 결과 재정의.</b> MerRec 첫 구매는 <b>즉시적</b>(t0로부터 중앙값 0일,
전환 80%가 피처 창 안). 즉 <i>획득</i>이지 리텐션이 아니며, 누수 안전 결과 창엔 전환이 ~214건만 남아 모델 불가.
그래서 스파인을 <b>엠바고 이후 재방문(=리텐션)</b>으로 확정(사전등록 D-1 보조 결과의 승격 — 사후 낚시 아님).</div>

<h2>방법 (MVS 스파인)</h2>
<ul>
<li><b>Phase-0 게이트</b> — 타임라인 복원·이벤트·검열 정의 검증 (GATE PASS).</li>
<li><b>이산시간 경쟁위험 생존</b> — 재방문 vs 이탈(정보적 검열 해결), 지연진입(좌측절단), 풀드 로지스틱+GBM 해저드.</li>
<li><b>누수 통제</b> — embargo gap sweep plateau = 누수 제거된 진짜 성능(레버 t → 결과 t+h 블랙아웃).</li>
<li><b>임팩트 = g-computation</b> — g-formula(주력)+IPTW/MSM(교차)+naive(대조), <b>E-value</b>로 교란 강건성 봉투.</li>
</ul>

<h2>핵심 결과 — 활성화 레버(초기 카트) → 리텐션</h2>
<table>
<tr><th>추정량</th><th>Δ 재방문확률</th><th>해석</th></tr>
<tr><td>naive (비보정)</td><td class="pos">+0.151</td><td>카트 유저 재방문 47.7% vs 32.7% — 큰 연관</td></tr>
<tr><td><b>g-formula (표준화)</b></td><td class="neg">−0.012</td><td>인게이지먼트 보정 시 효과 <b>소멸</b></td></tr>
<tr><td>IPTW/MSM (교차)</td><td>+0.027</td><td>작은 양수 — g와 절대차 3.9pp(부호만 반대)</td></tr>
</table>
<p>RR=0.97 → <b>E-value=1.23</b>. 두 인과 추정기 모두 0의 ±3pp 안 → <b>효과 null·부호 미식별</b>.
326% 상대차는 분모≈0의 <b>null-스케일 착시</b>이지 진짜 발산이 아니며, 진단 프로토콜이 <b>절대차 가드</b>로
이를 구분한다. 양의 식별 효과가 없어 레버 원장은 생략.</p>

<h2>검증 — 방법론이 헛돌지 않음</h2>
<ul>
<li><b>시간외(OOT) 검증</b>: retain-hazard holdout PR-AUC=<b>0.184</b> (base 0.080의 2배+), ROC-AUC 0.658.</li>
<li><b>누수 통제</b>: gap sweep PR-AUC ~0.19 plateau — 누수 아티팩트 아님.</li>
<li><b>리텐션 드라이버(SHAP)</b>: 인게이지먼트 폭(세션수·활동일수·조회수)이 상위, 카트는 ~0.</li>
<li><b>정확성 백스톱</b>: 합성 ground-truth(심어둔 +효과)를 g-formula/IPTW가 복원 — <code>make test</code> 통과.</li>
</ul>

<div class="grid">{cards}</div>

<h2>한계 & 정직성</h2>
<ul>
<li>재방문은 <i>행동</i> 리텐션 프록시이지 <i>재구매(수익)</i> 아님 — 수익 임팩트는 후속.</li>
<li>g-계산은 순차적 교환가능성·positivity·consistency 가정에 의존 → <b>E-value로 봉투</b>, 인과 단정 금지.</li>
<li>좌측절단(가입 미관측)·정보적 검열·선택/생존 편향 노출. MerRec엔 A/B 부재 → 모든 인과는 <i>조건부</i>.</li>
</ul>

<p class="foot">설계 <code>PLAN.md</code> · 사전등록 <code>docs/decisions.md</code> · 여정 <code>docs/log.md</code> ·
한계 <code>docs/limitations.md</code> · 생성 리포트 <code>docs/*_report.md</code>. 그림·수치는 <code>make all</code>로 재생성.</p>

</main></body></html>
"""


def main() -> int:
    out = ROOT / "report.html"
    out.write_text(build(), encoding="utf-8")
    print(f"[report_html] wrote {out} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
