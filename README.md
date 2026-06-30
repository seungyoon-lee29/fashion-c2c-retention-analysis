# 패션 C2C 신규 유저 리텐션 분석

**첫날 탐색 경험을 넓히면 신규 유저는 D7에 다시 돌아오는가?**  
Mercari C2C 행동 로그 277만 건으로 퍼널, 코호트, 식별 진단, A/B 설계까지 연결한 제품 데이터 분석 프로젝트다.

## Candidate Snapshot

| Item | Detail |
|---|---|
| Author | 이승윤 |
| Target role | Product / Growth Data Analyst |
| Contact | [sy3097@gmail.com](mailto:sy3097@gmail.com) · [GitHub profile](https://github.com/seungyoon-lee29) |
| Repository | [fashion-c2c-retention-analysis](https://github.com/seungyoon-lee29/fashion-c2c-retention-analysis) |
| Core tools | Python, pandas, DuckDB SQL, scikit-learn, matplotlib, Makefile |

## 10초 결론

- 구매완료율은 **4.4%**로 낮아 신규 유저 경험의 주지표를 구매가 아니라 **D7 재방문**으로 잡았다.
- 첫날 활동 폭은 D7 재방문과 **+27pp** 연관됐지만, 관측 데이터만으로 인과효과를 확정하지 않았다.
- 카트는 리텐션 레버처럼 보였지만 보정 후 효과가 0 근처로 약해졌다.
- 최종 제안은 카트 최적화가 아니라 **첫날 탐색 폭 넛지 A/B 실험**이다.

## 4단계 분석 흐름

| 단계 | 질문 | 발견 | 판단 |
|---|---|---|---|
| Funnel | 어디서 새는가 | view 98.7% -> buy 4.4%, 최대 유출은 조회 -> 찜 | 구매 전환보다 D7 재방문을 주지표로 둔다 |
| Cohort | 누가 돌아오는가 | 첫날 활동 Q4 D7 66.2% vs Q1 39.3% | 단일 행동보다 첫날 경험 폭을 후보로 본다 |
| Identification | 보이는 레버가 인과인가 | cart +16.0pp -> +3.2pp, cat>=3 +25.4pp -> -6.5pp | 관측 추정은 인과효과로 쓰지 않는다 |
| Experiment | 무엇을 실행할 것인가 | 관측 신호만으로 부호를 확정하기 어렵다 | 첫날 탐색 폭 넛지를 A/B로 검증한다 |

## 보여준 역량

| 역량 | 이 프로젝트에서 한 일 |
|---|---|
| 제품 KPI 재정의 | 구매완료율 4.4%의 한계를 보고 D7 재방문으로 의사결정 KPI를 전환 |
| SQL 데이터 QA | DuckDB로 required fields, event vocabulary, timestamp, price, denominator 검증 |
| 퍼널/코호트 분석 | 조회 -> 찜 최대 유출과 첫날 활동 폭별 D7 차이를 연결 |
| 인과 과대해석 방지 | naive 연관과 보정 진단을 분리하고, 관측 로그의 식별 한계를 명시 |
| 실험 설계 | 주지표, 가드레일, MDE, 표본수, 기간, 성공/중단 규칙을 제안 |

## 읽는 순서

**[`onepager.html`](onepager.html) 한 장이면 충분하다** — 문제 -> 4단계 발견 -> A/B 핸드오프까지 60초 요약.

> GitHub는 HTML을 바로 렌더링하지 않는다. 한 번에 보려면 **GitHub Pages**를 켜거나, 클릭하면 바로 열리는 **[`slides.pdf`](slides.pdf)**(9장 발표 덱)를 본다. 더 깊은 근거는 [`docs/index.md`](docs/index.md)(선택).

## 재현

```bash
make setup
make test
make data-quality
make all
```

`make all`은 공개 리포트, 진단 리포트, figure, `onepager.html`을 재생성한다.  
로컬 MerRec parquet 폴더를 쓰려면 `config/config.yaml`의 `data.local_dir`에 경로를 지정한다.

## 범위

- 리텐션은 재구매가 아니라 **재방문 행동**이다. 매출 효과는 후속 검증이다.
- 가입일이 없어 `t0 = 첫 관측 이벤트`로 정의했고, 데이터 시작일 유저는 신규 코호트에서 제외했다.
- 관측 데이터만으로 양성 인과 효과를 확정하지 않는다. 제품 의사결정은 유저 단위 A/B로 넘긴다.
