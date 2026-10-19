# 나도사장 — 프로젝트 기획서

> AI 기반 예비창업자 사업성 분석 서비스

---

## 1. 문제 정의

### 1.1 현황 분석

| 지표 | 수치 |
|---|---|
| 연간 신규 창업 건수 | 약 140만 건 |
| 5년 생존율 | 30% 미만 |
| 정부 창업지원 예산 | 연간 1조 원 이상 |
| 창업 컨설팅 비용 (1회) | 수십만 ~ 수백만 원 |

### 1.2 핵심 문제

> **"좋은 아이디어를 가진 예비창업자가 전문 분석 없이 섣불리 창업하거나, 분석 비용 때문에 아예 포기한다."**

**세부 Pain Point:**

1. **정보 비대칭** — 시장 규모, 경쟁사, 재무 추정을 개인이 검증하기 어려움
2. **비용 장벽** — 전문 창업 컨설팅 접근이 사실상 어려운 초기 창업자
3. **시간 비용** — 지원사업 공고 파악에만 수십 시간 소요
4. **낮은 실행률** — 막연한 불안과 정보 부족으로 아이디어 단계에서 포기

### 1.3 해결 방향

Multi-Agent AI 시스템으로 전문 컨설팅 수준의 분석을 **저비용·고속**으로 자동화하고, 창업 공고 탐색부터 지원서 초안 작성까지 원스톱으로 제공한다.

---

## 2. 타겟 사용자

### 2.1 Primary User

| 구분 | 내용 |
|---|---|
| 대상 | 예비창업자 (사업자 등록 전, 아이디어 단계) |
| 연령대 | 20대 후반 ~ 40대 초반 |
| 특성 | 아이디어 보유, 시장 분석 경험 부족, 컨설팅 비용 부담 |
| 주요 니즈 | 빠른 사업 타당성 검토, 정부 지원사업 정보, 구체적 실행 계획 |

**핵심 사용자 시나리오:**
- 퇴직 후 창업을 준비하는 40대 직장인이 배달 세탁 아이디어를 가지고 있으나 시장 규모를 모름
- 졸업을 앞둔 대학생이 AI 기반 서비스를 기획하고 창업경진대회 지원서를 써야 함
- 부업에서 시작해 독립 사업화를 고민 중인 20대 프리랜서

### 2.2 Secondary User

- 초기 스타트업 (Seed 이전 단계) — 투자 유치 전 사업계획 검증
- 대학교 창업 동아리 / 창업 경진대회 참가자
- 창업 교육 기관 — 교육 실습 도구로 활용

---

## 3. AI 활용 방식

### 3.1 Multi-Agent Architecture

총 **8개의 AI 에이전트**가 역할별로 협력한다.

- **분석 파이프라인 에이전트 (7개, Orchestrator 관리):** 사업 아이디어를 입력받아 GO/PIVOT/VALIDATE_MORE/STOP 판정을 산출한다.
- **인터뷰/프로필 에이전트 (1개, 독립 운영):** 대화형 인터뷰로 아이디어를 탐색하고 아이템 프로필 초안을 생성한다.

#### 분석 파이프라인 (7개)

```
[사용자 입력]
  사업 아이디어 (제목·문제·고객·솔루션·산업·지역)
        │
        ▼
[Orchestrator Agent]  ← 전체 workflow 관리
        │
  ┌─────┴───────────────────────────────┐
  │          Phase 1: 병렬 실행          │
  │  MarketAgent  CustomerAgent  CompetitorAgent
  └─────────────────────────────────────┘
        │
        ▼
  BusinessModelAgent  (Phase 2: 순차)
        │
  ┌─────┴───────────────────────────────┐
  │          Phase 3: 병렬 실행          │
  │        FinancialAgent  RiskAgent    │
  └─────────────────────────────────────┘
        │
        ▼
  DecisionAgent → GO / PIVOT / VALIDATE_MORE / STOP
```

### 3.2 에이전트별 AI 활용 전략

| Agent | AI 활용 방법 | 핵심 출력 |
|---|---|---|
**분석 파이프라인 (Orchestrator, 7개)**

