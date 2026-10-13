/**
 * 아이디어 저장소 — 모든 페이지는 이 파일을 통해서만 읽고 쓴다.
 * 로그인: Firestore가 기준. 처음 불러올 때 브라우저에 있던 아이디어와 예전 기록을 계정으로 옮긴다.
 * 비로그인: 브라우저 localStorage (메모 단계까지만 쓰인다)
 */
import type { User } from "firebase/auth";
import { analyze, type Decision } from "@/lib/api";
import {
  EMPTY_PROFILE,
  type Idea,
  type IdeaProfile,
  type IdeaReport,
  newIdea,
  summarizeReport,
  toAnalyzeRequest,
} from "@/lib/idea";
import {
  deleteIdeaFS,
  getIdeaFS,
  getIdeaIdsFS,
  getIdeasFS,
  getLegacyAnalysesFS,
  getReportsFS,
  setIdeaFS,
  setReportFS,
  updateIdeaFS,
} from "@/lib/firestore";
import {
  type LegacyDetail,
  type LegacyIdea,
  clearLocalIdeas,
  deleteLocalIdea,
  loadLocalIdeas,
  loadLocalReports,
  saveLocalIdea,
  saveLocalReport,
  takeLegacyLocalIdeas,
} from "@/lib/storage";

/** 구조 개편 전 분석 기록 → 보고서 상태의 아이디어 */
function fromLegacy(summary: LegacyIdea, detail: LegacyDetail | null): { idea: Idea; report: IdeaReport | null } {
  const input = detail?.input;
  const profile: IdeaProfile = {
    ...EMPTY_PROFILE,
    name: input?.title ?? summary.title,
    industry: input?.industry ?? summary.industry,
    location: input?.location ?? EMPTY_PROFILE.location,
    customer: input?.customer ?? "",
    problem: input?.problem ?? "",
    solution: input?.solution ?? "",
  };
  const report: IdeaReport | null = detail
    ? {
        id: summary.id,
        version: 1,
        profile,
        input: detail.input,
        response: detail.response,
        elapsedMs: detail.elapsedMs,
        createdAt: summary.savedAt,
      }
    : null;
  const idea: Idea = {
    ...newIdea(summary.id, ""),
    status: "report",
    profile,
    latestReport: report
      ? summarizeReport(report)
      : {
          id: summary.id,
          version: 1,
          decision: summary.decision as Decision,
          confidence: summary.confidence,
          summary: summary.summary,
          createdAt: summary.savedAt,
        },
    reportCount: report ? 1 : 0,
    statusChangedAt: summary.savedAt,
    createdAt: summary.savedAt,
    updatedAt: summary.savedAt,
  };
  return { idea, report };
}

/** 예전 키의 기록을 새 구조로 옮겨 브라우저에 둔다 */
function migrateLegacyLocal() {
  const existing = new Set(loadLocalIdeas().map((i) => i.id));
  for (const { summary, detail } of takeLegacyLocalIdeas()) {
    if (existing.has(summary.id)) continue;
    const { idea, report } = fromLegacy(summary, detail);
    saveLocalIdea(idea);
    if (report) saveLocalReport(idea.id, report);
  }
}

const syncedUids = new Set<string>();

/** 브라우저에 있던 아이디어와 예전 Firestore 기록을 계정의 새 구조로 옮긴다 (세션당 한 번) */
async function syncToAccount(uid: string) {
  if (syncedUids.has(uid)) return;
  migrateLegacyLocal();
  const existing = await getIdeaIdsFS(uid);

  for (const idea of loadLocalIdeas()) {
    if (existing.has(idea.id)) continue;
    await setIdeaFS(uid, idea);
    for (const report of loadLocalReports(idea.id)) await setReportFS(uid, idea.id, report);
    existing.add(idea.id);
  }
  clearLocalIdeas();

  for (const { summary, detail } of await getLegacyAnalysesFS(uid)) {
    if (existing.has(summary.id)) continue;
    const { idea, report } = fromLegacy(summary, detail);
    await setIdeaFS(uid, idea);
    if (report) await setReportFS(uid, idea.id, report);
  }
  syncedUids.add(uid);
}

