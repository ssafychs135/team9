# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

iPhone 스펙/리뷰 게시판 + LM Studio 로 서빙되는 RAG 챗봇 (Gemma 4 E4B + EmbeddingGemma) + YouTube 자막 Gemini 요약을 합쳐놓은 SSAFY 소규모 팀 PJT. SSAFY 표준 `S14P##` 네임스페이스가 아닌 **개인 네임스페이스 레포** (`lab.ssafy.com/sunnychoi135/team9`)에 호스팅돼 있어 phase 식별 시 헷갈리지 말 것. 작업 언어는 한국어 (커밋·주석·README·UI 카피 전부).

세 서비스가 함께 동작 + 외부 LM Studio 1개:

| Dir | Role | Stack | Port |
|---|---|---|---|
| `backend-core/` | Django API + RAG 챗봇 + 리뷰 게시판 | Django 5 + DRF + dj-rest-auth + ChromaDB + LangChain + `langchain-openai` (LM Studio 호출) | 8000 |
| `backend-worker/` | YouTube videoId → 자막 → Gemini 요약 | Node 20+ ESM + Express 5 + `@google/generative-ai` + `youtube-caption-extractor` | 3000 |
| `frontend/` | 사용자 UI (게시판 + 챗봇 + 인증) | Vue 3.5 + Vite 7 + Pinia + Vue Router 4 + axios + marked | 5173 |

`setup_project.py`와 `run_services.py`가 세 서비스를 오케스트레이트한다.

## Commands

### 부트스트랩 (최초 1회)
```bash
python setup_project.py     # venv 생성, pip install, npm install (×2), .env 템플릿, migrate, loaddata fixture.json
# 완료 후 → backend-core/.env 의 다음 값을 채워야 함:
#   LM_STUDIO_API_KEY        : 게이트웨이(lmstudio.chs135.com) Bearer 토큰
#   LM_STUDIO_CHAT_MODEL     : 게이트웨이가 인식하는 챗 모델 식별자
#   LM_STUDIO_EMBED_MODEL    : 게이트웨이가 인식하는 임베딩 모델 식별자
# 그리고 backend-worker/.env 의 GEMINI_API_KEY 채우기
# LM Studio 게이트웨이는 외부 인프라 — body 의 "model" 필드 기준으로 백엔드 라우팅
```

### 3개 서비스 동시 기동
```bash
python run_services.py      # Django(8000) + worker(3000) + Vite(5173). Ctrl+C로 일괄 종료
```

### backend-core
```bash
cd backend-core && source venv/bin/activate
python manage.py runserver
python manage.py makemigrations && python manage.py migrate
python manage.py loaddata fixture.json
python manage.py embed_iphone_data   # crawled_data/*.json → ChromaDB 컬렉션 재생성
python manage.py webcrawler          # selenium 기반 iPhone 스펙 수집
python manage.py test                # Django test runner (현재 테스트 거의 없음 — import-time 에러는 잡힘)
```

### backend-worker
```bash
cd backend-worker
npm run dev                          # nodemon
# 호출 예: curl 'http://localhost:3000/?videoId=<자막있는ID>'
# 빌드/린터/테스트 없음. npm test 는 의도적으로 실패.
```

### frontend
```bash
cd frontend
npm run dev
npm run build
npm run lint                         # eslint --fix --cache
npm run format                       # prettier --write --experimental-cli src/
```

## Big-picture architecture

