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

## [2026-06-08] mcpb Windows — cmd.exe + 공백 경로 + Electron 이중 쿼팅

**Tried**: mcpb `mcp_config.command`를 `cmd.exe`, args를 `["/c", "<launcher.bat 전체 경로>"]`로 설정.
launcher.bat이 Python 자동 탐색(conda env 순회)을 담당.

**Result**: `Claude Extensions` 폴더명에 공백이 있어 다음 두 가지 실패가 연속 발생:
1. 따옴표 없이 → `cmd.exe /c C:\...\Claude Extensions\...\launcher.bat` → cmd.exe가 공백에서 토큰 분리 → `'...\Claude\Claude'은(는) 내부 또는 외부 명령... 아닙니다.`
2. `\"...\"`로 따옴표 추가 → Electron이 이미 args를 quote-wrap하므로 이중 쿼팅 → `'"C:\...\launcher.bat"'은(는) 내부 또는 외부 명령...` (따옴표 자체가 경로에 포함)

이 문제가 0.1.2부터 존재했지만 `%APPDATA%\Claude\claude_desktop_config.json` 수동 설정(python.exe 직접 지정)이 병행 작동하고 있어서 노출이 안 됐음.
0.1.4 mcpb 재설치 후 mcpb 쪽이 우선권을 가져가면서 처음으로 사용자에게 노출.

**Lesson**:
- mcpb `mcp_config.command`에는 **절대 `cmd.exe`를 쓰지 말 것**. `Claude Extensions` 폴더명 공백 때문에 어떤 쿼팅 조합도 Electron spawn 레이어와 충돌함.
- 정답 패턴 (event-intel-mcp 검증): `"command": "${user_config.python_path}"`, `"args": ["-m", "<module>"]`. Python 경로는 공백 없음.
- 자동 탐색 로직이 필요하면 launcher.bat이 아니라 launcher.py에서 구현하고, 그 py를 python_path로 실행.
- `required: true` / `type: "file"` 로 python_path를 form 필드로 받는 것이 battle-tested.

**Related**: `mcpb/manifest.json` server.mcp_config. 참조: event-intel-mcp manifest (동일 패턴 작동 확인).

---

## [2026-06-08] sentence_transformers pre-import → Claude Desktop startup timeout

**Tried**: `mcp_server.py::main()`에서 `import sentence_transformers`를 pymongo와 함께 pre-import.
FastMCP worker-thread 이슈 예방 차원의 선제 import.

**Result**: sentence_transformers import 시 torch + transformers 전체 로드에 **4.9초** 소요.
FastMCP 서버가 stdio를 열기 전에 Claude Desktop 타임아웃 → `Server disconnected` 즉시 발생.

**Lesson**:
- sentence_transformers는 pre-import 금지. `embed()` 첫 호출 시 lazy load가 맞음 (thread-safe).
- pre-import 대상 선정 기준: import 자체가 **0.5초 이내**인 것만. torch 계열은 전부 제외.
- pymongo는 ~0.1초라 pre-import 유효. 기준선: `python -c "import X"` 시간으로 측정 후 결정.

**Related**: `src/deal_intel/mcp_server.py::main()`.

---

## [2026-06-08] search_deals 4분 hang → 진짜 원인 및 최종 수정

**상황**: search_deals가 Claude Desktop에서 정확히 4분 후 `-32001: Request timed out`으로 취소됨.
MCP 로그로 확인: 요청 수신 → 응답 없음 → 4분 후 client-side 강제 취소.

**잘못된 가설들**:
- ~~"10초 warmup 문제"~~ — 진단 스크립트에서 9.97s warmup 측정 → 이걸 원인으로 단정. 틀림.
- ~~"MongoDB silent connection drop"~~ — socketTimeoutMS=15s 추가했지만 여전히 4분 hang.
- 15초 지나도 안 끝나는 hang은 MongoDB가 아닌 곳에서 발생 중이었음.

**실제 원인**: `SentenceTransformer()` 생성자가 HuggingFace Hub에 네트워크 체크를 함.
이 체크에 timeout이 없어 네트워크 지연 시 **무한 대기**.
warmup thread가 lock을 쥔 채 HF Hub 응답을 기다리는 동안,
search_deals의 embed() 호출도 같은 lock을 기다리며 함께 무한 대기.
결과: Claude Desktop 4분 timeout까지 아무 응답 없음.

**최종 수정 (외부 리뷰로 발견)**:

1. **`mcp_server.py::search_deals`**: `is_ready` + `load_error` 선행 체크 → 모델 미준비 시 **즉시 반환** (0.022s).
   blocking embed() 호출 전에 탈출. warmup 중이면 `warming_up: true` + `retry_after_seconds: 5`.

2. **`mcp_server.py::main()`**: `ensure_indexes()` 를 **별도 background thread**(`mongo-indexes`)로 분리.
   기존: `_context.mongo()` 첫 호출 시 동기 실행 → 첫 tool call 지연 유발.
   수정: 서버 시작과 동시에 daemon thread로 실행 → 첫 tool call 비차단.

3. **`_context.py`**: singleton 초기화에 `threading.Lock()` 적용 (double-checked locking).
   기존: race condition 가능 (warmup thread + tool call thread 동시 접근).

