@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv (
  echo [1/3] 가상환경 만드는 중...
  python -m venv .venv || (echo Python 3.10 이상을 설치하세요: https://www.python.org/downloads/ & pause & exit /b 1)
)
call .venv\Scripts\activate.bat
echo [2/3] 패키지 설치 중...
pip install -q -r requirements.txt
if not exist .env (
  copy .env.example .env >nul
  echo.
  echo .env 파일을 만들었습니다. 메모장이 열리면 발급받은 키를 넣고 저장한 뒤 이 창으로 돌아오세요.
  notepad .env
)
echo [3/3] 키 점검
python -m bizrag check
pause
