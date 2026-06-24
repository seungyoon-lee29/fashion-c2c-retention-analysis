# 활성화→리텐션 생존분석 + g-계산 임팩트 (그로스 DS 포트폴리오)

> **정체성**: "리텐션을 **인과적으로 정직하게** 다루고(검열·누수·교란을 *방법으로* 처리), 모던 시퀀스 모델을
> 헤드라인이 아니라 **정밀 계측기**로 쓰는 그로스 데이터 사이언티스트."

## Context (왜)
취업용 그로스 데이터분석 포트폴리오. "목표 Y(전환·리텐션)를 위해 어떤 초기 행동 X를 언제 시켜야 하나"를
**생존분석**으로 정직하게 발굴하고, 그 행동을 올리면 회사가 얼마나 나아가는지를 **g-계산(인과 표준화)**으로
추정한다. 데이터는 **MerRec**(Mercari 공식 C2C 행동 이벤트 로그, KDD2025; **가입 필드 없는 순수 행동 로그**).

여러 라운드 정제로 초기안(아하 임계+마르코프 중심)의 구조적 약점 — 연관/교란 근거, 검열 미처리, 시변 처치에
부적합한 횡단면 보정 — 을 제거하고 아래로 수렴했다.

## 확정 설계 (락)
- **스파인 = 이산시간 경쟁위험 생존**(person-period 해저드). KM/CIF가 서술 동반자. (이산시간 유연 해저드가
  비례위험을 *완화*하므로 Cox/Schoenfeld는 미채택 — PH를 가정하지 않는 스파인엔 덜 유연한 중복 모델.)
- **3층 구조**: 스파인(생존=정체성·단독 방어) · 계측층(시퀀스/next-action 임베딩을 *시변공변량*으로, Tier 2) ·
  운영층(아하 임계·마르코프를 *운영 규칙/플레이북*으로 강등).
- **임팩트 = 스파인 재사용 g-computation**: g-formula(주력) + IPTW/MSM(교차, 모형의존 다름) + (여유 시 TMLE).
  식별가정 = **순차적 교환가능성 + positivity + consistency**, **E-value로 봉투**(Rosenbaum 아님 — 모델 기반엔 E-value).
- **삼각검증 = "독립 확인"이 아니라 "가정-스트레스"**: 다리마다 식별가정이 다르고 **일치=안심이 아니라 발산=진단**.
  **사전등록 불일치 프로토콜**(`config.disagreement_threshold_pct`).
- **누수=인과 공유 장치**: embargo gap을 누수 통제뿐 아니라 인과 estimand에도 강제(레버 t → 결과 t+h, 블랙아웃).
- **RDD(분석적 임계) 폐기**(임계가 처치를 유발하지 않음 → 식별 불성립). 매칭+Γ는 횡단면 보조로만.
- 마르코프는 **해저드의 무기억 *근사*** (엄밀 동치 아님 — 시변이력 의존이라 본질은 비마르코프). 과대주장 금지.

## Phase 0 — 실현가능성 게이트 (스파인 락 전, go/no-go)  ← `src/data.py validate()`
- **복원**: `user_id`가 세션 간 시간축으로 이어져 유저×스텝 person-period 복원.
- **이벤트/검열**: 전환=`buy_comp`; 이탈(lapse)=N일 무활동(흡수); 우검열=관측창 종료; 좌측절단=t0(첫 관측, **가입 아님**).
- **충분성/positivity**: 전환 이벤트 수·person-day·처치 중첩 점검. **시간 단위**(일 vs 2–3일 bin)는 활동 희소성 보고 결정.
- **GO 기준**: 타임라인 복원 ✓ + 전환 ≥ 임계수 ✓ + 다수 유저 ≥2스텝 관측 ✓ + positivity ✓.
- **폴백**: 실패 시 단일-horizon 분류로 회귀(사유 기록). positivity 실패 → 인과 주장 철회, **연관 + E-value만**.

## 방법론 (MVS 스파인)
1. **시간축·코호트**: t0=첫 관측("신규-관측 코호트", 좌측절단→생존 **지연진입**). 절단 완화 `t0≥data_start+buffer`.
   `[t0,t0+W)` 피처 → `[t0+W,t0+W+G)` embargo → `[t0+W+G,+H)` 결과. 아하 윈도우 `n≤W`.
