@echo off
chcp 65001 >nul
cd /d "%~dp0"
call .venv\Scripts\activate.bat
if not exist logs mkdir logs
python -m bizrag sync >> logs\sync.log 2>&1
