# 리텐션 활성화 전략 리포트

`strategy_report`는 활성화→리텐션 분석을 **실행 전략 관점**으로 재구성한 정적 HTML 리포트다.
루트 `report.html`이 방법론 엄밀성을 보이는 분석 케이스라면, 이 리포트는 그 결과를 팀 의사결정과
A/B 실험 후보로 번역한다.

## 흐름

1. 목표 `Y`를 정의한다 — 엠바고 이후 재방문(t0+5~t0+19일).
2. SHAP으로 후보 행동 `X`를 좁힌다.
3. `X >= k within n days` 형태로 아하 규칙을 조작적으로 정의한다.
4. precision·recall·coverage·MCC로 규칙을 선택한다.
5. g-formula/IPTW로 인과 게이트를 통과하는지 보고, Markov로 회사 임팩트 언어로 번역한다.
6. A/B 테스트로 검증할 후보 X와 측정 설계를 제안한다.

핵심 결론: 카트는 좋은 마커지만 인과 보정 후 리텐션 레버로는 null이다. 실행 방향은 카트 유도가
아니라 `활동일 수 >= 2 / 3일`(확장 후보 grid 1위, MCC 0.302)을 늘리는 “두 번째 활동일” 실험이다.

## 산출물

- `index.html` — 한국어 정적 HTML 전략 리포트
- `assets/*.png` — 리포트 차트 이미지
- `candidate_rules.csv` — 원본 이벤트 테이블에서 5개 행동지표로 재계산한 확장 후보 X grid
- `scripts/build_strategy_report.py` — 재생성 스크립트

## 재생성

```bash
MPLCONFIGDIR=/tmp/matplotlib python3 strategy_report/scripts/build_strategy_report.py
```

`data/events.parquet`가 있으면 grid를 재계산해 `candidate_rules.csv`를 갱신하고, 없으면 커밋된
`candidate_rules.csv`를 단일 출처로 읽는다(같은 수치).
