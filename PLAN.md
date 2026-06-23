# 신규 포트폴리오: 아하 모먼트(활성화) 발굴 → 임팩트 추정 (그로스 데이터 분석)

## ⚡ 즉시 실행 (이번 승인 범위 — Ultraplan 클라우드 정제 가능하게 git init만)
> Ultraplan은 **현재 세션 cwd**(`…/Obsidian Vault/marketplace-seller-entry-analysis`)를 git 저장소로 검사함. 거기가 git이 아니라 계속 실패. 사용자가 "지금 폴더에 git init" 선택. → **현재 폴더를 git 저장소로 만들어 이 세션에서 Ultraplan이 뜨게 한다. 전체 구현은 클라우드 정제+teleport 이후.**
1. 현재 폴더에 `.gitignore` 추가(.venv/ data/raw/ data/*.parquet __pycache__/).
2. `docs/PLAN.md` = 이 기획서(`~/.claude/plans/parsed-petting-tower.md`) 사본 — 클라우드가 읽을 컨텍스트.
3. `git init` + `git add -A` + 첫 커밋("plan: growth-activation 기획 + 정리 예정 Olist 스캐폴드").
4. → 이 세션에서 Ultraplan 재실행하면 통과.
- ⚠️ 현재 폴더엔 폐기 예정 Olist 코드가 들어있음 → 클라우드 정제/teleport 후 본구현 때 정리(또는 새 폴더로 이전). 지금은 속도 우선으로 그대로 커밋.
- 참고: 사용자가 GitHub 온라인 repo("project6.23-")도 만들었다고 함 → 원하면 이 로컬 repo의 remote로 연결 가능(별도).

---


## Context (왜)
취업용 데이터분석 포트폴리오. 사용자는 **전략적 제안이 들어간** 프로젝트를 원한다 — 단순 기술통계가 아니라 그로스 데이터 분석의 정석:
"목표 Y를 위해 어떤 행동 X를 윈도우 N 내 몇 번 시켜야 하나(아하 모먼트)"를 SHAP·precision/recall·MCC로 발굴하고, **마르코프 체인으로 임팩트("이 지표 올리면 회사가 얼마 나아가나")를 추정**하며, **AI를 언제 쓰고 언제 규칙으로 가는지** 분별해 팀 방향을 제시.

데이터 여정: Olist(흔함) 폐기 → StockX(거래기록뿐, 행동·유저 없어 아하모먼트 **불가**) 폐기 → **행동 이벤트 로그 필요**. 탐색 결과 무인증·경량·희소·풀퍼널을 만족하는 **MerRec(Mercari 공식, KDD2025)** 채택. (Taobao=8일·풀퍼널아님, REES46/KKBox/Instacart=Kaggle인증+수GB로 제외.)

- **독립 프로젝트**(crm과 연결 안 함). **`~/Desktop/`에 신규 폴더** 생성.
- 목표 Y: **전환(buy_comp) 주지표 + 초기 리텐션(재방문) 보조지표** (사용자 확정).

## 데이터 (확정)
- **MerRec** `https://huggingface.co/datasets/mercari-us/merrec` — 날짜폴더(20230501..) 안 파일들. **1파일(68MB)=한 달 완결 로그**(유저 단위 샤딩): 504K 이벤트/7,571유저, event 타입 `item_view·item_like·item_add_to_cart_tap·offer_make·buy_start·buy_comp`.
- 로드: `20230501/` 파일 **약 5개(~350MB) urllib 캐시** → ~35k 유저, ~1.5k 전환. 컬럼만 선택(user_id, stime, session_id, event_id, item_id, c0/c1_name, brand_name, price).
- 검증됨(읽기 테스트 통과): user당 이벤트 중앙값 11, 한 달 span, 전환율 ~4%.

## 이름/위치
- `~/Desktop/growth-activation-analysis` (또는 `aha-moment-impact-analysis`). git init + 첫 커밋(승인 시).

## 분석 파이프라인 (사용자 프레임워크를 정밀화)
1. **북극성/목표 Y (조작적 정의)** — 주: 전환=윈도우 이후 `buy_comp` 발생. 보조: 초기 리텐션=활성 윈도우 이후 주에 재방문. 코호트=첫 활동 기준 신규 유저.
2. **후보 행동 X (조작적 정의)** — 첫 윈도우(첫 세션 / 첫 3·7일) 내: #view, #like, #add_to_cart, #offer, #session, 카테고리 다양성, 브랜드 다양성, 활동일수.
3. **X 좁히기 (SHAP)** — `GradientBoosting`(sklearn)으로 Y 예측, **SHAP** 중요도·방향으로 전환/리텐션을 끌어올리는 행동 선별.
4. **아하 모먼트 임계 (k,n) 탐색** — "X ≥ k in window n" 격자에서 **precision/recall/F1/MCC + lift**로 평가해 조작적으로 아하 모먼트 확정(상관 아닌 분류성능·리프트로 정당화). [crm 계승] train/holdout 분리로 임계 과적합 방지.
5. **검증** — 아하 달성 vs 미달성 코호트의 리텐션/전환 곡선 + holdout 지표.
6. **임팩트 추정 (마르코프 체인)** — 유저 상태 {신규→브라우저(view만)→인게이지(like/cart/offer)→전환(buy)→휴면→이탈} 주간 전이행렬 추정 → 아하 달성률을 Δ 올리는 개입을 전이확률에 반영 → 정상상태 활성유저·기대 전환수 변화 시뮬레이션 = "지표 X를 올리면 회사가 얼마 나아가나".
7. **전략 제안 + AI 사용 분별 (report/strategy_memo.md)** — 팀 방향(온보딩에서 어떤 행동을 몇 번 유도), 실행안(넛지·추천 배치), **AI 분별**: 아하 모먼트는 *단순 규칙*으로 운영(모델 불필요), SHAP·예측모델은 *발굴·개인화*에만; 임계 과적합·관측편향 주의.

## 구조 (crm 정직성 규율 계승 + 확장)
```
~/Desktop/growth-activation-analysis/
├── Makefile          # setup / features / aha / impact / figures / all / clean
├── README.md         # 가상 사전과제 + 핵심결과 + figures + 정직한 한계
├── requirements.txt  # numpy pandas pyarrow scikit-learn shap matplotlib pyyaml
├── .gitignore        # .venv/ data/raw/ data/*.parquet __pycache__/
├── config/config.yaml# Y정의·윈도우·임계격자·마르코프 상태·가정
├── src/
│   ├── data.py       # MerRec May N파일 캐시 로드 + 코호트/세션 구성 + validate()
│   ├── features.py   # 유저×윈도우 행동피처 + Y라벨(전환/리텐션) 생성 → data/user_features.parquet
│   ├── aha.py        # GBM+SHAP로 X선별 → (k,n)격자 P/R/F1/MCC/lift → 아하모먼트 확정 → docs/aha_report.md
│   ├── impact.py     # 마르코프 전이행렬 + 아하 Δ 임팩트 시뮬 → docs/impact_report.md
│   └── figures.py    # SHAP요약·아하 리프트곡선·코호트 리텐션·마르코프 임팩트 4종
├── docs/
│   ├── eda_findings.md / aha_report.md / impact_report.md (생성)
│   ├── decisions.md / limitations.md (수기, D-1.. + 한계)
│   └── figures/
└── report/strategy_memo.md   # 전략 제안 + 실행 + AI 사용 분별
```

## 정직성 규율 (crm 계승)
- **관측 데이터 → 인과 아님**: 아하 모먼트는 *예측적 연관*이지 증명된 인과 아님 → "A/B로 검증할 가설"로 명시(crm은 무작위배정으로 인과를 다뤘다는 대비).
- **선택/생존 편향**: 활동 로그에 남은 유저만 관측.
- **짧은 horizon**(1개월 샘플) → 리텐션은 수주 범위로 한정. 마르코프 무기억성 가정 명시.
- 가정(윈도우·임계·상태정의)은 config 분리 + 민감도. 단일 답 회피.

## 기존 vault 정리 (이전 시도 폐기)
- vault `marketplace-seller-entry-analysis/`(Olist) **삭제**.
- `crm-uplift-analysis/README.md`의 `../marketplace-seller-entry-analysis` 형제 링크를 **평문**으로 되돌림(독립 방침).
- 위키 `crm-uplift-analysis-wiki/log.md`에 폐기/전환 기록 append.

## 검증 (end-to-end)
1. `make setup` → venv(shap 포함).
2. `make all` → features → aha → impact → figures 무오류, 산출물 생성.
3. 콘솔==docs 재현성, README figure 링크 점검.
4. SHAP·마르코프 수치 sanity(전이행렬 행합=1 등).
5. (승인 시) git init + 첫 커밋.