| Agent | AI 활용 방법 | 핵심 출력 |
|---|---|---|
| **MarketAgent** | RAG + KOSIS·DataLab 실데이터 → LLM 종합 | 시장 규모, 성장률, 트렌드 |
| **CustomerAgent** | LLM 기반 페르소나 생성, Pain/Gain 추출 | 고객 세그먼트, 핵심 니즈 |
| **CompetitorAgent** | 웹 검색 + LLM 경쟁사 비교 분석 | 경쟁 구도, 차별화 포인트 |
| **BusinessModelAgent** | LLM 기반 Business Model Canvas 구조화 | 수익 모델, 가치 제안 |
| **FinancialAgent** | 구조화 계산 + LLM 시나리오 생성 | 초기 비용, 손익분기점 |
| **RiskAgent** | LLM 기반 리스크 매트릭스 생성 | 리스크 항목, 대응 전략 |
| **DecisionAgent** | 전체 결과 종합 → SWOT + 판정 | 최종 GO/PIVOT/VALIDATE/STOP |

**인터뷰/프로필 에이전트 (독립, 1개)**

| Agent | AI 활용 방법 | 핵심 출력 |
|---|---|---|
| **InterviewAgent** | LLM 기반 대화형 인터뷰 진행 (최대 14턴), 메모·대화 기록 기반 프로필 초안 생성 | `next_turn` — 다음 인터뷰 질문 / `draft_profile` — 프로필 섹션 1~7 / `preview-profile` — 비회원 프로필 1~3 미리보기 |

### 3.3 Evidence 기반 판단 원칙

- 임의의 시장 규모·재무 수치 LLM 생성 **금지**
- 각 에이전트는 수집한 `Evidence`(출처 포함)에 근거한 판단만 수행
- 근거 부족 시 `"근거 부족 / 추가 검토 필요"` 명시
- 최종 결과물에 반드시 면책 고지 포함

### 3.4 LLM Provider 추상화

```
Agent → LLMProvider → OpenAI GPT / Anthropic Claude
```

환경변수(`LLM_PROVIDER`, `LLM_MODEL`)로 모델 교체 가능하여 비용 최적화와 모델 유연성을 동시에 확보한다.

### 3.5 외부 API Evidence 수집

| API | 용도 |
|---|---|
| **KOSIS (통계청)** | 산업별 사업체 수·종사자 통계, 시장 규모 근거 |
| **Naver DataLab** | 키워드 검색 트렌드 (검색 비율·추이) |
| **KIPRIS (특허정보)** | 관련 기술·특허 동향 |
| **공공데이터포털** | 창업 지원 공고 실데이터 |
| **한국은행 ECOS** | 기업경기조사(BSI), 소비자동향(CSI), 업종별 재무분석 |
| **WorldBank** | 국가별 GDP·소비·인구 지표 |
| **국가법령정보 (법제처)** | 창업·소비자·식품 관련 법령 조문 및 법원 판례 |
| **Pinecone Vector DB** | 수집된 공공데이터 시맨틱·하이브리드 RAG 검색 |

---

## 4. 기술적 접근 방식

### 4.1 Backend

| 구분 | 기술 스택 | 선택 이유 |
|---|---|---|
| 언어 | Python 3.11 | AI/ML 생태계, 팀 숙련도 |
| API Framework | FastAPI | 비동기 지원, Swagger 자동 생성 |
| AI Orchestration | 자체 Multi-Agent Framework | 병렬/순차 workflow 세밀 제어 |
| LLM | OpenAI GPT / Anthropic Claude | 환경변수 교체 가능 추상화 |
| RAG | bizrag 어댑터 + 외부 API Evidence Retriever | 실데이터 기반 분석 |
| ORM | SQLAlchemy 2.0 (async) | 비동기 DB 처리 |
| DB | SQLite (개발) / PostgreSQL (프로덕션) | 환경별 분리 |

### 4.2 Frontend

| 구분 | 기술 스택 | 선택 이유 |
|---|---|---|
| Framework | Next.js 14 (App Router) | SSR, 파일 기반 라우팅 |
| 언어 | TypeScript | 타입 안전성 |
| 스타일 | Tailwind CSS | 빠른 UI 개발 |
| API 통신 | Next.js API Routes (서버 사이드 프록시) | CORS 우회, 타임아웃 제어 |
| 상태 관리 | React useState + localStorage | 경량 상태, 오프라인 이력 보존 |

