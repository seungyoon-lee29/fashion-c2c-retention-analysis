# 문서 인덱스

## 먼저 읽기

| 순서 | 문서 | 내용 |
|---:|---|---|
| 1 | [`../README.md`](../README.md) | 프로젝트 요약, 작성자/연락 링크, 읽는 순서 |
| 2 | [`../onepager.html`](../onepager.html) | 채용담당자용 60초 요약 |
| 3 | [`portfolio_report.md`](portfolio_report.md) | 공개용 메인 분석 리포트 |

## 근거 리포트

| 문서 | 생성 | 내용 |
|---|---|---|
| [`data_quality_report.md`](data_quality_report.md) | `make data-quality` | DuckDB SQL 데이터 품질 감사 |
| [`funnel_report.md`](funnel_report.md) | `make funnel` | 퍼널 도달률과 최대 유출 |
| [`cohort_report.md`](cohort_report.md) | `make cohort` | D1/D3/D7 재방문과 첫날 경험 폭 |
| [`drivers_report.md`](drivers_report.md) | `make drivers` 또는 `make all` | 드라이버 중요도와 gap sweep |
| [`impact_report.md`](impact_report.md) | `make impact` 또는 `make all` | g-formula, IPTW, E-value, Markov 진단 |
| [`causal_report.md`](causal_report.md) | `make causal` | 4개 후보 레버의 overlap과 보정 진단 |
| [`ab_test_design.md`](ab_test_design.md) | `make abtest` | 첫날 탐색 폭 넛지 A/B 설계 |

## 부록

| 문서 | 내용 |
|---|---|
| [`limitations.md`](limitations.md) | 한계와 분석 범위 |
| [`metrics_glossary.md`](metrics_glossary.md) | KPI 정의와 단위 |
| [`decisions.md`](decisions.md) | 사전등록 결정 |
| [`project_history.md`](project_history.md) | 공개용 짧은 진행 기록 |
| [`methods_appendix.md`](methods_appendix.md) | 기술 면접용 방법론 깊이 |

> 생성 문서는 `make all`이 재생성하므로 수기 편집하지 않는다. 공개 첫 동선은 `README.md`, `onepager.html`, `docs/portfolio_report.md`다.
