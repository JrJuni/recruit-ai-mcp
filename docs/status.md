# Status

진행 중인 작업과 최근 완료 항목. 장기 계획은 [backlog.md](backlog.md).

## 현재 (2026-06-08)

### BI Reporting Milestone 0.1 완료

- 9개 MCP 도구의 runtime 입력 계약과 응답 surface 기록
- 전체 테스트 `17 passed`
- 기존 Ruff 28건 정리, `ruff check .` 통과
- wheel build와 CLI entry point 검증
- 실제 MongoDB Atlas 읽기 smoke 통과 (10개 딜)
- 상세 기준선: [baseline.md](baseline.md)

### Customer Themes / Semantic Search MVP 완료

- 9개 MCP 도구 등록, `get_customer_themes` 추가
- `add_meeting`에서 MEDDPICC와 함께 고객 고민 주제를 통제 taxonomy로 추출
- 고유 딜 기준 주제 빈도, coverage, 대표 회사·evidence 집계
- 기존 데이터용 `backfill-customer-themes` CLI 추가
- 기존 10개 딜의 customer themes backfill 완료
- Atlas Charts용 aggregation pipeline 추가
- M0 호환 Python cosine 기반 `search_deals`와 startup warmup guard 추가

### 문서 정합성 완료

- `CLAUDE.md`, `AGENTS.md`, README, architecture, backlog, MCPB 안내를 현재 코드 기준으로 동기화
- M0 검색 경로를 Python cosine으로 명확히 하고 M10+ Atlas 전환과 구분
- 로컬 전용 설정과 build artifact는 gitignore 유지

### BI Reporting Milestone 1.1 Part A 완료

- Active, Stalled, Open, Terminal stage population 계약 고정
- 미평가 딜을 `unassessed`로 분리하고 평균 health에서 제외
- Health band 기본값 `70/40`을 `metrics.health_bands` config로 이동
- 잘못된 threshold는 명시적 오류로 차단
- 계약 및 미결정 항목: [metrics.md](metrics.md)

## 다음 스텝

1. Milestone 1.1 Part B: pipeline value와 누락 금액 처리 결정
2. Milestone 1.1 Part C: stuck/overdue와 win rate 결정
3. 전체 metric 계약 완료 후 공통 계산 모듈 구현
