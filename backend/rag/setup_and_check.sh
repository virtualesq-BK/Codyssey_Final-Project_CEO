#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "[1/3] 가상환경 만드는 중..."
  python3 -m venv .venv
fi
source .venv/bin/activate
echo "[2/3] 패키지 설치 중..."
pip install -q -r requirements.txt
if [ ! -f .env ]; then
  cp .env.example .env
  echo ".env 파일을 만들었습니다. 키를 넣고 저장한 뒤 다시 실행하세요: ${EDITOR:-nano} .env"
  exit 0
fi
echo "[3/3] 키 점검"
python -m bizrag check
