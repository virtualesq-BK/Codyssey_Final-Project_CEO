# 나도사장 (NadoSajang)

> AI 기반 예비창업자 사업성 분석 서비스 — "아이디어 한 줄에서 지원서 재료까지"

---

## 배포 링크

| 서비스 | URL | 플랫폼 |
|---|---|---|
| **Frontend (프론트엔드)** | https://codyssey-final-project.vercel.app | Vercel |
| **Backend API** | https://nadosajang-api.onrender.com | Render |
| **API 문서 (Swagger)** | https://nadosajang-api.onrender.com/docs | Render |
| **Health Check** | https://nadosajang-api.onrender.com/api/v1/health | Render |

> Render 무료 플랜은 비활성 상태에서 스핀다운됩니다. 첫 요청 시 30~60초 지연이 발생할 수 있습니다.

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [문제 정의](#2-문제-정의)
3. [타겟 사용자](#3-타겟-사용자)
4. [서비스 구성](#4-서비스-구성)
5. [서비스 흐름](#5-서비스-흐름)
6. [AI 활용 방식](#6-ai-활용-방식)
7. [기술적 접근 방식](#7-기술적-접근-방식)
8. [프로젝트 구조](#8-프로젝트-구조)
9. [팀 구성 및 담당 업무](#9-팀-구성-및-담당-업무)
10. [일정 계획](#10-일정-계획)
11. [개발 환경 설정](#11-개발-환경-설정)
12. [API 명세](#12-api-명세)
13. [Git 브랜치 전략](#13-git-브랜치-전략)

---

## 1. 프로젝트 개요

**나도사장**은 예비창업자가 사업 아이디어를 입력하면, Multi-Agent AI 시스템이 시장·고객·경쟁·재무·리스크를 자동으로 분석하고 사업성 리포트와 실행 계획을 제공하는 서비스다.  
"창업자판 사람인"을 모토로, 공고 찾기부터 AI 지원서 초안까지 창업 전 과정을 지원한다.

| 항목 | 내용 |
|---|---|
| 개발 기간 | 4주 |
| 팀 규모 | 5명 |
| 주요 기술 | Python · FastAPI · Multi-Agent AI · Next.js · Tailwind CSS |
| GitHub | https://github.com/virtualesq-BK/Codyssey_Final-Project_CEO |

---

## 2. 문제 정의

### 현황

- 한국의 연간 신규 창업 건수는 약 140만 건이지만, 5년 생존율은 30% 미만이다.
- 예비창업자의 대다수는 사업 아이디어가 있어도 **시장 조사·경쟁 분석·재무 계획**을 전문가 없이 스스로 하기 어렵다.
- 정부 창업지원사업은 연간 1조 원 이상 운영되지만, 자신에게 맞는 지원사업을 찾는 것조차 많은 시간이 필요하다.
- 기존 창업 컨설팅은 비용이 높아 초기 창업자가 접근하기 어렵다.

### 핵심 문제

> **"좋은 아이디어를 가진 예비창업자가 전문 분석 없이 섣불리 창업하거나, 분석 비용 때문에 포기한다."**

### 우리의 해결 방식

AI Multi-Agent 시스템으로 전문 컨설팅 수준의 사업성 분석을 **저비용·빠른 속도**로 자동화하고, 맞춤 창업 공고와 지원서 초안까지 한 번에 제공한다.

---

## 3. 타겟 사용자

### Primary User

| 구분 | 내용 |
|---|---|
| 대상 | 예비창업자 (창업 준비 중, 아직 사업자 등록 전) |
| 연령 | 20대 후반 ~ 40대 초반 |
| 특성 | 아이디어는 있으나 시장 분석 경험 부족, 컨설팅 비용 부담 |
| 니즈 | 빠른 사업 타당성 검토, 정부 지원사업 정보, 구체적 실행 계획 |

### Secondary User

- 초기 스타트업 (Seed 이전 단계)
- 대학교 창업 동아리 / 창업 경진대회 참가자
- 창업 교육 기관 (강의 자료로 활용)

---

## 4. 서비스 구성

나도사장은 5개 메뉴로 구성된다.

| 메뉴 | URL | 기능 |
|---|---|---|
| **공고 찾기** | `/programs` | 정부·지자체 창업 지원 공고 검색 및 필터링 (상태·지역·분야·키워드) |
| **MY아이디어** | `/ideas` | AI 진단을 완료한 아이디어 목록 · 판정 결과 카드 조회 |
| **AI 지원서** | `/` | 아이디어 입력 → 6개 에이전트 병렬 분석 → 사업성 판정 (메인 기능) |
| **스타트업라운지** | `/lounge` | 창업 뉴스, 정부 포털, 투자·교육 리소스 링크 모음 |
| **마이페이지** | `/mypage` | 분석 통계 요약, 최근 아이디어 목록, 빠른 메뉴 |

---

## 5. 서비스 흐름

```
[사용자 입력]
  사업 아이디어 (제목·문제·고객·솔루션·산업·지역)
       │
       ▼
[Orchestrator Agent]
  전체 workflow 관리
       │
  ┌────┴────────────────┐
  │ 병렬 실행 (Phase 1) │
  ├─────────────────────┤
  │  MarketAgent        │  → 시장 규모·트렌드 분석
  │  CustomerAgent      │  → 고객 세그먼트·니즈 분석
  │  CompetitorAgent    │  → 경쟁사·차별화 분석
  └─────────────────────┘
       │
       ▼
  BusinessModelAgent    → 수익 모델·가치 제안 분석
       │
  ┌────┴────────────────┐
  │ 병렬 실행 (Phase 3) │
  ├─────────────────────┤
  │  FinancialAgent     │  → 초기 비용·손익분기점
  │  RiskAgent          │  → 리스크 식별·대응책
  └─────────────────────┘
       │
       ▼
  DecisionAgent         → GO / PIVOT / VALIDATE MORE / STOP
       │
       ▼
[결과 출력]
  사업성 리포트 + Action Plan
  + MY아이디어 자동 저장 (localStorage)
```

---

## 6. AI 활용 방식

### Multi-Agent Architecture

각 분석 영역을 독립적인 Agent로 분리하여 전문화된 분석을 수행한다.

| Agent | AI 활용 방법 |
|---|---|
| **MarketAgent** | RAG(Retrieval-Augmented Generation)로 실제 시장 통계·뉴스 검색 후 LLM 종합 분석 |
| **CustomerAgent** | LLM 기반 고객 페르소나 생성, Pain Point / Gain 추출 |
| **CompetitorAgent** | 웹 검색 + LLM으로 경쟁사 비교 분석 |
| **BusinessModelAgent** | LLM 기반 Business Model Canvas 구조화 |
| **FinancialAgent** | 구조화된 계산 + LLM으로 재무 시나리오 생성 |
| **RiskAgent** | LLM 기반 리스크 매트릭스 생성 |
| **DecisionAgent** | 전체 결과 종합 → SWOT + 최종 GO/PIVOT/VALIDATE_MORE/STOP 판정 |

### LLM Provider 추상화

```
Agent → LLMProvider → OpenAI / Anthropic
```

- 환경변수(`LLM_PROVIDER`, `LLM_MODEL`)로 모델 교체 가능
- `OPENAI_BASE_URL` 지원 → 커스텀 프록시 엔드포인트 사용 가능
- API 키는 `.env`에서만 관리

### Evidence 기반 판단 원칙

- 임의의 시장 규모·재무 수치를 생성하지 않는다
- 각 Agent가 수집한 `Evidence`(출처 포함)에 근거한 판단만 수행
- 근거 부족 시 "근거 부족 / 추가 검토 필요"로 명시

---

## 7. 기술적 접근 방식

### Backend

| 구분 | 기술 |
|---|---|
| 언어 | Python 3.11 |
| API Framework | FastAPI |
| AI Orchestration | 자체 Multi-Agent Framework |
| LLM | OpenAI GPT 계열 / Anthropic Claude (환경변수 선택) |
| RAG | bizrag 어댑터 (SQLite Knowledge DB) |
| Database | SQLite (개발) / PostgreSQL (프로덕션 예정) |
| ORM | SQLAlchemy 2.0 (async) |

### Frontend

| 구분 | 기술 |
|---|---|
| Framework | Next.js 14 (App Router) |
| 언어 | TypeScript |
| 스타일 | Tailwind CSS + IBM Plex Sans KR |
| 상태 | React useState + localStorage (아이디어 기록) |
| API 통신 | Next.js API Routes (서버 사이드 프록시) |

### 배포

| 구분 | 기술 | URL |
|---|---|---|
| Frontend | Vercel (Next.js 자동 빌드·배포) | https://codyssey-final-project.vercel.app |
| Backend | Render (Python Web Service, `render.yaml`) | https://nadosajang-api.onrender.com |
| 로컬 개발 | Docker + Docker Compose | `http://localhost:3000` / `http://localhost:8000` |

### 공통 Schema (Pydantic)

```python
BusinessIdea  →  Orchestrator  →  AgentResult × 6  →  DecisionResult
```

모든 Agent 간 데이터는 Pydantic 모델로 타입 검증된다.

---

## 8. 프로젝트 구조

```
Codyssey_Final-Project_CEO/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── schemas.py          # 공통 Domain 모델
│   │   │   ├── base_agent.py       # BaseAgent (retry, logging)
│   │   │   ├── llm_provider.py     # LLM 추상화 (OpenAI / Anthropic)
│   │   │   └── config.py           # .env 자동 로드 (절대 경로)
│   │   ├── agents/
│   │   │   ├── orchestrator.py     # Orchestrator (병렬/순차 workflow)
│   │   │   ├── decision_agent.py   # DecisionAgent (GO/PIVOT/VALIDATE/STOP)
│   │   │   ├── market_agent.py     # MarketAgent (RAG 연동)
│   │   │   ├── business_agents.py  # CustomerAgent, CompetitorAgent, BusinessModelAgent
│   │   │   ├── financial_agent.py  # FinancialAgent
│   │   │   ├── risk_agent.py       # RiskAgent
│   │   │   └── dummy_agents.py     # E2E 테스트용 Dummy
│   │   ├── api/
│   │   │   ├── main.py             # FastAPI app (CORS, lifespan)
│   │   │   └── routes.py           # API endpoints
│   │   ├── rag/
│   │   │   ├── providers.py        # RAG provider 초기화
│   │   │   └── bizrag_adapters.py  # bizrag ↔ Agent 인터페이스 어댑터
│   │   ├── financial/              # 재무 계산 모듈
│   │   ├── risk/                   # 리스크 분류 모듈
│   │   └── db/
│   │       ├── models.py           # SQLAlchemy models
│   │       └── session.py          # DB session (async)
│   ├── api_catalog/                # 창업 공고 수집·저장 모듈
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx            # AI 지원서 (메인 분석 페이지)
│       │   ├── programs/page.tsx   # 공고 찾기
│       │   ├── ideas/page.tsx      # MY아이디어
│       │   ├── lounge/page.tsx     # 스타트업라운지
│       │   ├── mypage/page.tsx     # 마이페이지
│       │   ├── layout.tsx
│       │   ├── globals.css
│       │   └── api/v1/             # Next.js API Routes (백엔드 프록시)
│       │       ├── analyze/route.ts
│       │       ├── health/route.ts
│       │       └── programs/route.ts
│       └── components/
│           ├── Header.tsx          # 네비게이션 (5개 메뉴)
│           ├── AgentResultCard.tsx # 에이전트별 결과 카드
│           └── DecisionBanner.tsx  # 종합 판정 배너
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## 9. 팀 구성 및 담당 업무

### A팀원 — AI Architecture Lead & Frontend
**브랜치:** `feature/A-ai-architecture`

**완료된 작업:**
- [x] 공통 Domain Schema (`BusinessIdea`, `Evidence`, `AgentResult`, `DecisionResult`)
- [x] `BaseAgent` (retry, fallback, token 수집)
- [x] `LLMProvider` 추상화 (OpenAI / Anthropic / Mock, `OPENAI_BASE_URL` 지원)
- [x] `OrchestratorAgent` (병렬/순차 workflow, PARTIAL 상태)
- [x] `DecisionAgent` (SWOT + GO/PIVOT/VALIDATE_MORE/STOP)
- [x] FastAPI 서버 (`/api/v1/analyze`, `/api/v1/health`, `/api/v1/programs`)
- [x] bizrag 어댑터 (RAG provider 주입 인터페이스)
- [x] `.env` 절대 경로 자동 탐색 (`config.py`)
- [x] Next.js 프론트엔드 전체 구현
  - [x] 랜딩 히어로 + 5단계 프로세스 소개
  - [x] AI 사업성 진단 폼 + 6개 에이전트 결과 UI
  - [x] 공고 찾기 (검색·필터·상세 패널)
  - [x] MY아이디어 (localStorage 기반 이력 관리)
  - [x] 스타트업라운지 (뉴스·리소스 링크)
  - [x] 마이페이지 (통계 요약)
- [x] Next.js API Routes 백엔드 프록시 (300초 타임아웃)
- [x] Docker Compose 배포 구성
- [x] Vercel 배포 (Frontend) — `frontend/vercel.json` 설정, Render API URL 환경변수 주입
- [x] Render 배포 (Backend) — `render.yaml` 설정, Python 3.12 고정, 헬스체크 엔드포인트 연결

**남은 작업:**
- [ ] 팀원 실제 Agent 통합 테스트
- [ ] Token usage DB 저장 연동
- [ ] 전체 E2E 통합 테스트
- [ ] Render → PostgreSQL 마이그레이션 (현재 SQLite 사용 중)
- [ ] Vercel 환경변수 `NEXT_PUBLIC_API_URL` 프로덕션 값 고정 확인
- [ ] Render 무료 플랜 스핀다운 개선 (Cron Job 또는 유료 플랜 업그레이드 검토)
- [ ] CI/CD 파이프라인 구성 (GitHub Actions → Vercel·Render 자동 배포)

---

### B팀원 — RAG & Market Agent
**브랜치:** `feature/B-rag-market`

**담당 작업:**
- [ ] **Market Agent** 구현 (RAG 파이프라인 완성)
- [ ] Vector DB 구축 (시장 통계, 뉴스, 산업 보고서)
- [ ] bizrag Knowledge DB 동기화 (`rag/data/knowledge.db`)

**파일 위치:** `backend/app/agents/market_agent.py`

---

### C팀원 — Business Analysis Agent
**브랜치:** `feature/C-business`

**담당 작업:**
- [ ] **CustomerAgent** 구현 (`business_agents.py`)
- [ ] **CompetitorAgent** 구현 (`business_agents.py`)
- [ ] **BusinessModelAgent** 구현 (`business_agents.py`)

---

### D팀원 — Financial & Risk Agent
**브랜치:** `feature/D-financial-risk`

**담당 작업:**
- [ ] **FinancialAgent** 완성 (`financial_agent.py`)
- [ ] **RiskAgent** 완성 (`risk_agent.py`)
- [ ] 재무 계산 로직 단위 테스트

---

### E팀원 — 추가 기능 지원
**브랜치:** `feature/E-frontend`

**담당 작업:**
- [ ] 창업지원사업 공고 실데이터 연동 (`api_catalog` → `/api/v1/programs`)
- [ ] UI/UX 개선 및 반응형 최적화

---

## 10. 일정 계획

| 주차 | 목표 | 완료 기준 |
|---|---|---|
| **1주차** | E2E 골격 연결 | Frontend → FastAPI → Orchestrator → Agents → Frontend 동작 ✅ |
| **2주차** | 핵심 Agent 구현 | MarketAgent RAG 완성, Customer/Competitor/BM Agent LLM 연결 |
| **3주차** | 전체 Agent 통합 | Financial/Risk Agent 완성, 공고 실데이터 연동 |
| **4주차** | 완성 및 배포 | UI 완성, 통합 테스트, 발표 자료 준비 |

---

## 11. 개발 환경 설정

### 사전 요구사항

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (선택)

### 빠른 시작 (Docker Compose)

```bash
git clone https://github.com/virtualesq-BK/Codyssey_Final-Project_CEO.git
cd Codyssey_Final-Project_CEO

# .env 설정
cp .env.example .env
# .env에 OPENAI_API_KEY, OPENAI_BASE_URL 입력

# 전체 서비스 실행
docker compose up --build
# → Frontend: http://localhost:3000
# → Backend API: http://localhost:8000/docs
```

### 로컬 개발

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.api.main:app --reload --port 8000

# Frontend (별도 터미널)
cd frontend
npm install
npm run dev   # → http://localhost:3000
```

### 테스트

```bash
cd backend
python -m pytest tests/ -v
```

### API 동작 확인

```bash
# 헬스 체크
curl http://localhost:8000/api/v1/health

# 사업성 분석
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "title": "배달 세탁 서비스",
    "problem": "직장인 세탁소 방문 불편",
    "customer": "25-40대 직장인",
    "solution": "앱 기반 픽업·배달 세탁",
    "industry": "생활서비스",
    "location": "서울"
  }'

# 창업 공고 목록
curl "http://localhost:8000/api/v1/programs?status=모집중&region=서울"
```

---

## 12. API 명세

### POST /api/v1/analyze

사업 아이디어를 입력받아 Multi-Agent 분석 결과를 반환한다.

**Request Body**

```json
{
  "title": "사업 아이디어 제목",
  "problem": "해결하려는 문제",
  "customer": "타겟 고객",
  "solution": "제안 솔루션",
  "industry": "산업 분야",
  "location": "서울",
  "business_stage": "idea"
}
```

**Response**

```json
{
  "idea_id": "uuid",
  "workflow_result": {
    "status": "success | partial | failed",
    "agent_results": {
      "MarketAgent": { "status": "success", "summary": "...", "confidence": 0.7 }
    },
    "decision_result": {
      "summary": "종합 요약",
      "strengths": ["강점1"],
      "weaknesses": ["약점1"],
      "action_plan": ["1단계: ..."],
      "decision": "GO | PIVOT | VALIDATE_MORE | STOP",
      "confidence": 0.75,
      "disclaimer": "본 분석은 의사결정 지원 목적입니다."
    }
  }
}
```

### GET /api/v1/health

```json
{ "status": "ok", "service": "나도사장 API" }
```

### GET /api/v1/programs

창업 지원 공고 목록을 반환한다.

**Query Parameters**

| 파라미터 | 설명 | 예시 |
|---|---|---|
| `status` | 마감 상태 필터 | `모집중` \| `마감임박(D-3)` \| `마감` |
| `region` | 지역 필터 | `서울`, `경기`, `전국` |
| `category` | 분야 필터 | `청년창업`, `기술창업` |
| `q` | 키워드 검색 | `AI`, `헬스케어` |

**Response**

```json
{
  "total": 8,
  "items": [
    {
      "id": "P001",
      "title": "2024년 초기창업패키지",
      "organization": "중소벤처기업부",
      "category": "창업지원",
      "region": "전국",
      "deadline_status": "모집중",
      "ends_on": "2025-03-31",
      "amount": "최대 1억원",
      "detail_url": "https://www.k-startup.go.kr"
    }
  ]
}
```

---

## 13. Git 브랜치 전략

자세한 내용은 [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md) 참고.

```
main          ← 최종 배포 (PR만 허용)
  └── develop ← 팀 통합 브랜치
       ├── feature/A-ai-architecture  (A팀원)
       ├── feature/B-rag-market       (B팀원)
       ├── feature/C-business         (C팀원)
       ├── feature/D-financial-risk   (D팀원)
       └── feature/E-frontend         (E팀원)
```

**PR 대상:** 모든 feature → `develop`  
**main 직접 push 금지**

---

## 주의사항 및 개발 규칙

- `.env` 파일 commit 절대 금지
- 공통 스키마(`schemas.py`) 변경 시 전체 팀 공지 필수
- Next.js API Routes(`/api/v1/*`)는 백엔드 프록시 역할 — 직접 로직 추가 금지
- 임의의 시장 규모·재무 수치를 LLM으로 생성 금지 (근거 기반 분석 원칙)
- 본 서비스는 **의사결정 지원** 도구이며 실제 사업 성공을 보장하지 않음

---

*본 프로젝트는 Codyssey Final Project로 4주간 개발됩니다.*
