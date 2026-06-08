# Architecture

## 전체 흐름

```
[입력]
Claude Desktop → MCP 도구 호출
        ↓
[처리 — deal-intel-mcp FastMCP 서버]
add_meeting  : raw_notes → LLM → MEDDPICC 추출 → MongoDB 저장
analyze_deal : MongoDB 조회 → MEDDPICC 집계 → LLM → BD 전략 생성
        ↓
[저장 — MongoDB Atlas M0]
deals collection (document-per-deal)
        ↓
[출력]
Atlas Charts — stage 분포 / MEDDPICC 히트맵 / 성공 패턴 BI
```

## MCP 도구 5개

| 도구 | 입력 | 기능 |
|---|---|---|
| `create_deal` | company, industry?, deal_size_krw? | 신규 딜 생성 |
| `add_meeting` | deal_id, date, raw_notes | 회의록 추가 + MEDDPICC 자동 추출 |
| `get_deal` | deal_id | 딜 전체 조회 (회의록 + MEDDPICC 포함) |
| `list_deals` | stage?, limit | 딜 목록 조회 |
| `analyze_deal` | deal_id | MEDDPICC 갭 분석 + BD 전략 생성 |

## Deal 도큐먼트 스키마

```json
{
  "deal_id": "uuid",
  "company": "ACME Corp",
  "industry": "제조",
  "deal_size_krw": 150000000,
  "deal_stage": "qualification",
  "close_reason": null,
  "contacts": ["홍길동 CTO"],
  "prospect_id": null,
  "meetings": [
    {
      "meeting_id": "uuid",
      "date": "2026-06-08",
      "raw_notes": "...",
      "summary": "",
      "meddpicc": {
        "metrics": {"score": 3, "evidence": "비용 20% 절감 목표"},
        "identify_pain": {"score": 4, "evidence": "현 시스템 주 1회 다운타임"}
      }
    }
  ],
  "bd_strategy": "Claude가 생성한 전략 텍스트",
  "gtm_notes": "",
  "created_at": "2026-06-08T...",
  "updated_at": "2026-06-08T..."
}
```

## 모듈 구조

```
src/deal_intel/
  mcp_server.py      — FastMCP 진입점, 5개 tool 등록
  cli.py             — typer CLI (login-chatgpt)
  _env.py            — dotenv 로드 + 3-tier config 병합
  _context.py        — LLM/MongoDB 프로세스 싱글톤
  providers/
    llm.py           — LLMProvider ABC + AnthropicProvider + ChatGPTOAuthProvider + factory
  schema/
    meddpicc.py      — Pydantic 모델 (Deal, Meeting, Meddpicc, MeddpiccField)
  storage/
    mongodb.py       — MongoDBClient (pymongo lazy import)
  tools/
    create_deal.py
    add_meeting.py
    get_deal.py
    list_deals.py
    analyze_deal.py
```

## LLM Provider

- **기본**: `chatgpt_oauth` — ChatGPT Plus/Pro 구독 사용, 추가 비용 없음
- **옵션**: `anthropic` — `ANTHROPIC_API_KEY` 필요, prompt caching 지원
- `~/.deal-intel/config.yaml`에 `llm.provider: chatgpt_oauth` 설정으로 override
- Token cache: `~/.deal-intel/chatgpt_auth.json`

## 3-tier Config

1. `config/defaults.yaml` — shipped defaults
2. `.env` — ANTHROPIC_API_KEY, MONGODB_URI (gitignored)
3. `~/.deal-intel/config.yaml` — per-user override (optional)
