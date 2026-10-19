# 나도사장 — 기능 요구 명세서

> AI 기반 예비창업자 사업성 분석 서비스

---

## 1. 기능 요구사항 (Functional Requirements)

### FR-01. 사업성 AI 분석 (핵심 기능)

#### FR-01-1. 아이디어 입력
- 사용자는 다음 6개 필드를 입력하여 분석을 요청할 수 있다.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `title` | string | ✅ | 사업 아이디어 제목 |
| `problem` | string | ✅ | 해결하려는 문제 |
| `customer` | string | ✅ | 타겟 고객 |
| `solution` | string | ✅ | 제안 솔루션 |
| `industry` | string | ✅ | 산업 분야 |
| `location` | string | ✅ | 주요 사업 지역 |
| `business_stage` | enum | — | 사업 단계 (기본값: `idea`) |

#### FR-01-2. Multi-Agent 병렬 분석
- 시스템은 입력된 아이디어를 분석 파이프라인의 7개 전문 에이전트에 전달하여 분석을 수행한다. (인터뷰/프로필 전용 InterviewAgent 포함 시 총 8개 AI 에이전트 운영)
- Phase 1 (병렬): MarketAgent, CustomerAgent, CompetitorAgent가 동시에 실행된다.
- Phase 2 (순차): BusinessModelAgent가 Phase 1 결과를 바탕으로 실행된다.
- Phase 3 (병렬): FinancialAgent, RiskAgent가 동시에 실행된다.
- Phase 4 (순차): DecisionAgent가 모든 결과를 종합하여 최종 판정을 내린다.

#### FR-01-3. 분석 결과 출력
- 각 에이전트별 분석 요약, 신뢰도(confidence), 근거(evidence)를 카드 형태로 표시한다.
- 종합 판정 배너에 GO / PIVOT / VALIDATE_MORE / STOP 중 하나를 표시한다.
- SWOT 분석, 강점·약점, Action Plan을 구조화하여 제공한다.
- 분석 결과 하단에 면책 고지(disclaimer)를 필수로 표시한다.

#### FR-01-4. 에이전트 부분 실패 처리
- 일부 에이전트 실패 시에도 성공한 에이전트의 결과로 `PARTIAL` 상태 응답을 반환한다.
- 실패한 에이전트 항목은 `"분석 불가 / 오류 발생"` 메시지와 함께 표시한다.

---

### FR-02. 창업 지원 공고 검색

#### FR-02-1. 공고 목록 조회
- 사용자는 정부·지자체 창업 지원 공고 목록을 조회할 수 있다.
- 기본 정렬: 마감일 오름차순

#### FR-02-2. 필터링 및 검색
- 마감 상태 필터: `모집중`, `마감임박(D-3)`, `마감`
- 지역 필터: 서울, 경기, 전국 등
- 분야 필터: 청년창업, 기술창업 등
- 키워드 검색: 공고명·기관명 포함 검색

#### FR-02-3. 공고 상세 정보
- 공고 항목 클릭 시 사이드 패널 또는 상세 페이지를 통해 다음 정보를 표시한다.
  - 기관명, 분야, 지역, 마감일, 지원 금액, 원문 링크

---

### FR-03. MY아이디어 이력 관리

#### FR-03-1. 분석 결과 자동 저장
- 분석 완료 후 결과를 자동으로 localStorage에 저장한다.
- Firebase 로그인 사용자의 경우 Firestore에도 저장한다.

#### FR-03-2. 이력 목록 조회
- 저장된 분석 이력을 최신순으로 카드 목록 형태로 표시한다.
- 각 카드에는 아이디어 제목, 분석 일시, 최종 판정(GO/PIVOT/VALIDATE/STOP)을 표시한다.

#### FR-03-3. 이력 상세 조회
- 특정 이력 선택 시 해당 분석의 전체 결과를 다시 조회할 수 있다.

---

### FR-04. 스타트업 라운지

