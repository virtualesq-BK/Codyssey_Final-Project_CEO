/**
 * Firestore 경로
 *   users/{uid}/ideas/{ideaId}                    아이디어 (상태·프로필·최신 보고서 요약)
 *   users/{uid}/ideas/{ideaId}/reports/{reportId} 상세 진단 결과, 버전별로 쌓임
 *   users/{uid}/applications/{appId}              지원서 (아이템 × 지원사업)
 *   users/{uid}/analyses/{id}                     구조 개편 전 기록 — 읽기만 함
 */
import {
  collection,
  deleteDoc,
  doc,
  getDoc,
  getDocs,
  limit,
  orderBy,
  query,
  setDoc,
  Timestamp,
  updateDoc,
  type DocumentData,
} from "firebase/firestore";
import { db } from "@/lib/firebase";
import type { Application } from "@/lib/application";
import type { Idea, IdeaReport } from "@/lib/idea";
import type { LegacyDetail, LegacyIdea } from "@/lib/storage";

// Firestore는 undefined 값을 거부하므로 JSON 왕복으로 제거
function clean<T>(value: T): T {
  return JSON.parse(JSON.stringify(value));
}

function ideaRef(uid: string, ideaId: string) {
  return doc(db, "users", uid, "ideas", ideaId);
}

function reportsCol(uid: string, ideaId: string) {
  return collection(db, "users", uid, "ideas", ideaId, "reports");
}

export async function getIdeasFS(uid: string, count = 50): Promise<Idea[]> {
  const q = query(collection(db, "users", uid, "ideas"), orderBy("updatedAt", "desc"), limit(count));
  const snap = await getDocs(q);
  return snap.docs.map((d) => ({ ...(d.data() as Idea), id: d.id }));
}

export async function getIdeaIdsFS(uid: string): Promise<Set<string>> {
  const snap = await getDocs(collection(db, "users", uid, "ideas"));
  return new Set(snap.docs.map((d) => d.id));
}

export async function getIdeaFS(uid: string, ideaId: string): Promise<Idea | null> {
  const snap = await getDoc(ideaRef(uid, ideaId));
  return snap.exists() ? { ...(snap.data() as Idea), id: snap.id } : null;
}

export async function setIdeaFS(uid: string, idea: Idea) {
  await setDoc(ideaRef(uid, idea.id), clean(idea));
}

export async function updateIdeaFS(uid: string, ideaId: string, patch: Partial<Idea>) {
  await updateDoc(ideaRef(uid, ideaId), clean(patch) as DocumentData);
}

export async function deleteIdeaFS(uid: string, ideaId: string) {
  // 하위 컬렉션은 문서와 함께 지워지지 않아 보고서부터 지운다
  const reports = await getDocs(reportsCol(uid, ideaId));
  await Promise.all(reports.docs.map((d) => deleteDoc(d.ref)));
  await deleteDoc(ideaRef(uid, ideaId));
}

export async function getReportsFS(uid: string, ideaId: string): Promise<IdeaReport[]> {
  const snap = await getDocs(query(reportsCol(uid, ideaId), orderBy("version", "desc")));
  return snap.docs.map((d) => ({ ...(d.data() as IdeaReport), id: d.id }));
}

export async function setReportFS(uid: string, ideaId: string, report: IdeaReport) {
  await setDoc(doc(reportsCol(uid, ideaId), report.id), clean(report));
}

export async function getLegacyAnalysesFS(
  uid: string,
): Promise<{ summary: LegacyIdea; detail: LegacyDetail | null }[]> {
  const snap = await getDocs(collection(db, "users", uid, "analyses"));
  return snap.docs.map((d) => {
    const data = d.data();
    return {
      summary: {
        id: d.id,
        title: data.title,
        industry: data.industry,
        decision: data.decision,
        confidence: data.confidence,
        summary: data.summary,
        savedAt: data.savedAt instanceof Timestamp ? data.savedAt.toDate().toISOString() : data.savedAt,
      },
      detail: data.detail ?? null,
    };
  });
}

// ── 지원서 ────────────────────────────────────────────────────────────

export async function getApplicationsFS(uid: string): Promise<Application[]> {
  const snap = await getDocs(query(collection(db, "users", uid, "applications"), orderBy("updatedAt", "desc")));
  return snap.docs.map((d) => ({ ...(d.data() as Application), id: d.id }));
}

export async function setApplicationFS(uid: string, app: Application) {
  await setDoc(doc(db, "users", uid, "applications", app.id), clean(app));
}

export async function deleteApplicationFS(uid: string, appId: string) {
  await deleteDoc(doc(db, "users", uid, "applications", appId));
}
