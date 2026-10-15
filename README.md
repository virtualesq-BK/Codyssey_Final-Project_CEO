# 나도사장 (I'm the Boss)

> **AI 기반 예비창업자 사업성 분석 서비스**  
> 창업 아이디어를 Multi-Agent AI로 분석하여 Go / Pivot / Validate / Stop 의사결정을 지원하는 AI Business Decision Copilot

---

## 프로젝트 개요

예비창업자가 아이디어를 입력하면 7개의 전문 AI 에이전트가 시장·고객·경쟁사·비즈니스모델·재무·리스크를 단계적으로 분석하고, 공공데이터 기반 근거(Evidence)와 함께 창업 여부에 대한 최종 판정을 제공합니다.

- **목표:** 단순 창업정보 챗봇이 아닌, 근거 기반 의사결정 지원
- **원칙:** 임의 수치 생성 금지 — 근거 부족 시 "데이터 부족 / 추가 조사 필요"로 명시
- **배포:**
  - Frontend → [Vercel](https://codyssey-final-project-ceo-g9sg.vercel.app/)
  - Backend → [Render](https://codyssey-final-project-ceo.onrender.com)

---

## 팀원 역할

| 팀원 | 브랜치 | 담당 영역 |
|------|--------|-----------|
| 김병국 | `feature/A-ai-architecture` | AI Architecture Lead — BaseAgent, Orchestrator, DecisionAgent, LLMProvider, 공통 Schema |
| 조경학 | `feature/B-rag-market` | Data / RAG Lead — Shared RAG Infrastructure, MarketAgent, CompetitorAgent, 외부 API 커넥터, Pinecone Vector DB, 법원 판례 수집 |
| 유상우 | `feature/C-business` | Business Lead — CustomerAgent, BusinessModelAgent |
| 전선형 | `feature/D-financial-risk` | Finance / Risk Lead — FinancialAgent, RiskAgent, 재무 계산기 |
| 전지영 | `feature/E-frontend` | Frontend Lead — Next.js UI/UX, Firebase 연동, API 프록시 |

> 브랜치 전략: `feature/*` → `develop` (PR) → `main` (스프린트 종료)

---

## 기술 스택

### Backend

| 항목 | 내용 |
|------|------|
| 언어 | Python 3.11 |
| API Framework | FastAPI 0.115 + Uvicorn |
| LLM | OpenAI GPT-4o / GPT-4o-mini, Anthropic Claude 3.5 Sonnet / Haiku |
| ORM | SQLAlchemy 2.0 (async) + aiosqlite |
| DB | SQLite (개발) / PostgreSQL (프로덕션) |
| HTTP 클라이언트 | httpx |
| 검증 | Pydantic v2 |
| 테스트 | pytest + pytest-asyncio + pytest-mock |

### Frontend

| 항목 | 내용 |
|------|------|
| Framework | Next.js 14 (App Router) |
| 언어 | TypeScript 5 |
| UI | React 18, Tailwind CSS 3 |
| 인증 / DB | Firebase Auth + Firestore |

### 인프라

| 항목 | 내용 |
|------|------|
| 컨테이너 | Docker Compose (로컬 개발) |
| Frontend 배포 | Vercel |
| Backend 배포 | Render |

---

## Multi-Agent 분석 워크플로우

```
사용자 아이디어 입력
        │
  Phase 1 (병렬)
  ┌─────┴──────┐
MarketAgent  CustomerAgent  CompetitorAgent
  └─────┬──────┘
  Phase 2 (순차)
  BusinessModelAgent
        │
  Phase 3 (병렬)
  ┌─────┴──────┐
FinancialAgent  RiskAgent
  └─────┬──────┘
  Phase 4 (순차)
  DecisionAgent
        │
  판정: GO / PIVOT / VALIDATE_MORE / STOP
```

**공공데이터 커넥터 (RAG Evidence):** KOSIS(통계청), Naver DataLab, KIPRIS(특허청), 공공데이터포털, 한국은행, WorldBank, 국가법령정보(법령·판례), Pinecone Vector DB (시맨틱/하이브리드 검색)

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| 사업성 AI 분석 | 아이디어 입력 → 7 에이전트 분석 → 최종 판정 + 근거 리포트 |
| MY아이디어 이력 | 분석 결과 자동 저장 (localStorage + Firestore) |
| 창업 지원 공고 | 정부·지자체 공고 목록 (필터: 마감·지역·분야·키워드) |
| 스타트업 라운지 | 창업 뉴스, 투자 정보, 정부 포털 링크 |
| 인터뷰 모드 | 대화형 아이디어 탐색 + 프로필 구성 |
| 음성 입력 | Web Speech API 기반 아이디어 입력 |
| 판례 기반 리스크 분석 | 법원 판례(law.go.kr) 수집 → 업종별 법적 리스크 근거 제시 |
| 시맨틱 RAG 검색 | Pinecone Vector DB 기반 시맨틱·하이브리드 검색으로 관련 공공데이터 정밀 조회 |

---

## 실행 방법

### 사전 요구사항

- Node.js 18+
- Python 3.11
- Docker (선택, 로컬 통합 실행 시)

### 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성합니다:

```env
# LLM
LLM_PROVIDER=openai          # openai 또는 anthropic
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# 공공 API
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
KOSIS_API_KEY=...
KIPRIS_API_KEY=...
DATA_GO_KR_SERVICE_KEY=...

# DB
DATABASE_URL=sqlite+aiosqlite:///./nadosajang.db
```

`frontend/` 에 `.env.local` 파일을 생성합니다:

```env
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=...
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=...
NEXT_PUBLIC_FIREBASE_APP_ID=...
BACKEND_URL=http://localhost:8000
```

### 로컬 실행 (Docker Compose)

```bash
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs

### 개별 실행

**Backend**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.api.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

### 테스트

```bash
cd backend
pytest
```

---

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/api/v1/analyze` | 사업 아이디어 분석 (전체 워크플로우 실행) |
| `GET` | `/api/v1/programs` | 창업 지원 공고 목록 |
| `GET` | `/api/v1/programs/{id}` | 공고 상세 |
| `GET` | `/api/v1/news` | 창업 관련 뉴스 |
| `POST` | `/api/v1/interview/next` | 인터뷰 다음 질문 |
| `POST` | `/api/v1/interview/profile` | 인터뷰 기반 프로필 생성 |
| `GET` | `/api/v1/health` | 헬스체크 |

---

## 프로젝트 구조

```
.
├── backend/
│   ├── app/
│   │   ├── agents/          # 7개 전문 에이전트 + Orchestrator
│   │   ├── api/             # FastAPI 라우터
│   │   ├── core/            # 공통 Schema, BaseAgent, LLMProvider
│   │   ├── db/              # SQLAlchemy 모델 및 세션
│   │   ├── financial/       # 재무 계산기 (BEP, CAC, LTV 등)
│   │   └── rag/             # RAG 어댑터 및 외부 리트리버
│   └── rag/bizrag/          # Shared RAG 인프라 (벡터 스토어, 커넥터)
├── frontend/
│   └── src/
│       ├── app/             # Next.js App Router 페이지
│       ├── components/      # 공통 UI 컴포넌트
│       ├── contexts/        # Auth Context
│       └── lib/             # API, Firebase, 상태 관리
├── docker-compose.yml
├── render.yaml
└── firebase.json
```

---

## 주요 결과

- 7개 전문 에이전트의 병렬·순차 파이프라인으로 분석 시간 단축
- 공공데이터(KOSIS, 특허청, 공공데이터포털, 한국은행, 법원 판례 등) 기반 Evidence-Chain으로 hallucination 방지
- GO / PIVOT / VALIDATE_MORE / STOP 4단계 판정 + 실행 계획 자동 생성
- Firebase Auth를 통한 소셜 로그인 및 Firestore 기반 분석 이력 영속화
- Next.js API Routes를 프록시 레이어로 활용하여 백엔드 URL 노출 방지
- Pinecone Serverless Vector DB + fastembed 기반 시맨틱·하이브리드 RAG 검색 (벡터 2,773개+)
- 국가법령정보 판례 API 연동 — 창업·소비자·식품위생 등 10개 주제 정기 수집