### 4.3 배포 아키텍처

```
사용자 브라우저
      │
      ▼
  Vercel (Frontend, Next.js)
      │  Next.js API Routes (프록시, 300초 타임아웃)
      │    /api/v1/analyze
      │    /api/v1/programs
      │    /api/v1/report/scores
      │    /api/v1/report/profile-digest
      │    /api/v1/report/modues-application
      │    /api/v1/interview/preview-profile  ← NEW
      │    /api/v1/market/sizing
      │    /api/v1/finance/statement
      ▼
  Render (Backend, FastAPI)
      │
      ├── OpenAI / Anthropic API
      ├── KOSIS / Naver DataLab / KIPRIS
      └── SQLite / PostgreSQL
```

| 레이어 | 플랫폼 | URL |
|---|---|---|
| Frontend | Vercel | https://codyssey-final-project-ceo-g9sg.vercel.app |
| Backend | Render | https://codyssey-final-project-ceo.onrender.com |
| 로컬 개발 | Docker Compose | localhost:3000 / localhost:8000 |

### 4.4 데이터 흐름

```
BusinessIdea (Pydantic)
  → Orchestrator
  → AgentResult × 6 (Pydantic)
  → DecisionResult (Pydantic)
  → API Response (JSON)
  → Frontend 렌더링
  → localStorage 저장 (MY아이디어)
```

모든 에이전트 간 데이터는 Pydantic 모델로 타입 검증된다.

---

## 5. 일정 계획

### 5.1 마일스톤 요약

| 주차 | 마일스톤 | 완료 기준 |
|---|---|---|
| **1주차** | E2E 골격 연결 | Frontend → FastAPI → Orchestrator → Agents → Frontend 정상 응답 ✅ |
| **2주차** | 핵심 Agent 구현 | MarketAgent RAG 완성, Customer·Competitor·BM Agent LLM 연결 |
| **3주차** | 전체 Agent 통합 | Financial·Risk Agent 완성, 공고 실데이터 연동 |
| **4주차** | 완성 및 배포 | UI 완성, 통합 테스트, 발표 자료 준비 |

### 5.2 주차별 세부 계획

**1주차 (완료)**
- 공통 Domain Schema 정의
- BaseAgent / LLMProvider 추상화
- OrchestratorAgent, DecisionAgent 구현
- FastAPI 서버 및 엔드포인트 구성
- Next.js 전체 UI 구현 (5개 메뉴)
- Vercel / Render 배포 파이프라인 구성
- 외부 API Evidence Retriever 연결 (KOSIS ✅)

**2주차**
- MarketAgent RAG 파이프라인 완성 (조경학)
- Pinecone Serverless Vector DB 구축 및 시맨틱·하이브리드 검색 연동 (조경학)
- CustomerAgent / CompetitorAgent / BusinessModelAgent LLM 연결 (유상우)
- Firebase 로그인 / Firestore 분석 결과 저장 통합

**3주차**
- FinancialAgent 완성 — 재무 계산 로직 + 단위 테스트 (전선형)
- RiskAgent 완성 — 리스크 매트릭스 (전선형)
- 법원 판례 수집기 연동 (law.go.kr DRF API, 10개 주제 정기 수집) (조경학)
- 창업 공고 실데이터 연동 (api_catalog → /api/v1/programs) (전지영)
- Naver DataLab / KIPRIS API 권한 활성화
- Token usage DB 저장 연동

**4주차**
- 전체 E2E 통합 테스트
- UI/UX 개선 및 반응형 최적화 (전지영)
- PostgreSQL 마이그레이션 (SQLite → Render PostgreSQL)
- CI/CD 파이프라인 구성 (GitHub Actions)
- 발표 자료 및 데모 시나리오 준비

