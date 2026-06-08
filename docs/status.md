# Status

진행 중인 작업과 최근 완료 항목. 장기 계획은 [backlog.md](backlog.md).

## 현재 (2026-06-08)

### Phase 0 — 초기 스캐폴드 완료

- 5개 MCP 도구 구현: `create_deal`, `add_meeting`, `get_deal`, `list_deals`, `analyze_deal`
- LLM provider (ChatGPT OAuth 기본 / Anthropic 옵션) — event-intel-mcp에서 이식
- MongoDB Atlas 연동 준비 완료 (MONGODB_URI 설정 필요)

## 다음 스텝

1. **MongoDB Atlas M0 계정 생성** + `.env`에 `MONGODB_URI` 설정
2. **패키지 설치**: `~/miniconda3/envs/event-intel/python.exe -m pip install -e ".[dev]"`
3. **ChatGPT OAuth 로그인**: `deal-intel login-chatgpt`
4. **Claude Desktop MCP 등록** 후 `create_deal`로 첫 번째 딜 생성 테스트
5. Atlas Charts 연결 (BI 대시보드)
