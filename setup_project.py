import subprocess
import os
import sys
import platform

# 프로젝트 경로 설정
BASE_DIR = os.getcwd()
BACKEND_CORE_DIR = os.path.join(BASE_DIR, "backend-core")
BACKEND_WORKER_DIR = os.path.join(BASE_DIR, "backend-worker")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

def get_venv_python():
    """
    운영체제에 따라 가상환경 내부의 Python 실행 파일 경로를 반환합니다.
    Windows: venv/Scripts/python.exe
    Mac/Linux: venv/bin/python
    """
    venv_dir = os.path.join(BACKEND_CORE_DIR, "venv")
    if platform.system() == "Windows":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        return os.path.join(venv_dir, "bin", "python")

def run_command(command, cwd=None, description=""):
    """
    명령어를 실행하고 결과를 출력하는 함수입니다.
    """
    print(f"\n🚀 [진행 중] {description}...")
    try:
        # 윈도우에서는 shell=True가 필요할 수 있습니다.
        is_windows = platform.system() == "Windows"
        subprocess.check_call(command, cwd=cwd, shell=is_windows)
        print(f"✅ [완료] {description}")
    except subprocess.CalledProcessError as e:
        print(f"❌ [실패] {description} 중 오류가 발생했습니다.")
        print(f"에러 코드: {e}")
        sys.exit(1)

