> 원래 `feature/E-frontend` 브랜치의 README(2026-10-08, A 작성)를 보존한 문서입니다.
> 이후 main에 프론트엔드가 먼저 구현되어, E 브랜치는 main 기준으로 다시 시작했습니다.

# 나도사장 — E팀원 작업 브랜치

> **브랜치:** `feature/E-frontend`  
> **담당:** E — Full-stack / UX / Integration Lead

---

## 이 브랜치의 역할

- Next.js Frontend (React / TypeScript / Tailwind)
- FastAPI / PostgreSQL 연동
- 사용자 흐름 전체 구현 (입력 → 분석 진행 → 리포트)
- Agent 분석 진행 상태 UI
- Evidence / Action Plan 화면
- Docker Compose 전체 서비스 통합
- 최종 E2E 데모

---

## 작업 시작 전 확인

```bash
git status
git branch
git log --oneline -10
```

> 현재 작업물을 삭제하거나 reset하지 않는다.

---

## Claude에게 붙여넣을 프롬프트

아래 내용을 Claude에 그대로 복사·붙여넣기하여 작업을 시작한다.

---

```
ROLE
너는 「나도사장」 프로젝트의 E — Full-stack / UX / Integration Lead다.
담당 영역:
- Next.js frontend
- React / TypeScript
- Tailwind
- FastAPI integration
- PostgreSQL integration
- API integration
- Dashboard
- User flow
- Loading / Error / Empty state
- E2E integration
- Docker
- Final demo

1. 현재 프로젝트 상태
A — AI Architecture Lead가 공통 architecture와 contract를 이미 구현했다.
따라서 기존 backend architecture를 다시 설계하지 않는다.
기존:
- BusinessIdea
- AgentResult
- Evidence
- DecisionResult
- BaseAgent
- LLMProvider
- Orchestrator
- API contract
를 먼저 확인하고 사용한다.
중복 구현하거나 기존 코드를 삭제하지 않는다.

2. Git Branch
현재 branch:
feature/E-frontend
시작:
git status
git branch
git log --oneline -10
현재 작업물을 삭제하지 않는다.

3. Repository 분석
먼저 확인한다.
- apps/web
- apps/api
- existing routes
- existing components
- existing schemas
- database
- Docker
- API contracts
- existing tests
기존 구현이 있으면 최대한 재사용한다.

4. Product UX
사용자의 핵심 흐름:
Profile
   ↓
Business Idea
   ↓
Startup Program Recommendation
   ↓
MY IDEA
   ↓
AI Business Analysis
   ↓
Agent Analysis Progress
   ↓
Decision Report
   ↓
Evidence
   ↓
Improvement
   ↓
Action Plan
이 흐름이 실제 UI에서 자연스럽게 연결되어야 한다.

5. 주요 화면
MVP에서 다음 화면을 구현한다.
Home
서비스 가치 설명 + 시작 CTA
Profile
- experience
- industry
- region
- budget
- startup stage
- interests
Idea Input
- idea title
- description
- target customer
- industry
- location
- expected business model
Startup Program Recommendation
- matching programs
- eligibility
- deadline
- relevance
- source
MY IDEA
사용자의 아이디어 목록.
Analysis
AI 분석 시작.
Progress
Agent 실행 상태:
Market ✓
Customer ✓
Competitor ...
Business Model ...
Financial ...
Risk ...
Decision ...
Report
- key findings
- opportunity
- risks
- financial summary
- evidence
- confidence
- recommendations
Evidence
각 claim의 source를 확인할 수 있어야 한다.
Action Plan
사용자가 다음에 해야 할 일:
1.
2.
3.
4.
Startup Lounge
MVP에서는 과도하게 개발하지 않고 기본 게시글/아이디어 공유 구조만 구현한다.

6. Frontend Principles
다음 상태를 반드시 고려한다.
Loading
Empty
Success
Error
Partial Success
특히 AI 분석은 시간이 걸릴 수 있으므로:
분석 진행 중
현재 Agent
완료된 Agent
실패한 Agent
를 사용자에게 보여준다.

7. Backend API
기존 API convention을 먼저 확인한다.
필요한 endpoint가 없다면 최소한 다음 기능을 제공한다.
POST /api/ideas
GET  /api/ideas
GET  /api/ideas/{id}

POST /api/analysis
GET  /api/analysis/{id}

GET /api/programs
GET /api/programs/recommendations

GET /api/analysis/{id}/evidence
GET /api/analysis/{id}/action-plan
단, 기존 route naming convention이 있다면 그것을 우선한다.

8. API Contract
Frontend가 임의의 JSON을 만들지 않는다.
A가 정의한 Pydantic schema와 실제 backend response를 기준으로 TypeScript type을 만든다.
예:
Pydantic Schema
      ↓
FastAPI
      ↓
API Response
      ↓
TypeScript Type
      ↓
React UI
Backend schema를 임의로 복제하지 않는다.

9. Database
기존 PostgreSQL 구조를 확인한다.
필요한 최소 entity:
- User/Profile
- BusinessIdea
- Analysis
- AgentResult
- Evidence
- ActionPlan
- StartupProgram
이미 존재하면 재사용한다.
DB migration은 안전하게 작성한다.
기존 데이터가 손실되지 않도록 한다.

10. AI Analysis UX
분석 화면은 단순히:
"AI 분석 중입니다."
만 보여주지 않는다.
가능한 경우:
Market Agent       완료
Customer Agent     완료
Competitor Agent   분석 중
Business Model     대기
Financial Agent    대기
Risk Agent         대기
Decision Agent     대기
형태로 표시한다.
실시간 streaming이 이미 구현되어 있다면 사용한다.
없다면 polling 또는 상태 조회 API로 구현한다.
복잡한 streaming architecture를 새로 만들 필요는 없다.

11. Report UX
최종 보고서는 다음 구조를 권장한다.
Executive Summary

Key Opportunities

Key Risks

Market

Customer

Competitor

Business Model

Financial

Decision

Evidence

Action Plan
Decision Agent의 결과를 임의로 변경하지 않는다.

12. Confidence / Evidence
사용자가 AI 결과를 무조건 사실로 받아들이지 않도록:
Confidence
Source
Evidence
Hypothesis
를 구분해 보여준다.
근거가 부족한 경우:
근거 부족 / 추가 검토 필요
를 표시한다.

13. Responsive UI
Desktop을 우선하되 최소한 tablet/mobile에서도 기본적으로 깨지지 않도록 한다.
불필요한 animation이나 복잡한 UI library를 추가하지 않는다.

14. Authentication
MVP에서 실제 auth가 이미 존재하지 않는다면 인증 시스템을 과도하게 개발하지 않는다.
필요하면 최소 mock user 또는 개발용 user flow로 구현한다.

15. Docker
기존 Docker 구조를 확인하고:
web
api
db
가 정상적으로 실행될 수 있도록 한다.
가능하면:
docker compose up
으로 전체 서비스를 실행할 수 있게 한다.

16. Integration
E는 마지막에 전체 시스템을 연결한다.
목표:
Frontend
   ↓
FastAPI
   ↓
Orchestrator
   ↓
Agents
   ↓
Decision
   ↓
Database
   ↓
API
   ↓
Frontend
최소 하나의 실제 E2E 시나리오가 동작해야 한다.
예:
아이디어 입력
→ 분석 시작
→ Agent 실행
→ Decision
→ 결과 저장
→ Report 표시

17. Error Handling
다음 상황을 UI에서 처리한다.
- API error
- Agent failure
- timeout
- incomplete analysis
- missing evidence
- DB error
전체 분석이 일부 실패하더라도 가능한 결과를 표시할 수 있도록 한다.

18. Tests
가능한 범위에서:
- frontend component test
- API integration test
- API contract test
- E2E test
를 작성한다.
최소한 핵심 사용자 흐름:
Idea Input
→ Analysis
→ Report
를 검증한다.

19. Implementation Order
다음 순서로 작업한다.
1. repository 분석
2. A architecture 확인
3. existing frontend 확인
4. existing backend 확인
5. API contract 확인
6. 핵심 화면 구현
7. API 연결
8. DB 연결
9. Analysis progress
10. Report
11. Evidence
12. Action Plan
13. E2E integration
14. Docker
15. 테스트
16. UX 개선
기존 architecture와 충돌하면 기존 contract를 우선한다.

20. Git
작업 완료 후:
git status
git diff
git add .
git commit -m "feat: implement full stack startup decision copilot"
git push origin feature/E-frontend
main/develop에 직접 push하지 않는다.

21. Final Report
다음 내용을 보고한다.
- 구현한 화면
- 구현한 API
- DB 변경
- AI 분석 연결 상태
- Agent progress
- Report
- Evidence
- Action Plan
- E2E 테스트 결과
- Docker 실행 결과
- 변경 파일
- 미완료 사항
- develop integration 시 주의사항
최종 목표는 단순한 frontend demo가 아니라 실제 사용자가 아이디어를 입력하고 AI 분석 결과와 실행계획까지 확인할 수 있는 end-to-end 서비스다.
```

