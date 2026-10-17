import type { ValidationInput } from "@/lib/validation";
export type BusinessStage = "idea" | "validation" | "early" | "growth";
export type AgentStatus = "pending" | "running" | "success" | "partial" | "failed" | "skipped";
export type Decision = "GO" | "PIVOT" | "VALIDATE_MORE" | "STOP";

export interface AnalyzeRequest {
  title: string;
  problem: string;
  customer: string;
  solution: string;
  industry: string;
  location: string;
  business_stage: BusinessStage;
  /** 창업가 검증 기록 — 있으면 '창업가 검증' 근거로 들어간다 (상세분석 작업만 받음) */
  validations?: ValidationInput[];
}

export interface Evidence {
  title: string;
  source: string;
  url?: string;
  content: string;
  confidence: number;
}

export interface AgentResult {
  agent_name: string;
  status: AgentStatus;
  summary: string;
  findings: Record<string, unknown>[];
  evidence: Evidence[];
  recommendations: string[];
  confidence: number;
  error_message?: string;
  execution_time_ms?: number;
}

export interface DecisionResult {
  summary: string;
  strengths: string[];
  weaknesses: string[];
  opportunities: string[];
  risks: string[];
  financial_summary: string;
  validation_items: string[];
  action_plan: string[];
  decision: Decision;
  confidence: number;
  disclaimer: string;
}

export interface WorkflowResult {
  idea_id: string;
  status: AgentStatus;
  agent_results: Record<string, AgentResult>;
  decision_result?: DecisionResult;
  total_execution_time_ms?: number;
  created_at: string;
}

export interface AnalyzeResponse {
  idea_id: string;
  workflow_result: WorkflowResult;
}

/** 상세분석 백그라운드 작업 — 화면을 떠나도 서버에서 계속 돈다 */
export type StageState = "waiting" | "running" | "done" | "failed";

export interface StageProgress {
  state: StageState;
  status: AgentStatus | null;
  summary: string;
  evidence: number;
  elapsed_ms: number;
}

export interface AnalyzeJob {
  job_id: string;
  status: "running" | "done" | "failed";
  started_at: string;
  finished_at: string | null;
  stages: Record<string, StageProgress>;
  result: AnalyzeResponse | null;
  error: string | null;
}

export class JobGoneError extends Error {}

export async function startAnalyzeJob(req: AnalyzeRequest): Promise<string> {
  const res = await fetch("/api/v1/analyze/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "알 수 없는 오류" }));
    throw new Error(err.detail ?? "분석을 시작하지 못했어요.");
  }
  return (await res.json()).job_id;
}

export async function getAnalyzeJob(jobId: string): Promise<AnalyzeJob> {
  const res = await fetch(`/api/v1/analyze/jobs/${encodeURIComponent(jobId)}`, { cache: "no-store" });
  if (res.status === 404) throw new JobGoneError("분석 작업이 끊겼어요. 서버가 다시 시작됐을 수 있어요.");
  if (!res.ok) throw new Error("진행 상황을 불러오지 못했어요.");
  return res.json();
}

export async function analyze(req: AnalyzeRequest): Promise<AnalyzeResponse> {
  const res = await fetch("/api/v1/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "알 수 없는 오류" }));
    throw new Error(err.detail ?? "분석 요청 실패");
  }
  return res.json();
}

// ── 딥 인터뷰 · 1차 분석 ─────────────────────────────────────────────

export type InterviewSlot = "idea" | "customer" | "alternative" | "payer" | "context";
export type SlotState = "filled" | "skipped" | "empty";
export type Coverage = Record<InterviewSlot, SlotState>;

export interface InterviewMessage {
  role: "assistant" | "user";
  content: string;
}

export interface InterviewTurn {
  message: string;
  quick_replies: string[];
  covered: Coverage;
  done: boolean;
}

