/** 지원사업 공고 — 백엔드 /api/v1/programs (지금은 샘플 데이터) */
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
};

export async function fetchPrograms(params?: URLSearchParams): Promise<Program[]> {
  const res = await fetch(`/api/v1/programs${params ? `?${params}` : ""}`);
  if (!res.ok) throw new Error("공고를 불러오지 못했어요.");
  const data = await res.json();
  return data.items ?? [];
}
