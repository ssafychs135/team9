# iPhone 리뷰 사이트 (AI 챗봇 포함)

이 프로젝트는 Django 기반의 iPhone 리뷰 사이트이며, Upstage AI 모델을 활용한 챗봇 기능을 포함하고 있습니다. 사용자는 아이폰 모델에 대한 정보를 검색하고, 챗봇과 대화하며 궁금증을 해결할 수 있습니다.

## 🚀 시작하기

프로젝트를 로컬 환경에서 설정하고 실행하는 방법을 안내합니다.

### 📋 전제 조건

*   Python 3.11 이상
*   Node.js (npm 포함)
*   Git

### 🛠️ 설정

#### 1. 저장소 클론

```bash
git clone [저장소_URL]
cd review_site
```

#### 2. Python 환경 설정

가상 환경을 생성하고 활성화한 후, 필요한 Python 패키지들을 설치합니다.

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 프로젝트에 필요한 Python 패키지들을 설치합니다.
# 호환성 문제를 방지하기 위해 특정 버전을 명시합니다.
pip install -r requirements.txt

#### 3. Node.js 환경 설정

프론트엔드 개발 및 빌드를 위한 Node.js 패키지들을 설치합니다.

```bash
npm install
```

#### 4. `.env` 파일 설정

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 다음 환경 변수들을 설정합니다. 이 변수들은 Django 및 AI 챗봇 기능에 필수적입니다.

```
# Django 프로젝트의 보안을 위한 비밀 키 (반드시 고유한 값으로 변경하세요!)
SECRET_KEY='your_django_secret_key_here'

# Upstage AI API 키 (Upstage 개발자 콘솔에서 발급받으세요)
UPSTAGE_API_KEY='your_upstage_api_key_here'

# ChromaDB 데이터가 저장될 경로 (기본값: ./chroma_db_upstage)
# 프로젝트 루트 디렉토리 기준으로 상대 경로를 지정할 수 있습니다.
CHROMA_DB_PATH='./chroma_db_upstage'

# 기타 필요한 환경 변수 (예: 데이터베이스 설정 등)
# DATABASE_URL='...'
```

#### 5. 데이터베이스 설정

Django 마이그레이션을 적용하고, AI 챗봇을 위한 ChromaDB를 구축합니다.

```bash
# Django 데이터베이스 마이그레이션 적용
python manage.py migrate

# iPhone 모델 데이터를 ChromaDB에 임베딩하여 저장 (AI 챗봇 기능에 필수)
# 이 명령은 AI/management/commands/embed_iphone_data.py 스크립트를 실행합니다.
python manage.py embed_iphone_data
```

#### 6. 서버 실행

모든 설정이 완료되면, 다음 명령어를 사용하여 개발 서버를 실행할 수 있습니다. 이 명령어는 Django 백엔드 서버와 필요한 프론트엔드 빌드 프로세스를 동시에 시작합니다.

```bash
npm run dev

```

서버가 성공적으로 실행되면, 웹 브라우저에서 `http://127.0.0.1:8000` (또는 콘솔에 표시되는 주소)으로 접속하여 프로젝트를 확인할 수 있습니다.

### 📝 사용법

*   **리뷰 작성:** 로그인 후 아이폰 모델에 대한 리뷰를 작성할 수 있습니다.
*   **챗봇 대화:** 챗봇 페이지에서 아이폰 모델에 대한 질문을 하거나 일반적인 대화를 나눌 수 있습니다. 챗봇은 질문의 종류에 따라 RAG 검색을 활용하거나 일반적인 답변을 제공합니다.

---
