# Status

## BI Reporting Milestone 0.1 (2026-06-08)

- Runtime contracts for all 9 MCP tools recorded
- Full test baseline: 17 passed
- Ruff cleanup: all 28 pre-existing findings resolved; `ruff check .` passes
- Live MongoDB Atlas read smoke: passed with 10 deals
- Details: [baseline.md](baseline.md)

진행 중인 작업과 최근 완료 항목. 장기 계획은 [backlog.md](backlog.md).

## 현재 (2026-06-08)

### Customer Themes BI MVP 완료

- 9개 MCP 도구 등록, `get_customer_themes` 추가
- `add_meeting`에서 MEDDPICC와 함께 고객 고민 주제를 통제 taxonomy로 추출
- 고유 딜 기준 주제 빈도, coverage, 대표 회사·evidence 집계
- 기존 데이터용 `backfill-customer-themes` CLI 추가
- 기존 10개 딜의 customer themes backfill 완료
- Atlas Charts용 aggregation pipeline 추가
- M0 호환 Python cosine 기반 `search_deals`와 startup warmup guard 추가

## 다음 스텝

1. BI Reporting Milestone 1.1 metric 계약 정의
2. metric 경계값·누락값·종료 딜 fixture 테스트
3. 공통 metric 계산 모듈 구현 전 계약 gate 검증
