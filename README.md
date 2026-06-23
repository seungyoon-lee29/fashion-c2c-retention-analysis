# 활성화→리텐션 생존분석 + g-계산 임팩트 — 그로스 데이터 분석

**리텐션을 인과적으로 정직하게 다루고(검열·누수·교란을 *방법으로* 처리), "어떤 초기 행동을 올리면 회사가 얼마나
나아가는가"를 g-계산으로 정량화하는 그로스 분석 프로젝트.** 상세 설계는 [`PLAN.md`](PLAN.md).

## 분석 질문
신규(관측) 유저를 **무슨 초기 행동으로 활성화**시켜야 전환·리텐션이 오르나? 그 활성화 지표를 올리면 비즈니스
임팩트는 얼마인가 — 그리고 그 추정이 *무엇을 주장할 수 있고 없는지*?

## 데이터
[MerRec](https://huggingface.co/datasets/mercari-us/merrec) — Mercari 공식 C2C 행동 이벤트 로그(KDD 2025).
`item_view → item_like → add_to_cart → offer → buy_comp` 풀퍼널 + 유저·세션·시계열. **가입 필드 없음**(→ t0=첫 관측,
좌측절단을 생존모델 지연진입으로 처리). HF는 환경에 따라 네트워크 차단 → **오프라인 합성 fixture**로 전 파이프라인이 동작.

## 접근 (요약 — 상세는 PLAN.md)
1. **Phase 0 게이트** — 유저 타임라인·이벤트(전환=`buy_comp`)·검열(우검열·좌측절단) 정의가 서는지 EDA로 검증.
2. **스파인 = 이산시간 경쟁위험 생존** — 전환 vs 이탈을 경쟁위험으로(정보적 검열 해결), 좌측절단=지연진입, 시간외 검증.
3. **누수 통제** — embargo gap sweep의 plateau = 누수 제거된 진짜 성능(레버 t → 결과 t+h 블랙아웃).
4. **드라이버** — 해저드 SHAP/순열 중요도로 활성화 행동 선별. **아하 임계는 운영 규칙으로 강등**(근거는 생존+시간외).
5. **임팩트 = g-computation** — g-formula(주력) + IPTW/MSM(교차) + naive(대조). **E-value**로 교란 강건성 봉투.

## 핵심 결과 (합성 fixture 데모)
| 추정량 | Δ 전환위험 | 해석 |
|---|---|---|
| naive (비보정) | +0.052 | 교란으로 상향 편향 |
| **g-formula (표준화)** | **+0.040** | 교란 보정 → 진짜 효과에 근접 |
| IPTW/MSM (교차) | +0.050 | 독립 모형, g-formula와 일치 |

RR=1.65 → **E-value=2.68** (이 효과를 설명해 없애려면 미관측 교란이 그만큼 강해야 함).
![impact](docs/figures/impact_estimators.png) ![cif](docs/figures/cif_by_aha.png)

## 정직성 규율
관측 → 인과 아님: g-계산도 순차적 교환가능성·positivity·consistency 가정에 기댐 → **E-value로 가정 강건성 봉투**,
식별 위조 금지. 좌측절단·정보적 검열·선택/생존 편향 노출. 가정은 `config/config.yaml` 분리 + 민감도.

## 실행
```bash
make setup     # 의존성 (shap·lifelines는 선택, 없어도 동작)
make test      # 오프라인 합성 fixture로 전 파이프라인 + ground-truth 복원 검증 (네트워크 불요)
make all       # eda(Phase0) → drivers → impact → figures  (실데이터는 config data.source=merrec)
```
> 재현성 백스톱: `tests/test_smoke.py`는 합성 데이터에 **알려진 인과효과를 심어** g-formula/IPTW가 그걸
> 복원하는지(naive > g-formula > 0, IPTW 일치, E-value>1) 검증한다.
