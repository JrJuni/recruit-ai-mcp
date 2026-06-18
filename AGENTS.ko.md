# AGENTS.ko.md

이 파일은 `AGENTS.md`의 한국어 companion 문서다. 최신 source of truth는
항상 `AGENTS.md`이며, 이 파일은 관리자가 한국어 문서 업데이트를 요청했을 때
함께 갱신한다.

## 문서 언어 정책

- 영문 문서가 기본 source of truth다.
- `docs/`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `mcpb/README.md`는 영어와
  ASCII 중심으로 유지한다.
- 한국어로 지속 관리하는 문서는 두 개만 둔다.
  - `README.ko.md`
  - `AGENTS.ko.md`
- 그 외 문서의 한국어 설명이 필요하면 repo에 남기기보다 대화에서 번역을 요청한다.

## 프로젝트 방향

`deal-intel-mcp`는 B2B 딜 인텔리전스 MCP 서버다. 회의록을 MEDDPICC 신호로
구조화하고, 딜 상태와 BI/reporting 도구를 Claude, Codex, ChatGPT, CSV,
Atlas Charts에서 쓸 수 있게 한다.

제품 방향은 한 레포/한 패키지 안에서 세 가지 profile을 제공하는 것이다.

- `sample`: MongoDB 없이 bundled sample data로 바로 써보는 read-only 데모
- `full`: MongoDB Atlas 기반 실제 운영 모드
- `pro`: OpenAI/Anthropic API와 Atlas Vector Search 같은 유료 인프라 경로

## 먼저 읽을 문서

기본 작업에서는 모든 문서를 다 읽지 않는다.

1. `AGENTS.md` 또는 `CLAUDE.md`
2. `docs/README.md`
3. `docs/status.md`
4. `docs/baseline.md`
5. 필요한 영역별 계약 문서

긴 기록 문서인 `docs/lesson-learned.md`, 오래된 `docs/backlog.md` 섹션은
검색해서 필요한 부분만 본다.

## 작업 루프

관리자가 선호하는 루프:

1. 큰 작업 단위와 다음 서브태스크를 먼저 정한다.
2. 복잡하거나 제품 의사결정이 필요한 일은 계획, 리스크, 검증 기준,
   sensemaker 요약을 먼저 정리한다.
3. 작은 일은 바로 구현-검증 루프로 간다.
4. 우려되는 코너케이스를 targeted test로 먼저 고정한다.
5. targeted test, 관련 regression, full pytest, Ruff, 필요한 smoke test로 닫는다.
6. 검증하지 못한 위험은 `docs/status.md` 또는 `docs/backlog.md`에 남긴다.
7. docs를 업데이트하고 의도한 범위만 커밋한다. push는 요청받았을 때 진행한다.

## 현재 MCP 도구

정확한 기준:

- 등록: `src/deal_intel/mcp_server.py`
- profile별 노출: `src/deal_intel/tool_surfaces.py`
- 런타임 확인: `get_tool_catalog`, `config_doctor`,
  `deal-intel config show`

현재 계약 기준 tool surface는 `sample=24`, `standard=38`, `developer=41`이다.
다만 agent-facing 문서에서는 가능하면 숫자를 하드코딩하지 말고 런타임 도구로
확인한다.

주요 그룹:

- Config/readiness: `config_doctor`, `update_config`
- Discovery: `get_tool_catalog`
- Write/lifecycle: `create_deal`, `add_interaction`, `update_stage`,
  `update_deal`, `archive_deal`, `restore_deal`, `delete_deal`
- Product context: `add_product_context_note`, `index_product_context`,
  `get_product_context`
- Qualification framework admin: `get_qualification_templates`,
  `validate_qualification_framework`, `update_qualification_framework`,
  `list_qualification_frameworks`, `set_active_qualification_framework`,
  `delete_qualification_framework`, `backfill_qualification`,
  `backfill_qualification_reextract`
- Read/review: `get_deal`, `list_deals`, `get_deal_gaps`,
  `get_deal_review`
- BI/reporting/export: `get_insights`, `get_metrics`, `get_usage`,
  `export_report`, `export_data`
- User memory: `get_user_memory`, `record_user_memory`
- Customer themes: `get_customer_themes`, `get_customer_theme_breakdown`,
  `get_customer_theme_evidence`
- Search/analysis: `search_deals`, `analyze_deal`
- Deprecated compatibility: `add_meeting`은 developer surface 전용 alias이며,
  새 작업은 `add_interaction(interaction_type="meeting")`을 사용한다.

## 중요한 규칙

- storage와 LLM provider는 `_context.py`를 통해 접근한다.
- provider class를 직접 만들지 말고 `make_llm_provider(config)`를 쓴다.
- BI/reporting 경로에서는 LLM과 embedding을 사용하지 않는다.
- metric/report/review 경로는 raw notes, contacts, embedding을 기본적으로 제외한다.
- `add_interaction`은 stage를 자동 변경하지 않는다. 필요하면
  `stage_suggestion`만 반환하고, 실제 변경은 사용자 확인 후 `update_stage`로 한다.
- `add_meeting`은 deprecated compatibility alias다.
- 삭제/수정 도구는 dry-run, 명시적 확인, reason, audit-safe snapshot을 우선한다.
- 테스트나 문서에 진짜 secret처럼 보이는 placeholder를 쓰지 않는다.
