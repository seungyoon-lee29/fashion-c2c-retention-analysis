"""Build a single self-contained portfolio one-pager (report.html) with figures embedded.

Curated presentation layer: headline numbers are the locked real-MerRec results
(see docs/impact_report.md, docs/eda_findings.md). Figures are embedded as base64 so
the file is shareable on its own. Run: `python src/report_html.py` (or `make report`).
Written for a non-specialist reader: every causal-inference term is glossed inline and
in the glossary at the bottom.
"""
from __future__ import annotations

import base64

from _util import ROOT

FIGS = [
    ("cif_competing_risks.png",
     "시간이 지날수록 <b>재방문(초록)</b>·<b>이탈(빨강)</b>이 쌓이는 곡선. 둘을 경쟁관계로 함께 모델링한다."),
    ("cif_by_aha.png",
     "카트한 유저(초록)가 안 한 유저(회색)보다 재방문이 높아 <i>보인다</i> — 단 이건 <b>보정 전(연관)</b> 그림이다."),
    ("drivers_importance.png",
     "재방문을 잘 예측하는 초기 행동 순위. 세션수·활동일수 같은 <b>폭넓은 활동</b>이 상위, <b>카트는 거의 0</b>."),
    ("gap_sweep.png",
     "미래 정보 차단 구간을 늘려도 성능이 평평하게 유지됨 = 부정 누수가 아니라 <b>진짜 신호</b>라는 증거."),
    ("impact_estimators.png",
     "왼쪽(보정 전)은 높지만 교란을 보정하면(가운데·오른쪽) <b>0 근처로 주저앉음</b> = 효과는 대부분 교란이었다."),
    ("markov_per1000.png",
     "단순 근사로 본 1,000명당 기대 재방문 수(참고용, 헤드라인 아님)."),
]

GLOSSARY = [
    ("리텐션 (retention)", "유저가 떠나지 않고 다시 돌아와 활동하는 것. 이 분석의 목표 지표."),
    ("활성화 레버 (activation lever)", "올리면 리텐션이 오를 것으로 기대하는 초기 행동. 여기선 '초기 장바구니 담기'."),
    ("연관 vs 인과", "연관=같이 움직인다. 인과=하나가 다른 하나를 <i>일으킨다</i>. 연관이 커도 인과는 0일 수 있다(핵심)."),
    ("교란 (confounding)", "진짜 원인이 따로 있는데(예: 원래 적극적인 유저) 엉뚱한 변수(카트)에 효과가 잘못 귀속되는 것."),
    ("naive (비보정)", "아무 보정 없이 단순 비교한 값. 교란이 그대로 섞여 보통 부풀려져 있다."),
    ("g-computation / g-formula", "교란 변수를 통계로 '맞춰 고정'한 뒤 개입의 <b>순수 효과</b>를 추정하는 인과 표준화 기법(주력)."),
    ("IPTW", "처치받을 확률의 역수로 가중해 교란을 제거하는 <i>다른</i> 방식. g-formula와 교차검증용."),
    ("E-value", "이 결과를 뒤집으려면 '미관측 교란'이 얼마나 강해야 하는지. <b>1에 가까우면 효과가 약하다</b>는 뜻."),
    ("null (효과 없음)", "효과가 사실상 0이라 방향(+/−)조차 단정할 수 없는 상태."),
    ("허영지표 (vanity metric)", "좋아 보이지만 실제 성과를 <i>움직이진</i> 않는 지표. 여기선 카트가 그 예."),
    ("생존분석 (survival analysis)", "'어떤 일이 <i>언제</i> 일어나나(또는 안 일어나나)'를 다루는 통계. 원래 환자 생존시간 분석에서 옴."),
    ("경쟁위험 (competing risks)", "서로 배타적인 여러 결말(재방문 vs 이탈)을 동시에 모델링하는 생존분석."),
    ("검열 / 좌측절단", "관측 기간이 끝나 결말을 못 본 경우(검열), 가입 시점을 몰라 첫 관측부터 세는 편향(좌측절단). 둘 다 보정함."),
    ("누수 / embargo", "미래 정보가 몰래 섞여 성능이 부풀려지는 것(누수). 일정 구간을 블랙아웃해(embargo) 차단."),
    ("CIF (누적발생)", "시간이 지나며 결말(재방문)이 누적으로 일어난 비율 곡선."),
    ("OOT (시간외 검증)", "과거로 학습해 미래를 맞히는지 검증 — 과적합·누수 방어의 핵심."),
    ("SHAP", "각 변수가 모델 예측에 얼마나 기여했는지 측정하는 방법."),
    ("pp (퍼센트포인트)", "비율의 차이 단위. 47%→32%는 15pp 차이."),
]


