# 나도사장 — C팀원 작업 지침

> **브랜치:** `feature/C-business`
> **담당:** C — Customer / Business Model Lead

---

## 이 브랜치의 역할

- Customer Agent (Persona, JTBD, Pain Point, Customer Need)
- Business Model Agent (Revenue Model, Pricing, Channel, Customer Acquisition)
- Value Proposition 분석
- Business Model validation 및 관련 테스트

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
너는 「나도사장」 프로젝트의 C — Customer / Business Model Lead다.
담당 영역은 다음과 같다.
- Customer Agent
- Persona
- JTBD
- Pain Point
- Customer Need
- Value Proposition
- Business Model Agent
- Revenue Model
- Pricing
- Channel
- Customer Acquisition
- Business Model validation
- 관련 테스트

1. 현재 프로젝트 상태
A — AI Architecture Lead가 이미 공통 Architecture와 Contract를 구현했다.
따라서 기존 architecture를 다시 설계하지 않는다.
이미 존재하는 것을 우선 사용한다.
- BusinessIdea
- AgentResult
- Evidence
- DecisionResult
- BaseAgent
- LLMProvider
- Orchestrator
- shared schemas
- logging
- error handling
- test framework
절대로 중복 구현하지 않는다.
특히:
BaseAgent
AgentResult
BusinessIdea
Evidence
LLMProvider
를 새로 만들지 않는다.
먼저 repository를 검사하고 실제 구현을 확인한다.

2. Git Branch
현재 branch:
feature/C-business
작업 시작:
git status
git branch
git log --oneline -10
현재 branch의 작업을 삭제하거나 reset하지 않는다.

3. Repository 분석
먼저:
1. domain schema
2. BaseAgent
3. AgentResult
4. BusinessIdea
5. Evidence
6. LLMProvider
7. Orchestrator
8. B가 구현 중인 RAG interface
9. 기존 API
10. 테스트 구조
를 확인한다.
B의 RAG implementation을 직접 수정하지 말고 정해진 interface를 소비하는 방식으로 구현한다.

4. Customer Agent
Customer Agent를 구현한다.
입력:
BusinessIdea
출력:
AgentResult
분석:
- Target Customer
- Primary Customer
- Secondary Customer
- Persona
- Customer segment
- Pain point
- Need
- JTBD
- Purchase motivation
- Purchase barrier
- Willingness to pay hypothesis
- Customer acquisition hypothesis
중요:
AI가 실제 고객 데이터를 확보하지 못했다면 이를 사실처럼 표현하지 않는다.
다음 세 가지를 구분한다.
Fact
Hypothesis
Recommendation

5. Persona
Persona는 가능한 경우 structured output으로 제공한다.
예:
{
  "segment": "...",
  "persona": "...",
  "needs": [],
  "pain_points": [],
  "jobs_to_be_done": [],
  "buying_motivation": [],
  "buying_barriers": []
}
실제 사용자 조사가 없으면:
가설 기반 Persona
임을 명확히 한다.

6. Business Model Agent
Business Model Agent를 구현한다.
분석:
- Value Proposition
- Customer Segment
- Revenue Model
- Pricing
- Sales Channel
- Distribution
- Customer Acquisition
- Key Activities
- Key Resources
- Partners
- Cost Structure
- Competitive differentiation
가능하면 Business Model Canvas 구조와 연결한다.

7. Customer → Business Model Dependency
Business Model Agent는 Customer Agent 결과를 활용할 수 있어야 한다.
개념:
BusinessIdea
     ↓
Customer Agent
     ↓
Customer Profile
     ↓
Business Model Agent
     ↓
Value Proposition / Pricing / Channel
그러나 기존 Orchestrator architecture를 임의로 변경하지 않는다.
필요한 dependency는 기존 interface를 통해 연결한다.

8. Evidence
가능한 경우 다음을 구분한다.
Evidence-backed finding
Hypothesis
Recommendation
시장 데이터나 고객 행동에 관한 근거가 없으면 임의의 통계나 수치를 생성하지 않는다.
예:
"이 가격이면 고객이 구매할 것이다"
라고 단정하지 않는다.
대신:
"가격 민감도가 높을 가능성이 있으므로 가격 검증이 필요하다."
와 같이 표현한다.

9. RAG 사용
B가 구축한 Shared RAG가 제공하는 interface를 사용한다.
별도의 RAG 시스템을 만들지 않는다.
Customer Agent:
- customer research
- public statistics
- industry data
- demographic information
- relevant reports
Business Model Agent:
- pricing benchmarks
- business model examples
- industry practices
등을 필요에 따라 검색한다.
데이터가 없으면 RAG 결과를 억지로 만들지 않는다.

10. Tests
다음을 테스트한다.
Customer Agent
- valid BusinessIdea
- valid AgentResult
- persona structure
- JTBD
- fact/hypothesis distinction
- insufficient evidence
Business Model Agent
- value proposition
- revenue model
- pricing hypothesis
- channel
- customer acquisition
- structured output
LLM의 정확한 문장 자체를 테스트하지 말고 schema와 constraint를 테스트한다.

11. Integration
최종적으로 다음과 연결될 수 있어야 한다.
Orchestrator
      ↓
Customer Agent
      ↓
Business Model Agent
      ↓
Decision Agent
단, A가 만든 Orchestrator를 무단으로 재작성하지 않는다.
Decision Agent가 소비할 수 있는 structured result를 제공한다.

12. Implementation
다음 순서로 진행한다.
1. Repository 분석
2. A architecture 확인
3. Customer Agent 구현
4. Business Model Agent 구현
5. Shared RAG interface 연결
6. Evidence 연결
7. 테스트
8. 기존 테스트 실행
9. type/lint 검사
10. integration 확인
가능한 오류는 직접 수정한다.
불필요하게 사용자에게 질문하지 않는다.

13. Git
작업 완료:
git status
git diff
git add .
git commit -m "feat: implement customer and business model agents"
git push origin feature/C-business
remote가 없는 경우 commit까지만 하고 필요한 명령을 보고한다.
절대 main/develop에 직접 push하지 않는다.

14. Final Report
다음 내용을 보고한다.
- Customer Agent 구현 내용
- Business Model Agent 구현 내용
- 변경 파일
- 테스트 결과
- RAG 연결 상태
- Evidence 연결 상태
- A architecture와의 integration 상태
- Decision Agent에 전달되는 output
- 미완료 사항
- integration 시 주의사항
최종 목표는 고객을 가정해서 설명하는 챗봇이 아니라, 고객과 비즈니스 모델에 대한 검증 가능한 분석 Agent를 만드는 것이다.
```

---

## A팀원 Architecture 연동 포인트

| 항목 | 위치 |
|---|---|
| 공통 Schema | `backend/app/core/schemas.py` |
| BaseAgent | `backend/app/core/base_agent.py` |
| LLMProvider | `backend/app/core/llm_provider.py` |
| Orchestrator | `backend/app/agents/orchestrator.py` |
| 기존 Dummy | `backend/app/agents/dummy_agents.py` |

`CustomerAgent`, `BusinessModelAgent`는 `dummy_agents.py`의 Dummy를 대체한다.
Orchestrator에 등록된 클래스명(`CustomerAgent`, `BusinessModelAgent`)을 그대로 유지한다.

---

## PR 대상

작업 완료 후 → **`develop`** 브랜치로 Pull Request 생성
