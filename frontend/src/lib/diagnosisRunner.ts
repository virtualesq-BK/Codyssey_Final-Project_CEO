/**
 * 상세분석 진행 감시 — 서버 작업(job)을 주기적으로 확인하고, 끝나면 보고서를 저장한다.
 * 페이지가 아니라 이 모듈이 들고 있어서, 다른 화면으로 옮겨 가도 감시가 이어진다.
 * 창을 닫았다가 다시 열면 DiagnosisWatcher가 진단 중인 아이디어를 찾아 다시 붙인다.
 */
import type { User } from "firebase/auth";
import { type AnalyzeJob, JobGoneError, getAnalyzeJob } from "@/lib/api";
import type { Idea } from "@/lib/idea";
import { completeDiagnosis, failDiagnosis, getIdea } from "@/lib/ideaStore";

const POLL_MS = 3000;
/** 네트워크 오류가 이만큼 이어지면 포기한다 (약 3분) */
const MAX_ERRORS = 60;

export interface DiagnosisRun {
  ideaId: string;
  jobId: string;
  job: AnalyzeJob | null;
  /** 끝나면 저장된 최신 아이디어 */
  result: Idea | null;
}

type Listener = (run: DiagnosisRun) => void;

const runs = new Map<string, { run: DiagnosisRun; listeners: Set<Listener>; promise: Promise<Idea> }>();
const finishListeners = new Set<(idea: Idea) => void>();

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function emit(ideaId: string) {
  const entry = runs.get(ideaId);
  if (!entry) return;
  const snapshot = { ...entry.run };
  entry.listeners.forEach((l) => l(snapshot));
}

async function poll(user: User | null, idea: Idea, jobId: string): Promise<Idea> {
  const t0 = Date.parse(idea.statusChangedAt) || Date.now();
  let errors = 0;
  for (;;) {
    let job: AnalyzeJob;
    try {
      job = await getAnalyzeJob(jobId);
      errors = 0;
    } catch (err) {
      if (err instanceof JobGoneError || ++errors >= MAX_ERRORS) {
        return finish(user, idea, jobId, null, err instanceof Error ? err.message : String(err));
      }
      await sleep(POLL_MS);
      continue;
    }
    const entry = runs.get(idea.id);
    if (entry) {
      entry.run.job = job;
      emit(idea.id);
    }
    if (job.status === "done" && job.result) return finish(user, idea, jobId, job, null, Date.now() - t0);
    if (job.status === "failed") return finish(user, idea, jobId, job, job.error ?? "분석이 실패했어요.");
    await sleep(POLL_MS);
  }
}

async function finish(
  user: User | null,
  idea: Idea,
  jobId: string,
  job: AnalyzeJob | null,
  error: string | null,
  elapsedMs = 0,
): Promise<Idea> {
  // 다른 탭이 먼저 저장했으면 다시 저장하지 않는다 (보고서 버전이 두 번 늘지 않게)
  const latest = (await getIdea(user, idea.id).catch(() => null)) ?? idea;
  let saved: Idea = latest;
  if (latest.status === "diagnosing" && latest.diagnosisJobId === jobId) {
    saved = error || !job?.result
      ? await failDiagnosis(user, latest, error ?? "분석 결과가 비어 있어요.")
      : await completeDiagnosis(user, latest, job.result, elapsedMs);
  }
  const entry = runs.get(idea.id);
  if (entry) {
    entry.run.result = saved;
    emit(idea.id);
  }
  finishListeners.forEach((l) => l(saved));
  return saved;
}

/** 진단 중인 아이디어의 작업을 감시한다. 이미 감시 중이면 같은 약속(promise)을 돌려준다 */
export function watchDiagnosis(user: User | null, idea: Idea): Promise<Idea> | null {
  const jobId = idea.diagnosisJobId;
  if (idea.status !== "diagnosing" || !jobId) return null;
  const existing = runs.get(idea.id);
  if (existing && existing.run.jobId === jobId) return existing.promise;
  const entry = {
    run: { ideaId: idea.id, jobId, job: null, result: null } as DiagnosisRun,
    listeners: existing?.listeners ?? new Set<Listener>(),
    promise: Promise.resolve(idea),
  };
  runs.set(idea.id, entry);
  entry.promise = poll(user, idea, jobId);
  return entry.promise;
}

/** 아이디어 하나의 진행 상황 구독. 해제 함수를 돌려준다 */
export function subscribeDiagnosis(ideaId: string, listener: Listener): () => void {
  let entry = runs.get(ideaId);
  if (!entry) {
    // 감시 시작 전에 구독해도 나중 진행을 받도록 자리만 만들어 둔다
    entry = { run: { ideaId, jobId: "", job: null, result: null }, listeners: new Set(), promise: Promise.resolve(null as never) };
    runs.set(ideaId, entry);
  }
  entry.listeners.add(listener);
  if (entry.run.job) listener({ ...entry.run });
  return () => entry!.listeners.delete(listener);
}

/** 어떤 아이디어든 진단이 끝나면 알림 (전역 알림용) */
export function onDiagnosisFinished(listener: (idea: Idea) => void): () => void {
  finishListeners.add(listener);
  return () => finishListeners.delete(listener);
}

/** 진행률(0~100)과 남은 시간 대략값 */
export function progressOf(job: AnalyzeJob | null, startedAt: string): { percent: number; remainingSec: number } {
  const TYPICAL_SEC = 150;
  const elapsed = Math.max(0, (Date.now() - Date.parse(job?.started_at ?? startedAt)) / 1000);
  const stages = Object.values(job?.stages ?? {});
  const byStage = stages.length
    ? stages.reduce((s, st) => s + (st.state === "done" || st.state === "failed" ? 1 : st.state === "running" ? 0.35 : 0), 0) / stages.length
    : 0;
  const byTime = Math.min(elapsed / TYPICAL_SEC, 0.95);
  const remainingSec = Math.max(0, Math.round(TYPICAL_SEC - elapsed));
  if (job?.status === "done") return { percent: 100, remainingSec: 0 };
  return { percent: Math.min(99, Math.round(Math.max(byStage, byTime * 0.9) * 100)), remainingSec };
}
