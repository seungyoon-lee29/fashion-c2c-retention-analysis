"""Build the legacy self-contained portfolio case-study page.

Curated presentation layer. Headline numbers are the locked real-MerRec results
(docs/impact_report.md, docs/eda_findings.md, docs/drivers_report.md). Figures are
base64-embedded so the file is shareable on its own. Written for a non-specialist:
every causal-inference term is glossed inline and in the glossary.
Run: `python src/report_html.py`  (or `make report`). The current public
portfolio path is README.md -> onepager.html -> docs/portfolio_report.md.
"""
from __future__ import annotations

import base64

from _util import ROOT

REPO = "https://github.com/seungyoon-lee29/fashion-c2c-retention-analysis"
HF = "https://huggingface.co/datasets/mercari-us/merrec"

STATS = [
    ("2,771,473", "행동 이벤트"),
    ("43,311", "유저"),
    ("30일", "관측 기간"),
    ("49%", "결과창 내 재방문율"),
    ("≈0", "카트의 인과 효과 (E-value 1.23)"),
]

PIPELINE = [
    ("①", "원천 데이터", "MerRec 행동 로그 (조회·찜·카트·제안·구매)"),
    ("②", "코호트·시간축", "t0=첫 관측, 좌측절단을 지연진입으로 보정"),
    ("③", "person-period", "유저×스텝 표 — 한 줄=한 시점"),
    ("④", "경쟁위험 생존 스파인", "재방문 vs 이탈을 함께 모델링"),
    ("⑤", "드라이버·누수통제", "SHAP 중요도 + embargo gap sweep"),
    ("⑥", "인과 임팩트", "g-formula × IPTW × E-value (삼각검증)"),
    ("⑦", "검증·결론", "시간외(OOT) 검증 + 정직한 보고"),
]

DIFF = [
    ("정직한 null", "효과 없음을 숨기지 않고 <i>증명</i>한다. '연관은 크다(+15%p)'는 함정을 보여준 뒤 인과 보정으로 무너뜨린다."),
    ("누수(leakage) 통제", "초기행동→결과 사이 블랙아웃 구간(embargo)을 두고, 그 폭을 0~7일로 바꿔도 성능이 평평함을 보여 부정 누수가 아님을 입증."),
    ("삼각검증 + 불일치 프로토콜", "g-formula와 IPTW 두 방식으로 같은 효과를 추정. 효과가 0 근처일 때 상대차가 폭주하는 함정을 <b>절대차 가드</b>로 차단."),
    ("사전등록 (pre-registration)", "결과를 보기 <i>전에</i> 분석 결정을 문서에 잠가둠. 목표를 리텐션으로 바꾼 것도 원래 적어둔 보조 목표의 승격(사후 끼워맞춤 아님)."),
    ("정확성 백스톱", "일부러 효과를 심은 가짜 데이터에서 같은 코드가 그 효과를 정확히 복원함을 자동 테스트로 보증 — '효과 없음'이 버그가 아님을 증명."),
]

STACK = [
    ("언어·분석", "Python · pandas · numpy · scipy"),
    ("모델", "scikit-learn (HistGradientBoosting·LogisticRegression) · SHAP"),
    ("시각화", "matplotlib"),
    ("데이터", "HuggingFace MerRec parquet (config로 synthetic ↔ 실데이터 토글)"),
    ("재현", "make setup · make test · make all · make report"),
]

