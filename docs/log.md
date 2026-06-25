# 여정 로그 (시간순 · append-only)

> 무엇을 언제 왜 했는가. 사전등록 결정은 `decisions.md`, 여기는 그 *여정*.
> 형식: `## [YYYY-MM-DD] type | 제목` (type ∈ data·finding·decision·run·lint). `grep "^## \[" docs/log.md | tail` 로 최근 이력.

## [2026-06-23] data | 데이터셋 선정 — MerRec 확정
- Olist 폐기(Kaggle 입문용으로 흔함, 차별성 없음). StockX 폐기(거래기록만, 유저 행동 시퀀스 없어 활성화/리텐션 분석 불가).
- → **MerRec**(Mercari 공식 C2C 행동로그, KDD2025): 풀퍼널 이벤트·유저·세션·시계열, 가입 필드 없음(→ t0=첫 관측, 좌측절단을 지연진입으로).

## [2026-06-24] run | 합성 fixture 데모 + 코드 정리
- 합성 데이터로 전 파이프라인 + ground-truth 복원 검증 통과(`make test`).
- 데드 코드 제거(`gap_override` 미사용 파라미터·`docs_dir`·`sigmoid`·미사용 config 키), `survival.oot_validation`을 impact 리포트에 배선(데드→활성).

## [2026-06-24] data | 실 MerRec 전환 (HuggingFace)
- `mercari-us/merrec` `20230501/` parquet 5개(~352MB) 다운로드, `data.source: merrec`.
- **스키마 교정:** 이벤트 타입 문자열이 `event_id` 컬럼에 있음(`name`=상품명). `event_col_candidates`를 `[event_id, ...]`로 수정(`name` 제거 — 오매핑 버그 방지).
- **Phase-0 GATE PASS:** 이벤트 277만, 유저 43,311, 30일 스팬, 전환자 1,923(4.4%), 절단 후 유지 33,671.

## [2026-06-24] finding | ⚠️ 구매 즉시성 — 첫 구매는 리텐션 타깃이 아님
- 누수 안전 설계(`W=3,G=2,H=14`)로 실데이터를 돌리니 SHAP 전부 0, gap-sweep/OOT PR-AUC ≈ base rate, g-formula Δ≈0, g-vs-IPTW 1498% 발산.
- **진단(코드 버그 아님, 데이터 성질):** 전환자 전환시점 중앙값 = t0로부터 **0일**. 전환의 **80%(1198/1506)가 피처 창 안**에서 발생. 누수 안전 설계가 이 당일 전환을 정당하게 제외 → 모델 가능한 결과 창엔 **전환 214건만** 남음.
- 단, 카트는 **유저 단위 연관 lift ~3x**(인과 보정 시 소멸 = 허영지표 경계 스토리).

## [2026-06-24] finding | 리텐션(재방문) 신호 검증 — 풍부함
- 결과 창 내 **재방문율 49%(16,527 유저)** vs 첫 구매 0.6% → 모델 신호 ~80배.
- `aha_cart` → 재방문 lift **1.21**(58% vs 48%). n_view 3분위 재방문 **12.6%→41%→65%**(깔끔한 단조 용량-반응).

## [2026-06-24] decision | 주력 결과를 리텐션으로 승격 (승인·완료)
- 즉시성 때문에 첫 구매는 다일 타깃 부적합. 재방문 리텐션은 신호 풍부 + 프로젝트 정체성("활성화→**리텐션**")과 일치.
- **사후 낚시 아님:** `decisions.md` D-1에 리텐션은 이미 *보조 결과*로 사전등록됨 → 보조를 주력으로 승격(`decisions.md` A-1 amendment).
- 구현(ponytail 최소 diff): 경쟁위험 스파인·정수 코드·추정기 전부 재사용, 관심 이벤트만 `CONVERT`→`RETAIN`(첫 재방문). 합성 백스톱은 리텐션에 인과효과 심도록 갱신(테스트 통과).

## [2026-06-24] run | 클린업 (ponytail audit + karpathy wiki 패턴)
- karpathy "LLM Wiki" 패턴에서 경량 3개만 채택: `CLAUDE.md`(규약 스키마), `docs/log.md`(여정 로그), `docs/index.md`(카탈로그). 위키 전체/Obsidian/qmd 등은 무관으로 기각.
- ponytail audit: 코드 이미 린 → `t_last`/`n_events` 미사용 컬럼, `fig_cif*`의 미사용 `cfg` 파라미터만 축소. 전면 재작성은 ponytail 규칙(재사용·YAGNI) 위반이라 안 함.

