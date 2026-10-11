import {
  collection,
  deleteDoc,
  doc,
  getDoc,
  setDoc,
  getDocs,
  query,
  orderBy,
  limit,
  Timestamp,
  type DocumentData,
} from "firebase/firestore";
import { db } from "@/lib/firebase";
import type { IdeaDetail } from "@/lib/ideaStore";

export interface SavedAnalysis {
  id: string;
  title: string;
  industry: string;
  decision: string;
  confidence: number;
  summary: string;
  savedAt: string;
}

function toSavedAnalysis(id: string, data: DocumentData): SavedAnalysis {
  return {
    id,
    title: data.title,
    industry: data.industry,
    decision: data.decision,
    confidence: data.confidence,
    summary: data.summary,
    savedAt:
      data.savedAt instanceof Timestamp
        ? data.savedAt.toDate().toISOString()
        : data.savedAt,
  };
}

export async function saveAnalysis(userId: string, analysis: SavedAnalysis, detail?: IdeaDetail) {
  const ref = doc(db, "users", userId, "analyses", analysis.id);
  await setDoc(ref, {
    ...analysis,
    savedAt: Timestamp.fromDate(new Date(analysis.savedAt)),
    // Firestore는 undefined 값을 거부하므로 JSON 왕복으로 제거
    ...(detail ? { detail: JSON.parse(JSON.stringify(detail)) } : {}),
  });
}

export async function getAnalyses(userId: string, count = 20): Promise<SavedAnalysis[]> {
  const ref = collection(db, "users", userId, "analyses");
  const q = query(ref, orderBy("savedAt", "desc"), limit(count));
  const snap = await getDocs(q);
  return snap.docs.map((d) => toSavedAnalysis(d.id, d.data()));
}

export async function getAnalysis(
  userId: string,
  id: string,
): Promise<{ summary: SavedAnalysis; detail: IdeaDetail | null } | null> {
  const snap = await getDoc(doc(db, "users", userId, "analyses", id));
  if (!snap.exists()) return null;
  const data = snap.data();
  return { summary: toSavedAnalysis(snap.id, data), detail: data.detail ?? null };
}

export async function deleteAnalysis(userId: string, id: string) {
  await deleteDoc(doc(db, "users", userId, "analyses", id));
}
