# SummaryHub: AI 기반 YouTube 리뷰 요약 및 RAG 챗봇 플랫폼

## Part 1. 기술 중심 발표 문서 (Technical Document)

### 1. 프로젝트 개요
본 프로젝트는 **YouTube 영상 리뷰 AI 요약 플랫폼**으로, 사용자가 입력한 영상 링크를 기반으로 핵심 내용을 추출하고, 수집된 데이터를 바탕으로 **RAG(검색 증강 생성)** 기반 챗봇과 상호작용할 수 있는 풀스택 웹 애플리케이션입니다.

- **핵심 가치**: 비디오 콘텐츠의 정보 밀도를 높이고, 검증된 데이터를 바탕으로 한 AI 대화 경험 제공.
- **아키텍처**: Frontend, Backend-Core, Backend-Worker로 분리된 **Microservices Architecture (MSA)**.

### 2. 기술 스택 상세 (Detailed Tech Stack)

| 구분 | 주요 기술 |
| :--- | :--- |
| **Frontend** | Vue 3 (Composition API), Vite, Pinia, Vue Router, Axios, Marked (Markdown) |
| **Backend Core** | Django 5.2.8, DRF, SQLite, **ChromaDB (Vector DB)**, LangChain, Selenium |
| **Backend Worker** | Node.js, Express.js, Google Gemini AI, youtube-caption-extractor |
| **UI/UX** | Apple-inspired Design System, Scoped CSS, Dark Mode Support |

### 3. 백엔드 설계 패러다임 (Backend Design Paradigms)
각 앱은 서비스 성격에 맞춰 독립적인 설계 철학을 유지합니다.

*   **Accounts (인증)**: **Library-driven API**. `dj-rest-auth` 및 `allauth` 라이브러리를 활용하여 검증된 표준 보안 프로토콜을 구현했습니다.
*   **Reviews (커뮤니티)**: **Pure REST API**. DRF `ModelViewSet`과 `drf-nested-routers`를 사용하여 `/reviews/{id}/comments/`와 같은 계층적인 RESTful 엔드포인트를 구축했습니다.
*   **AI (챗봇)**: **Service-oriented RAG**. `chatbot_service.py`에 비즈니스 로직을 분리하여 캡슐화하고, ChromaDB를 통한 검색 증강 생성 로직을 구현했습니다.

### 4. 프론트엔드 아키텍처 (Frontend Architecture)
*   **Component-Based**: Composition API 및 SFC(Single File Components)를 통한 높은 재사용성.
*   **State Management**: Pinia를 활용한 중앙 집중식 상태 관리 및 `localStorage` 연동을 통한 인증 영속성 유지.
*   **Security**: Vue Router의 **Navigation Guards**(`requireAuth`, `requireGuest`)를 통한 세밀한 접근 제어.

---

## Part 2. 발표 스크립트 (Speech Script) - 약 8분 분량

### 1. 도입 및 프로젝트 비전 (0:00 ~ 1:00)
안녕하세요, **"AI 기반 YouTube 리뷰 요약 및 RAG 챗봇 플랫폼"** 발표를 맡은 [이름]입니다.
저희 프로젝트는 "영상은 길고 시간은 부족한" 현대인의 문제를 해결하기 위해 시작되었습니다. 단순히 영상을 요약하는 것에 그치지 않고, 요약된 데이터와 수집된 전문 지식을 바탕으로 AI와 깊이 있는 대화를 나눌 수 있는 환경을 구축했습니다.

### 2. MSA 기반 시스템 아키텍처 (1:00 ~ 2:30)
저희 시스템은 확장성과 유지보수성을 극대화하기 위해 세 가지 마이크로서비스로 분리되어 있습니다.
- **Frontend**는 Vue 3를 사용하여 미려한 인터페이스를 제공하며,
- **Backend Core**는 Django REST Framework를 통해 데이터와 RAG 엔진을 관리합니다.
- 특히, 영상 분석과 같은 무거운 작업은 Node.js 기반의 **Backend Worker**가 전담하도록 설계하여, 메인 서버의 응답성을 보장하고 전체적인 시스템 부하를 분산시켰습니다.

### 3. 기술적 도전: 백엔드 설계 (2:30 ~ 4:30)
백엔드 구현 시 가장 신경 쓴 부분은 **"적재적소의 설계 패러다임 적용"**입니다. 
인증 시스템은 검증된 라이브러리인 `dj-rest-auth`를 활용해 보안 안정성을 높였고, 리뷰 시스템은 DRF의 `ModelViewSet`과 커스텀 권한 클래스를 통해 계층적이고 안전한 REST API를 구축했습니다.
가장 핵심인 AI 앱은 **RAG(검색 증강 생성)** 패러다임을 채택했습니다. 사용자의 질문이 들어오면 **ChromaDB**라는 벡터 데이터베이스에서 관련 정보를 먼저 검색하고, 그 컨텍스트를 LLM에 전달하여 답변의 신뢰도를 획기적으로 높였습니다.

### 4. 사용자 경험: 프론트엔드 아키텍처 (4:30 ~ 6:00)
프론트엔드는 **Vue 3의 Composition API**를 적극 활용하여 로직의 재사용성을 극대화했습니다. 
**Pinia** 상태 저장소를 통해 인증 정보를 중앙 관리하며, 사용자가 새로고침을 하더라도 로그인 상태가 유지되도록 영속성을 확보했습니다. 또한, **Navigation Guards**를 구현하여 비인가 사용자의 접근을 원천 차단하는 등 보안과 UX를 동시에 고려했습니다. 디자인적으로는 Apple 스타일의 미니멀한 Aesthetic을 적용하여 사용자가 정보에만 집중할 수 있는 깔끔한 환경을 제공합니다.

### 5. 주요 성과 및 결론 (6:00 ~ 8:00)
본 프로젝트는 **YouTube 자막 추출, Gemini AI 요약, 그리고 ChromaDB 기반 RAG**라는 복잡한 파이프라인을 성공적으로 통합했습니다.
이를 통해 사용자는 긴 영상을 직접 보지 않고도 핵심을 파악하고, 궁금한 점은 챗봇을 통해 데이터 기반의 답변을 얻을 수 있습니다. 앞으로는 더 다양한 도메인의 데이터를 학습시켜 서비스의 전문성을 확장해 나갈 계획입니다. 이상으로 발표를 마치겠습니다. 감사합니다.