**추가 완료 (4주차 이후)**
- MY지원서 기능 전체 구현 ✅
  - 보고서 완성 아이디어 기반 지원서 생성·상태 관리 (작성중/제출완료/선정/탈락)
  - Firestore(로그인) / localStorage(비로그인) 이중 저장
  - `/ideas` 카드에서 "지원서 쓰기" 버튼 → `/applications?new=1&idea=...` 직통 연결
- 모두의 창업 지원서 AI 자동 작성 ✅
  - 지원사업 목록 상단에 "모두의 창업" 상시 노출 (PINNED_PROGRAMS 상수)
  - 보고서 DecisionResult 데이터로 6개 문항 LLM 자동 작성
  - 백엔드 `/api/v1/report/modues-application` 엔드포인트 신규 추가
  - 프론트엔드 2-step 다이얼로그: 아이템·공고 선택 → 폼 자동작성 진입
- 보고서 영역별 점수 채점 기능 (`/api/v1/report/scores`) ✅
- 프로필 섹션 요약 생성 기능 (`/api/v1/report/profile-digest`) ✅
- 시장 규모(TAM/SAM/SOM) 계산 API (`/api/v1/market/sizing`) ✅
- 손익계산서 생성 API (`/api/v1/finance/statement`) ✅
- Concept-B 디자인 시스템 적용 (Pretendard 폰트, 수평 로고 헤더, 새 파비콘) ✅
- Naver API Fallback 추가 (웹검색 안정성 강화) ✅
- **가설 검증 시스템 구현** ✅ (2026-10-17~18)
  - 보고서 약점·면적 점수 섹션에 "이 분야 검증하기" 링크 표시, 검증 N건 배지
  - ValidationBoard: 가설 검증 기록 상태 보드 (미처리 건수·재분석 버튼)
  - ValidationForm: 인터뷰·설문·예약주문·MVP·영업테스트·전문가 자문·데이터 분석 7가지 방법
  - 검증 기록 Firestore `users/{uid}/ideas/{id}/validations` 서브컬렉션에 저장
  - 다음 재분석 시 `user_validation.py`가 검증 기록을 `창업가 검증` Evidence로 변환·주입
  - 보고서 v(n-1)→v(n) 판정·점수·검증 활용 변화 요약 표시
- **비회원 프로필 미리보기** ✅ (2026-10-18)
  - 메모만 입력한 비회원도 프로필 섹션 1~3 AI 생성 미리보기
  - `POST /api/v1/interview/preview-profile` — IP당 하루 1회 제한(인메모리), 429 시 로그인 CTA
  - ProfilePreviewModal: 2턴 인터뷰 예시 리플레이 + 프로필 1~3 결과 표시
  - 비회원 IdeaCard 버튼 "프로필 / 미리보기" 두 줄 표기
  - 미리보기 결과는 브라우저 저장 후 로그인 시 계정으로 자동 이전
- **공고 목록 페이지네이션 및 필터 개선** ✅ (2026-10-18)
  - 30개씩 번호 페이저, 필터 변경 시 첫 페이지로 자동 이동
  - 2행 필터: 1행(검색), 2행(모집상태·지역·분야 라벨 셀렉트)
  - 기본값: 모집중 · 전체 지역 · 사업화 분야
- **Vercel 빌드 오류 수정** ✅ (2026-10-19)
  - 루트 `vercel.json` 추가로 FastAPI 오감지(`FASTAPI_ENTRYPOINT_NOT_FOUND`) 해결
  - 빌드 경로를 `frontend/` 명시, Next.js 프레임워크 선언

### 5.3 팀 구성 및 담당

| 팀원 | 역할 | 담당 |
|---|---|---|
| 김병국 | AI Architecture Lead & Frontend | Orchestrator, 공통 스키마, 전체 Frontend, 배포 |
| 조경학 | RAG & Market Agent | MarketAgent RAG, Pinecone Vector DB, 법원 판례 수집기 |
| 유상우 | Business Analysis Agent | Customer·Competitor·BusinessModel Agent |
| 전선형 | Financial & Risk Agent | FinancialAgent, RiskAgent |
| 전지영 | 추가 기능 지원 | 공고 실데이터 연동, UI/UX 개선 |

---

*본 문서는 Codyssey Final Project 4주 개발 기획서입니다.*
