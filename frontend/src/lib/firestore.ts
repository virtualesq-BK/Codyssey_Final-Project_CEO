import {
  collection,
  doc,
  setDoc,
  getDocs,
  query,
  orderBy,
  limit,
  Timestamp,
} from "firebase/firestore";
import { db } from "@/lib/firebase";

export interface SavedAnalysis {
  id: string;
  title: string;
  industry: string;
  decision: string;
  confidence: number;
  summary: string;
  savedAt: string;
}

export async function saveAnalysis(userId: string, analysis: SavedAnalysis) {
  const ref = doc(db, "users", userId, "analyses", analysis.id);
  await setDoc(ref, {
    ...analysis,
    savedAt: Timestamp.fromDate(new Date(analysis.savedAt)),
  });
}

export async function getAnalyses(userId: string, count = 20): Promise<SavedAnalysis[]> {
  const ref = collection(db, "users", userId, "analyses");
  const q = query(ref, orderBy("savedAt", "desc"), limit(count));
  const snap = await getDocs(q);
  return snap.docs.map((d) => {
    const data = d.data();
    return {
      id: d.id,
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
  });
}
