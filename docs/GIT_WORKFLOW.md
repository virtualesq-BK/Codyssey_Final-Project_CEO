# Git Workflow — 나도사장 팀 개발 규칙

## 브랜치 구조

```
main
  │   (최종 안정 버전, PR을 통해서만 merge)
  └── develop
       │   (팀 통합 개발 브랜치, 모든 feature의 merge 대상)
       ├── feature/A-ai-architecture
       ├── feature/B-rag-market
       ├── feature/C-business
       ├── feature/D-financial-risk
       └── feature/E-frontend
```

## 브랜치별 담당자 및 역할

| 브랜치 | 담당 | 주요 작업 |
|---|---|---|
| `main` | 전체 | 최종 배포 버전. 직접 push 금지 |
| `develop` | 전체 | 팀 통합 브랜치. feature → develop PR 병합 |
| `feature/A-ai-architecture` | A팀원 | BaseAgent, Orchestrator, DecisionAgent, LLMProvider, 공통 Schema |
| `feature/B-rag-market` | B팀원 | RAG 기반 시장/Market Agent, 창업지원사업 검색 Agent |
| `feature/C-business` | C팀원 | Customer Agent, Competitor Agent, BusinessModel Agent |
| `feature/D-financial-risk` | D팀원 | Financial Agent, Risk Agent |
| `feature/E-frontend` | E팀원 | Frontend (React/Next.js), UI/UX, API 연동 |

---

## 작업 시작 방법 (팀원 각자)

### 1. Repository clone

```bash
git clone https://github.com/virtualesq-BK/Codyssey_Final-Project_CEO.git
cd Codyssey_Final-Project_CEO
```

### 2. 자신의 feature 브랜치로 전환

```bash
# A팀원
git checkout feature/A-ai-architecture

# B팀원
git checkout feature/B-rag-market

# C팀원
git checkout feature/C-business

# D팀원
git checkout feature/D-financial-risk

# E팀원
git checkout feature/E-frontend
```

### 3. develop 최신 변경사항 동기화 (작업 시작 전 항상 실행)

```bash
git fetch origin
git rebase origin/develop
# 또는
git merge origin/develop
```

---

## 개발 → PR → Merge 사이클

```
feature/X 브랜치에서 작업
    ↓
git add / git commit
    ↓
git push origin feature/X
    ↓
GitHub에서 develop 대상 Pull Request 생성
    ↓
팀원 코드 리뷰 (선택)
    ↓
develop에 Merge
    ↓
(스프린트 종료 시) develop → main PR 생성 후 Merge
```

---

## Commit 메시지 규칙

```
<type>(<scope>): <짧은 설명>

예시:
feat(market-agent): 창업지원사업 검색 기능 추가
fix(orchestrator): 병렬 실행 오류 수정
test(decision): Decision Agent mock 테스트 추가
docs(workflow): GIT_WORKFLOW 문서 작성
```

| type | 설명 |
|---|---|
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `test` | 테스트 추가/수정 |
| `refactor` | 리팩토링 |
| `docs` | 문서 |
| `chore` | 빌드, 설정 등 |

---

## 충돌 방지를 위한 공통 파일 목록

아래 파일은 여러 팀원이 동시에 수정할 가능성이 높다.  
**수정 전 반드시 팀 채널에 공지하고, 작업 후 즉시 PR을 올린다.**

| 파일 | 주의 사항 |
|---|---|
| `backend/app/core/schemas.py` | 공통 Domain Schema. 변경 시 전체 팀 영향. 반드시 사전 합의 |
| `backend/app/core/base_agent.py` | 모든 Agent의 기반. 변경 시 A팀원과 협의 |
| `backend/app/core/llm_provider.py` | LLM 추상화. API 변경 시 A팀원과 협의 |
| `backend/app/agents/orchestrator.py` | Agent 등록/연결 포인트. A팀원 담당 |
| `backend/requirements.txt` | 패키지 추가 시 팀 공지 후 수정 |
| `backend/app/api/routes.py` | API endpoint. 추가 시 팀 공지 |

---

## 금지 사항

- `main`에 직접 `git push` 금지
- 다른 팀원의 feature 브랜치에 push 금지
- `git push --force` 금지 (본인 feature 브랜치 제외, 신중하게)
- `.env` 파일 commit 금지 (`.env.example` 참고)
- 테스트 없이 develop PR 금지

---

## GitHub Remote URL

```
https://github.com/virtualesq-BK/Codyssey_Final-Project_CEO.git
```

## PR 생성 대상 브랜치

모든 feature 브랜치의 PR 대상: **`develop`**  
`develop` → `main` PR은 스프린트 종료 시 팀장 승인 후 진행
