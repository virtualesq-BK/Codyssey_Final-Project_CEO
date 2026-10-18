/** 지원사업 공고 — 백엔드 /api/v1/programs (K-Startup 모집 중 공고, 실패 시 샘플) */
export type Program = {
  id: string;
  title: string;
  organization: string;
  category: string;
  region: string;
  deadline_status: string;
  ends_on: string;
  starts_on: string;
  target: string;
  body: string;
  detail_url: string;
  amount: string;
  /** 온라인 접수 주소 (K-Startup 공고에 있을 때) */
  apply_url?: string;
  source?: string;
};

/** 상시 노출되는 고정 프로그램 */
export const PINNED_PROGRAMS: Program[] = [
  {
    id: "modues-changup",
    title: "모두의 창업",
    organization: "모두의 창업",
    category: "창업교육",
    region: "전국",
    deadline_status: "상시",
    ends_on: "상시",
    starts_on: "",
    target: "예비창업자·초기창업자",
    body: "누구나 도전할 수 있는 창업 지원 프로그램입니다.",
    detail_url: "",
    amount: "",
    source: "pinned",
  },
];

export async function fetchPrograms(params?: URLSearchParams): Promise<Program[]> {
  const res = await fetch(`/api/v1/programs${params ? `?${params}` : ""}`);
  if (!res.ok) throw new Error("공고를 불러오지 못했어요.");
  const data = await res.json();
  return data.items ?? [];
}