/** 백엔드 ProfileDraft (snake_case) */
export interface ProfileDraft {
  name: string;
  one_liner: string;
  industry: string;
  location: string;
  customer: string;
  problem: string;
  solution: string;
  revenue_model: string;
}

async function postJson<T>(url: string, body: unknown, fallback: string): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: fallback }));
    throw new Error(typeof err.detail === "string" ? err.detail : fallback);
  }
  return res.json();
}

export function interviewNext(memo: string, messages: InterviewMessage[], covered?: Coverage) {
  return postJson<InterviewTurn>("/api/v1/interview/next", { memo, messages, covered }, "인터뷰 질문 요청 실패");
}

export function interviewDraftProfile(memo: string, messages: InterviewMessage[]) {
  return postJson<ProfileDraft>("/api/v1/interview/profile", { memo, messages }, "프로필 초안 요청 실패");
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch("/api/v1/health");
    return res.ok;
  } catch {
    return false;
  }
}

/** 월 손익계산서 항목 — 매출 / 매출원가(변동비) / 판매관리비(고정비) */
export type LineGroup = "revenue" | "cogs" | "opex";

export interface StatementSuggestion {
  unit_label: string;
  unit_count: number;
  lines: { group: LineGroup; label: string; amount: number; basis: string }[];
}

/** 업종·수익 방식에 맞는 손익 항목과 예시 금액 (AI 제안) */
export async function suggestStatement(req: { revenue_type: string; idea: Record<string, string>; context: string }): Promise<StatementSuggestion> {
  const res = await fetch("/api/v1/finance/statement", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error("손익 항목을 만들지 못했어요. 직접 입력해 주세요.");
  return res.json();
}

/** 시장 규모 — 금액은 원(KRW), 연도별 시리즈는 근거 원문 통화 그대로 */
export interface MarketTier {
  value: number | null;
  display: string;
  basis: string;
  evidence_index: number | null;
  estimated: boolean;
}

export interface MarketSeries {
  name: string;
  unit: "KRW" | "USD";
  evidence_index: number;
  points: { year: number; value: number; projected: boolean; raw: string }[];
}

export interface MarketSizing {
  tam: MarketTier;
  sam: MarketTier;
  som: MarketTier;
  series: MarketSeries[];
  usd_krw: number;
  /** evidence_index가 가리키는 출처 (보고서 근거 + 최신 웹 근거). 예전 저장본엔 없을 수 있다 */
  sources?: { title: string; source: string; url?: string | null }[];
}

export async function suggestMarketSizing(req: {
  idea: Record<string, string>;
  market_summary: string;
  claims: Record<string, string>;
  evidence: { title: string; source: string; url?: string | null; content: string }[];
}): Promise<MarketSizing> {
  const res = await fetch("/api/v1/market/sizing", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error("시장 규모를 정리하지 못했어요.");
  return res.json();
}

/** 보고서 영역별 점수 (10점 만점 + 한 줄 이유) */
export interface AreaScore {
  area: string;
  score: number;
  reason: string;
}

export async function scoreReport(req: {
  idea: Record<string, string>;
  areas: Record<string, { summary: string; findings: string; evidence_count: number }>;
  finance_summary: string;
  validations?: { area: string; hypothesis: string; result: string; method: string; sample_size: number | null; metric: string }[];
}): Promise<AreaScore[]> {
  const res = await fetch("/api/v1/report/scores", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error("영역별 점수를 매기지 못했어요.");
  return (await res.json()).scores;
}

/** 프로필 4~7 칸 요약 — 보고서 긴 문장을 '짧은 요약 + 명사형 근거'로 */
export async function profileDigest(rows: { id: string; label: string; text: string }[]): Promise<{ id: string; summary: string; points: string[] }[]> {
  const res = await fetch("/api/v1/report/profile-digest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rows }),
  });
  if (!res.ok) throw new Error("프로필 요약을 만들지 못했어요.");
  return (await res.json()).rows;
}
