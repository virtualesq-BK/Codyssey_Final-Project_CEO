/**
 * 아이디어 저장소 — 모든 페이지는 이 파일을 통해서만 읽고 쓴다.
 * 로그인: Firestore가 기준 (브라우저에도 사본 저장)
 * 비로그인: 브라우저 localStorage
 */
import type { User } from "firebase/auth";
import type { AnalyzeRequest, AnalyzeResponse } from "@/lib/api";
import { deleteAnalysis, getAnalyses, getAnalysis, saveAnalysis } from "@/lib/firestore";
import {
  type SavedIdea,
  deleteIdeaFromStorage,
  loadIdeaDetailFromStorage,
  loadIdeasFromStorage,
  saveIdeaToStorage,
} from "@/lib/storage";

export type IdeaSummary = SavedIdea;

/** 상세 페이지를 다시 그리는 데 필요한 분석 전체 */
export interface IdeaDetail {
  input: AnalyzeRequest;
  response: AnalyzeResponse;
  elapsedMs?: number;
}

export async function saveIdea(user: User | null, summary: IdeaSummary, detail: IdeaDetail) {
  saveIdeaToStorage(summary, detail);
  if (user) {
    await saveAnalysis(user.uid, summary, detail);
  }
}

export async function listIdeas(user: User | null): Promise<IdeaSummary[]> {
  if (!user) return loadIdeasFromStorage();
  try {
    return await getAnalyses(user.uid);
  } catch {
    return loadIdeasFromStorage();
  }
}

export async function getIdea(
  user: User | null,
  id: string,
): Promise<{ summary: IdeaSummary; detail: IdeaDetail | null } | null> {
  if (user) {
    try {
      const found = await getAnalysis(user.uid, id);
      if (found) {
        // 예전에 요약만 저장된 문서라면 브라우저 사본의 상세로 보완
        return { summary: found.summary, detail: found.detail ?? loadIdeaDetailFromStorage(id) };
      }
    } catch {}
  }
  const summary = loadIdeasFromStorage().find((i) => i.id === id);
  if (!summary) return null;
  return { summary, detail: loadIdeaDetailFromStorage(id) };
}

export async function deleteIdea(user: User | null, id: string) {
  deleteIdeaFromStorage(id);
  if (user) {
    await deleteAnalysis(user.uid, id);
  }
}
