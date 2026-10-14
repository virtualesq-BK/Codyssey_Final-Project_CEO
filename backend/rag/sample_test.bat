@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv (
  echo 가상환경 만드는 중...
  python -m venv .venv || (echo Python 3.10 이상을 설치하세요 & pause & exit /b 1)
  call .venv\Scripts\activate.bat
  pip install -q -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)
python sample_test.py
pause
