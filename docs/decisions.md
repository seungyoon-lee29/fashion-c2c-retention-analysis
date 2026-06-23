# 의사결정 로그 (사전등록 · holdout 잠금)

> 결과를 보기 **전에** 고정한 결정들. 사후 가지치기/체리피킹을 막기 위한 사전등록.

- **D-1 목표 Y**: 주=전환(`buy_comp`), 보조=초기 리텐션(재방문). 라벨 윈도우는 embargo gap 이후 `[t0+W+G, +H)`.
- **D-2 코호트/시간축**: t0=첫 관측 이벤트(가입 아님 → 좌측절단). `t0≥data_start+buffer`로 절단 완화.
  피처 `[t0,t0+W)` → embargo `[t0+W,t0+W+G)` → 결과 `[t0+W+G,+H)`. 아하 윈도우 `n≤W`.
- **D-3 스파인**: 이산시간 **경쟁위험** 생존(전환 vs 이탈). 이탈을 단순 검열로 두지 않음(정보적 검열).
- **D-4 누수 통제**: embargo gap을 0→7일 sweep, holdout PR-AUC **plateau**에서 gap 고정. 동일 gap을 인과 estimand에도 강제.
- **D-5 레버/조정집합**: 레버=`aha_cart`(첫 윈도우 cart≥1). 조정집합은 `n_cart` **제외**(레버와 중복 → 위양성·positivity 붕괴 방지).
- **D-6 임팩트**: 주력 g-formula, 교차 IPTW/MSM, 대조 naive. 인과 단정 금지 → **E-value 봉투**.
- **D-7 불일치 프로토콜**: g-formula vs IPTW 상대차 > `disagreement_threshold_pct`(기본 30%)면 평균내지 말고
  **어느 가정이 일하는지 진단**.
- **D-8 검증 분할**: 시간외(out-of-time) — 이른 t0 코호트 train, 늦은 코호트 holdout. 임계 과적합 방지.
- **D-9 폐기**: RDD(분석적 임계엔 실제 처치 불연속 없음) · 매칭+Rosenbaum 기본(시변 처치에 부적합) → 보조로만.

## Holdout 잠금
시간외 holdout(늦은 t0 코호트)은 최종 보고 수치 산출에만 1회 사용. 모델/임계 선택은 train에서만.
