# Handoff

현재 공개 정본은 `README.md`, `onepager.html`, `docs/portfolio_report.md`다. 내부 설계는 `PLAN.md`에 둔다. 생성 리포트는 수기 편집하지 말고 `make all`로 재생성한다.

## Current State

- DA 4단계 파이프라인 구현: funnel, cohort, drivers, impact, causal map, A/B design, data-quality, onepager.
- User-level binary retention summaries restrict to full-follow-up users so right-censored users are not counted as non-retained.
- Survival/person-period models may still use right-censored rows where that is the correct survival-analysis representation.
- Legacy `report.html`, `strategy_report/`, old drafts, raw build logs, and version2 remnants are archived under `docs/archive/` and should not be used as headline evidence.

## Usual Checks

```bash
make test
make data-quality
make all
```

After changing `config/config.yaml` windows, lever thresholds, or experiment settings, regenerate reports and re-check duplicated headline numbers in `README.md`, `docs/portfolio_report.md`, and `onepager.html`.
