# Backlog

장기 계획, 미구현 항목. 진행 중/직전 완료는 [status.md](status.md).

---

## P1 — 다음 phase

### #1 Atlas Charts BI 대시보드
딜 stage 분포, MEDDPICC 점수 히트맵, 성공/실패 패턴. `close_reason` 기준 승리/패배 분석.

### #2 회의록 요약 (summary 필드 채우기)
현재 `add_meeting`은 `summary: ""`. MEDDPICC 추출과 동시에 요약 생성 추가.

### #3 in-app ChatGPT 로그인 (MCP 도구화)
현재 `login-chatgpt`는 CLI-only (blocking). event-intel-mcp backlog #14 패턴으로 비동기화.

---

## P2

### #4 Vector Search — 유사 성공 사례 검색
MongoDB Atlas Vector Search로 "이 딜과 비슷한 과거 성공 사례" 검색. 임베딩 생성 파이프라인 필요.

### #5 Notion 연동
Notion에서 작성한 회의록을 Notion API → `add_meeting`으로 자동 싱크.

### #6 deal_stage 전환 로직
MEDDPICC 점수 임계값 기반 stage 자동 추천 (예: champion 3+ + economic_buyer 3+ → qualification 이동 권고).

---

## P3

### #7 event-intel-mcp 연결
event-intel-mcp의 prospect → deal 전환 트리거. `prospect_id` 필드는 이미 스키마에 있음.

### #8 성공 사례 GTM 확산 리포트
유사 딜 패턴 기반 GTM 전략 자동 생성. Vector Search (#4) 선행 필요.

---

## 의도적 OOS

- **Web UI**: CLI + Claude Desktop으로 충분. 별도 결정 시 새 product.
- **실시간 CRM 동기 (Salesforce/HubSpot)**: v0 scope 밖. 별도 export 기능으로.
