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

def main():
    print("="*50)
    print("🛠️  프로젝트 초기 설정(Setup)을 시작합니다.")
    print("="*50)

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
