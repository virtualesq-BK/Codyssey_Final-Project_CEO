const STORAGE_KEY = "nadosajang_ideas";

export type SavedIdea = {
  id: string;
  title: string;
  industry: string;
  decision: string;
  confidence: number;
  summary: string;
  savedAt: string;
};

export function saveIdeaToStorage(idea: SavedIdea) {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const list: SavedIdea[] = raw ? JSON.parse(raw) : [];
    const filtered = list.filter((i) => i.id !== idea.id);
    filtered.unshift(idea);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered.slice(0, 20)));
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

export function deleteIdeaFromStorage(id: string): SavedIdea[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const list: SavedIdea[] = raw ? JSON.parse(raw) : [];
    const updated = list.filter((i) => i.id !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    return updated;
  } catch {
    return [];
  }
}
