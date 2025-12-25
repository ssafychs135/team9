# SummaryHub (써머리허브) 프로젝트 개요

이 프로젝트는 YouTube 영상 리뷰를 AI로 요약하고 공유하며, 챗봇과 상호작용할 수 있는 웹 애플리케이션입니다. 프론트엔드, 백엔드 API 서버, 그리고 별도의 워커 서비스로 구성된 마이크로서비스 아키텍처를 지향하고 있습니다.

## 📂 프로젝트 구조

프로젝트는 크게 세 가지 주요 디렉토리로 구성되어 있습니다:

- **frontend/**: 사용자 인터페이스를 담당하는 Vue.js 애플리케이션
- **backend-core/**: 메인 API 서버 역할을 하는 Django REST Framework 애플리케이션
- **backend-worker/**: 영상 처리 및 AI 요약을 담당하는 Node.js 마이크로서비스

## 🛠 사용 기술 스택

### 1. Frontend (`frontend/`)
- **Framework**: Vue.js 3 (Composition API)
- **Build Tool**: Vite
- **State Management**: Pinia
- **Routing**: Vue Router
- **HTTP Client**: Axios
- **Styling**: CSS (Apple-inspired aesthetic)
- **Markdown**: marked (마크다운 렌더링)

### 2. Backend Core (`backend-core/`)
- **Framework**: Django 5.2.8
- **API**: Django REST Framework (DRF)
- **Authentication**: dj-rest-auth, django-allauth (Token Authentication)
- **Database**: SQLite (기본), ChromaDB (Vector DB for RAG)
- **AI/LLM**: LangChain, OpenAI API, Google GenAI
- **Crawling/Data**: BeautifulSoup4, Selenium

### 3. Backend Worker (`backend-worker/`)
- **Runtime**: Node.js
- **Framework**: Express.js
- **AI**: Google Generative AI (Gemini)
- **YouTube Tools**: youtube-caption-extractor

## 🏗 백엔드 앱별 설계 패러다임

각 Django 앱은 그 목적에 따라 서로 다른 설계 방식과 패러다임을 채택하고 있습니다.

### 1. `accounts` (사용자 인증)
- **방식**: **Library-driven REST API**
- **설명**: `dj-rest-auth`와 `allauth` 라이브러리를 기반으로 구현되었습니다. 직접적인 View 작성보다는 검증된 라이브러리의 엔드포인트를 활용하여 보안성과 표준성을 높인 방식입니다.

### 2. `reviews` (게시글 및 댓글 관리)
- **방식**: **Pure REST API (ViewSet-based)**
- **설명**: 
    - 과거의 Template 기반 FBV 코드는 주석 처리되어 있으며, 현재는 **Django REST Framework (DRF)**의 **ModelViewSet**을 전적으로 사용하여 클라이언트(Vue.js)와 통신합니다.
    - `drf-nested-routers`를 활용하여 `/reviews/{id}/comments/`와 같은 직관적이고 계층적인 URL 구조를 구현했습니다.
    - `IsOwnerOrReadOnly`와 같은 커스텀 권한 클래스를 통해 리소스 접근 제어를 체계적으로 관리합니다.

### 3. `AI` (챗봇 서비스)
- **방식**: **Service-oriented RAG Paradigm**
- **설명**: 
    - **Functional API**: 복잡한 비즈니스 로직보다는 데이터 처리에 집중하기 위해 함수형 뷰(FBV)를 주로 사용합니다.
    - **RAG (Retrieval-Augmented Generation)**: 단순히 LLM에 질의하는 것이 아니라, `ChromaDB`에서 관련 정보를 검색한 후 답변을 생성하는 검색 증강 생성 방식을 채택하고 있습니다. 비즈니스 로직은 `chatbot_service.py`에 분리되어 서비스 레이어처럼 동작합니다.

## 🎨 프론트엔드 아키텍처

프론트엔드는 사용자 경험(UX)과 유지보수성을 최우선으로 고려하여 **Vue 3** 생태계를 기반으로 설계되었습니다.

### 1. Component-Based Architecture
- **Composition API**: 모든 컴포넌트는 `<script setup>` 문법과 Composition API를 사용하여 로직의 재사용성과 가독성을 극대화했습니다.
- **Single File Components (SFC)**: HTML, JavaScript, CSS를 하나의 `.vue` 파일로 캡슐화하여 컴포넌트 단위의 독립적인 개발과 관리가 가능합니다.

### 2. State Management (Pinia)
- **Centralized Store**: `authStore`를 통해 사용자 인증 토큰, 로그인 상태, 사용자 정보를 중앙에서 관리합니다.
- **Persistence**: `localStorage`와 연동하여 브라우저 새로고침 시에도 로그인 상태가 유지되도록 구현했습니다.

### 3. Routing & Navigation Guards
- **Vue Router**: SPA(Single Page Application) 라우팅을 담당하며, 각 페이지 뷰는 **Lazy Loading**(`() => import(...)`)을 적용하여 초기 로딩 속도를 최적화했습니다.
- **Navigation Guards**: 
    - `requireAuth`: 챗봇, 리뷰 작성/수정 등 로그인이 필요한 페이지 접근을 제어합니다.
    - `requireGuest`: 로그인 및 회원가입 페이지에 이미 인증된 사용자가 접근하는 것을 방지합니다.

### 4. Styling & Design System
- **Scoped CSS**: 컴포넌트 간 스타일 충돌을 방지하기 위해 Scoped 스타일을 기본으로 사용합니다.
- **Apple-inspired Design**: `base.css`에 정의된 CSS 변수(`--c-background`, `--c-accent` 등)를 활용하여 일관된 디자인 시스템을 구축했으며, 미려하고 현대적인 UI/UX를 제공합니다.
- **Dark Mode Support**: 시스템 설정에 따른 다크 모드를 지원하여 사용자 환경에 최적화된 시각 경험을 제공합니다.

## 🚀 주요 기능

1.  **사용자 인증**: 회원가입, 로그인, 로그아웃 (Token 기반)
2.  **리뷰 관리**:
    - YouTube 링크 입력을 통한 AI 자동 요약 및 리뷰 생성
    - 리뷰 목록 조회, 상세 보기, 수정, 삭제
    - Markdown 형식의 본문 지원
3.  **댓글 시스템**: 리뷰에 대한 댓글 작성 및 조회
4.  **AI 챗봇**:
    - LangChain과 ChromaDB를 활용한 RAG(검색 증강 생성) 기반 챗봇
    - iPhone 관련 스펙 및 정보 질의응답 기능

## ⚙️ 실행 방법

각 서비스는 독립적으로 실행됩니다.

1.  **Frontend**: `npm run dev` (Port 5173)
2.  **Backend Core**: `python manage.py runserver` (Port 8000)
3.  **Backend Worker**: `npm start` (Port 3000)

## 📝 개발 환경
- **OS**: macOS (Darwin)
- **Version Control**: Git
