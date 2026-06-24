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