#### FR-04-1. 창업 정보 링크 제공
- 창업 뉴스, 정부 창업 포털, 투자 정보, 교육 리소스를 카테고리별로 제공한다.
- 외부 링크는 새 탭에서 열린다.

---

### FR-05. 마이페이지

#### FR-05-1. 분석 통계 요약
- 총 분석 횟수, 판정별 분포(GO/PIVOT/VALIDATE/STOP)를 수치로 표시한다.

#### FR-05-2. 최근 아이디어 목록
- 최근 5건의 분석 이력을 빠르게 확인할 수 있다.

#### FR-05-3. 빠른 메뉴
- 핵심 기능(AI 지원서, 공고 찾기)으로의 바로가기 링크를 제공한다.

---

### FR-06. 사용자 인증

#### FR-06-1. Firebase 소셜 로그인
- Google OAuth를 통한 로그인/로그아웃을 지원한다.
- 로그인 시 Firestore 동기화가 활성화된다.
- 비로그인 사용자도 localStorage 기반으로 서비스 이용이 가능하다.

---

### FR-07. MY지원서 관리

#### FR-07-1. 지원서 생성
- 사용자는 상세분석 보고서가 완성된 아이디어와 창업 지원 공고를 선택하여 지원서를 생성할 수 있다.
- 동일 아이디어·공고 조합으로 중복 지원서 생성을 방지한다.
- `/ideas` 페이지의 보고서 단계 아이디어 카드에서 "지원서 쓰기" 버튼으로 직접 진입할 수 있다.

#### FR-07-2. 지원사업 목록
- 지원서 생성 다이얼로그의 "2. 지원사업" 항목에는 실시간 공고 목록과 함께 "모두의 창업"이 상시 노출된다.
- 사업명·기관명으로 검색 필터링이 가능하다.

#### FR-07-3. 지원서 상태 관리
- 각 지원서는 다음 4가지 상태를 가진다: `작성 중`, `제출 완료`, `선정`, `탈락`
- 사용자는 지원서 카드에서 상태를 직접 변경할 수 있다.

#### FR-07-4. 지원서 저장
- 로그인 사용자: Firestore `users/{uid}/applications` 컬렉션에 저장
- 비로그인 사용자: 브라우저 localStorage에 저장

#### FR-07-5. 지원서 삭제
- 사용자는 지원서 카드에서 개별 지원서를 삭제할 수 있다.

---

### FR-08. 모두의 창업 지원서 AI 자동 작성

#### FR-08-1. 폼 진입
- 지원서 생성 다이얼로그에서 "모두의 창업"을 선택하고 "지원서 작성하기"를 클릭하면 자동 작성 후 6문항 폼으로 전환된다.

#### FR-08-2. AI 자동 작성
- 시스템은 선택된 아이디어의 최신 보고서 데이터(프로필 + DecisionResult)를 백엔드 LLM에 전달하여 6개 문항을 자동 작성한다.
- 자동 작성 실패 시 빈 폼으로 진입하여 수동 작성을 허용한다.

#### FR-08-3. 6개 문항 구성

| 문항 | 내용 | 글자 제한 | 데이터 소스 |
|------|------|-----------|------------|
| Q1 | 아이디어 한 줄 소개 | 100자 | `profile.oneLiner` |
| Q2 | 아이디어 배경 이야기 | 1,000자 | `profile.problem` + `idea.memo` |
| Q3-1 | 기존 대비 차별점·문제 해결 | 1,000자 | `profile.solution` + `strengths` + `opportunities` |
| Q3-2 | 수익 창출 계획 | 1,000자 | `profile.revenueModel` + `financial_summary` |
| Q4-1 | 사업화 계획 | 1,000자 | `action_plan` |
| Q4-2 | 책임멘토에게 받고 싶은 도움 | 1,000자 | `weaknesses` + `validation_items` |

#### FR-08-4. 폼 유효성 검사
- 6개 문항 모두 내용이 있어야 "지원서 제출" 버튼이 활성화된다.
- 각 문항에 실시간 글자수 카운터를 표시한다.
- 글자수 초과 시 빨간 테두리와 경고 색상으로 표시한다.

