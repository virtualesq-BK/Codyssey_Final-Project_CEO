/** 아이템 관련 뉴스 — 백엔드 /api/v1/news (Google 뉴스 RSS) */
export type NewsItem = {
  title: string;
  source: string;
  url: string;
  published_at: string;
};

export async function fetchNews(q: string, limit = 5): Promise<NewsItem[]> {
  const res = await fetch(`/api/v1/news?q=${encodeURIComponent(q)}&limit=${limit}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.items ?? [];
}