FIGS = [
    ("cif_competing_risks.png",
     "<b>경쟁위험 CIF.</b> 시간이 지날수록 <b>재방문(초록)</b>과 <b>이탈(빨강)</b>이 누적되는 비율. 둘을 경쟁관계로 함께 모델링한다."),
    ("cif_by_aha.png",
     "<b>활성화별 재방문 곡선.</b> 카트한 유저(초록)가 안 한 유저(회색)보다 높아 <i>보인다</i> — 단 이건 <b>보정 전(연관)</b> 그림이다."),
    ("drivers_importance.png",
     "<b>재방문 드라이버(SHAP).</b> 세션수·활동일수 같은 <b>폭넓은 활동</b>이 상위, <b>카트(aha_cart)는 거의 0</b>."),
    ("gap_sweep.png",
     "<b>누수 통제.</b> 미래 차단 구간(embargo)을 늘려도 성능이 평평하게 유지됨 = 부정 누수가 아니라 <b>진짜 신호</b>."),
    ("impact_estimators.png",
     "<b>임팩트 비교.</b> 왼쪽(보정 전)은 높지만 교란을 보정하면(가운데·오른쪽) <b>0 근처로 주저앉음</b> = 효과는 대부분 교란이었다."),
    ("markov_per1000.png",
     "<b>Markov 근사.</b> 단순 근사로 본 1,000명당 기대 재방문 수(참고용, 헤드라인 아님)."),
]

GLOSSARY = [
    ("리텐션 (retention)", "유저가 떠나지 않고 다시 돌아와 활동하는 것. 이 분석의 목표 지표."),
    ("활성화 레버 (activation lever)", "올리면 리텐션이 오를 것으로 기대하는 초기 행동. 여기선 '초기 장바구니 담기'."),
    ("연관 vs 인과", "연관=같이 움직인다. 인과=하나가 다른 하나를 <i>일으킨다</i>. 연관이 커도 인과는 0일 수 있다(이 분석의 핵심)."),
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
    ("누수 / embargo", "미래 정보가 몰래 섞여 성능이 부풀려지는 것(누수). 일정 구간을 블랙아웃(embargo)해 차단."),
    ("CIF (누적발생)", "시간이 지나며 결말(재방문)이 누적으로 일어난 비율 곡선."),
    ("OOT (시간외 검증)", "과거로 학습해 미래를 맞히는지 검증 — 과적합·누수 방어의 핵심."),
    ("SHAP", "각 변수가 모델 예측에 얼마나 기여했는지 측정하는 방법."),
    ("person-period", "유저×시점으로 펼친 표. 한 줄이 '유저 u의 시점 t'이며, 그 시점에 재방문/이탈/지속을 기록."),
    ("pp / %p (퍼센트포인트)", "비율의 차이 단위. 47%→32%는 15%p 차이."),
]

