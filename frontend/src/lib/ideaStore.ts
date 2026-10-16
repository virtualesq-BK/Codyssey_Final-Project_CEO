/**
 * 아이디어 저장소 — 모든 페이지는 이 파일을 통해서만 읽고 쓴다.
 * 로그인: Firestore가 기준. 처음 불러올 때 브라우저에 있던 아이디어와 예전 기록을 계정으로 옮긴다.
 * 비로그인: 브라우저 localStorage (메모 단계까지만 쓰인다)
 */
import type { User } from "firebase/auth";
import {
  type AnalyzeResponse,
  startAnalyzeJob,
  type Decision,
  type InterviewMessage,
  type InterviewTurn,
  interviewDraftProfile,
  interviewNext,
} from "@/lib/api";
import {
  EMPTY_PROFILE,
  type Idea,
  type IdeaInterview,
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

// randomUUID는 https·localhost에서만 있어 Tailscale 등 http 접속용 대체 생성기를 둔다
export function newId(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

export async function createMemo(user: User | null, memo: string): Promise<Idea> {
  const idea = newIdea(newId(), memo.trim());
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
/** 아이디어의 일부 칸만 저장한다 — 손익표·시장 규모·점수처럼 동시에 저장될 수 있는 부가 정보용 (다른 칸을 덮어쓰지 않음) */
export async function patchIdea(user: User | null, ideaId: string, patch: Partial<Idea>): Promise<void> {
  const fields = { ...patch, updatedAt: new Date().toISOString() };
  if (user) {
    await updateIdeaFS(user.uid, ideaId, fields);
    return;
  }
  const local = loadLocalIdeas().find((i) => i.id === ideaId);
  if (local) saveLocalIdea({ ...local, ...fields });
}

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

function withTurn(messages: InterviewMessage[], turn: InterviewTurn): IdeaInterview {
  return {
    messages: [...messages, { role: "assistant", content: turn.message }],
    covered: turn.covered,
    quickReplies: turn.quick_replies,
    done: turn.done,
  };
}

/** 인터뷰 시작 — 첫 질문을 받아 '인터뷰 중'으로 */
export async function startInterview(user: User | null, idea: Idea): Promise<Idea> {
  const turn = await interviewNext(idea.memo, []);
  return updateIdea(user, idea, {
    status: "interviewing",
    failedStage: null,
    errorMessage: null,
    interview: withTurn([], turn),
  });
}

/** 답변을 보내고 다음 질문을 받는다. 실패하면 저장하지 않고 에러를 던진다 (입력은 화면에 남음) */
export async function answerInterview(user: User | null, idea: Idea, answer: string): Promise<Idea> {
  const interview = idea.interview;
  if (!interview) throw new Error("인터뷰가 시작되지 않았어요.");
  const messages: InterviewMessage[] = [...interview.messages, { role: "user", content: answer.trim() }];
  const turn = await interviewNext(idea.memo, messages, interview.covered);
  return updateIdea(user, idea, { interview: withTurn(messages, turn) });
}

/** 인터뷰 마치기 → 1차 분석(LLM)으로 프로필 초안 → '프로필' 상태 */
export async function finishInterview(user: User | null, idea: Idea): Promise<Idea> {
  const messages = idea.interview?.messages ?? [];
  const current = await updateIdea(user, idea, { status: "profiling", failedStage: null, errorMessage: null });
  let draft;
  try {
    draft = await interviewDraftProfile(current.memo, messages);
  } catch (err) {
    return updateIdea(user, current, {
      status: "failed",
      failedStage: "profiling",
      errorMessage: err instanceof Error ? err.message : String(err),
    });
  }
  return updateIdea(user, current, {
    status: "profile",
    profile: {
      name: draft.name || current.profile.name || current.memo.split("\n")[0].slice(0, 40),
      oneLiner: draft.one_liner,
      industry: draft.industry,
      location: draft.location || EMPTY_PROFILE.location,
      customer: draft.customer,
      problem: draft.problem,
      solution: draft.solution,
      revenueModel: draft.revenue_model,
    },
  });
}

/** 상세분석 시작 — 서버에 작업을 맡기고 작업 번호를 아이디어에 적어 둔다 (결과는 diagnosisRunner가 받아 저장) */
export async function startDiagnosis(user: User | null, idea: Idea): Promise<Idea> {
  const input = toAnalyzeRequest(idea.profile);
  const jobId = await startAnalyzeJob(input);
  return updateIdea(user, idea, {
    status: "diagnosing",
    failedStage: null,
    errorMessage: null,
    diagnosisJobId: jobId,
    diagnosisInput: input,
  });
}

/** 상세분석 실패로 남긴다 */
export function failDiagnosis(user: User | null, idea: Idea, message: string): Promise<Idea> {
  return updateIdea(user, idea, {
    status: "failed",
    failedStage: "diagnosing",
    errorMessage: message,
    diagnosisJobId: null,
  });
}

/** 상세분석 결과 → 새 버전 보고서 저장 */
export async function completeDiagnosis(user: User | null, idea: Idea, response: AnalyzeResponse, elapsedMs: number): Promise<Idea> {
  // 모든 분야가 실패하면 보고서로 남기지 않는다 (기본값 판정이 진짜 판정처럼 보이지 않도록)
  if (response.workflow_result.status === "failed") {
    return failDiagnosis(user, idea, "모든 분야의 분석이 실패했어요.");
  }
  const report: IdeaReport = {
    id: response.idea_id,
    // 예전 기록은 요약만 있고 보고서 문서가 없을 수 있어 최신 버전 번호도 함께 본다
    version: Math.max(idea.reportCount, idea.latestReport?.version ?? 0) + 1,
    profile: idea.profile,
    input: idea.diagnosisInput ?? toAnalyzeRequest(idea.profile),
    response,
    elapsedMs,
    createdAt: new Date().toISOString(),
  };
  try {
    if (user) await setReportFS(user.uid, idea.id, report);
    else saveLocalReport(idea.id, report);
  } catch (err) {
    return failDiagnosis(user, idea, err instanceof Error ? err.message : String(err));
  }
  return updateIdea(user, idea, {
    status: "report",
    latestReport: summarizeReport(report),
    reportCount: report.version,
    profileChangedSinceReport: false,
    diagnosisJobId: null,
    diagnosisInput: null,
  });
}