## [2026-06-24] finding | 리텐션 인과 결과 (실 MerRec) — 카트는 레버 아닌 마커
- naive Δ=**+0.151**(카트 재방문 47.7% vs 32.7%) → g-formula Δ=**−0.012**, IPTW=+0.027, **326% 발산**(불일치 프로토콜 발동). RR 0.97, **E-value 1.23**.
- **카트의 큰 연관이 인과 보정에서 ~0으로 붕괴 = 허영지표.** 진짜 드라이버(SHAP)=인게이지먼트 폭(n_session·active_days·n_view).
- 방법론 검증 작동: retain-hazard 시간외 PR-AUC=**0.184**(base 0.080), gap sweep PR-AUC ~0.19 plateau. `make all` 전 산출물 재생성, ground-truth 테스트 통과.

## [2026-06-24] run | 채용용 STAR 1-pager 추가 (onepager.html)
- 그로스 DS 직무 포트폴리오 모범사례(케이스 스터디 구조·`[기법]+[지표]+[결과]` 공식·역량/JD 키워드 매핑·60초 스킴) 리서치 후,
  기존 두 리포트(`report.html` 방법론·`strategy_report` 실행전략)와 겹치지 않는 **채용담당자 대면 1-pager**를 신규 추가.
- 구성: Hero → TL;DR(+지표 4) → **STAR 서사** → **역량 매트릭스(직무·면접 키워드 매핑)** → 핵심 그림 2장
  → 다음 실행(A/B 설계) → 정직성·한계 → 푸터(3종 리포트·데이터 출처).
- 생성기 `src/onepager_html.py`(고정 실데이터 수치·figures base64 임베딩, 자족 HTML) + `make onepager`. 헤드리스 렌더 확인.

## [2026-06-25] finding | 2막 견고성 실측 (v2 윈도우 W=7) — 카트 처치는 positivity 경계·DIVERGE
- 검증 스크립트(`verify_act2.py`/`verify_act2b.py`): v1 `src/`(personperiod·survival·impact) 그대로 재사용, 윈도우만 v2 PLAN §6(W=7·G=2·H=14)로 오버라이드. 코드 수정 불요 — X=cart 레버는 이미 `aha_cart`로 박혀 그대로 돌아감.
- **코호트 재현 정확**: eligible 18,017 / 처치(cart in 7d) 2,185 / 대조 15,832 (1:7.2) / 재방문 Y=1 6,384. 표본 충분(v1 첫구매 214 문제 아님).
- **Positivity 경계선**: 표준화·정규화 PS 모델에서도 e_max=1.0(near-deterministic treatment). 미클립 IPTW 최대가중 ~6,000, ESS≈44/18,017. 다만 e<0.05 = 0%, 공통지지 밖 0.64%. → 극단은 **near-1 꼬리**(고활동 유저가 카트 거의 확정)이지 near-0 아님. 클립(config 0.99)이 이 꼬리를 가려 max_w 3.4로 보이게 함.
- **균형 나쁨**: 전 교란변수 SMD_raw 0.37~0.78(모두 >0.1 기준 초과). 활동량(n_session·active_days·n_view)이 카트와 강결합 → 카트는 활동량 마커.
- **효과 3종 발산**: naive Δ=+0.206 → IPTW Δ=+0.013(clip 0.99) → g-comp Δ=**−0.035**. 보정이 +20pp를 0 근처로 무너뜨림. IPTW Δ는 클립에 민감(0.90→+0.067, 0.99→+0.013, 1.0→−0.076) = positivity 불안정 신호. E-value: naive RR 1.62→2.63, g-comp RR 0.90→1.45.
- **판정**: 2막 인과추정은 **견고하지 않다**. v1(W=3) null과 동형 — 보정하면 카트→리텐션 신호 붕괴. v2 W=7에서는 진단이 NULL이 아니라 **DIVERGE**(g-comp −3.5pp vs IPTW +1.3pp, abs-diff 4.7pp>band 3pp)로 떨어지며, 이는 positivity near-1 꼬리에서 IPTW가 클립에 휘둘린 결과. 1:7 불균형 자체보다 **고활동 유저의 처치 near-결정성(positivity 경계)**이 주범. 결론: 카트는 인과 레버 아님(활동량 마커) — v2 PLAN의 "프록시 vs 북극성 간극(Goodhart)" 서사와 R2(positivity 약화 시 연관+E-value로 강등) 폴백이 실측으로 정당화됨.