CSS = r"""
:root{--ink:#16181d;--mut:#5b6370;--line:#e6e8ec;--acc:#16a34a;--bad:#dc2626;
--blu:#2563eb;--bg:#f7f8fa;--card:#fff;--ink2:#2b2f36}
*{box-sizing:border-box}
body{font:16px/1.7 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,'Noto Sans KR',sans-serif;
color:var(--ink);background:var(--bg);margin:0}
.hero{background:linear-gradient(135deg,#0f172a,#1e3a5f);color:#fff;padding:54px 20px 46px}
.hero .wrap{max-width:900px;margin:0 auto}
.eyebrow{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:#9ec5fe;font-weight:700;margin:0 0 12px}
.hero h1{font-size:34px;line-height:1.22;margin:0 0 12px;font-weight:800}
.hero .lead{font-size:18px;color:#cdd6e4;margin:0 0 18px;max-width:680px}
.byline{font-size:13.5px;color:#93a4bd}
.byline a{color:#9ec5fe;text-decoration:none}
main{max-width:900px;margin:0 auto;padding:8px 20px 80px}
section{margin:40px 0}
h2{font-size:22px;margin:0 0 14px;padding-bottom:8px;border-bottom:2px solid var(--line)}
h3{font-size:16px;margin:18px 0 6px}
p{margin:10px 0}
a{color:var(--blu)}
.statstrip{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;
margin:-28px auto 0;max-width:900px;position:relative;padding:0 20px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 14px;
box-shadow:0 4px 14px rgba(15,23,42,.06)}
.stat .v{font-size:24px;font-weight:800;color:var(--ink)}
.stat .l{font-size:12.5px;color:var(--mut);margin-top:3px;line-height:1.4}
.easy{background:#eff6ff;border:1px solid #bfdbfe;border-left:4px solid var(--blu);border-radius:10px;padding:16px 20px;margin:18px 0}
.easy .tag{display:inline-block;font-size:12px;font-weight:800;color:#1e40af;background:#dbeafe;border-radius:20px;padding:3px 11px;margin-bottom:8px}
.easy b{color:#1e40af}
.src{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 20px}
.src table{width:100%;border-collapse:collapse}
.src td{padding:7px 6px;border-bottom:1px solid var(--line);vertical-align:top;font-size:14.5px}
.src td:first-child{color:var(--mut);width:120px;font-weight:600}
.src tr:last-child td{border-bottom:none}
.lic{display:inline-block;font-size:12px;font-weight:700;color:#7c2d12;background:#ffedd5;border-radius:6px;padding:2px 8px}
.flow{display:flex;flex-wrap:wrap;gap:8px;align-items:stretch;margin:14px 0}
.step{flex:1 1 180px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;position:relative}
.step .n{font-weight:800;color:var(--blu);font-size:14px}
.step .t{font-weight:700;font-size:14.5px;margin:2px 0}
.step .d{font-size:12.5px;color:var(--mut);line-height:1.45}
table.data{width:100%;border-collapse:collapse;margin:14px 0;background:var(--card)}
table.data th,table.data td{padding:10px 12px;border:1px solid var(--line);text-align:left;vertical-align:top}
table.data th{background:#f1f3f6;font-weight:700}
.pos{color:var(--acc);font-weight:700}.neg{color:var(--bad);font-weight:700}
.callout{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--acc);border-radius:10px;padding:14px 18px;margin:16px 0}
.callout.warn{border-left-color:var(--bad)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin:14px 0}
.cardx{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.cardx b{display:block;margin-bottom:4px}
.cardx span{font-size:14px;color:var(--ink2)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:16px;margin:16px 0}
figure{margin:0;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}
figure img{width:100%;height:auto;border-radius:5px;border:1px solid var(--line)}
figcaption{color:#3a3f47;font-size:13px;margin-top:9px;line-height:1.55}
dl{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:6px 20px;columns:1}
dt{font-weight:700;margin-top:15px;font-size:15px}
dd{margin:3px 0 0;color:#333;font-size:14.5px}
ul{margin:10px 0;padding-left:22px}li{margin:5px 0}
code{background:#eef0f3;padding:1px 6px;border-radius:5px;font-size:13.5px}
.foot{color:var(--mut);font-size:13px;margin-top:48px;border-top:1px solid var(--line);padding-top:16px;line-height:1.6}
@media(min-width:760px){dl{columns:2;column-gap:34px}dt:first-child{margin-top:8px}}
"""


def _img(name: str) -> str:
    p = ROOT / "docs" / "figures" / name
    return f"data:image/png;base64,{base64.b64encode(p.read_bytes()).decode()}"


def build() -> str:
    stats = "".join(f'<div class="stat"><div class="v">{v}</div><div class="l">{l}</div></div>' for v, l in STATS)
    flow = "".join(f'<div class="step"><div class="n">{n}</div><div class="t">{t}</div><div class="d">{d}</div></div>'
                   for n, t, d in PIPELINE)
    diff = "".join(f'<div class="cardx"><b>{t}</b><span>{d}</span></div>' for t, d in DIFF)
    stack = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in STACK)
    figs = "".join(f'<figure><img src="{_img(n)}" alt=""><figcaption>{c}</figcaption></figure>' for n, c in FIGS)
    gloss = "".join(f"<dt>{t}</dt><dd>{d}</dd>" for t, d in GLOSSARY)

    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>활성화 → 리텐션: 무엇이 신규 유저를 돌아오게 하는가 (그로스 DS 케이스 스터디)</title>
<style>{CSS}</style></head>
<body>

