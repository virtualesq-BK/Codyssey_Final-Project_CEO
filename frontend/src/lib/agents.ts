import type { AgentStatus } from "@/lib/api";

export const AGENT_ORDER = [
  "MarketAgent",
  "CustomerAgent",
  "CompetitorAgent",
  "BusinessModelAgent",
  "FinancialAgent",
  "RiskAgent",
];

export const STATUS_BG: Record<AgentStatus, string> = {
  success: "#F0FFF4",
  partial: "#FFF7EB",
  failed: "#FDECEA",
  running: "#F5F6F8",
  pending: "#F5F6F8",
  skipped: "#F5F6F8",
};

export const STATUS_TEXT: Record<string, string> = {
  success: "분석 완료",
  partial: "부분 완료 · 일부 근거 부족",
  failed: "분석 실패",
  running: "분석 중",
  pending: "대기",
  skipped: "건너뜀",
};
