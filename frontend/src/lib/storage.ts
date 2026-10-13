/**
 * 비로그인용 브라우저 저장소. 로그인하면 ideaStore가 여기 있는 아이디어를 계정으로 옮긴다.
 */
import type { AnalyzeRequest, AnalyzeResponse } from "@/lib/api";
import type { Idea, IdeaReport } from "@/lib/idea";

const IDEAS_KEY = "nadosajang_ideas_v2";
const REPORTS_KEY_PREFIX = "nadosajang_reports_";
const MAX_IDEAS = 20;

// 구조 개편 전 키 — 읽기만 하고 지우지 않는다
const LEGACY_IDEAS_KEY = "nadosajang_ideas";
const LEGACY_DETAIL_KEY_PREFIX = "nadosajang_idea_detail_";
const LEGACY_MIGRATED_KEY = "nadosajang_v2_migrated";

/** 구조 개편 전 목록 한 줄 */
export type LegacyIdea = {
  id: string;
  title: string;
  industry: string;
  decision: string;
  confidence: number;
  summary: string;
  savedAt: string;
};

/** 구조 개편 전 상세 */
export interface LegacyDetail {
  input: AnalyzeRequest;
  response: AnalyzeResponse;
  elapsedMs?: number;
}

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function write(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {}
}

function remove(key: string) {
  try {
    localStorage.removeItem(key);
  } catch {}
}

export function loadLocalIdeas(): Idea[] {
  return read<Idea[]>(IDEAS_KEY, []);
}

export function saveLocalIdea(idea: Idea) {
  const list = loadLocalIdeas().filter((i) => i.id !== idea.id);
  list.unshift(idea);
  // 목록에서 밀려난 아이디어의 보고서도 함께 정리
  list.slice(MAX_IDEAS).forEach((i) => remove(REPORTS_KEY_PREFIX + i.id));
  write(IDEAS_KEY, list.slice(0, MAX_IDEAS));
}

export function deleteLocalIdea(id: string) {
  write(
    IDEAS_KEY,
    loadLocalIdeas().filter((i) => i.id !== id),
  );
  remove(REPORTS_KEY_PREFIX + id);
}

export function loadLocalReports(ideaId: string): IdeaReport[] {
  return read<IdeaReport[]>(REPORTS_KEY_PREFIX + ideaId, []);
}

export function saveLocalReport(ideaId: string, report: IdeaReport) {
  const reports = loadLocalReports(ideaId).filter((r) => r.id !== report.id);
  write(REPORTS_KEY_PREFIX + ideaId, [report, ...reports]);
}

export function clearLocalIdeas() {
  loadLocalIdeas().forEach((i) => remove(REPORTS_KEY_PREFIX + i.id));
  remove(IDEAS_KEY);
}

/** 예전 키에 남은 분석 기록. 한 번 꺼내면 다시 꺼내지 않는다 */
export function takeLegacyLocalIdeas(): { summary: LegacyIdea; detail: LegacyDetail | null }[] {
  if (read<boolean>(LEGACY_MIGRATED_KEY, false)) return [];
  const legacy = read<LegacyIdea[]>(LEGACY_IDEAS_KEY, []).map((summary) => ({
    summary,
    detail: read<LegacyDetail | null>(LEGACY_DETAIL_KEY_PREFIX + summary.id, null),
  }));
  write(LEGACY_MIGRATED_KEY, true);
  return legacy;
}