<header class="hero"><div class="wrap">
<p class="eyebrow">그로스 데이터사이언스 포트폴리오 · 인과추론 × 생존분석</p>
<h1>활성화 → 리텐션: 무엇이 신규 유저를 돌아오게 하는가</h1>
<p class="lead">Mercari(미국 중고거래 앱)의 실제 행동 로그로, "어떤 초기 행동을 유도하면 유저가 다시 돌아오나(리텐션)"를
<b>인과적으로 정직하게</b> 따져본 분석. 어려운 통계를 헤드라인이 아니라 <i>정밀한 측정 도구</i>로 쓴다.</p>
<p class="byline">분석·구현 <a href="{REPO}">seungyoon-lee29</a> · 2026-06 · 데이터 <a href="{HF}">MerRec (Mercari)</a></p>
</div></header>
<div class="statstrip">{stats}</div>

<main>

<section>
<div class="easy">
<span class="tag">💡 30초 요약 — 쉽게 말하면</span>
<p style="margin:4px 0"><b>질문.</b> 신규 유저가 앱에 <b>다시 돌아오게(리텐션)</b> 하려면 처음에 무슨 행동을
유도해야 할까? 특히 "상품을 장바구니에 담게" 하면 효과가 있을까?</p>
<p style="margin:4px 0"><b>답.</b> 장바구니를 담은 유저가 더 많이 돌아오긴 한다(<b>+15%p</b>). 하지만 그건
<b>원래 적극적인 유저라서</b>지 장바구니 행동 자체의 힘이 아니다. 적극성의 영향을 통계로 걷어내자 효과는
<b>거의 0으로 사라졌다</b>(g-formula −1.2%p, IPTW +2.7%p, E-value 1.23).</p>
<p style="margin:4px 0"><b>그래서.</b> "장바구니를 유도하자"는 리텐션 전략은 <b>인과적 근거가 없다</b> — 좋아 보이지만
성과를 못 움직이는 <b>허영지표</b>의 전형. 이걸 <i>정직하게 증명</i>하고, 진짜 드라이버(폭넓은 초기 활동)를 가려낸 것이 이 분석의 핵심이다.</p>
</div>
</section>

<section>
<h2>데이터 출처</h2>
<div class="src"><table>
<tr><td>데이터셋</td><td><b>MerRec</b> — Mercari 공식 C2C(개인 간 거래) 행동 이벤트 로그. 조회·찜·장바구니·가격제안·구매의 풀퍼널 + 유저·세션·시계열.</td></tr>
<tr><td>제공</td><td>Mercari, Inc. (HuggingFace <code>mercari-us/merrec</code>), KDD 2025 공개. <a href="{HF}">{HF}</a></td></tr>
<tr><td>라이선스</td><td><span class="lic">CC BY-NC 4.0</span> 비상업·저작자표시. 본 페이지는 <b>교육·포트폴리오(비상업)</b> 목적의 분석 결과물이다.</td></tr>
<tr><td>사용 범위</td><td>날짜 파티션 <code>20230501</code>의 parquet 5개(~352MB) → <b>277만 이벤트 · 43,311 유저 · 30일</b>.</td></tr>
<tr><td>특이점</td><td>가입(회원가입) 필드가 <b>없음</b> → 각 유저의 '첫 관측'을 기준점으로 삼고 그로 인한 편향을 생존분석으로 보정.</td></tr>
</table></div>
</section>

<section>
<h2>이 분석이 푸는 문제</h2>
<p>신규(처음 관측된) 유저의 <b>초기 행동 → 리텐션(재방문)</b> 관계를 찾고, 그 행동을 올리면 회사가 실제로 얼마나
나아지는지를 <b>인과적으로</b> 추정한다. 핵심은 "같이 움직인다(<i>연관</i>)"가 아니라 "정말 <i>원인</i>인가(<i>인과</i>)"를
구분하는 것 — 그로스 지표에서 둘은 자주 다르고, 그 차이가 잘못된 전략을 만든다.</p>
</section>

