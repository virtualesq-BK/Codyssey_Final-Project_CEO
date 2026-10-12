import type { IdeaDetail } from "@/lib/ideaStore";

const STORAGE_KEY = "nadosajang_ideas";
// 목록은 가볍게 유지하고, 분석 결과 전체는 아이디어별 키에 따로 저장
const DETAIL_KEY_PREFIX = "nadosajang_idea_detail_";
const MAX_IDEAS = 20;

export type SavedIdea = {
  id: string;
  title: string;
  industry: string;
  decision: string;
  confidence: number;
  summary: string;
  savedAt: string;
};

export function saveIdeaToStorage(idea: SavedIdea, detail?: IdeaDetail) {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const list: SavedIdea[] = raw ? JSON.parse(raw) : [];
    const filtered = list.filter((i) => i.id !== idea.id);
    filtered.unshift(idea);
    // 목록에서 밀려난 아이디어의 상세도 함께 정리
    filtered.slice(MAX_IDEAS).forEach((i) => localStorage.removeItem(DETAIL_KEY_PREFIX + i.id));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered.slice(0, MAX_IDEAS)));
    if (detail) {
      localStorage.setItem(DETAIL_KEY_PREFIX + idea.id, JSON.stringify(detail));
    }
  } catch {}
}

export function loadIdeasFromStorage(): SavedIdea[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function loadIdeaDetailFromStorage(id: string): IdeaDetail | null {
  try {
    const raw = localStorage.getItem(DETAIL_KEY_PREFIX + id);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function deleteIdeaFromStorage(id: string): SavedIdea[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const list: SavedIdea[] = raw ? JSON.parse(raw) : [];
    const updated = list.filter((i) => i.id !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    localStorage.removeItem(DETAIL_KEY_PREFIX + id);
    return updated;
  } catch {
    return [];
  }
}