4. **`embedding.py`**: `load_error` 속성 추가. warmup 실패 시 에러 메시지 캡처 → tool handler에서 노출.
   `is_ready`는 `_get_model()`이 아닌 `embed()` 성공 후 set → 실제 동작 가능 상태만 True.

5. **`.env`**: `TRANSFORMERS_OFFLINE=1` 추가. HF Hub 체크 자체를 차단해 warmup 시간 단축 및 hang 원인 제거.

**Lesson**:
- MCP tool에서 blocking 가능한 작업은 **먼저 상태 체크 후 즉시 반환** 패턴이 필수.
  embed() 자체를 빠르게 만드는 것보다 hang 전에 탈출하는 게 우선순위.
- Claude Desktop timeout은 **4분**. 15초 안에 에러가 안 나면 MongoDB가 아님.
  timeout 길이로 hang 위치를 역추적할 수 있음.
- `ensure_indexes()` 같은 초기화 작업은 첫 tool call 경로에 두지 말 것.
  background thread로 분리해야 첫 응답이 빠름.
- singleton 초기화는 thread-safe하게. warmup thread와 tool call thread가 동시에 접근함.

**Related**: `src/deal_intel/providers/embedding.py`, `src/deal_intel/mcp_server.py`, `src/deal_intel/_context.py`.

---

## [2026-06-08] sentence_transformers — GPU 감지 오버헤드 제거로 cold-load 10s → 4.4s

**Tried**: `SentenceTransformer(model_name)` (device 미지정) — GPU 자동 감지 + CUDA 미탐지 시 CPU 폴백.

**Result**: cold load **10.16초**. Background warmup thread를 시작해도 첫 호출이 10초 이내이면 여전히 타임아웃.

**Fix**: `SentenceTransformer(model_name, device="cpu")` 명시 → cold load **4.39초**. 절반 이상 단축.
Background warmup (4.4s)과 결합하면 Claude Desktop 프로토콜 협상 + 사용자 첫 입력 (~5-10초) 동안 warmup이 완료됨.

**Lesson**:
- CUDA 없는 환경에서 `device` 미지정은 GPU 감지 루프를 실행 → 순수 CPU 시스템에서 수초 낭비.
- CPU 전용 배포라면 `device="cpu"` 항상 명시. GPU가 있으면 `"cuda"` 명시. 자동 감지는 개발환경 편의 기능.
- 측정 방법: `SentenceTransformer(name)` vs `SentenceTransformer(name, device="cpu")` 타이밍 비교로 즉시 확인 가능.

**Related**: `src/deal_intel/providers/embedding.py::SentenceTransformerProvider._get_model()`.

---

## [2026-06-08] search_deals warmup guard 문서화 후 실제 handler 반영 누락

**Tried**: background embedding warmup과 `is_ready` 상태를 추가하고 수정 완료로 기록했지만,
`mcp_server.py::search_deals`에는 준비 상태 확인 없이 `embed()`를 호출하는 코드가 남아 있었음.
동시에 `_context.mongo()`가 첫 tool 호출 안에서 인덱스 4개를 동기 생성하고 있었음.

**Result**: cold start MCP 재현에서 첫 검색이 MongoDB DNS 대기로 8.3초 블로킹됨.
로컬 embedding cold load도 별도로 약 5.8초 걸려, 호출 시점에 따라 두 대기가 사용자 요청 경로에 겹침.

**Lesson**:
- background warmup을 추가했으면 handler가 readiness를 확인하고 즉시 재시도 응답을 반환하는지
  MCP protocol-level 테스트로 검증할 것.
- idempotent한 DB 초기화라도 첫 사용자 tool 호출에서는 실행하지 말고 background maintenance로 분리할 것.
- 수정 완료 문서보다 실행 가능한 회귀 테스트를 ground truth로 삼을 것.

**Related**: `src/deal_intel/mcp_server.py`, `src/deal_intel/_context.py`,
`tests/test_search_deals_startup.py`.

---

## [2026-06-08] FastMCP 실행 중 background native import 정지

**Tried**: FastMCP stdio 시작과 동시에 background thread에서 `sentence_transformers`를 최초 import.

**Result**: Windows에서 NumPy `multiarray`, 이후 SciPy `special` 네이티브 모듈 생성 단계가 정지.
CPU 사용량이 0인 채 `warming_up`이 1분 이상 지속됨. 메인 스레드에서 동일 모델을 로드하면 약
5.8초 만에 정상 완료됨.

**Lesson**:
- Windows background thread에서 ML 네이티브 런타임을 최초 import하지 말 것.
- `numpy`, `scipy`, `sklearn`, `torch`만 메인 스레드에서 선행 import하고 모델 생성은 background로
  유지하면 MCP 초기화 3.8초, embedding 준비 약 7초로 정상화됨.
- warmup 상태에 phase와 elapsed를 포함하고 30초를 넘으면 stalled 오류로 전환할 것.

**Related**: `src/deal_intel/mcp_server.py::main()`,
`src/deal_intel/providers/embedding.py::SentenceTransformerProvider`.

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