<section>
<h2>첫 번째 큰 발견 — 목표를 바꾸다</h2>
<div class="callout warn">
<b>MerRec에선 구매가 '첫날 즉시' 일어난다.</b> 전환(구매)의 80%가 유저의 관측 첫 구간 안에서 발생한다(중앙값 0일).
즉 첫 구매는 '리텐션'이 아니라 <i>일회성 획득</i>이며, 누수를 막은 결과창에는 모델링할 구매가 거의 안 남는다(≈214건).
→ 그래서 분석 목표를 <b>"구매"가 아니라 "재방문(리텐션)"</b>으로 재정의했다. 이는 결과를 보고 끼워맞춘 게 아니라,
계획서에 <i>보조 목표</i>로 미리 적어둔 항목을 주력으로 올린 것이다(사전등록 원칙).</div>
</section>

<section>
<h2>분석 파이프라인</h2>
<div class="flow">{flow}</div>
<h3>방법 요약</h3>
<ul>
<li><b>재방문을 시간 흐름으로 모델링</b> — "언제 돌아오나 / 언제 이탈하나"를 함께 보는 <i>이산시간 경쟁위험 생존분석</i>.</li>
<li><b>부정 누수 차단</b> — 초기행동과 결과 사이에 블랙아웃 구간(<i>embargo</i>)을 두고, 그 폭을 바꿔도 성능이 평평함을 확인.</li>
<li><b>진짜 원인 가려내기</b> — 단순 비교(naive)에 더해 교란을 보정하는 <b>g-computation</b>과 이를 교차검증하는 <b>IPTW</b>로
같은 효과를 두 방식으로 추정하고, 가정 민감도는 <b>E-value</b>로 봉투.</li>
</ul>
</section>

<section>
<h2>핵심 결과 — "장바구니 → 재방문"의 진짜 효과</h2>
<table class="data">
<tr><th>추정 방식</th><th>재방문 효과 (Δ)</th><th>뜻</th></tr>
<tr><td>naive — 단순 비교</td><td class="pos">+15.1%p</td><td>카트한 유저 재방문 47.7% vs 안 한 유저 32.7%. <b>커 보이지만 교란 포함.</b></td></tr>
<tr><td><b>g-formula — 교란 보정(주력)</b></td><td class="neg">−1.2%p</td><td>적극성을 걷어내자 <b>효과 소멸</b>(재방문 33.9% vs 35.1%).</td></tr>
<tr><td>IPTW — 다른 방식 교차검증</td><td>+2.7%p</td><td>역시 0 근처. g-formula와 3.9%p 차이(부호만 반대).</td></tr>
</table>
<div class="easy">
<span class="tag">💡 이 표 읽는 법</span>
<p style="margin:4px 0">맨 윗줄(<b>+15%p</b>)이 "장바구니 = 리텐션"처럼 보이게 만드는 함정이다. 두 인과 추정법으로 적극성을
보정하면 둘 다 <b>0의 ±3%p 안</b>으로 내려앉는다 → <b>효과는 사실상 없음(null)</b>, 방향조차 단정 불가.
<b>E-value=1.23</b>(1에 가까움)도 "강건한 효과 아님"을 뒷받침한다.</p>
</div>
</section>

<section>
<h2>"효과 없음"이 무능이 아니라는 증거</h2>
<p>모델이 못 맞혀서 0이 나온 게 아니라 <i>실제로 효과가 없어서</i>임을 보이는 검증들:</p>
<ul>
<li><b>미래 예측 검증(OOT)</b>: 과거 유저로 학습해 미래 유저의 재방문을 맞히는 정확도(PR-AUC) <b>0.184</b> — 기준선(0.080)의
<b>2.3배</b>(ROC-AUC 0.658). 재방문 자체는 분명히 <b>예측 가능</b>하다.</li>
<li><b>진짜 드라이버는 따로</b>: 재방문을 끌어올리는 건 <b>폭넓은 초기 활동</b>(여러 세션·여러 날 방문·많은 조회)이지 장바구니가 아니다.</li>
<li><b>누수 통제</b>: embargo 폭을 0→7일로 바꿔도 성능이 ~0.19로 평평 = 부풀려진 신호가 아니다.</li>
<li><b>정확성 자가검증</b>: <i>일부러 효과를 심은</i> 가짜 데이터에선 같은 코드가 그 효과를 정확히 복원한다 → 도구는 멀쩡하다.</li>
</ul>
</section>

