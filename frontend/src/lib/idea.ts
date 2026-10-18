/**
 * 아이디어 한 건의 모양과 상태 규칙.
 * 메모 → 인터뷰 → (1차 분석) → 아이템 프로필 → (상세 진단) → 분석 보고서
 */
import type { AnalyzeRequest, AnalyzeResponse, AreaScore, Coverage, Decision, InterviewMessage, InterviewSlot, MarketSizing } from "@/lib/api";
import type { FinancePlan } from "@/lib/financePlan";

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

/** 백엔드 MAX_QUESTIONS와 맞춘다 — 인터뷰 시작 전·진행 중 안내에 쓴다 */
export const INTERVIEW_MAX_QUESTIONS = 14;

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
  /** 진행 중인 상세분석 작업 (서버 백그라운드). 화면을 떠났다 와도 이어서 결과를 받는다 */
  diagnosisJobId?: string | null;
  /** 상세분석 작업을 시작할 때 보낸 입력 — 보고서에 함께 남긴다 */
  diagnosisInput?: AnalyzeRequest | null;
  /** 사용자가 보고서 화면에서 직접 넣은 재무 숫자 — 수익 방식 + 값 (시나리오 계산용) */
  financePlan?: FinancePlan | null;
  /** 보고서 '시장' 섹션의 TAM·SAM·SOM·연도별 그래프 (보고서 버전마다 한 번 만들어 저장) */
  marketSizing?: { reportId: string; data: MarketSizing } | null;
  /** 보고서 요약의 영역별 점수 (보고서 버전마다 한 번 매겨 저장) */
  areaScores?: { reportId: string; data: AreaScore[] } | null;
  /** 프로필 4~7 칸의 짧은 요약 (칸 id → "요약\n· 근거") — 보고서 버전마다 한 번 만들어 저장 */
  reportDigest?: { reportId: string; rows: Record<string, string> } | null;
  reportCount: number;
  profileChangedSinceReport: boolean;
  /** 비로그인 '프로필 미리보기'로 메모만 보고 만든 프로필 (인터뷰 없음) */
  previewProfile?: boolean;
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
  /** 이 보고서를 만들기 직전 버전의 판정·점수 — '무엇이 바뀌었나' 비교용 */
  baseline?: { reportId: string; version: number; decision?: Decision; scores: AreaScore[] | null } | null;
  createdAt: string;
}

// 상태 배지: 단계별 은은한 색 — 메모 회색, 인터뷰 주황, 프로필 파랑, 보고서 바이올렛 (디자인 A안)
export const STATUS_META: Record<IdeaStatus, { label: string; color: string; bg: string; dot: string }> = {
  memo: { label: "메모", color: "#53647A", bg: "#F5F7FB", dot: "#9CA3AF" },
  interviewing: { label: "인터뷰 중", color: "#B45309", bg: "#FFF4E5", dot: "#F59E0B" },
  profiling: { label: "프로필 만드는 중", color: "#B45309", bg: "#FFF4E5", dot: "#F59E0B" },
  profile: { label: "프로필", color: "#1D4ED8", bg: "#E8F1FF", dot: "#3B82F6" },
  diagnosing: { label: "진단 중", color: "#1D4ED8", bg: "#E8F1FF", dot: "#3B82F6" },
  report: { label: "보고서", color: "#FFFFFF", bg: "#134CD8", dot: "#FFFFFF" },
  failed: { label: "실패", color: "#B42318", bg: "#FEF2F2", dot: "#B42318" },
};

export const DECISION_META: Record<Decision, { label: string; color: string }> = {
  GO: { label: "GO", color: "#1A7A4A" },
  PIVOT: { label: "PIVOT", color: "#856404" },
  VALIDATE_MORE: { label: "VALIDATE MORE", color: "#53647A" },
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