### 데이터 흐름 (게시판 + 챗봇 + 요약)
1. **유저가 챗봇에 질문** → 프론트 `ChatbotPage` → `POST /ai/chatbot/api/` (Django).
2. Django `AI/views.py` (앱 import 시점에 `initialize_chatbot()` 호출됨 — `AI/lm_studio.py` 어댑터 경유) → `AI/chatbot_service.py` 의 LangChain 파이프라인.
3. 토픽 라우터(`RunnableBranch`)가 "아이폰 질문"이면 `SelfQueryRetriever`(메타데이터 필터 LLM 자동 생성) → 실패 시 일반 similarity 폴백 → `released_date` 내림차순 **수동 정렬** → LM Studio 의 Gemma 4 E4B 응답. 일반 대화는 RAG 우회. 출력 dict 키 `{answer, context}`로 통일 (`format_general_output` 래퍼).
4. **유저가 리뷰 작성 시 YouTube videoId 입력** → 프론트가 worker `GET /?videoId=…` 호출 → worker가 자막 fetch → Gemini로 한국어 마크다운 요약 → 프론트가 `marked`로 렌더. videoId/lang_code 는 `reviews.Review` 모델에 **그대로 저장** — 워커가 게시판과 연결되는 브릿지 필드.
5. 리뷰 CRUD 는 `reviews.ReviewViewSet` (nested `CommentViewSet`) — `/api/reviews/...` 접두사는 루트 `review_site/urls.py` 에서 붙음.

### Django 앱 구조
- `accounts/` — `User(AbstractUser)` (확장 필드 없음). `AUTH_USER_MODEL = "accounts.User"`. URL은 dj-rest-auth 위임.
- `reviews/` — `Review` (필드: `user, title, content, video_id, lang_code, created_at, updated_at`), `Comment`. `IsOwnerOrReadOnly + IsAuthenticatedOrReadOnly`. **URL 파일이 두 개**: `urls.py`(웹 페이지용), `api_urls.py`(DRF nested router).
- `AI/` — **앱 이름 대문자**. `chatbot_service.py`(LangChain 체인), `views.py`(API), `management/commands/{embed_iphone_data,webcrawler,clean_dates,update_dates}.py`.

### 인증
- dj-rest-auth + django-allauth. JWT 아님 — DRF `TokenAuthentication` + Basic.
- 프론트는 로그인 응답의 `response.data.key` 를 `localStorage.access_token` 으로 저장. axios 글로벌 인터셉터 없음 — 각 호출 컴포넌트가 헤더(`Authorization: Token <key>`)를 **직접** 붙인다. `Bearer` 가 아니라 `Token` 이라는 점에 주의.

### 프론트 라우팅/상태
- Pinia 2개 스토어: `authStore`(토큰+username 영속), `modalStore`(async `alert()` 대체).
- 보호 라우트(`requireAuth`): `/reviews/create`, `/reviews/:id/edit`, `/chatbot`. 비보호 인증(`requireGuest`): `/login`, `/signup`. 가드는 `beforeEnter` 로 라우트별 적용.
- 백엔드 URL **하드코딩**: `http://localhost:8000`(Django), `http://localhost:3000`(워커). 환경 분리 미도입 — 변경 시 모든 호출처를 grep으로 동시 수정.

## Project-specific landmines

이 프로젝트에서 "관례에 맞춰 정리"하다가 깨지기 쉬운 항목들.

- **`AI` 앱은 대문자 그대로**. `INSTALLED_APPS`, `import AI.urls`, `AI/chatbot_service.py` 등 모든 import 경로가 대문자. 소문자 `ai` 로 바꾸지 말 것.
- **ChromaDB 컬렉션명 `iphone_specs_collection` 은 두 곳에 하드코딩**: `AI/chatbot_service.py` 와 `AI/management/commands/embed_iphone_data.py`. 한쪽만 고치면 retrieve 깨짐.
- **`CHROMA_DB_PATH` 환경변수는 존재하지만 사용 안 됨** — 챗봇 코드는 `CHROMA_DB_PATH_CRAWLED` 만 읽는다 (legacy 잔재). 잘못된 변수를 만지지 말 것.
- **iPhone JSON 데이터는 두 디렉터리에 따로 존재**:
  - `backend-core/crawled_data/iPhone *.json` — 사람이 읽기 좋은 이름. **임베딩 대상**.
  - `backend-core/AI/iPhone/iPhoneN,M.json` — 식별자 기반. 별도 raw 데이터. 혼동 주의.
