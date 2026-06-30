# Project Plan

## Positioning

이 프로젝트는 패션 C2C 신규 관측 유저의 첫날 행동 로그를 바탕으로 **D7 재방문을 높일 제품 실험을 설계하는 Product/Growth Data Analyst 포트폴리오**다.

핵심 메시지:

> 구매완료율은 4.4%로 희소했다. 그래서 신규 유저 경험의 의사결정 KPI를 D7 재방문으로 전환했고, 카트가 아니라 첫날 탐색 폭 넛지를 A/B로 검증하는 결론에 도달했다.

## Decision Spine

| Stage | Question | Output | Decision |
|---|---|---|---|
| M0 Data QA | 분석 가능한 로그인가 | `docs/data_quality_report.md` | required fields, event vocabulary, timestamp, price checks PASS |
| M1 Funnel | 어디서 새는가 | `docs/funnel_report.md` | 구매 전환은 4.4%로 희소하므로 D7 재방문을 주지표로 둔다 |
| M1 Cohort | 누가 돌아오는가 | `docs/cohort_report.md` | 첫날 활동 폭이 강한 관측 후보지만 인과 단정은 하지 않는다 |
| M2 Identification | 보이는 레버가 인과인가 | `docs/causal_report.md`, `docs/impact_report.md` | 카트/탐색폭의 관측 신호는 보정 후 불안정하므로 제품 의사결정에는 부족하다 |
| M3 Experiment | 무엇을 실행할 것인가 | `docs/ab_test_design.md` | 첫날 탐색 폭 넛지를 유저 단위 A/B로 검증한다 |
| M4 Packaging | 어떻게 보여줄 것인가 | `README.md`, `onepager.html`, `docs/portfolio_report.md` | 채용담당자, hiring manager, technical interviewer 동선을 분리한다 |

## Data Scope

- Data: MerRec / Mercari C2C behavior logs.
- Current cache: 2,771,473 events, 43,311 users, 494,603 raw sessions.
- Observation window: 2023-05-01 to 2023-05-31.
- No signup timestamp. `t0` is first observed event.
- Data-start users may include existing users and are excluded from new-user cohort retention.

## Metric Scope

- Primary portfolio KPI: D7 revisit / retention.
- Retention means return activity, not repeat purchase or revenue retention.
- Purchase conversion is used to explain why buy completion is weak as the primary experiment metric.
- D7 cohort base and causal retain base can differ because their populations and estimands differ. See `docs/metrics_glossary.md`.

## Experiment Handoff

Recommended experiment:

- Population: new observed users eligible at first session. In production, prefer signup-new first-session users if signup timestamp exists.
- Treatment: expose adjacent categories and save/like candidates during the first session to widen exploration.
- Primary metric: D7 revisit.
- Guardrails: buy completion, immediate bounce, session quality, SRM.
- MDE: 2.0pp.
- Sample size: 9,805 users per arm at current base-rate assumptions.

Decision rule belongs in `docs/ab_test_design.md`; README and one-pager should summarize only the headline.

## Reproducibility

```bash
make test
make data-quality
make all
```

`make all` regenerates drivers, impact, figures, funnel/cohort, causal map, A/B design, data quality report, and one-pager.

## Public vs Internal

Public first path:

1. `README.md`
2. `onepager.html`
3. `docs/portfolio_report.md`

Technical evidence:

- `docs/data_quality_report.md`
- `docs/funnel_report.md`
- `docs/cohort_report.md`
- `docs/causal_report.md`
- `docs/impact_report.md`
- `docs/ab_test_design.md`
- `docs/limitations.md`
- `docs/metrics_glossary.md`

Archived drafts and legacy reports stay under `docs/archive/` and should not be used as headline evidence.