#### FR-08-5. 답변 저장
- 제출 완료된 지원서에는 `modeusAnswers` 필드에 6개 문항 답변이 함께 저장된다.

---

### FR-09. 가설 검증 시스템

#### FR-09-1. 검증 링크 표시
- 보고서의 각 약점(weaknesses) 항목과 점수가 가장 낮은 영역 점수 섹션에 "이 분야 검증하기" 링크를 표시한다.
- 검증 기록이 1건 이상 있을 경우 "검증 N건" 배지를 함께 표시한다.

#### FR-09-2. 검증 기록 입력
- 사용자는 다음 7가지 방법 중 하나로 가설 검증 기록을 입력할 수 있다: 인터뷰, 설문, 예약주문, MVP 테스트, 영업 테스트, 전문가 자문, 데이터 분석
- 각 검증 기록에는 가설 내용, 검증 방법, 표본 크기, 결과 요약, 결론(확인/반증/불명)을 입력한다.
- 검증 기록은 로그인 사용자의 경우 Firestore `users/{uid}/ideas/{ideaId}/validations` 서브컬렉션에 저장된다.

#### FR-09-3. 검증 보드
- 프로필 워크스페이스 내 "검증 기록" 탭에서 상태 보드 형태로 검증 현황을 확인할 수 있다.
- 미처리(결론 미정) 건수와 "재분석 시작" 버튼을 상단에 표시한다.

#### FR-09-4. 재분석 시 Evidence 반영
- 재분석 요청 시 시스템은 Firestore에서 해당 아이디어의 검증 기록을 조회하여 `창업가 검증` Evidence로 변환한다.
- 검증 방법과 표본 강도에 따라 영역 점수에 가산 또는 감산을 적용한다.
- 이전 보고서 대비 판정·영역 점수·검증 활용 변화 요약을 보고서 상단에 표시한다.

---

### FR-10. 비회원 프로필 미리보기

#### FR-10-1. 미리보기 진입
- 메모(아이디어 메모)만 저장한 비회원 사용자가 아이디어 카드에서 "미리보기" 버튼을 클릭하면 프로필 미리보기 모달이 열린다.
- 모달에서 2턴 인터뷰 예시 리플레이(약 4초)가 재생되는 동안 백엔드가 메모 기반으로 프로필 섹션 1~3을 생성한다.

#### FR-10-2. IP 기반 사용 제한
- 비회원 미리보기는 동일 IP당 한국 표준시(KST) 기준 하루 1회로 제한한다.
- 제한 초과(429) 시 로그인 CTA로 안내한다.
- 제한은 서버 인메모리 관리(서버 재시작 시 초기화)이며 보안 경계가 아닌 비용 제어 목적이다.

#### FR-10-3. 미리보기 결과 처리
- 미리보기 결과(프로필 섹션 1~3)는 브라우저에 저장된다.
- 섹션 4~7은 잠금 상태로 표시하며 로그인을 유도한다.
- 로그인 후에는 브라우저에 저장된 프로필 미리보기가 계정으로 자동 이전된다.
- 미리보기로 생성된 프로필 카드에는 "메모 · AI" 배지를 표시한다.

---

### FR-11. 창업 지원 공고 페이지네이션 및 필터 개선

#### FR-11-1. 페이지네이션
- 공고 목록은 30개씩 페이지로 분리하여 표시한다.
- 하단에 번호 페이저를 제공하며 필터 변경 시 자동으로 1페이지로 이동한다.

#### FR-11-2. 2행 필터 레이아웃
- 1행: 키워드 검색 입력창
- 2행: 모집상태(모집중/마감임박/마감) · 지역 · 분야 라벨 셀렉트 3종
- 기본값: 모집중 · 전체 지역 · 사업화 분야

---

## 2. 비기능 요구사항 (Non-Functional Requirements)

### NFR-01. 성능