def _img(name: str) -> str:
    p = ROOT / "docs" / "figures" / name
    return f"data:image/png;base64,{base64.b64encode(p.read_bytes()).decode()}"


def build() -> str:
    cards = "\n".join(
        f'<figure><img src="{_img(n)}" alt="{c}"><figcaption>{c}</figcaption></figure>'
        for n, c in FIGS
    )
    gloss = "\n".join(f"<dt>{t}</dt><dd>{d}</dd>" for t, d in GLOSSARY)
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>활성화 → 리텐션 분석 (쉽게 풀어쓴 버전)</title>
<style>
:root{{--ink:#1a1a1a;--mut:#666;--line:#e4e4e7;--acc:#2a7;--bad:#c44;--blu:#2563eb;--bg:#fafafa}}
*{{box-sizing:border-box}}
body{{font:16px/1.7 -apple-system,Segoe UI,Roboto,'Noto Sans KR',sans-serif;color:var(--ink);
background:var(--bg);margin:0;padding:0 20px}}
main{{max-width:880px;margin:0 auto;padding:44px 0 80px}}
h1{{font-size:29px;line-height:1.25;margin:0 0 6px}}
.sub{{color:var(--mut);font-size:16px;margin:0 0 26px}}
h2{{font-size:21px;margin:38px 0 12px;padding-bottom:6px;border-bottom:2px solid var(--line)}}
p{{margin:10px 0}}
.easy{{background:#eff6ff;border:1px solid #bfdbfe;border-left:4px solid var(--blu);
border-radius:8px;padding:14px 18px;margin:18px 0}}
.easy b{{color:#1e40af}}
.easy .tag{{display:inline-block;font-size:12px;font-weight:700;color:#1e40af;
background:#dbeafe;border-radius:20px;padding:2px 10px;margin-bottom:6px}}
.callout{{background:#fff;border:1px solid var(--line);border-left:4px solid var(--acc);
border-radius:8px;padding:14px 18px;margin:18px 0}}
.callout.warn{{border-left-color:var(--bad)}}
table{{width:100%;border-collapse:collapse;margin:14px 0;background:#fff}}
th,td{{padding:9px 12px;border:1px solid var(--line);text-align:left;vertical-align:top}}
th{{background:#f4f4f5;font-weight:600}}
.pos{{color:var(--acc);font-weight:600}}.neg{{color:var(--bad);font-weight:600}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:18px;margin:18px 0}}
figure{{margin:0;background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px}}
figure img{{width:100%;height:auto;border-radius:4px}}
figcaption{{color:#444;font-size:13px;margin-top:8px;line-height:1.55}}
code{{background:#f0f0f1;padding:1px 5px;border-radius:4px;font-size:13.5px}}
.note{{color:var(--mut);font-size:13.5px}}
ul{{margin:10px 0;padding-left:22px}}li{{margin:5px 0}}
dl{{background:#fff;border:1px solid var(--line);border-radius:8px;padding:6px 18px;margin:14px 0}}
dt{{font-weight:700;margin-top:14px;font-size:15px}}
dd{{margin:3px 0 0;color:#333;font-size:14.5px}}
.foot{{color:var(--mut);font-size:13px;margin-top:44px;border-top:1px solid var(--line);padding-top:14px}}
</style></head>
<body><main>

<h1>신규 유저를 다시 돌아오게 만드는 건 무엇인가</h1>
<p class="sub">Mercari(미국 중고거래 앱) 행동 로그로 한 <b>리텐션(재방문) 인과 분석</b> ·
어려운 통계를 헤드라인이 아니라 <i>정밀한 측정 도구</i>로 사용.</p>

<div class="easy">
<span class="tag">💡 쉽게 말하면</span>
<p style="margin:4px 0"><b>질문:</b> 신규 유저가 앱에 <b>다시 돌아오게(리텐션)</b> 하려면 처음에 무슨 행동을
유도해야 할까? 특히 "상품을 장바구니에 담게" 하면 효과가 있을까?</p>
<p style="margin:4px 0"><b>답:</b> 장바구니를 담은 유저가 더 많이 돌아오긴 한다(<b>+15%p</b>). 하지만 그건
<b>원래 적극적인 유저라서</b>지, 장바구니 행동 자체의 힘이 아니다. 적극성의 영향을 통계로 걷어내자
효과는 <b>거의 0으로 사라졌다.</b></p>
<p style="margin:4px 0"><b>그래서:</b> "장바구니를 유도하자"는 리텐션 전략으로는 <b>근거가 없다</b>.
좋아 보이지만 성과를 움직이지 못하는 <b>허영지표</b>의 전형. 이걸 <i>정직하게 증명</i>한 것이 이 분석의 핵심이다.</p>
</div>

<h2>이 분석이 푸는 문제</h2>
<p>신규(처음 관측된) 유저의 <b>초기 행동 → 리텐션(재방문)</b> 관계를 찾고, 그 행동을 올리면 회사가
실제로 얼마나 나아지는지를 <b>인과적으로</b> 추정한다. 핵심은 단순히 "같이 움직인다(연관)"가 아니라
"정말 <i>원인</i>인가(인과)"를 구분하는 것 — 둘은 자주 다르다.</p>

<h2>데이터 & 첫 번째 큰 발견</h2>
<p><b>MerRec</b> — Mercari 공식 행동 로그(조회·찜·장바구니·제안·구매). 실데이터 <b>277만 건 · 유저 4.3만 명 · 30일</b>.
가입 시점 정보가 없어, 각 유저의 <b>첫 관측 시점</b>을 기준점으로 삼고 그로 인한 편향을 생존분석으로 보정했다
(<i>좌측절단·지연진입</i> — 아래 용어 풀이 참고).</p>
<div class="callout warn">
<b>발견 → 목표를 바꿨다.</b> MerRec에선 구매가 <b>첫날 즉시</b> 일어난다(구매의 80%가 관측 첫 구간 안).
즉 첫 구매는 '리텐션'이 아니라 <i>일회성 획득</i>이다. 그래서 분석 목표를 <b>"구매"가 아니라 "재방문(리텐션)"</b>으로
재정의했다. (원래 계획서에 보조 목표로 적어둔 항목을 주력으로 올린 것 — 결과 보고 끼워 맞춘 게 아니다.)
</div>

<h2>어떻게 분석했나</h2>
<ul>
<li><b>재방문을 시간 흐름으로 모델링</b> — "언제 돌아오나 / 언제 이탈하나"를 함께 보는 <i>경쟁위험 생존분석</i>.</li>
<li><b>부정 누수 차단</b> — 초기 행동과 결과 사이에 <i>블랙아웃 구간(embargo)</i>을 둬, 미래 정보가 새어들어
성능이 부풀려지는 것을 막았다.</li>
<li><b>진짜 원인 가려내기</b> — 단순 비교(naive)에 더해, 교란(적극성 등)을 통계로 보정하는 <b>g-computation</b>과
이를 교차검증하는 <b>IPTW</b>로 같은 효과를 두 방식으로 추정. 결과가 가정에 얼마나 민감한지는 <b>E-value</b>로 봉투.</li>
</ul>

<h2>핵심 결과 — "장바구니 → 재방문"의 진짜 효과</h2>
<table>
<tr><th>추정 방식</th><th>재방문 효과(Δ)</th><th>뜻</th></tr>
<tr><td>naive — 그냥 단순 비교</td><td class="pos">+15.1%p</td><td>카트한 유저 재방문 47.7% vs 안 한 유저 32.7%. <b>커 보이지만 교란 포함.</b></td></tr>
<tr><td><b>g-formula — 교란 보정</b></td><td class="neg">−1.2%p</td><td>적극성을 걷어내자 <b>효과 소멸</b>(오히려 살짝 음수).</td></tr>
<tr><td>IPTW — 다른 방식 교차검증</td><td>+2.7%p</td><td>역시 0 근처. g-formula와 3.9%p 차이(부호만 반대).</td></tr>
</table>
<div class="easy">
<span class="tag">💡 이 표 읽는 법</span>
<p style="margin:4px 0">맨 윗줄(<b>+15%p</b>)은 "장바구니 = 리텐션"처럼 보이게 만드는 함정이다. 두 인과 추정법으로
적극성을 보정하면 둘 다 <b>0의 ±3%p 안</b>으로 내려앉는다 → <b>효과는 사실상 없음(null)</b>, 방향조차 단정 불가.
<b>E-value=1.23</b>(1에 가까움)도 "강건한 효과 아님"을 뒷받침한다.</p>
</div>

<h2>그런데 분석이 헛돈 게 아니라는 증거</h2>
<p>"효과 없음"이 모델이 무능해서가 아니라 <i>실제로 효과가 없어서</i>임을 보이는 검증들:</p>
<ul>
<li><b>미래 예측 검증(OOT)</b>: 과거로 학습해 미래 유저의 재방문을 맞히는 정확도(PR-AUC)가 <b>기준의 2배 이상</b>
(0.184 vs 0.080) — 재방문 자체는 분명히 <b>예측 가능</b>하다.</li>
<li><b>진짜 드라이버는 따로 있다</b>: 재방문을 끌어올리는 건 <b>폭넓은 활동</b>(여러 세션·여러 날 방문·많은 조회)이지
장바구니가 아니다(아래 그림).</li>
<li><b>정확성 자가검증</b>: <i>일부러 효과를 심은</i> 가짜 데이터에선 같은 코드가 그 효과를 정확히 복원한다 — 즉 도구는 멀쩡하다.</li>
</ul>

<div class="grid">{cards}</div>

<h2>한계 (정직하게)</h2>
<ul>
<li>여기서 '리텐션'은 <b>재방문(행동)</b>이지 <b>재구매(매출)</b>가 아니다 — 매출 효과는 후속 과제.</li>
<li>인과 추정은 검증 불가능한 가정에 의존한다 → 그래서 단정하지 않고 <b>E-value로 강건성을 봉투</b>했다.</li>
<li>MerRec엔 A/B 테스트가 없다 → 모든 인과 결론은 <i>조건부</i>이며, "A/B로 확인할 가설"을 제공하는 단계다.</li>
</ul>

<h2>용어 풀이</h2>
<dl>
{gloss}
</dl>

<p class="foot">설계 <code>PLAN.md</code> · 사전등록 <code>docs/decisions.md</code> · 여정 <code>docs/log.md</code> ·
한계 <code>docs/limitations.md</code> · 생성 리포트 <code>docs/*_report.md</code>. 수치·그림은 <code>make all</code>,
이 페이지는 <code>make report</code>로 재생성.</p>

</main></body></html>
"""


def main() -> int:
    out = ROOT / "report.html"
    out.write_text(build(), encoding="utf-8")
    print(f"[report_html] wrote {out} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
