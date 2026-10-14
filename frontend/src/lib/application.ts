/**
 * 지원서 = 아이템(보고서까지 나온 아이디어) × 지원사업 1건. 한 아이템으로 여러 사업에 지원할 수 있다.
 * 아이템·공고 정보는 만들 때의 사본을 함께 둔다 (목록 카드를 다시 조회 없이 그리려고).
 */
export type ApplicationStatus = "draft" | "submitted" | "selected" | "rejected";

export interface Application {
  id: string;
  ideaId: string;
  ideaName: string;
  programId: string;
  programTitle: string;
  programOrg: string;
  programDeadline: string;
  programAmount: string;
  status: ApplicationStatus;
  createdAt: string;
  updatedAt: string;
}

export const APPLICATION_STATUS: Record<ApplicationStatus, { label: string; color: string; bg: string }> = {
  draft: { label: "작성 중", color: "#B45309", bg: "#FFF4E5" },
  submitted: { label: "제출 완료", color: "#1D4ED8", bg: "#E8F1FF" },
  selected: { label: "선정", color: "#FFFFFF", bg: "#7270FF" },
  rejected: { label: "탈락", color: "#4B5563", bg: "#F3F4F6" },
};

export type ApplicationFilter = "all" | "draft" | "submitted" | "result";

export const APPLICATION_FILTERS: { key: ApplicationFilter; label: string }[] = [
  { key: "all", label: "전체보기" },
  { key: "draft", label: "작성 중" },
  { key: "submitted", label: "제출 완료" },
  { key: "result", label: "결과" },
];

export function matchesFilter(app: Application, filter: ApplicationFilter) {
  if (filter === "all") return true;
  if (filter === "result") return app.status === "selected" || app.status === "rejected";
  return app.status === filter;
}