| 항목 | 목표 |
|---|---|
| 분석 응답 시간 | 60초 이내 (Multi-Agent 병렬 실행 기준) |
| 공고 목록 응답 시간 | 2초 이내 |
| 페이지 최초 로딩 (LCP) | 3초 이내 |
| API 타임아웃 | 300초 (Next.js API Routes) |

### NFR-02. 가용성 및 신뢰성

| 항목 | 요구사항 |
|---|---|
| 서비스 가용성 | 99% 이상 (월간 기준) |
| 에이전트 부분 실패 | PARTIAL 상태로 나머지 결과 반환 (전체 실패 방지) |
| LLM API 오류 | 자동 재시도 (retry) 후 fallback 메시지 반환 |
| 외부 API 오류 | graceful degradation — 해당 Evidence 없이 분석 진행 |

### NFR-03. 보안

| 항목 | 요구사항 |
|---|---|
| API 키 관리 | 환경변수 전용 관리, 코드·Git 커밋 금지 |
| `.env` 파일 | `.gitignore` 등록 필수 |
| CORS | Backend는 Frontend 도메인만 허용 |
| 사용자 데이터 | 분석 결과 외 개인 식별 정보 수집 없음 |
| HTTPS | 모든 서비스 HTTPS 강제 (Vercel·Render 기본 적용) |

### NFR-04. 유지보수성

| 항목 | 요구사항 |
|---|---|
| LLM 교체 | 환경변수 변경만으로 OpenAI ↔ Anthropic 전환 가능 |
| 에이전트 확장 | BaseAgent 상속으로 신규 에이전트 추가 가능 |
| 스키마 변경 | schemas.py 변경 시 전 팀원 공지 및 영향 범위 검토 |
| 코드 일관성 | Pydantic 모델로 모든 에이전트 간 데이터 타입 보장 |

### NFR-05. 접근성 및 UX

| 항목 | 요구사항 |
|---|---|
| 반응형 지원 | 모바일(320px) ~ 데스크탑(1920px) 모두 지원 |
| 로딩 상태 | 분석 진행 중 스피너 및 단계 표시 |
| 에러 메시지 | 사용자가 이해할 수 있는 한국어 오류 메시지 표시 |
| 면책 고지 | 분석 결과 하단에 항상 표시 |

### NFR-06. 배포 및 운영

| 항목 | 요구사항 |
|---|---|
| CI/CD | Git 푸시 → 자동 빌드·배포 (Vercel·Render) |
| 헬스체크 | `/api/v1/health` 엔드포인트 상시 운영 |
| 로그 | 에이전트별 실행 시간, 토큰 사용량 기록 |
| 스핀다운 대응 | Render 무료 플랜 스핀다운 시 첫 요청 지연 안내 표시 |

---

## 3. 시스템 아키텍처 설계

### 3.1 전체 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                      사용자 브라우저                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Next.js 14 (App Router) — Vercel          │   │
│  │                                                     │   │
│  │  Pages: / · /programs · /ideas · /applications · /lounge · /mypage │   │
│  │  Components: Header · AgentResultCard · DecisionBanner│  │
│  │  State: React useState + localStorage + Firestore   │   │
│  │                                                     │   │
│  │  Next.js API Routes (서버사이드 프록시, 300s timeout) │   │
│  │    /api/v1/analyze  →  Backend POST /api/v1/analyze  │   │
│  │    /api/v1/programs →  Backend GET  /api/v1/programs │   │
│  │    /api/v1/health   →  Backend GET  /api/v1/health   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │ HTTPS
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI — Python 3.11 — Render                 │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                 OrchestratorAgent                    │  │
│  │                                                      │  │
│  │  Phase 1 (parallel)                                  │  │
│  │    MarketAgent ─── CustomerAgent ─── CompetitorAgent │  │
│  │                                                      │  │
│  │  Phase 2 (sequential)                                │  │
│  │    BusinessModelAgent                                │  │
│  │                                                      │  │
│  │  Phase 3 (parallel)                                  │  │
│  │    FinancialAgent ──────────── RiskAgent             │  │
│  │                                                      │  │
│  │  Phase 4 (sequential)                                │  │
│  │    DecisionAgent → GO/PIVOT/VALIDATE_MORE/STOP       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────┐  ┌───────────────────────────────────┐   │
│  │  SQLAlchemy  │  │         LLMProvider               │   │
│  │  SQLite/PG   │  │  OpenAI GPT / Anthropic Claude    │   │
│  └──────────────┘  └───────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Evidence Retriever (RAG)                │  │
│  │  bizrag · KOSIS · DataLab · KIPRIS · 한국은행 · 판례 │  │
│  │        Pinecone Vector DB (시맨틱·하이브리드)         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼──────────────────┐
          ▼                   ▼                  ▼
    OpenAI API         Anthropic API      Firebase/Firestore
    (LLM)              (LLM)              (Auth + DB)
          │
    ┌─────┴──────────────────────┐
    ▼           ▼               ▼
  KOSIS       Naver           KIPRIS
  (통계청)   DataLab         (특허정보)
