#  ReviewSite: AI-Powered Review Hub (Project Documentation)

이 문서는 ReviewSite 프로젝트의 아키텍처, 핵심 기술 구현, 그리고 개발 중 적용된 최적화 기법들에 대한 상세 정보를 기술합니다.

---

## 📂 프로젝트 구조 및 서비스 아키텍처

저희 프로젝트는 확장성과 효율적인 리소스 관리를 위해 **마이크로서비스 지향 아키텍처(MSA)**를 채택하고 있습니다.

- **Frontend (Vue.js 3)**: 사용자 인터페이스 및 상태 관리를 담당하는 SPA.
- **Backend Core (Django DRF)**: 메인 API 서버로, 인증, 데이터 CRUD, RAG 기반 지능형 서비스를 처리합니다.
- **Backend Worker (Node.js/Express)**: 외부 API와의 통신 및 무거운 연산(유튜브 자막 추출 및 AI 요약)을 분리하여 메인 서버의 부하를 최소화합니다.

---

## 🛠 핵심 기술 스택 및 구현 디테일

### 1. 지능형 AI 에이전트 (AI & LLM)
- **RAG (Retrieval-Augmented Generation)**: 단순히 모델의 지식에 의존하지 않고, **ChromaDB** 벡터 데이터베이스에 저장된 실제 iPhone 스펙 데이터를 검색하여 답변의 정확도를 극대화했습니다.
- **LangChain Framework**: 대화 기록 관리 및 **Self-Querying Retriever**를 구현하여 사용자의 질문 의도에 따른 정밀한 메타데이터 필터링을 수행합니다.
- **Multi-Model Pipeline**: 챗봇에는 **Upstage Solar Pro**를, 영상 요약에는 **Google Gemini** 모델을 사용하여 각 도메인에 최적화된 성능을 구현했습니다.

### 2. 프론트엔드 아키텍처 및 UI/UX
- **Custom Global Modal System**: 브라우저의 기본 `window.alert`과 `confirm`을 완전히 대체하는 **Promise 기반 커스텀 모달**을 구축했습니다. 디자인 일관성을 확보하고 비동기 흐름 제어의 가독성을 높였습니다.
- **Atomic CSS Refactoring**: 파편화된 스타일을 `base.css`의 전역 변수와 유틸리티 클래스로 통합하여 중복 코드를 80% 이상 제거하고 유지보수성을 향상시켰습니다.
- **Responsive Layout**: `aspect-ratio`를 이용한 16:9 영상 비율 유지, `line-clamp`를 활용한 텍스트 요약 처리 등 디테일한 UI 구현이 적용되었습니다.

### 3. 운영 및 시스템 안정성 (Stability)
- **Standard Stream Control**: 데이터 관리(`dumpdata`) 시 시스템 로그가 JSON 출력물에 섞이지 않도록 모든 초기화 및 비즈니스 로그를 **표준 에러(stderr)** 채널로 격리 출력하도록 설계했습니다.
- **Automated Environment Setup**: `setup_project.py` 스크립트를 통해 가상환경 구축, 의존성 설치, `.env` 환경 변수 템플릿 생성을 자동화하여 개발 환경의 파편화를 방지했습니다.

---

## 🏗 백엔드 설계 패러다임

| 앱(App) | 설계 방식 | 핵심 특징 |
| :--- | :--- | :--- |
| **accounts** | **Library-driven** | `dj-rest-auth` 및 `allauth` 기반의 표준화된 보안 인증 |
| **reviews** | **Pure REST API** | `ViewSet` 및 중첩 라우팅을 통한 계층적 리소스 관리 |
| **AI** | **Service-oriented RAG** | 별도의 서비스 레이어(`chatbot_service.py`)를 통한 비즈니스 로직 분리 |

---

## ⚙️ 실행 및 관리 가이드

1.  **초기 설정**: `python setup_project.py` 실행 (가상환경 및 환경 변수 자동 세팅)
2.  **서비스 실행**: `python run_services.py` 실행 (모든 마이크로서비스 동시 가동)
3.  **데이터 백업**: `python manage.py dumpdata > fixture.json` (로그 간섭 없는 안전한 덤프 가능)

---

## 📝 개발 환경 및 사양
- **Frontend**: Vue 3, Pinia, Vue Router, Axios, Vite
- **Backend**: Python 3.10+, Django 5.2.8, Node.js 20+
- **Database**: SQLite (Relational), ChromaDB (Vector)
- **VCS**: Git (branch-based workflow)
