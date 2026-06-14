# AI Full Install Guide (Korean)

이 문서는 비개발자 사용자가 AI assistant의 도움을 받아
`deal-intel-mcp`를 **full 모드**로 설치할 때 참고하는 가이드입니다.

full 모드는 기본 제품 경로입니다. 실제 딜 데이터는 MongoDB Atlas에
저장합니다. sample 모드는 MongoDB 없이 빠르게 제품 흐름을 확인하는
zero-config trial/demo 경로입니다.

## 1. 사용자에게 처음 설명할 말

AI assistant는 먼저 아래처럼 짧게 설명하세요.

```text
정식 사용 기준으로는 네 가지가 필요합니다.
1. MongoDB Atlas 계정과 Free/M0 클러스터
2. Atlas 연결 문자열(MONGODB_URI)
3. Claude Desktop 또는 Codex/ChatGPT 같은 MCP 클라이언트
4. ChatGPT OAuth 또는 Anthropic/OpenAI API key 중 하나

MongoDB 없이 먼저 맛만 보려면 sample 모드도 가능하지만,
실제 팀 데이터 운용은 full 모드가 기본입니다.
```

사용자가 명시적으로 원하지 않는 한 API key, OAuth token, MongoDB URI 같은
secret을 채팅창에 붙여넣게 하지 마세요. `.env`, MCPB 설정창, 로컬 환경변수를
우선 사용하세요.

## 2. 준비물 체크리스트

명령을 실행하기 전에 아래 준비물이 있는지 확인합니다.

| 항목 | 필요한 이유 | 메모 |
|---|---|---|
| Windows + PowerShell 또는 macOS Terminal | 로컬 설치 | 이 가이드의 예시는 주로 PowerShell 기준입니다. |
| Git | 레포 clone | 이미 zip으로 받은 경우 생략 가능합니다. |
| Miniconda | Python runtime | 비개발자에게 안정적인 Python 경로를 제공하므로 권장합니다. |
| Python 3.11 conda env | 패키지 설치와 MCPB 설정 | bare `python`/`py` 대신 env의 Python 경로를 직접 씁니다. |
| MongoDB Atlas 계정 | full 모드 저장소 | Free/M0로 MVP 사용이 가능합니다. |
| Atlas database user | MongoDB URI | 선택한 database에 read/write 권한이 필요합니다. |
| Atlas network access | MongoDB URI | 현재 IP를 허용하거나 테스트 중 임시 allowlist를 사용합니다. |
| MCP client | 채팅 UI | 현재는 Claude Desktop MCPB가 가장 쉬운 경로입니다. |
| LLM provider | 추출/채점 | ChatGPT OAuth, Anthropic API key, OpenAI API key 중 하나입니다. |

### 플랫폼과 sandbox 참고

- Windows에서는 PowerShell quoting, UTF-8 표시, `Downloads`, OneDrive,
  보호 폴더 권한 문제가 macOS보다 자주 보일 수 있습니다. 정확한 conda
  Python 경로와 기본 `~/.deal-intel` 출력 디렉터리를 우선 사용하세요.
- macOS는 UTF-8과 shell quoting이 보통 더 부드럽지만, 패키지가 설치된
  환경의 정확한 Python interpreter path를 쓰는 원칙은 같습니다.
- Claude Desktop, Codex Desktop 같은 AI host는 명령을 제한된 sandbox 안에서
  실행할 수 있습니다. 이 경우 같은 설정이 일반 터미널에서는 정상이어도
  host 안에서 MongoDB/Atlas DNS ping이 실패할 수 있습니다.
- `config doctor --offline`은 통과하지만 live ping만 실패하면, credential을
  바꾸기 전에 일반 터미널에서 `config doctor`를 한 번 더 실행하세요.

## 3. Python Interpreter Path

Python interpreter path는 `deal-intel-mcp`가 설치된 conda 환경 안의
`python.exe` 전체 경로입니다. MCPB 설정에는 이 경로가 필요합니다.

새 `deal-intel` 환경을 만들었다면 보통 아래와 비슷한 형태입니다.

```text
<absolute-path-to-your-conda-env>\python.exe
```

정확한 경로는 아래 명령으로 확인합니다.

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -c "import sys; print(sys.executable)"
```

출력된 값을 MCPB의 `Python interpreter path` 필드에 넣으세요.

## 4. MongoDB Atlas 설정

사용자에게 Atlas에서 아래 순서로 진행하게 안내합니다.

1. MongoDB Atlas 계정을 만들거나 로그인합니다.
2. Free/M0 cluster를 만듭니다.
3. Database user를 만듭니다.
4. Network Access에서 현재 IP를 허용합니다.
5. Cluster driver connection string을 복사합니다.
6. URI 안의 `<password>`를 로컬에서 실제 비밀번호로 바꿉니다.

사용자에게 아래처럼 말하세요.

```text
Atlas 연결 문자열에는 비밀번호가 들어가는 경우가 많아서 secret입니다.
채팅창에 그대로 붙여넣지 말고, 로컬 `.env` 파일이나 MCPB 설정창에만
입력하는 것이 좋습니다.
```

## 5. 로컬 설치

레포를 clone합니다.

```powershell
git clone <repo-url>
cd deal-intel-mcp
```

필요하면 conda env를 만듭니다.

```powershell
& "$HOME\miniconda3\Scripts\conda.exe" create -n deal-intel python=3.11 -y
```

패키지를 설치합니다.

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m pip install -e ".[dev,embedding]"
```

