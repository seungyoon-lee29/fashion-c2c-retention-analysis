# Project History

이 문서는 공개용으로 정리한 짧은 진행 기록이다. 원시 작업 로그와 철회된 탐색 기록은 [`archive/build_log.md`](archive/build_log.md)에 보존했다.

## What Changed

| Date | Decision | Why It Matters |
|---|---|---|
| 2026-06-24 | 주지표를 구매완료에서 재방문으로 전환 | MerRec의 첫 구매는 대부분 첫 관측 직후 발생해 리텐션 지표로 부적합했다. |
| 2026-06-26 | 퍼널·코호트·식별지도·A/B 설계의 4단계 구조로 정리 | 채용용 포트폴리오에서 제품 판단의 흐름이 보이도록 재구성했다. |
| 2026-06-26 | 카트 효과를 단순 연관과 보정 진단으로 분리 | 카트는 재방문과 강하게 연관되지만, 보정 후 양성효과를 확정하지 못했다. |
| 2026-06-27 | 첫날 탐색 폭 넛지 A/B를 사전등록 | 관측 데이터로 후보를 좁히고, 효과 검증은 무작위 실험으로 넘겼다. |
| 2026-06-28 | full-follow-up 기준과 SQL data-quality audit 추가 | 우검열 유저를 binary non-retained로 세지 않도록 고쳤고, DuckDB SQL로 원천 이벤트 품질을 검증했다. |

## Current Public Claim

구매완료율은 4.4%로 희소했다. 따라서 성공지표를 D7 재방문으로 두었다. 첫날 활동 폭은 D7 재방문과 강하게 연관됐지만, 관측 보정만으로 인과효과를 확정할 수 없었다. 최종 산출물은 첫날 탐색 폭 넛지 A/B 설계다.

## Archived, Not Deleted

아래 자료는 판단 과정의 흔적이므로 보존하지만, 채용용 첫 독서 경로에서는 제외한다.

- [`archive/build_log.md`](archive/build_log.md): 원시 작업 로그
- [`archive/report_legacy.html`](archive/report_legacy.html): 이전 생존분석 중심 HTML 리포트
- [`archive/strategy_report_legacy/`](archive/strategy_report_legacy/): 이전 실행전략 리포트
- [`archive/drafts/`](archive/drafts/): 과거 플랜 드래프트
- [`archive/design_detail.md`](archive/design_detail.md): 과거 추천/OPE 통합 설계 문서
- [`archive/version2/`](archive/version2/): 추천/OPE 탐색 잔여물