def create_env_files():
    """
    backend-core와 backend-worker에 필요한 .env 파일을 생성합니다.
    이미 파일이 존재하면 생성을 건너뜁니다.
    """
    print("\n🚀 [진행 중] .env 환경 변수 파일 생성 확인...")

    # 1. Backend Core .env 설정
    # LM Studio 게이트웨이(lmstudio.chs135.com)로 챗+임베딩 모두 서빙되는 구성.
    # 게이트웨이가 body 의 "model" 필드 기준으로 라우팅하므로 LM_STUDIO_CHAT_MODEL /
    # LM_STUDIO_EMBED_MODEL 값은 게이트웨이가 인식하는 식별자여야 합니다.
    core_env_path = os.path.join(BACKEND_CORE_DIR, ".env")
    core_env_content = {
        "SECRET_KEY": "django-insecure-change-me-now",
        "DEBUG": "True",
        "ALLOWED_HOSTS": "*",
        # --- LM Studio (LLM + 임베딩) — 외부 게이트웨이로 서빙 중 ---
        # lmstudio.chs135.com 은 body 의 "model" 필드 기준으로 백엔드 인스턴스에 라우팅한다.
        # LM_STUDIO_API_KEY 는 Bearer 토큰으로 사용되므로 반드시 실제 키로 교체해야 한다.
        "LM_STUDIO_BASE_URL": "https://lmstudio.chs135.com/v1",
        "LM_STUDIO_API_KEY": "",
        "LM_STUDIO_CHAT_MODEL": "gemma-4-e4b-it",
        "LM_STUDIO_EMBED_MODEL": "text-embedding-embeddinggemma-300m",
        # --- Legacy (Upstage Solar 미사용, 호환성 위해 빈 값) ---
        "UPSTAGE_API_KEY": "",
        "OPENAI_API_KEY": "",
        "CHROMA_DB_PATH": "./chroma_db",
        "CHROMA_DB_PATH_CRAWLED": "./chroma_db_crawled",
    }
    if not os.path.exists(core_env_path):
        try:
            with open(core_env_path, "w", encoding="utf-8") as f:
                for key, value in core_env_content.items():
                    f.write(f"{key}={value}\n")
            print(f"✅ [완료] backend-core/.env 생성됨 (키 값만 포함)")
        except Exception as e:
            print(f"❌ [실패] backend-core/.env 생성 중 오류: {e}")
    else:
        # 기존 .env 가 있으면 보호하되, 새로 추가된 키가 누락됐는지 검사하여 안내
        try:
            existing_keys = set()
            with open(core_env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        existing_keys.add(line.split("=", 1)[0].strip())
            missing = [k for k in core_env_content if k not in existing_keys]
            if missing:
                print("ℹ️  [정보] backend-core/.env 가 이미 존재합니다.")
                print("⚠️  [주의] 다음 키가 누락되어 있습니다 — 수동으로 추가해주세요:")
                for k in missing:
                    print(f"     {k}={core_env_content[k]}")
            else:
                print("ℹ️  [정보] backend-core/.env 파일이 이미 존재합니다.")
        except Exception as e:
            print(f"⚠️  [주의] backend-core/.env 검사 중 오류: {e}")

    # 2. Backend Worker .env 설정
    worker_env_path = os.path.join(BACKEND_WORKER_DIR, ".env")
    if not os.path.exists(worker_env_path):
        worker_env_content = {
            "PORT": "3000",
            "GEMINI_API_KEY": ""
        }
        try:
            with open(worker_env_path, "w", encoding="utf-8") as f:
                for key, value in worker_env_content.items():
                    f.write(f"{key}={value}\n")
            print(f"✅ [완료] backend-worker/.env 생성됨 (키 값만 포함)")
        except Exception as e:
            print(f"❌ [실패] backend-worker/.env 생성 중 오류: {e}")
    else:
        print("ℹ️  [정보] backend-worker/.env 파일이 이미 존재합니다.")

def main():
    print("="*50)
    print("🛠️  프로젝트 초기 설정(Setup)을 시작합니다.")
    print("="*50)

    # 0. 환경 변수 파일(.env) 생성
    create_env_files()

    # 1. 파이썬 가상환경(venv) 생성
    # backend-core 폴더 안에 'venv'라는 이름으로 가상환경을 만듭니다.
    venv_path = os.path.join(BACKEND_CORE_DIR, "venv")
    if not os.path.exists(venv_path):
        run_command(
            [sys.executable, "-m", "venv", "venv"],
            cwd=BACKEND_CORE_DIR,
            description="파이썬 가상환경 생성"
        )
    else:
        print("\nℹ️  [정보] 가상환경이 이미 존재합니다. 생성을 건너뜁니다.")

    # 가상환경의 python 실행 파일 경로 가져오기
    venv_python = get_venv_python()

    # 2. pip 업그레이드 및 파이썬 패키지 설치
    # 가상환경의 pip를 사용하여 requirements.txt를 설치합니다.
    run_command(
        [venv_python, "-m", "pip", "install", "--upgrade", "pip"],
        cwd=BACKEND_CORE_DIR,
        description="pip 업그레이드"
    )
    
    if os.path.exists(os.path.join(BACKEND_CORE_DIR, "requirements.txt")):
        run_command(
            [venv_python, "-m", "pip", "install", "-r", "requirements.txt"],
            cwd=BACKEND_CORE_DIR,
            description="파이썬 라이브러리 설치 (requirements.txt)"
        )
    else:
        print("\n⚠️  [주의] requirements.txt 파일이 없습니다.")

    # 3. Node.js 패키지 설치 (Backend Worker)
    if os.path.exists(os.path.join(BACKEND_WORKER_DIR, "package.json")):
        run_command(
            ["npm", "install"],
            cwd=BACKEND_WORKER_DIR,
            description="Backend Worker (Node.js) 패키지 설치"
        )

    # 4. Node.js 패키지 설치 (Frontend)
    if os.path.exists(os.path.join(FRONTEND_DIR, "package.json")):
        run_command(
            ["npm", "install"],
            cwd=FRONTEND_DIR,
            description="Frontend (Vue.js) 패키지 설치"
        )

    # 5. Django 데이터베이스 마이그레이션 (DB 생성)
    # makemigrations: 변경사항 감지 파일 생성
    run_command(
        [venv_python, "manage.py", "makemigrations"],
        cwd=BACKEND_CORE_DIR,
        description="Django 마이그레이션 파일 생성 (makemigrations)"
    )
    
    # migrate: 실제 DB에 적용
    run_command(
        [venv_python, "manage.py", "migrate"],
        cwd=BACKEND_CORE_DIR,
        description="데이터베이스 적용 (migrate)"
    )

    # 6. 초기 데이터 로드 (Fixtures)
    # fixture.json 파일이 있다면 DB에 데이터를 넣습니다.
    fixture_path = os.path.join(BACKEND_CORE_DIR, "fixture.json")
    if os.path.exists(fixture_path):
        run_command(
            [venv_python, "manage.py", "loaddata", "fixture.json"],
            cwd=BACKEND_CORE_DIR,
            description="초기 데이터 로드 (fixture.json)"
        )
    else:
        print("\nℹ️  [정보] fixture.json 파일이 없어 데이터 로드를 건너뜁니다.")

    print("\n" + "="*50)
    print("🎉 모든 설정이 완료되었습니다!")
    print("이제 'python run_services.py'를 실행하여 프로젝트를 켤 수 있습니다.")
    print("="*50)

if __name__ == "__main__":
    main()
