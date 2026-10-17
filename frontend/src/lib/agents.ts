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
  partial: "#FFFBEB",
  failed: "#FEF2F2",
  running: "#F5F7FB",
  pending: "#F5F7FB",
  skipped: "#F5F7FB",
};

export const STATUS_TEXT: Record<string, string> = {
  success: "분석 완료",
  partial: "부분 완료 · 일부 근거 부족",
  failed: "분석 실패",
  running: "분석 중",
  pending: "대기",
  skipped: "건너뜀",
};

/** 분석 분야를 사람이 읽는 이름으로 */
export const AGENT_LABELS: Record<string, string> = {
  MarketAgent: "시장",
  CustomerAgent: "고객",
  CompetitorAgent: "경쟁",
  BusinessModelAgent: "수익 구조",
  FinancialAgent: "재무",
  RiskAgent: "위험",
};

/** 신뢰도 바·숫자 표시 — 개발 중 임시로 숨김 (true로 바꾸면 다시 보인다) */
export const SHOW_CONFIDENCE = false;