```

### 3.2 데이터 모델

#### BusinessIdea (입력)
```python
class BusinessIdea(BaseModel):
    title: str
    problem: str
    customer: str
    solution: str
    industry: str
    location: str
    business_stage: str = "idea"
```

#### Evidence (근거 단위)
```python
class Evidence(BaseModel):
    source: str        # 출처 (KOSIS, DataLab, 웹검색 등)
    content: str       # 근거 내용
    url: Optional[str] # 원문 링크
    retrieved_at: datetime
```

#### AgentResult (에이전트 출력)
```python
class AgentResult(BaseModel):
    agent_name: str
    status: Literal["success", "partial", "failed"]
    summary: str
    confidence: float          # 0.0 ~ 1.0
    evidence: List[Evidence]
    raw_output: Optional[dict]
```

#### DecisionResult (최종 판정)
```python
class DecisionResult(BaseModel):
    summary: str
    strengths: List[str]
    weaknesses: List[str]
    opportunities: List[str]
    threats: List[str]
    action_plan: List[str]
    decision: Literal["GO", "PIVOT", "VALIDATE_MORE", "STOP"]
    confidence: float
    disclaimer: str
```

#### WorkflowResult (API 응답)
```python
class WorkflowResult(BaseModel):
    idea_id: str
    status: Literal["success", "partial", "failed"]
    agent_results: Dict[str, AgentResult]
    decision_result: Optional[DecisionResult]
    elapsed_seconds: float
    token_usage: Optional[dict]
