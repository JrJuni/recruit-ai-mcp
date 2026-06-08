# Lessons Learned

Append-only log of approaches tried, failure causes, and validated know-how.
**Failures only** — successes belong in a future playbook.

## Entry format

```
## [YYYY-MM-DD] One-line topic

**Tried**: which approach was taken
**Result**: success / failure + observed behavior
**Lesson**: what to do next time
**Related**: file paths / linked entries
```

---

## [2026-06-08] ChatGPT OAuth → Codex backend — 5가지 누적 실패 (event-intel-mcp에서 이식)

**Tried**: ChatGPT Plus 구독을 LLM provider로 끌어다 쓰기 위해 OAuth 경로 구현.

**Result**: 한 가지 가정으로 시작했지만 5개의 독립적 backend 제약이 누적 발견됨:

1. **auth URL 필수 파라미터 누락** — `state`, `originator=codex_cli_rs`, `codex_cli_simplified_flow=true`, `id_token_add_organizations=true` 전부 필수.
2. **`api.openai.com` 거부 (401)** — OAuth 토큰은 `chatgpt.com/backend-api/codex/responses`만 허용. `chatgpt-account-id` + `OpenAI-Beta` + `originator` + `OAI-Product-Sku` 헤더 모두 필요.
3. **모델명 추측 실패** — `gpt-5.1-codex-mini` 등 전부 거부. 실제 동작 모델: `gpt-5.5` / `gpt-5.4`.
4. **`max_output_tokens` / `max_tokens` 전부 거부 (400)** — payload에서 완전 제외. `_ = max_tokens` 명시.
5. **`temperature` 도 거부** — 동일하게 payload 제외.

**Lesson**:
- 공식 backend 우회는 reverse engineering — backend 변경에 무방비. 개인 로컬 전용.
- AI에게 모델명/API 필드 추측 시키지 말 것. CLI config (`~/.codex/config.toml`) 등 ground truth 먼저 확인.
- 회귀 테스트로 lock: payload에서 빠진 필드가 실수로 다시 추가되지 않도록 absence-assert.
- ChatGPT provider는 prompt caching 없음 (`chat_cached`는 단순 concat으로 동작).

**Related**: `src/deal_intel/providers/llm.py::ChatGPTOAuthProvider`. 원본: event-intel-mcp `docs/lesson-learned.md` 2026-05-29.