2. **스파인 — 이산시간 경쟁위험 생존**: person-period(유저×스텝), 스텝별 경쟁 결과 0=지속/1=재방문(retain)/2=이탈.
   (Phase-0에서 첫 구매가 즉시적임을 확인 → 결과를 리텐션=재방문으로 확정. `decisions.md` A-1.)
   해저드=풀드 로지스틱(베이스)+**GBM 해저드**(유연)+확률보정. 공변량=시불변 초기행동 + (Tier2)시변 임베딩 — **과거 정보만**.
   동반자=**KM/Aalen-Johansen CIF** · **시간외(out-of-time) 검증**(신뢰 핵심).
   구조적 정직성: 경쟁위험(정보적 검열 해결)·지연진입(좌측절단)·past-only·embargo(반사성).
3. **드라이버 + 누수 통제**: 해저드에 **SHAP/순열 중요도** → 초기 행동 선별. **gap sweep**(0→7일) holdout 곡선의
   **plateau**=누수 제거 성능, gap별 중요도 안정성으로 누수 아티팩트 제거.
4. **운영층(강등)**: **아하 임계** "X≥k in n"을 운영 가능한 매직넘버(activation 플레이북)로. **마르코프** 흡수체인
   (`N=(I−Q)⁻¹`, `B=N·R`)은 단순 표현으로만.

## 임팩트 — g-computation 통합 + 삼각
- **주력 g-formula**: 시변 해저드 적합 → 레버를 `do(X=x)`로 고정해 person-period 전방 시뮬 → 자연진화 대비 **ΔCIF**.
- **교차 IPTW/MSM**: 과거이력 조건부 처치확률 역수(안정화 가중·positivity 점검) → 가중 위험차. g-formula와 가정 같고
  모형의존 다름 → 일치 시 강건. **naive(비보정) 대조**로 교란 제거를 가시화.
- **봉투/보고**: 점 아닌 범위(베이지안 신용구간), **E-value**, **레버 원장**(어느 행동을 얼마나 — 보수/기준/낙관).
  **do(X)=잘 정의된 조작가능 개입** + consistency/SUTVA/**Goodhart 주석**.

## 스코프 규율
- **MVS(단독 완결작)**: Phase0 게이트 → 경쟁위험 생존 + KM/CIF + SHAP 드라이버 + gap-sweep + 시간외 검증 +
  아하 플레이북 + **g-formula 임팩트(E-value 봉투)** + 정직한 한계 + 사전등록.
- **Tier 2(계측)**: 시퀀스 임베딩 시변공변량 · IPTW/MSM 교차 · 마르코프 베이지안 밴드.
- **Tier 3(인과 확장)**: 실제충격 DiD/ITS(있을 때만) · 유저-FE · IV · TMLE · 백테스트.

## 구조 (이 repo 루트 = 프로젝트)
```
Makefile · requirements.txt · config/config.yaml
src/ data.py(Phase0) _synth.py(오프라인 fixture) personperiod.py survival.py drivers.py impact.py figures.py
tests/test_smoke.py(합성 ground-truth 복원 검증) · docs/(생성 리포트+figures, 수기 decisions/limitations) · report/strategy_memo.md
```

## 정직성/식별 규율
- 관측→인과: g-계산도 가정에 기댐 → **E-value로 가정 강건성 봉투**, 식별 위조 금지.
- 편향 노출: 좌측절단(지연진입)·우검열·선택·**정보적 검열**(경쟁위험)·생존. 짧은 horizon(1개월): 리텐션=수주, 무기억성 한계.
- 모든 가정(buffer·W·G·N·n·k·레버) config 분리 + 민감도. 면접 방어 장전: positivity·E-value·시간외 검증.

## 실행 리스크 & 안전장치
- **여기서 멈춘다**: 방법론 수렴. 더 얹으면 구현·가정·서사 희석으로 net 마이너스. 남은 일=실행+스코핑+Phase0 EDA.
- **MVS는 인과 성공에 의존하지 않음**: 보장 산출물=생존 서술+누수통제+시간외 검증. g-formula는 best-effort,
  **positivity 실패 시 연관+E-value로 자동 강등**. DiD/IV는 MerRec엔 없을 가능성 높음 → 없으면 생략.
- **정확성 백스톱**: 합성 fixture에 **알려진 ground-truth 효과**를 심어 g-formula/IPTW가 복원하는지 검증
  (`tests/test_smoke.py` — naive>g-formula>0, IPTW 일치, E-value>1). HF 네트워크 차단·shap 미설치에도 무관히 동작.

## 검증 (end-to-end)
1. `make setup` → `make test`(합성 fixture, 네트워크 불요, ground-truth 복원).
2. (네트워크 허용) `make eda`(Phase0 게이트) → `make all` → docs 리포트 + 6 figures.
3. Sanity: CIF∈[0,1]·단조, 해저드∈[0,1], 전이행렬 행합=1·`(I−Q)` 가역, IPTW positivity, gap 곡선 plateau, E-value 계산.