다른 env 이름을 썼다면 이후 명령의 Python 경로를 `sys.executable` 출력값으로
바꿔서 사용하세요.

## 6. full 모드 설정

실제 데이터에는 full 모드를 사용합니다.

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli config switch full
```

secret은 채팅창이 아니라 로컬에 저장합니다. 선택지는 보통 세 가지입니다.

1. 레포의 `.env` 파일
2. MCPB 설정창
3. 현재 PowerShell session의 환경변수

일반적인 `.env` 예시는 아래와 같습니다.

```text
MONGODB_URI=<atlas-uri>
OPENAI_API_KEY=<only-if-using-openai-api>
ANTHROPIC_API_KEY=<only-if-using-anthropic>
```

ChatGPT OAuth를 쓸 경우 최초 1회 로그인합니다.

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli login-chatgpt
```

## 7. Doctor와 Smoke Check

먼저 offline check를 실행합니다.

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli config doctor --offline
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli smoke-profile --profile full --offline
```

그 다음 live storage check를 실행합니다.

```powershell
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli storage-status
& "$HOME\miniconda3\envs\deal-intel\python.exe" -m deal_intel.cli mongo doctor
```

기대 방향:

- `config doctor`: failed check가 없어야 합니다.
- `smoke-profile --profile full --offline`: pass여야 합니다.
- `storage-status`: MongoDB에 연결되어야 합니다.
- `mongo doctor`: index와 schema validator가 보이거나, 실행 가능한 조치가
  안내되어야 합니다.

## 8. Claude Desktop MCPB 설정

MCPB 설정창에는 아래 값을 권장합니다.

| 필드 | 권장값 |
|---|---|
| Python interpreter path | 이 패키지가 설치된 conda env Python |
| Storage backend | `mongo` |
| MCP tool surface | `auto` |
| MongoDB Atlas URI | 사용자의 Atlas URI, 로컬 설정창에만 입력 |
| LLM provider | 기본값은 `chatgpt_oauth` |
| Anthropic API key | provider가 `anthropic`일 때만 |
| OpenAI API key | provider가 `openai_api`일 때만 |

MCPB 설정을 바꾼 뒤에는 Claude Desktop을 재시작하세요.

재시작 후 Claude/Codex에게 먼저 이렇게 요청합니다.

```text
config_doctor 실행해서 설정 상태 확인해줘.
```

full 모드라면 일반적으로 standard real-data tool surface가 보여야 합니다.
sample 모드로 보이면 storage backend와 config profile을 확인하세요.

## 9. 처음 물어볼 질문

설정이 끝나면 아래 질문으로 바로 동작을 확인할 수 있습니다.

```text
딜 목록 보여줘.
현재 파이프라인 건강도 보여줘.
가장 위험한 딜 하나 리뷰해줘.
고객들이 가장 많이 고민하는 주제는 뭐야?
이번 주 파이프라인 보고서 만들어줘.
```

## 10. sample 모드를 쓸 때

sample 모드는 아래 상황에서만 권장합니다.

- 사용자가 MongoDB 없이 먼저 체험하고 싶을 때
- AI assistant가 빠르게 제품 흐름만 확인해야 할 때
- fictional bundled data로 demo를 해야 할 때
- 아직 Atlas credential을 만들 준비가 안 됐을 때

sample 모드는 가벼운 개인 테스트에는 쓸 수 있지만, 실제 팀 운용은
MongoDB-backed full 모드를 기준으로 설계되어 있다고 설명하세요.

## 11. Troubleshooting Map

| 증상 | 가능한 원인 | 먼저 확인할 것 |
|---|---|---|
| Claude에 sample tool만 보임 | storage backend/profile이 sample | `config_doctor` 실행 |
| Mongo doctor가 local_sample이라고 함 | full로 전환되지 않음 | `config switch full` 실행 |
| Mongo ping 실패 | URI, 비밀번호, IP allowlist, cluster 상태 | Atlas connection string과 Network Access 확인 |
| AI host 안에서만 Mongo ping 실패 | host sandbox/network 제한 | 일반 터미널에서 `config doctor` 실행 후 `config doctor --offline`과 비교 |
| LLM tool 실패 | OAuth 만료 또는 API key 누락 | `login-chatgpt` 또는 선택 provider key 확인 |
| MCP server 시작 실패 | MCPB의 Python path 오류 | 해당 interpreter에 `deal-intel-mcp`가 설치됐는지 확인 |
| 한글이 깨져 보임 | encoding/display 문제 | UTF-8 파일을 우선 사용하고 secret은 채팅창에 복사하지 않기 |

## 12. AI Assistant Safety Rules

- API key, OAuth token, MongoDB URI, password를 문서에 저장하지 마세요.
- 설치 가이드는 `user_docs/`에 넣지 마세요. `user_docs/`는 사용자 memory
  공간입니다.
- 사람 사용자에게 sample 모드를 기본 경로처럼 설명하지 마세요.
- delete 같은 파괴적 작업은 dry-run과 archive gate를 먼저 설명하세요.
- taxonomy/classification처럼 저위험 분류는 AI가 초안을 만들고, 사용자가
  필요할 때 수정하게 안내하세요.
