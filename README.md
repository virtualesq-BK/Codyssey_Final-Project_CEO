# 나도사장 (NadoSajang)

> AI 기반 예비창업자 사업성 분석 서비스

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [문제 정의](#2-문제-정의)
3. [타겟 사용자](#3-타겟-사용자)
4. [서비스 흐름](#4-서비스-흐름)
5. [AI 활용 방식](#5-ai-활용-방식)
6. [기술적 접근 방식](#6-기술적-접근-방식)
7. [프로젝트 구조](#7-프로젝트-구조)
8. [팀 구성 및 담당 업무](#8-팀-구성-및-담당-업무)
9. [일정 계획](#9-일정-계획)
10. [개발 환경 설정](#10-개발-환경-설정)
11. [API 명세](#11-api-명세)
12. [Git 브랜치 전략](#12-git-브랜치-전략)

---

## 1. 프로젝트 개요

**나도사장**은 예비창업자가 자신의 프로필과 사업 아이디어를 입력하면, Multi-Agent AI 시스템이 시장·고객·경쟁·재무·리스크를 자동으로 분석하고 사업성 리포트와 실행 계획을 제공하는 서비스다.

| 항목 | 내용 |
|---|---|
| 개발 기간 | 4주 |
| 팀 규모 | 5명 |
| 주요 기술 | Python, FastAPI, LangChain/LLM, React/Next.js |
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

AI Multi-Agent 시스템으로 전문 컨설팅 수준의 사업성 분석을 **저비용·빠른 속도**로 자동화한다.

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

## 4. 서비스 흐름

```
[사용자 입력]
  사업 아이디어 + 프로필
       │
       ▼
[Orchestrator Agent]
  전체 workflow 관리
       │
  ┌────┴────────────────┐
  │ 병렬 실행 (Phase 1) │
  ├─────────────────────┤
  │  Market Agent       │  → 시장 규모·트렌드 분석
  │  Customer Agent     │  → 고객 세그먼트·니즈 분석
  │  Competitor Agent   │  → 경쟁사·차별화 분석
  └─────────────────────┘
       │
       ▼
  BusinessModel Agent    → 수익 모델·가치 제안 분석
       │
  ┌────┴────────────────┐
  │ 병렬 실행 (Phase 3) │
  ├─────────────────────┤
  │  Financial Agent    │  → 초기 비용·손익분기점
  │  Risk Agent         │  → 리스크 식별·대응책
  └─────────────────────┘
       │
       ▼
  Decision Agent         → 종합 판단 (GO / PIVOT / VALIDATE MORE / STOP)
       │
       ▼
[결과 출력]
  사업성 리포트 + Action Plan
```

---

## 5. AI 활용 방식

### Multi-Agent Architecture

각 분석 영역을 독립적인 Agent로 분리하여 전문화된 분석을 수행한다.

| Agent | AI 활용 방법 |
|---|---|
| **Market Agent** | RAG(Retrieval-Augmented Generation)로 실제 시장 통계·뉴스 검색 후 LLM이 종합 분석 |
| **Customer Agent** | LLM 기반 고객 페르소나 생성, 고객 Pain Point 추출 |
| **Competitor Agent** | 웹 검색 + LLM으로 경쟁사 비교 분석 |
| **BusinessModel Agent** | LLM 기반 비즈니스 모델 Canvas 구조화 |
| **Financial Agent** | 구조화된 계산 + LLM으로 재무 시나리오 생성 |
| **Risk Agent** | LLM 기반 리스크 매트릭스 생성 |
| **Decision Agent** | 모든 Agent 결과를 종합하여 SWOT + 최종 판단 생성 |

### LLM Provider 추상화

```
Agent → LLMProvider → OpenAI / Anthropic
```

- 환경변수(`LLM_PROVIDER`, `LLM_MODEL`)로 모델 교체 가능
- API 키는 `.env`에서만 관리

### Evidence 기반 판단 원칙

- 임의의 시장 규모·재무 수치를 생성하지 않는다
- 각 Agent가 수집한 `Evidence`(출처 포함)에 근거한 판단만 수행
- 근거 부족 시 "근거 부족 / 추가 검토 필요"로 명시

---

## 6. 기술적 접근 방식

### Backend

| 구분 | 기술 |
|---|---|
| 언어 | Python 3.11 |
| API Framework | FastAPI |
| AI Orchestration | 자체 Multi-Agent Framework |
| LLM | OpenAI GPT-4o / Anthropic Claude (환경변수 선택) |
| RAG | LangChain + Vector DB (B팀원 구현) |
| Database | SQLite (개발) / PostgreSQL (프로덕션 예정) |
| ORM | SQLAlchemy 2.0 (async) |

### Frontend

| 구분 | 기술 |
|---|---|
| Framework | React / Next.js |
| 스타일 | Tailwind CSS |
| 상태관리 | (E팀원 선택) |
| API 통신 | fetch / axios |

### 공통 Schema (Pydantic)

```python
BusinessIdea  →  Orchestrator  →  AgentResult × 6  →  DecisionResult
```

모든 Agent 간 데이터는 Pydantic 모델로 타입 검증된다.

---

## 7. 프로젝트 구조

```
Codyssey_Final-Project_CEO/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── schemas.py        # 공통 Domain 모델 (BusinessIdea, AgentResult 등)
│   │   │   ├── base_agent.py     # BaseAgent (retry, logging)
│   │   │   ├── llm_provider.py   # LLM 추상화 (OpenAI / Anthropic / Mock)
│   │   │   └── config.py         # 환경변수 설정
│   │   ├── agents/
│   │   │   ├── orchestrator.py   # Orchestrator Agent
│   │   │   ├── decision_agent.py # Decision Agent
│   │   │   ├── dummy_agents.py   # 1주차 E2E용 Dummy Agents
│   │   │   ├── market_agent.py   # (B팀원 구현)
│   │   │   ├── customer_agent.py # (C팀원 구현)
│   │   │   ├── competitor_agent.py # (C팀원 구현)
│   │   │   ├── bm_agent.py       # (C팀원 구현)
│   │   │   ├── financial_agent.py # (D팀원 구현)
│   │   │   └── risk_agent.py     # (D팀원 구현)
│   │   ├── api/
│   │   │   ├── main.py           # FastAPI app
│   │   │   └── routes.py         # API endpoints
│   │   └── db/
│   │       ├── models.py         # SQLAlchemy models
│   │       └── session.py        # DB session
│   ├── tests/
│   │   ├── test_schemas.py
│   │   ├── test_llm_provider.py
│   │   ├── test_orchestrator.py
│   │   ├── test_decision_agent.py
│   │   └── test_agent_failure.py
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/                     # (E팀원 구현)
│   └── src/
├── docs/
│   └── GIT_WORKFLOW.md
├── .env.example
├── .gitignore
└── README.md
```

---

## 8. 팀 구성 및 담당 업무

### A팀원 — AI Architecture Lead
**브랜치:** `feature/A-ai-architecture`

**완료된 작업:**
- [x] 공통 Domain Schema (`BusinessIdea`, `Evidence`, `AgentResult`, `DecisionResult`)
- [x] `BaseAgent` (retry, fallback, token 수집)
- [x] `LLMProvider` 추상화 (OpenAI / Anthropic / Mock)
- [x] `OrchestratorAgent` (병렬/순차 workflow, PARTIAL 상태)
- [x] `DecisionAgent` (SWOT + GO/PIVOT/VALIDATE_MORE/STOP)
- [x] `DummyAgents` (1주차 E2E 연결용)
- [x] FastAPI 서버 (`/api/v1/analyze`, `/api/v1/health`)
- [x] 29개 테스트 통과

**남은 작업:**
- [ ] 팀원 실제 Agent를 Orchestrator에 등록
- [ ] Token usage DB 저장 연동
- [ ] 창업지원사업 Agent 추가 (B팀원과 협력)
- [ ] 전체 E2E 통합 테스트

**Integration 규칙 (다른 팀원 참고):**

```python
# 자신의 Agent를 이렇게 만들면 바로 연결된다
from app.core.base_agent import BaseAgent
from app.core.schemas import AgentResult, AgentStatus, BusinessIdea

class MyAgent(BaseAgent):
    async def _execute(self, idea: BusinessIdea) -> AgentResult:
        raw = await self.llm.generate(f"분석 대상: {idea.title}")
        return AgentResult(
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            summary="분석 완료",
            confidence=0.7,
        )
```

---

### B팀원 — RAG & Market Agent
**브랜치:** `feature/B-rag-market`

**담당 작업:**
- [ ] **창업지원사업 검색 Agent** 구현
  - 중소벤처기업부, K-스타트업 등 공공데이터 수집
  - 사용자 조건(업종, 지역, 단계)에 맞는 지원사업 매칭
- [ ] **Market Agent** 구현 (dummy → 실제 RAG)
  - Vector DB 구축 (시장 통계, 뉴스, 산업 보고서)
  - RAG 파이프라인: 검색 → 청킹 → 임베딩 → 생성
  - 출처 포함 `Evidence` 반환
- [ ] Vector DB 선택 및 설정 (Chroma / Pinecone / Weaviate)
- [ ] 데이터 수집 스크립트 작성

**파일 위치:** `backend/app/agents/market_agent.py` (신규 생성)

**A팀원과 협의 필요:**
- `MarketAgent` 클래스 이름 및 파일명 확정
- `Evidence` 스키마에 추가 필드 필요 시 사전 공지

---

### C팀원 — Business Analysis Agent
**브랜치:** `feature/C-business`

**담당 작업:**
- [ ] **Customer Agent** 구현 (dummy → 실제)
  - 타겟 고객 세그먼트 분석
  - 고객 페르소나 생성
  - Pain Point / Gain 분석
- [ ] **Competitor Agent** 구현 (dummy → 실제)
  - 직접/간접 경쟁사 식별
  - 경쟁사 포지셔닝 분석
  - 차별화 전략 도출
- [ ] **BusinessModel Agent** 구현 (dummy → 실제)
  - Business Model Canvas 자동 생성
  - 수익 모델 타당성 분석
  - 가치 제안 명확화

**파일 위치:**
- `backend/app/agents/customer_agent.py`
- `backend/app/agents/competitor_agent.py`
- `backend/app/agents/bm_agent.py`

**A팀원과 협의 필요:**
- `BusinessModelAgent` 클래스명 확정 (현재 Orchestrator에 `BusinessModelAgent`로 등록됨)

---

### D팀원 — Financial & Risk Agent
**브랜치:** `feature/D-financial-risk`

**담당 작업:**
- [ ] **Financial Agent** 구현 (dummy → 실제)
  - 초기 투자 비용 추정
  - 월 운영비 / BEP(손익분기점) 계산
  - 3년 재무 시나리오 (낙관/기본/비관)
  - 임의 수치 생성 금지 — 입력 기반 계산 원칙
- [ ] **Risk Agent** 구현 (dummy → 실제)
  - 시장/운영/재무/규제 리스크 매트릭스
  - 리스크 심각도 × 발생 가능성 평가
  - 리스크별 대응 전략 제시
- [ ] 재무 계산 로직 단위 테스트 작성

**파일 위치:**
- `backend/app/agents/financial_agent.py`
- `backend/app/agents/risk_agent.py`

**주의사항:**
- 재무 수치는 반드시 사용자 입력(`user_profile.capital` 등) 기반으로 계산
- 근거 없는 시장 규모 수치 사용 금지

---

### E팀원 — Frontend
**브랜치:** `feature/E-frontend`

**담당 작업:**
- [ ] **입력 페이지** — 사업 아이디어 + 사용자 프로필 입력 폼
- [ ] **분석 진행 페이지** — 각 Agent 실행 상태 실시간 표시
- [ ] **결과 리포트 페이지** — SWOT, 재무 요약, Action Plan 시각화
- [ ] **창업지원사업 추천** 카드 UI
- [ ] **Decision Badge** — GO / PIVOT / VALIDATE MORE / STOP 시각화
- [ ] FastAPI 연동 (`POST /api/v1/analyze`)

**API 연동 예시:**

```javascript
const response = await fetch('/api/v1/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: "배달 세탁 서비스",
    problem: "직장인 세탁소 방문 불편",
    customer: "25-40대 직장인",
    solution: "앱 기반 픽업·배달 세탁",
    industry: "생활서비스",
    location: "서울"
  })
});
const data = await response.json();
// data.workflow_result.decision_result.decision → "GO" | "PIVOT" | ...
```

**파일 위치:** `frontend/` 디렉터리 (구조는 E팀원 선택)

---

## 9. 일정 계획

### 전체 일정 (4주)

| 주차 | 목표 | 완료 기준 |
|---|---|---|
| **1주차** | E2E 골격 연결 | Frontend → FastAPI → Orchestrator → Dummy Agents → DecisionResult → Frontend 동작 |
| **2주차** | 핵심 Agent 구현 | Market / Customer / Competitor Agent 실제 LLM 연결, RAG 파이프라인 구축 |
| **3주차** | 전체 Agent 통합 | Financial / Risk Agent 완성, Decision Agent 품질 개선, 창업지원사업 검색 완성 |
| **4주차** | 완성 및 배포 | UI 완성, 통합 테스트, 발표 자료 준비 |

### 1주차 상세 계획 (현재 진행 중)

| 담당 | 이번 주 할 일 | 완료 기준 |
|---|---|---|
| **A** | ~~Architecture 구현~~ (완료), Orchestrator 안정화 | 테스트 29개 통과 ✅ |
| **B** | Vector DB 선택, 데이터 수집 파이프라인 설계 | `market_agent.py` 더미 → 실제 1차 연결 |
| **C** | Customer / Competitor Agent 1차 구현 | `customer_agent.py`, `competitor_agent.py` 초안 |
| **D** | Financial / Risk Agent 1차 구현 | `financial_agent.py`, `risk_agent.py` 초안 |
| **E** | Frontend 환경 세팅, 입력 폼 + API 연동 | `/api/v1/analyze` 호출 후 결과 화면 출력 |

### 2주차 목표

- B: RAG 파이프라인 완성 (Retrieval + Generation)
- C: 3개 Agent LLM 연결 완료
- D: 재무 계산 로직 구현
- E: 결과 리포트 페이지 UI 완성
- A: 실제 Agent 교체 및 통합 테스트

### 3주차 목표

- 전체 Agent 실제 데이터로 E2E 동작
- Decision Agent 품질 개선
- 창업지원사업 검색 기능 완성

### 4주차 목표

- 버그 수정 및 성능 최적화
- UI/UX 개선
- 발표 데모 준비

---

## 10. 개발 환경 설정

### 사전 요구사항

- Python 3.11+
- Node.js 18+ (Frontend)
- Git

### Backend 설정

```bash
# 1. 저장소 clone
git clone https://github.com/virtualesq-BK/Codyssey_Final-Project_CEO.git
cd Codyssey_Final-Project_CEO

# 2. 자신의 브랜치 checkout
git checkout feature/B-rag-market   # 예시

# 3. 가상환경 생성 및 패키지 설치
cd backend
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 4. 환경변수 설정
cp ../.env.example .env
# .env에 OPENAI_API_KEY 또는 ANTHROPIC_API_KEY 입력

# 5. 서버 실행
python -m uvicorn app.api.main:app --reload
# → http://localhost:8000/docs

# 6. 테스트 실행
python -m pytest tests/ -v
```

### API 동작 확인

```bash
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
```

---

## 11. API 명세

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
  "business_stage": "idea",
  "user_profile": {
    "name": "홍길동",
    "capital": 5000,
    "background": "IT 개발자",
    "region": "서울"
  }
}
```

**Response**

```json
{
  "idea_id": "uuid",
  "workflow_result": {
    "status": "success",
    "agent_results": {
      "MarketAgent": { "status": "success", "summary": "...", "confidence": 0.7 },
      "CustomerAgent": { "..." },
      "DecisionAgent": { "..." }
    },
    "decision_result": {
      "summary": "종합 요약",
      "strengths": ["강점1"],
      "weaknesses": ["약점1"],
      "opportunities": ["기회1"],
      "risks": ["위험1"],
      "financial_summary": "...",
      "action_plan": ["1단계: ...", "2단계: ..."],
      "decision": "GO",
      "confidence": 0.75,
      "disclaimer": "본 분석은 의사결정 지원 목적이며 실제 사업 성공을 보장하지 않습니다."
    }
  }
}
```

### GET /api/v1/health

서버 상태 확인

```json
{ "status": "ok", "service": "나도사장 API" }
```

---

## 12. Git 브랜치 전략

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
- 테스트 없이 PR 금지
- 임의의 시장 규모·재무 수치를 LLM으로 생성 금지 (근거 기반 분석 원칙)
- 본 서비스는 **의사결정 지원** 도구이며 실제 사업 성공을 보장하지 않음

---

*본 프로젝트는 Codyssey Final Project로 4주간 개발됩니다.*