## [2026-06-25] finding | 1막 추천 베이스라인 실측
**임무**: MerRec v2 1막 추천의 실측 성능(POP / Markov-1)을 내고, item_id 추천이 가능한지 판정.
**셋업**: 데이터 `data/raw/2023*.parquet`(2.77M행, 2023-05-01~31). 분할=세션 시작일 기준 train day0–23(2.24M행)/test day27–30(0.27M행). 길이≥2 test 세션, **leave-last-out**(prev=마지막직전, target=마지막). test 페어 최대 2만 랜덤샘플(seed=42). 코드 `version2/eval_baselines.py`(런타임 18s). item_id는 정답+랜덤199 네거티브 sampled 평가(풀랭킹 불가), product_id·c1_id는 full-catalog.

**표 (Recall@20 / NDCG@20 / MRR, n=20,000 페어)**
| 타깃단위(카탈로그) | 모델 | R@20 | NDCG@20 | MRR |
|---|---|---|---|---|
| product_id=brand_c2 (163,302) | POP | 0.1031 | 0.0436 | 0.0309 |
| product_id | **Markov-1+POP백오프** | **0.4698** | 0.3251 | 0.2835 |
| c1_id (297) | POP | 0.5903 | 0.2426 | 0.1555 |
| c1_id | **Markov-1** | **0.8536** | 0.6695 | 0.6184 |
| item_id (1,491,188; sampled 199neg) | POP | 0.0809 | 0.0338 | 0.0279 |
| item_id (sampled) | Markov-1 | 0.0839 | 0.0420 | 0.0374 |

**콜드/웜 (product_id, Markov)**: warm(타깃이 train존재, n=19,078) R@20=**0.4925** / cold(n=922) R@20=**0.0000**. → product_id 성능은 전적으로 warm이 견인. cold 타깃은 0. (leave-last-out 특성상 같은 세션 내 직전·마지막이 같은 product를 자주 공유해 warm 비율이 95%로 부풀려진 점 유의.)

**next-action(event_id 5+1종, n=33,153)**: 다수결(=item_view, 80.3% 점유) acc=**0.803**/macro-F1=**0.148**; Markov-1 acc=**0.808**/macro-F1=**0.296**. → acc는 클래스불균형으로 거의 무의미(항상 view 찍으면 80%), macro-F1로 보면 0.15~0.30 수준.

**판정 (숫자로 단정)**:
1. **item_id 추천은 불가능하다.** 1.49M 카탈로그, 73% 1회성 아이템. sampled-199neg(=200풀, 랜덤 R@20 기준선 0.10)에서 Markov R@20=**0.084 < 0.10(랜덤)**, POP=0.081. 즉 *200개 중에서 고르는 쉬운 셋업에서도 랜덤 이하*. full-catalog(1.49M)라면 사실상 0. → C2C 콜드스타트로 item-level 추천 헤드라인은 **방어 불가**.
2. **product_id(brand_c2)를 추천 헤드라인으로 단독 방어하는 것도 약하다.** R@20=0.47은 괜찮아 보이나 전부 warm(0.49)·직전세션 관성에서 나오고 cold=0.00, POP대비 게인의 상당부분이 "직전과 같은 brand_c2 반복"이다(진정한 추천이라기보다 세션 내 연속성). 163K 카탈로그에서 cold 타깃을 못 잡음.
3. **c1_id(카테고리, 297종)는 실측이 견고하다.** Markov R@20=0.85, MRR=0.62. 작은 출력공간 + 강한 세션 내 카테고리 일관성.

**결론/리프레이밍**: 1막을 "item_id 개인화 추천"으로 내세우면 숫자가 무너진다(랜덤 이하). 대신 **(a) 카테고리/brand_c2 다음행동 예측(c1 R@20=0.85, product warm R@20=0.49)을 헤드라인으로**, **(b) item-level은 명시적으로 "C2C 콜드스타트(73% 1회성·웜셋 18.9%) 연구 문제"로 리프레이밍**하는 것이 정직하다. POP→Markov 게인(product 0.10→0.47, c1 0.59→0.85)은 "세션 직전 신호가 인기보다 강하다"는 살아있는 발견 — 이게 1막의 실측 자산.
