# Codyssey_Final-Project_CEO — 나도사장

창업 아이디어를 분석하고 의사결정을 지원하는 AI Business Decision Copilot 프로젝트입니다.

## 코드 구성

- `backend/app/core`: 공통 스키마, BaseAgent, LLMProvider 및 설정
- `backend/app/agents`: Orchestrator, DecisionAgent, 고객·비즈니스 모델 분석 Agent
- `backend/app/api`: FastAPI 분석·상태 확인 API
- `backend/api_catalog`: K-Startup 공고·첨부·참고자료 수집 도구
- `backend/tests`: 공통 계약 및 분석 Agent 테스트

## 실행 및 검증

Python 가상 환경에서 다음 명령을 실행합니다.

```bash
pip install -r backend/requirements.txt
cd backend
python -m pytest -q
uvicorn app.api.main:app --reload
```

LLM 호출을 위해 `backend/.env`에 루트 `.env.example`의 설정을 복사하고 실제 API 키를 입력합니다.
API 키가 포함된 `.env`는 커밋하지 않습니다. 테스트는 MockProvider를 사용합니다.

K-Startup 수집 도구의 설정·실행 방법은 [수집 도구 안내](backend/api_catalog/README.md)를 확인하세요.
해당 도구의 테스트는 `backend/api_catalog`에서 `python -X utf8 -m unittest discover -s tests -v`로 실행합니다.
Windows에서는 UTF-8 모드를 지정해 한글 자료를 읽는 테스트의 기본 인코딩 차이를 방지합니다.

## 팀 작업 및 연동

작업 브랜치에서 커밋·푸시하고 PR을 통해 `develop`에 병합합니다.

- [C팀 작업 지침](docs/C-business-work-guide.md)
- [고객·비즈니스 모델 연동 안내](docs/C-business-integration.md)

CustomerAgent와 BusinessModelAgent는 기존 공통 계약을 사용합니다.
Shared RAG 실제 연결과 실 API 검증은 B팀 인터페이스 및 인증 설정이 준비된 뒤 진행합니다.
그 전에는 근거 부족 항목을 가설과 추가 검증 사항으로 반환합니다.