<section>
<h2>결과 시각화</h2>
<div class="grid">{figs}</div>
</section>

<section>
<h2>비즈니스 함의</h2>
<ul>
<li><b>하지 말 것:</b> "첫 장바구니 유도"를 리텐션 레버로 미는 것 — 인과 근거가 없다(허영지표). 카트 넛지는 <i>즉시 구매(획득)</i>엔
의미 있을 수 있으나 리텐션 효과로 보고하면 Goodhart 함정.</li>
<li><b>할 것:</b> 리텐션을 원하면 <b>초기 인게이지먼트 폭</b>(여러 세션·여러 카테고리 탐색)을 키우는 온보딩에 투자 — 단 이것도 아직 <i>연관</i> 우위라 A/B로 인과 확인 필요.</li>
<li><b>보고:</b> 효과가 식별되지 않으므로 '신규 1,000명당 기대 재방문' 같은 임팩트 원장은 과장 없이 <b>생략</b>했다.</li>
</ul>
</section>

<section>
<h2>이 분석을 신뢰할 수 있는 이유</h2>
<div class="cards">{diff}</div>
</section>

<section>
<h2>한계 (정직하게)</h2>
<ul>
<li>여기서 '리텐션'은 <b>재방문(행동)</b>이지 <b>재구매(매출)</b>가 아니다 — 매출 효과는 후속 과제.</li>
<li>인과 추정은 검증 불가능한 가정(순차적 교환가능성·positivity·consistency)에 의존 → 단정하지 않고 <b>E-value로 강건성을 봉투</b>.</li>
<li>MerRec엔 A/B 테스트가 없다 → 모든 인과 결론은 <i>조건부</i>이며, "A/B로 확인할 가설"을 제공하는 단계다.</li>
<li>관측 30일 → 장기 churn은 미관측. 단기 리텐션에 한정된 결론.</li>
</ul>
</section>

<section>
<h2>기술 스택 & 재현</h2>
<div class="src"><table>{stack}</table></div>
<p class="note" style="font-size:13.5px;color:var(--mut)">전체 코드·문서·재현 절차: <a href="{REPO}">{REPO}</a> ·
<code>make test</code>(네트워크 없이 정확성 검증) → <code>make all</code>(실데이터 파이프라인) → <code>make report</code>(이 페이지).</p>
</section>

<section>
<h2>용어 풀이</h2>
<dl>{gloss}</dl>
</section>

<p class="foot">
<b>출처.</b> 데이터: MerRec © Mercari, Inc. — HuggingFace <a href="{HF}">mercari-us/merrec</a>, CC BY-NC 4.0 (비상업). KDD 2025.<br>
본 페이지는 해당 데이터를 이용한 <b>비상업 교육·포트폴리오</b> 분석 결과물이며, 모든 수치·그림은 저장소의
<code>make all</code>/<code>make report</code>로 재현된다. 설계 <code>PLAN.md</code> · 사전등록 <code>docs/decisions.md</code> ·
여정 <code>docs/project_history.md</code> · 원본 로그 <code>docs/archive/build_log.md</code> · 한계 <code>docs/limitations.md</code>. 저장소: <a href="{REPO}">{REPO}</a>
</p>

</main></body></html>
"""


def main() -> int:
    out = ROOT / "docs" / "archive" / "report_legacy.html"
    out.write_text(build(), encoding="utf-8")
    print(f"[report_html] wrote {out} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
