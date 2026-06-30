# Metrics Glossary

이 문서는 포트폴리오 본문에서 쓰는 KPI의 단위와 해석을 고정한다. 목적은 이벤트 단위 수치와 유저 단위 수치를 섞지 않는 것이다.

| Metric | Unit | Definition | Current use |
|---|---|---|---|
| View reach | user | 관측 기간 중 `item_view`를 1회 이상 발생시킨 유저 비율 | 퍼널 시작점 |
| Like reach | user | 관측 기간 중 `item_like`를 1회 이상 발생시킨 유저 비율 | 조회 -> 찜 누수 및 첫날 탐색 후보 |
| Cart reach | user | 관측 기간 중 `item_add_to_cart_tap`을 1회 이상 발생시킨 유저 비율 | 허영지표 후보 및 식별 진단 레버 |
| Offer reach | user | 관측 기간 중 `offer_make`를 1회 이상 발생시킨 유저 비율 | 협상의도 레버 후보 |
| Buy conversion | user | 관측 기간 중 `buy_comp`를 1회 이상 가진 유저 비율 | 구매 전환 희소성 판단 |
| Retention / revisit | user | `t0` 이후 지정 horizon 안에 다시 활동한 유저 비율 | 주지표 후보 및 A/B primary metric |
| D1/D3/D7 revisit | user | 첫 관측일 이후 1/3/7일 안에 재방문한 유저 비율 | 신규 코호트 리텐션 |
| First-day activity breadth | user | 첫날 이벤트 수, 세션 수, 활동일수, 조회 수, 카테고리 다양성 등 초기 활동 폭 | 코호트 후보 및 넛지 방향 |
| `cat>=3` | user | feature window 안에서 3개 이상 카테고리를 탐색한 유저 | 탐색 폭 식별 진단 레버 |
| IPTW delta | percentage point | 처치 확률의 역수로 가중한 treated-control outcome 차이 | 관측 진단값, 인과 단정 아님 |
| g-formula delta | percentage point | 초기 confounder 분포를 표준화해 계산한 outcome 차이 | 카트 레버의 보정 후 효과 진단 |
| E-value | ratio | 관측된 risk ratio를 없애려면 필요한 미관측 교란 강도 | 효과 강건성 봉투 |
| MDE | percentage point | 실험에서 탐지할 최소 의미 효과 크기 | A/B 표본수 산정 |
| SRM | test result | 실험군/대조군 배정 비율이 설계와 다른지 보는 sample-ratio mismatch 점검 | A/B 가드레일 |

## Denominator Notes

- 퍼널의 reach는 전체 관측 유저 기준이다.
- 코호트의 D7 재방문 50.1%는 데이터 시작일 유저를 제외하고 D7 관측창을 확보한 신규 관측 유저 기준이다.
- 식별 진단의 retain base 40.1%는 person-period full-follow-up 유저 기준이다. 따라서 코호트 D7 base와 직접 비교하지 않는다.
- 리텐션은 재방문 행동 프록시다. 재구매 또는 매출 리텐션은 별도 데이터와 후속 검증이 필요하다.
