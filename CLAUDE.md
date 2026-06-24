# CLAUDE.md — 프로젝트 규약 (세션 간 인계용 스키마)

> 이 프로젝트는 여러 Claude Code 세션에 걸쳐 진행된다(`HANDOFF.md` 참고).
> 이 파일은 **규약을 코드화**해 매 세션이 같은 규율로 움직이게 한다. (Karpathy "LLM Wiki" schema 계층 아이디어 적용.)

## 무엇
활성화→리텐션 **이산시간 경쟁위험 생존** + **g-computation 인과 임팩트** 그로스 DS 포트폴리오. 데이터=MerRec(Mercari C2C 행동로그). 설계=`PLAN.md`, 요약=`README.md`.

## 어디에 무엇이
- `src/` — 파이프라인: `data.py`(Phase0·로딩) `_synth.py`(오프라인 fixture) `personperiod.py` `survival.py` `drivers.py` `impact.py` `figures.py` `_util.py`
- `config/config.yaml` — **모든 가정·하이퍼파라미터의 단일 출처.** 코드에 매직넘버 하드코딩 금지.
- `tests/test_smoke.py` — 합성 ground-truth 복원 검증(네트워크 불요).
- `docs/` — 생성 리포트(`eda_findings·drivers_report·impact_report`) + 수기 문서(`decisions·limitations·index·log`) + `figures/`.
- `report/strategy_memo.md` — 비즈니스 메모.

## 핵심 규약 (반드시 지킬 것)
1. **합성 데이터(`_synth.py`)는 테스트 백스톱이다 — 절대 삭제 금지.** 알려진 인과효과를 심어 g-formula/IPTW 정확성을 검증한다. 실제 분석은 MerRec(`data.source: merrec`)를 쓴다.
2. **사전등록 vs 여정 로그를 분리한다.** `docs/decisions.md`=결과 보기 *전에* 잠근 결정(사후 변경 금지). `docs/log.md`=시간순 append-only 여정(무엇을 언제 했나).
3. **가치 있는 발견은 docs에 박제한다.** 진단·검증 결과를 채팅에만 두지 말 것("file answers back").
4. **생성 리포트를 수기 편집하지 말 것.** `docs/{eda_findings,drivers_report,impact_report}.md`와 `docs/figures/*`는 `make all`이 재생성한다.
5. **정직성 규율.** 관측→인과 단정 금지. g-계산 가정(순차교환가능성·positivity·consistency)은 E-value로 봉투. 한계는 `docs/limitations.md`.

## 실행
```bash
make setup        # 의존성 (shap·lifelines 선택)
make test         # 합성 fixture + ground-truth 복원 (네트워크 불요)
make eda          # Phase-0 게이트 (실데이터/합성)
make all          # eda → drivers → impact → figures
```
- 실데이터: `config.yaml`에서 `data.source: merrec`. HF 자동 다운로드(`data/raw` 캐시) 또는 `data.local_dir`로 로컬 parquet.
- **MerRec 주의:** 이벤트 타입 문자열은 `event_id` 컬럼에 있음(`name`은 상품명 — 혼동 금지). `event_col_candidates`로 매핑.

## decisions/log 엔트리 형식
- `decisions.md`: `D-N <주제>: <잠근 결정>` (번호 안정 유지).
- `log.md`: `## [YYYY-MM-DD] <type> | <제목>` — `type ∈ {data, finding, decision, run, lint}`. 프리픽스 일관 유지 시 `grep "^## \[" docs/log.md | tail` 로 최근 이력 조회.

## 현재 상태 포인터
최신 진행/미결 결정은 `docs/log.md` 맨 아래를 볼 것.