- **임베딩은 비대칭 의도**: 인덱싱 시 `embedding-passage`, 질의 시 `embedding-query`. 같은 모델로 통일하지 말 것.
- **`reviews/views.py` 의 함수 기반 뷰들은 전부 주석 처리**된 상태로 ViewSet 마이그레이션 완료. 주석 살리지 말 것 (역행).
- **`.env` 가 두 파일로 분리**: `backend-core/.env` (LM Studio / Django / Chroma 키, Upstage 키는 legacy 잔류), `backend-worker/.env` (Gemini 키). 루트 `.env` 없음 — 만들지 말 것. 워커는 LM Studio 키를 모르고, 코어는 Gemini 키를 모른다.
- **CORS 화이트리스트**: `http://127.0.0.1:5173`, `http://localhost:5173` 둘만. 워커도 같은 두 origin 만 허용 (`server.js`). 프론트 dev 포트 변경 시 양쪽 동기 수정.
- **prettier `--experimental-cli` 플래그**: `frontend/package.json` 의 `format` 스크립트에 박혀 있음 (prettier 3.6 전용). 절대 제거 X.
- **Node engines 강제**: `^20.19.0 || >=22.12.0`. nvm 권장.
- **`Review.video_id`/`lang_code` 는 워커와의 브릿지 필드** — 새로 추가된 게 아니라 의도된 설계. 제거하지 말 것.
- **Worker 엔드포인트는 단 하나**: `GET /?videoId=...`. REST 컨벤션 따르지 않음. 새 기능 추가 시 라우터 도입 필요.
- **Gemini 모델 하드코딩**: `gemini-2.5-flash-lite` (`backend-worker/src/services/geminiService.js`). 모델 변경 시 응답 포맷·속도 영향.
- 챗봇 응답에서 검색 결과를 **`released_date` 내림차순으로 수동 재정렬**한다 (`chatbot_service.py`). 정렬 로직 건드리면 답변 품질 변동.
- **LangChain 어댑터는 `langchain-openai`** (LM Studio 의 OpenAI 호환 엔드포인트 호출). `langchain-upstage` 도 설치돼 있지만 현재 미사용(호환성 잔류). 모든 LLM/임베딩은 `AI/lm_studio.py` 의 `get_chat_llm()` / `EmbeddingGemmaEmbeddings` 를 통해서만 생성 — 모델명 하드코딩 금지.
- **EmbeddingGemma 의 task prefix 비대칭**: 인덱싱은 `title: none | text: …`, 질의는 `task: search result | query: …`. `EmbeddingGemmaEmbeddings` 어댑터가 자동 부착하므로 호출 측 코드에서 직접 prefix 붙이지 말 것.
- **챗봇 시스템 프롬프트는 한국어 대화체**. 수정 시 톤 유지.

## Conventions

- 브랜치/커밋: 기본 `master`. feature 브랜치 거의 없이 `master` 에 직접 commit. 메시지는 한국어 짧은 동사구 (`리뷰 수정삭제 기능 구현`, `setup 수정`). `feat:`/`fix:` 같은 prefix 없음.
- 백엔드 코드 스타일: black/ruff 미적용. PEP 8 수준만 유지, 임포트 정렬 강제 안 함.
- 프런트: prettier + eslint(`--fix`) 자동 포맷.

## Where to look for deeper context

각 모듈의 invariants 와 함정은 `.serena/memories/` 에 더 자세히 적혀 있다. 새 작업 시작 전 일독 권장:

- `.serena/memories/core.md` — 모듈 인덱스
- `.serena/memories/conventions.md` — 환경변수 분리, RAG 컬렉션, Django/auth, 브랜치/커밋, CORS
- `.serena/memories/tech_stack.md` — 버전 핀
- `.serena/memories/suggested_commands.md` — 명령어 모음
- `.serena/memories/task_completion.md` — 변경 후 smoke 체크
- `.serena/memories/backend-core/core.md`, `backend-worker/core.md`, `frontend/core.md` — 모듈별 상세

Serena MCP 가 붙어 있으면 `mem:core` 처럼 호출해 빠르게 컨텍스트를 잡을 수 있다.