```

### 3.3 API 엔드포인트 명세

#### POST /api/v1/analyze
| 항목 | 내용 |
|---|---|
| 설명 | 사업 아이디어 Multi-Agent 분석 요청 |
| Request | `BusinessIdea` JSON |
| Response | `WorkflowResult` JSON |
| 타임아웃 | 300초 |
| 오류 | 422 (유효성 검사 실패), 500 (서버 오류) |

#### GET /api/v1/programs
| 항목 | 내용 |
|---|---|
| 설명 | 창업 지원 공고 목록 조회 |
| Query Params | `status`, `region`, `category`, `q` |
| Response | `{ total: int, items: List[Program] }` |
| 캐시 | 1시간 (공고 데이터 변경 주기 고려) |

#### GET /api/v1/health
| 항목 | 내용 |
|---|---|
| 설명 | 서비스 상태 확인 |
| Response | `{ status: "ok", service: "나도사장 API" }` |

#### POST /api/v1/report/scores
| 항목 | 내용 |
|---|---|
| 설명 | 보고서 에이전트별 영역 점수 채점 (1~10점) |
| Request | `ScoreRequest` (아이디어 정보 + 에이전트별 summary/findings) |
| Response | `ScoreResponse` (분야별 점수 + 이유 한 줄) |

#### POST /api/v1/report/profile-digest
| 항목 | 내용 |
|---|---|
| 설명 | 보고서 프로필 섹션을 짧은 요약 + 근거 형식으로 변환 |
| Request | `DigestRequest` (칸 id·label·원문 목록) |
| Response | `DigestResponse` (summary + points 목록) |

#### POST /api/v1/report/modues-application
| 항목 | 내용 |
|---|---|
| 설명 | 모두의 창업 지원서 6개 문항 AI 자동 작성 |
| Request | 아이디어 프로필 + DecisionResult 데이터 (JSON) |
| Response | `ModeusApplicationResponse` (q1~q4_2 6개 문자열) |
| 타임아웃 | 90초 |

#### POST /api/v1/interview/preview-profile
| 항목 | 내용 |
|---|---|
| 설명 | 비회원 메모 기반 프로필 섹션 1~3 생성 미리보기 |
| Request | `{ memo: string }` |
| Response | `{ sections: ProfileSection[1~3] }` |
| 제한 | IP당 하루 1회 (인메모리, KST 기준), 초과 시 429 |
| 타임아웃 | 60초 |

#### POST /api/v1/market/sizing
| 항목 | 내용 |
|---|---|
| 설명 | TAM·SAM·SOM 시장 규모 계산 및 연도별 그래프 데이터 생성 |

#### POST /api/v1/finance/statement
| 항목 | 내용 |
|---|---|
| 설명 | 손익계산서 항목 계산 (매출·비용·영업이익·손익분기점) |

### 3.4 보안 설계

```
환경변수 (.env)
  OPENAI_API_KEY        ← LLM 호출
  ANTHROPIC_API_KEY     ← LLM 호출 (대안)
  LLM_PROVIDER          ← "openai" | "anthropic"
  LLM_MODEL             ← 모델명
  KOSIS_API_KEY         ← 통계청 API
  NAVER_CLIENT_ID       ← DataLab API
  KIPRIS_API_KEY        ← 특허정보 API
  FIREBASE_*            ← Firebase Admin SDK

  → .gitignore 등록 필수
  → CI/CD는 Secret Manager / 플랫폼 환경변수에서 주입
```

### 3.5 배포 URL

| 레이어 | 플랫폼 | URL |
|---|---|---|
| Frontend | Vercel | https://codyssey-final-project-ceo-g9sg.vercel.app/ |
| Backend | Render | https://codyssey-final-project-ceo.onrender.com |
| 로컬 개발 | Docker Compose | localhost:3000 / localhost:8000 |

### 3.6 에러 처리 전략

| 오류 유형 | 처리 방식 |
|---|---|
| LLM API 타임아웃 | 3회 자동 재시도 후 `"분석 오류"` 메시지 반환 |
| 외부 API (KOSIS 등) 오류 | Evidence 없이 LLM 자체 판단으로 대체, 로그 기록 |
| Pinecone 검색 오류 | SQLite FTS 키워드 검색으로 자동 fallback |
| 법원 판례 API 오류 | 해당 Evidence 제외 후 분석 진행, 로그 기록 |
| 에이전트 부분 실패 | `PARTIAL` 상태로 나머지 결과 정상 반환 |
| DB 연결 오류 | 분석은 정상 진행, 저장만 실패 (로그 기록) |
| 프론트엔드 API 타임아웃 | 300초 후 "분석 시간 초과" 안내 메시지 표시 |

---

## 4. 제약사항 (Constraints)

| 항목 | 제약 |
|---|---|
| 개발 기간 | 4주 (총 20일) |
| 팀 규모 | 5명 (김병국·조경학·유상우·전선형·전지영) |
| 예산 | LLM API 비용 최소화 (Mock 모드 개발 병행) |
| 근거 원칙 | 임의의 시장 규모·재무 수치 생성 금지 |
| 면책 고지 | 모든 분석 결과에 "의사결정 지원 도구" 면책 표시 필수 |
| 데이터 보존 | 비로그인 사용자 데이터는 localStorage에만 저장 (서버 미전송) |

---

*본 문서는 Codyssey Final Project 기능 요구 명세서입니다.*