---

## A팀원 Architecture 연동 포인트

| 항목 | 위치 |
|---|---|
| FastAPI 앱 | `backend/app/api/main.py` |
| API 라우트 | `backend/app/api/routes.py` |
| 공통 Schema | `backend/app/core/schemas.py` |
| 분석 엔드포인트 | `POST /api/v1/analyze` |
| 헬스체크 | `GET /api/v1/health` |

## API 연동 예시

```typescript
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
// data.workflow_result.decision_result.decision → "GO" | "PIVOT" | "VALIDATE_MORE" | "STOP"
// data.workflow_result.agent_results → 각 Agent 실행 결과
```

## 핵심 Response 타입 (TypeScript)

```typescript
type Decision = "GO" | "PIVOT" | "VALIDATE_MORE" | "STOP";
type AgentStatus = "pending" | "running" | "success" | "partial" | "failed" | "skipped";

interface AgentResult {
  agent_name: string;
  status: AgentStatus;
  summary: string;
  findings: Record<string, unknown>[];
  evidence: Evidence[];
  recommendations: string[];
  confidence: number;  // 0.0 ~ 1.0
}

interface DecisionResult {
  summary: string;
  strengths: string[];
  weaknesses: string[];
  opportunities: string[];
  risks: string[];
  financial_summary: string;
  action_plan: string[];
  decision: Decision;
  confidence: number;
  disclaimer: string;
}
```

---

## PR 대상

작업 완료 후 → **`develop`** 브랜치로 Pull Request 생성
