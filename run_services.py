import subprocess
import time
import os
import signal
import sys
import platform

# 프로젝트 경로 설정
BASE_DIR = os.getcwd()
BACKEND_CORE_DIR = os.path.join(BASE_DIR, "backend-core")

def get_venv_python():
    """
    가상환경이 존재하면 가상환경의 python 경로를, 
    없으면 시스템의 python(현재 실행 중인 python)을 반환합니다.
    """
    venv_dir = os.path.join(BACKEND_CORE_DIR, "venv")
    
    if platform.system() == "Windows":
        venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        venv_python = os.path.join(venv_dir, "bin", "python")
        
    if os.path.exists(venv_python):
        return venv_python
    else:
        # 가상환경이 없으면 현재 이 스크립트를 실행한 파이썬을 사용
        return sys.executable

# Django 실행 시 사용할 파이썬 명령어 결정
django_python_cmd = get_venv_python()

# 실행할 서비스들의 설정 정보입니다.
services = [
    {
        "name": "Backend Core (Django)",
        # 가상환경의 파이썬 경로를 사용하여 manage.py를 실행합니다.
        "command": [django_python_cmd, "manage.py", "runserver"],
        "cwd": "backend-core"
    },
    {
        "name": "Backend Worker (Node.js)",
        "command": ["npm", "run", "dev"],
        "cwd": "backend-worker"
    },
    {
        "name": "Frontend (Vue.js)",
        "command": ["npm", "run", "dev"],
        "cwd": "frontend"
    }
]

processes = []

def start_services():
    """서비스들을 차례대로 실행하는 함수"""
    print("🚀 모든 서비스 시작 중...")
    print(f"ℹ️  Django는 다음 파이썬을 사용합니다: {django_python_cmd}")
    
    for service in services:
        try:
            print(f"[{service['name']}] 실행 중... (위치: {service['cwd']})")
            
            is_windows = platform.system() == "Windows"
            process = subprocess.Popen(
                service['command'],
                cwd=service['cwd'],
                shell=is_windows  # 윈도우 호환성을 위해 조정
            )
            processes.append((service['name'], process))
            
        except FileNotFoundError:
            print(f"❌ 오류: '{service['cwd']}' 폴더를 찾을 수 없거나 명령어를 실행할 수 없습니다.")
        except Exception as e:
            print(f"❌ 오류 발생 ({service['name']}): {e}")

    print("\n✅ 모든 서비스가 백그라운드에서 실행되었습니다.")
    print("종료하려면 'Ctrl + C'를 누르세요.\n")

def stop_services(signum, frame):
    """Ctrl+C 종료 처리 함수"""
    print("\n\n🛑 서비스 종료 중...")
    
    for name, process in processes:
        print(f"[{name}] 종료하는 중...")
        # 윈도우에서는 taskkill로 프로세스 트리를 강제 종료해야 깔끔하게 닫힙니다.
        if platform.system() == "Windows":
             subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
        else:
            process.terminate()
    
    print("✅ 모든 서비스가 종료되었습니다.")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, stop_services)
    start_services()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_services(None, None)