export async function listIdeas(user: User | null): Promise<Idea[]> {
  if (!user) {
    migrateLegacyLocal();
    return loadLocalIdeas().sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  }
  await syncToAccount(user.uid);
  return getIdeasFS(user.uid);
}

export async function getIdea(user: User | null, id: string): Promise<Idea | null> {
  if (!user) {
    migrateLegacyLocal();
    return loadLocalIdeas().find((i) => i.id === id) ?? null;
  }
  await syncToAccount(user.uid);
  return getIdeaFS(user.uid, id);
}

export async function listReports(user: User | null, ideaId: string): Promise<IdeaReport[]> {
  if (!user) return loadLocalReports(ideaId);
  return getReportsFS(user.uid, ideaId);
}

export async function createMemo(user: User | null, memo: string): Promise<Idea> {
  const idea = newIdea(crypto.randomUUID(), memo.trim());
  if (user) await setIdeaFS(user.uid, idea);
  else saveLocalIdea(idea);
  return idea;
}

export async function updateIdea(user: User | null, idea: Idea, patch: Partial<Idea>): Promise<Idea> {
  const now = new Date().toISOString();
  const next: Idea = {
    ...idea,
    ...patch,
    ...(patch.status && patch.status !== idea.status ? { statusChangedAt: now } : {}),
    updatedAt: now,
  };
  if (user) {
    const { id, ...fields } = next;
    await updateIdeaFS(user.uid, id, fields);
  } else {
    saveLocalIdea(next);
  }
  return next;
}

/** 프로필 저장. 보고서가 이미 있으면 '보고서 새로 작성하기'가 켜지도록 표시한다 */
export async function saveProfile(user: User | null, idea: Idea, profile: IdeaProfile): Promise<Idea> {
  return updateIdea(user, idea, {
    profile,
    profileChangedSinceReport: idea.reportCount > 0 || idea.profileChangedSinceReport,
  });
}

export async function deleteIdea(user: User | null, id: string) {
  if (user) await deleteIdeaFS(user.uid, id);
  else deleteLocalIdea(id);
}

/** 상세 진단 실행 → 새 버전 보고서 저장. 실패하면 실패 상태로 남긴다 */
export async function runDiagnosis(user: User | null, idea: Idea): Promise<Idea> {
  let current = await updateIdea(user, idea, { status: "diagnosing", failedStage: null, errorMessage: null });
  const input = toAnalyzeRequest(current.profile);
  const t0 = Date.now();

  const fail = (message: string) =>
    updateIdea(user, current, { status: "failed", failedStage: "diagnosing", errorMessage: message });

  let response;
  try {
    response = await analyze(input);
  } catch (err) {
    return fail(err instanceof Error ? err.message : String(err));
  }
  // 모든 분야가 실패하면 보고서로 남기지 않는다 (기본값 판정이 진짜 판정처럼 보이지 않도록)
  if (response.workflow_result.status === "failed") {
    return fail("모든 분야의 분석이 실패했어요.");
  }

  const report: IdeaReport = {
    id: response.idea_id,
    // 예전 기록은 요약만 있고 보고서 문서가 없을 수 있어 최신 버전 번호도 함께 본다
    version: Math.max(current.reportCount, current.latestReport?.version ?? 0) + 1,
    profile: current.profile,
    input,
    response,
    elapsedMs: Date.now() - t0,
    createdAt: new Date().toISOString(),
  };
  try {
    if (user) await setReportFS(user.uid, current.id, report);
    else saveLocalReport(current.id, report);
  } catch (err) {
    return fail(err instanceof Error ? err.message : String(err));
  }

  current = await updateIdea(user, current, {
    status: "report",
    latestReport: summarizeReport(report),
    reportCount: report.version,
    profileChangedSinceReport: false,
  });
  return current;
}
