/**
 * 아이디어 한 건의 모양과 상태 규칙.
 * 메모 → 인터뷰 → (1차 분석) → 아이템 프로필 → (상세 진단) → 분석 보고서
 */
import type { AnalyzeRequest, AnalyzeResponse, Coverage, Decision, InterviewMessage, InterviewSlot } from "@/lib/api";

export type IdeaStatus =
  | "memo"
  | "interviewing"
  | "profiling"
  | "profile"
  | "diagnosing"
  | "report"
  | "failed";

export interface IdeaProfile {
  name: string;
  oneLiner: string;
  industry: string;
  location: string;
  customer: string;
  problem: string;
  solution: string;
  revenueModel: string;
}

export const EMPTY_PROFILE: IdeaProfile = {
  name: "",
  oneLiner: "",
  industry: "",
  location: "전국",
  customer: "",
  problem: "",
  solution: "",
  revenueModel: "",
};

/** 카드에 바로 보여줄 최신 보고서 요약 (판정이 없으면 decision 없음) */
export interface ReportSummary {
  id: string;
  version: number;
  decision?: Decision;
  confidence?: number;
  summary: string;
  createdAt: string;
}

/** 딥 인터뷰 진행 기록. 중간에 나가도 이어서 할 수 있게 매 턴 저장한다 */
export interface IdeaInterview {
  messages: InterviewMessage[];
  covered: Coverage;
  quickReplies: string[];
  done: boolean;
}

export const INTERVIEW_SLOTS: { key: InterviewSlot; label: string }[] = [
  { key: "idea", label: "아이디어 · 해결하려는 것" },
  { key: "customer", label: "고객 · 문제를 본 장면" },
  { key: "alternative", label: "지금 쓰는 대안" },
  { key: "payer", label: "돈 낼 사람 · 수익 생각" },
  { key: "context", label: "분야 · 시작 지역" },
];

export const EMPTY_COVERAGE: Coverage = {
  idea: "empty",
  customer: "empty",
  alternative: "empty",
  payer: "empty",
  context: "empty",
};

export interface Idea {
  id: string;
  status: IdeaStatus;
  memo: string;
  /** 구조 개편 직후 문서에는 없을 수 있다 */
  interview?: IdeaInterview | null;
  profile: IdeaProfile;
  /** status가 failed일 때 어느 단계에서 실패했는지 */
  failedStage: IdeaStatus | null;
  errorMessage: string | null;
  /** 진행 중 상태가 너무 오래 멈춰 있는지 판단하는 기준 */
  statusChangedAt: string;
  latestReport: ReportSummary | null;
  reportCount: number;
  profileChangedSinceReport: boolean;
  createdAt: string;
  updatedAt: string;
}

/** 상세 진단 1회 결과 — 버전별로 쌓인다 */
export interface IdeaReport {
  id: string;
  version: number;
  profile: IdeaProfile;
  input: AnalyzeRequest;
  response: AnalyzeResponse;
  elapsedMs?: number;
  createdAt: string;
}

// 상태 배지: 색조는 violet 하나만 쓰고 진하기로 단계를 나눈다 (레퍼런스: 다른 색조 금지)
export const STATUS_META: Record<IdeaStatus, { label: string; color: string; bg: string }> = {
  memo: { label: "메모", color: "#4B5563", bg: "#F3F4F6" },
  interviewing: { label: "인터뷰 중", color: "#5B59E0", bg: "#F0F0FF" },
  profiling: { label: "프로필 만드는 중", color: "#5B59E0", bg: "#F0F0FF" },
  profile: { label: "프로필", color: "#5B59E0", bg: "#E6E6FF" },
  diagnosing: { label: "진단 중", color: "#5B59E0", bg: "#F0F0FF" },
  report: { label: "보고서", color: "#FFFFFF", bg: "#7270FF" },
  failed: { label: "실패", color: "#B42318", bg: "#FEF2F2" },
};

export const DECISION_META: Record<Decision, { label: string; color: string }> = {
  GO: { label: "GO", color: "#1A7A4A" },
  PIVOT: { label: "PIVOT", color: "#856404" },
  VALIDATE_MORE: { label: "VALIDATE MORE", color: "#7270FF" },
  STOP: { label: "STOP", color: "#B42318" },
};

export const REGIONS = ["전국", "서울", "경기", "부산", "인천", "대구", "대전", "광주", "울산", "세종"];

/** 진단에 꼭 필요한 칸 — 백엔드 AnalyzeRequest 필수값과 맞춘다 */
export const REQUIRED_FIELDS: (keyof IdeaProfile)[] = ["name", "industry", "customer", "problem", "solution"];

// 진행 중 상태가 이보다 오래 바뀌지 않으면 중간에 끊긴 것으로 본다
const STALE_MS = 15 * 60 * 1000;

const IN_PROGRESS: IdeaStatus[] = ["profiling", "diagnosing"];

/** 화면에 보여줄 상태. 진행 중인 채로 끊긴 아이디어는 실패로 바꿔 보여준다 */
export function effectiveStatus(idea: Idea): { status: IdeaStatus; failedStage: IdeaStatus | null } {
  if (IN_PROGRESS.includes(idea.status) && Date.now() - Date.parse(idea.statusChangedAt) > STALE_MS) {
    return { status: "failed", failedStage: idea.status };
  }
  return { status: idea.status, failedStage: idea.failedStage };
}

export function displayTitle(idea: Idea) {
  return idea.profile.name.trim() || idea.memo.trim().split("\n")[0] || "이름 없는 아이디어";
}

export function missingFields(profile: IdeaProfile) {
  return REQUIRED_FIELDS.filter((f) => !profile[f].trim());
}

/** 프로필 → 백엔드 진단 요청. 한줄 소개·수익 모델은 아직 전용 필드가 없어 해결 방법에 덧붙인다 */
export function toAnalyzeRequest(profile: IdeaProfile): AnalyzeRequest {
  const solution = [
    profile.solution.trim(),
    profile.oneLiner.trim() && `한줄 소개: ${profile.oneLiner.trim()}`,
    profile.revenueModel.trim() && `수익 모델: ${profile.revenueModel.trim()}`,
  ]
    .filter(Boolean)
    .join("\n\n");
  return {
    title: profile.name.trim(),
    problem: profile.problem.trim(),
    customer: profile.customer.trim(),
    solution,
    industry: profile.industry.trim(),
    location: profile.location,
    business_stage: "idea",
  };
}

export function newIdea(id: string, memo: string): Idea {
  const now = new Date().toISOString();
  return {
    id,
    status: "memo",
    memo,
    interview: null,
    profile: { ...EMPTY_PROFILE },
    failedStage: null,
    errorMessage: null,
    statusChangedAt: now,
    latestReport: null,
    reportCount: 0,
    profileChangedSinceReport: false,
    createdAt: now,
    updatedAt: now,
  };
}

export function summarizeReport(report: IdeaReport): ReportSummary {
  const dr = report.response.workflow_result.decision_result;
  return {
    id: report.id,
    version: report.version,
    ...(dr ? { decision: dr.decision, confidence: dr.confidence } : {}),
    summary: dr?.summary ?? "",
    createdAt: report.createdAt,
  };
}
