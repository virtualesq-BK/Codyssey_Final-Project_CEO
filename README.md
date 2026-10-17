# 나도사장 (I'm the Boss)

> **AI 기반 예비창업자 사업성 분석 서비스**  
> 창업 아이디어를 Multi-Agent AI로 분석하여 Go / Pivot / Validate / Stop 의사결정을 지원하는 AI Business Decision Copilot

---

## 프로젝트 개요

예비창업자가 아이디어를 입력하면 7개의 전문 AI 에이전트가 시장·고객·경쟁사·비즈니스모델·재무·리스크를 단계적으로 분석하고, 공공데이터 기반 근거(Evidence)와 함께 창업 여부에 대한 최종 판정을 제공합니다.

- **목표:** 단순 창업정보 챗봇이 아닌, 근거 기반 의사결정 지원
- **원칙:** 임의 수치 생성 금지 — 근거 부족 시 "데이터 부족 / 추가 조사 필요"로 명시
- **배포:**
  - Frontend → [Vercel](https://codyssey-final-project-ceo-g9sg.vercel.app/) https://codyssey-final-project-ceo-g9sg.vercel.app/
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
| **MY지원서** | 보고서가 완성된 아이디어로 창업 지원 공고에 지원서 생성·관리 |
| **모두의 창업 지원서 자동 작성** | "모두의 창업" 선택 시 AI가 보고서 데이터 기반으로 6개 문항 자동 작성 |

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
| `POST` | `/api/v1/report/scores` | 보고서 영역별 점수 채점 (1~10점) |
| `POST` | `/api/v1/report/profile-digest` | 프로필 섹션 요약 생성 |
| `POST` | `/api/v1/report/modues-application` | 모두의 창업 지원서 6개 문항 AI 자동 작성 |
| `GET` | `/api/v1/market/sizing` | TAM·SAM·SOM 시장 규모 계산 |
| `POST` | `/api/v1/finance/statement` | 손익계산서 생성 |
| `GET` | `/api/v1/health` | 헬스체크 |

---

## 프로젝트 구조

```
.
├── backend/
│   ├── app/
│   │   ├── agents/          # 7개 전문 에이전트 + Orchestrator
│   │   ├── api/             # FastAPI 라우터
│   │   │   ├── routes.py            # 분석·공고 라우터
│   │   │   ├── report_routes.py     # 보고서 점수·요약·모두의창업 자동작성
│   │   │   ├── finance_routes.py    # 손익계산서
│   │   │   ├── market_routes.py     # 시장 규모 (TAM/SAM/SOM)
│   │   │   ├── interview_routes.py  # 인터뷰 대화
│   │   │   └── analyze_jobs.py      # 비동기 분석 작업 관리
│   │   ├── core/            # 공통 Schema, BaseAgent, LLMProvider
│   │   ├── db/              # SQLAlchemy 모델 및 세션
│   │   ├── financial/       # 재무 계산기 (BEP, CAC, LTV 등)
│   │   └── rag/             # RAG 어댑터 및 외부 리트리버
│   └── rag/bizrag/          # Shared RAG 인프라 (벡터 스토어, 커넥터)
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── ideas/               # MY아이디어 페이지·상세
│       │   ├── applications/        # MY지원서 관리
│       │   ├── programs/            # 창업 지원 공고
│       │   ├── lounge/              # 스타트업 라운지
│       │   └── api/v1/             # Next.js API 프록시 라우터
│       ├── components/
│       │   ├── NewApplicationDialog.tsx  # 지원서 생성 다이얼로그 (모두의창업 폼 포함)
│       │   └── ...
│       ├── contexts/        # Auth Context
│       └── lib/
│           ├── application.ts       # 지원서 타입 (ModeusAnswers 포함)
│           ├── applicationStore.ts  # 지원서 저장소 (Firestore/localStorage)
│           ├── programs.ts          # 공고 타입 + PINNED_PROGRAMS 상수
│           └── ...
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
- **MY지원서 기능** — 보고서가 완성된 아이디어 기반 지원서 생성·상태 관리 (Firestore/localStorage)
- **모두의 창업 지원서 AI 자동 작성** — 보고서 DecisionResult 데이터를 LLM에 전달하여 6개 문항(Q1~Q4-2) 자동 생성

---

## 변경 이력

### v1.2.0 (2026-10-18)

**MY지원서 & 모두의 창업 지원서 자동 작성**

- `frontend/src/lib/programs.ts`: `PINNED_PROGRAMS` 상수 추가 — "모두의 창업" 공고를 상시 노출
- `frontend/src/lib/application.ts`: `ModeusAnswers` 타입 및 `Application.modeusAnswers` 필드 추가
- `frontend/src/lib/applicationStore.ts`: `createApplication`에 `modeusAnswers` 파라미터 추가
- `frontend/src/components/NewApplicationDialog.tsx`:
  - 지원사업 목록 상단에 "모두의 창업" 항상 표시 (상시 뱃지)
  - "모두의 창업" 선택 → "지원서 작성하기" 클릭 시 백엔드 LLM 호출로 6문항 자동 작성
  - `step: "select" | "modues-form"` 상태로 다이얼로그 2-step 전환
  - 글자수 카운터 및 초과 시 시각적 경고
- `frontend/src/app/api/v1/report/modues-application/route.ts`: Next.js 프록시 라우트 신규 추가
- `backend/app/api/report_routes.py`: `POST /api/v1/report/modues-application` LLM 자동 작성 엔드포인트 추가
  - 보고서 프로필 + DecisionResult(강점·약점·기회·실행계획 등)를 LLM에 전달
  - Q1(100자)~Q4-2(1000자) 6개 문항 응답, 글자수 초과 자동 트리밍
