# 패션 C2C 신규 유저 리텐션 분석

**카트 최적화가 아니라 첫날 탐색 폭 A/B로 의사결정을 바꾼 분석 사례.**  
Mercari 행동 로그로 퍼널, 코호트, 식별 진단, 실험 설계까지 연결했다.

## Executive Summary

- 구매완료율은 **4.4%**로 낮았다. 신규 유저 경험의 성공지표를 구매가 아니라 **D7 재방문**으로 재정의했다.
- 첫날 활동 폭은 D7 재방문과 **+27pp** 연관됐다. 다만 관측 데이터만으로 인과효과를 확정하지 않았다.
- 카트는 리텐션 레버처럼 보였지만, 보정 후 효과가 0 근처로 약해졌다. 레버라기보다 행동 강도의 표식에 가깝다.
- 최종 제안은 **첫날 탐색 폭 넛지 A/B**다. 주지표 D7 재방문, MDE 2.0pp, 표본 **9,805명/arm**, 예상 기간 약 **4.7주**다.

## 1. 문제 설정

분석 질문은 다음 하나로 고정했다.

> 신규 유저가 다시 돌아오게 하려면 첫날 어떤 경험을 넓혀야 하는가?

MerRec에는 가입 시점이 없다. 따라서 `t0`를 첫 관측 이벤트로 두고, 데이터 시작일 유저는 기존 유저가 섞였을 가능성이 있어 신규 코호트 분석에서 제외했다.

## 2. 데이터 품질 확인

`make data-quality`로 `data/events.parquet`를 DuckDB SQL로 직접 검증했다.

| Check | Result |
|---|---|
| Required fields | `user_id`, `stime`, `session_id`, `event` null 없음 |
| Event vocabulary | config의 6개 이벤트 외 값 없음 |
| Price | 음수/0원 없음, median 25.0, p99 640.4 |
| Timestamp | 2023-05-01 ~ 2023-05-31 |
| Known warnings | 반복 로그 키 2,466건, `session_id`는 user-scoped로 해석 |

판정은 **PASS**다. 경고는 원천 데이터의 해석 이슈이므로 `docs/data_quality_report.md`와 `docs/limitations.md`에서 별도로 관리한다.

## 3. 분석 흐름

| Step | Question | Finding | Decision |
|---|---|---|---|
| Funnel | 어디서 새는가 | view 98.7% -> buy 4.4%, 최대 유출은 조회 -> 찜 | 구매 전환보다 D7 재방문을 주지표로 둔다 |
| Cohort | 누가 돌아오는가 | 첫날 활동 Q4 D7 66.2% vs Q1 39.3% | 단일 행동보다 첫날 경험 폭을 후보로 본다 |
| Identification | 보이는 레버가 인과인가 | cart +16.0pp -> +3.2pp, cat>=3 +25.4pp -> -6.5pp | 관측 추정은 인과효과로 쓰지 않는다 |
| Experiment | 무엇을 실행할 것인가 | 관측 신호만으로 부호를 확정하기 어렵다 | 첫날 탐색 폭 넛지를 A/B로 검증한다 |

## 4. 핵심 증거

### 퍼널

구매완료는 유저 기준 **4.4%**다. 구매 전환만 주지표로 두면 작은 개선을 보기 어렵다. 최대 누수는 조회 후 찜으로 넘어가지 않는 구간이었다.

자세한 계산: [`funnel_report.md`](funnel_report.md)

### 코호트

D7 재방문은 **50.1%**다. 첫날 활동량 상위 그룹은 하위 그룹보다 D7 재방문이 **+27pp** 높았다. 이 결과는 “첫날 경험 폭”을 후보로 볼 근거이지, 곧바로 인과효과를 뜻하지 않는다.

자세한 계산: [`cohort_report.md`](cohort_report.md)

### 식별 진단

카트는 리텐션 레버처럼 보였다. 하지만 full-follow-up 유저 기준 단순 연관 **+16.0pp**가 보정 후 **+3.2pp**로 작아졌다. 탐색 폭 후보(`cat>=3`)도 단순 연관은 **+25.4pp**였지만, 같은 초기창 활동량을 조건부에 넣으면 **-6.5pp**로 바뀌었다.

`D7 50.1%`와 `retain base 40.1%`는 서로 다른 모집단/estimand다. 전자는 신규 코호트의 D7 재방문 기준선이고, 후자는 person-period full-follow-up 기반 식별 진단의 outcome base다.

자세한 계산: [`causal_report.md`](causal_report.md), [`impact_report.md`](impact_report.md)

## 5. 실험 Handoff

최종 제품 제안은 **첫날 탐색 폭 넛지 A/B**다. 조회 직후 찜 후보와 인접 카테고리 노출은 별도 실험이 아니라, 첫날 탐색 폭을 넓히는 처치 구현 예시로 묶는다.

| Item | Design |
|---|---|
| Hypothesis | 신규 유저 첫 세션에서 탐색 폭을 넓히면 D7 재방문이 오른다 |
| Treatment | 인접 카테고리와 저장 후보를 첫 세션에 노출 |
| Randomization | 유저 단위 50/50 배정 |
| Primary metric | D7 재방문율 |
| Guardrails | 구매완료율, 즉시이탈, 세션 품질, SRM |
| MDE | 2.0pp |
| Sample size | 9,805명/arm |
| Duration | 약 4.7주 |

성공/중단 판정은 `docs/ab_test_design.md`에 둔다. 핵심은 관측 로그에서 레버를 단정하지 않고, 제품 의사결정을 전향 실험으로 넘긴 점이다.

## 6. What This Shows

- 제품 KPI를 데이터 상황에 맞게 재정의했다.
- SQL 기반 원천 데이터 QA를 수행했다.
- 퍼널/코호트에서 후보를 찾고, 인과 과대해석을 방지했다.
- 관측 분석을 실행 가능한 A/B 설계로 넘겼다.
- 한계와 가정을 문서화해 면접에서 검증 가능한 형태로 만들었다.

## 7. Scope

이 분석의 리텐션은 재구매가 아니라 **재방문 행동**이다. 원천 데이터만으로 GMV/AOV 또는 장기 churn은 확인하지 않았다. 따라서 매출 효과는 D7 실험 통과 후 후속 구매/재구매 로그로 검증해야 한다.

한계와 가정: [`limitations.md`](limitations.md)
