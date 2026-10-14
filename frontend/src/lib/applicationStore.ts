/**
 * 지원서 저장소. 로그인: Firestore users/{uid}/applications, 비로그인: 브라우저 localStorage.
 * 보고서까지 나온 아이템만 지원서를 만들 수 있다.
 */
import type { User } from "firebase/auth";
import type { Application, ApplicationStatus } from "@/lib/application";
import { deleteApplicationFS, getApplicationsFS, setApplicationFS } from "@/lib/firestore";
import { type Idea, displayTitle, effectiveStatus } from "@/lib/idea";
import { newId } from "@/lib/ideaStore";
import type { Program } from "@/lib/programs";

const KEY = "nadosajang_applications";

function loadLocal(): Application[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "[]");
  } catch {
    return [];
  }
}

function saveLocal(list: Application[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list));
  } catch {}
}

/** 지원서를 만들 수 있는 아이템인지 — 보고서가 있어야 한다 */
export function canApply(idea: Idea) {
  return idea.reportCount > 0 && effectiveStatus(idea).status !== "diagnosing";
}

export async function listApplications(user: User | null): Promise<Application[]> {
  const list = user ? await getApplicationsFS(user.uid) : loadLocal();
  return list.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
}

export async function createApplication(
  user: User | null,
  existing: Application[],
  idea: Idea,
  program: Program,
): Promise<Application> {
  if (existing.some((a) => a.ideaId === idea.id && a.programId === program.id)) {
    throw new Error("이 아이템으로 이 사업에 지원하는 지원서가 이미 있어요.");
  }
  const now = new Date().toISOString();
  const app: Application = {
    id: newId(),
    ideaId: idea.id,
    ideaName: displayTitle(idea),
    programId: program.id,
    programTitle: program.title,
    programOrg: program.organization,
    programDeadline: program.ends_on,
    programAmount: program.amount,
    status: "draft",
    createdAt: now,
    updatedAt: now,
  };
  if (user) await setApplicationFS(user.uid, app);
  else saveLocal([app, ...loadLocal()]);
  return app;
}

export async function updateApplicationStatus(user: User | null, app: Application, status: ApplicationStatus) {
  const next = { ...app, status, updatedAt: new Date().toISOString() };
  if (user) await setApplicationFS(user.uid, next);
  else saveLocal(loadLocal().map((a) => (a.id === app.id ? next : a)));
  return next;
}

export async function deleteApplication(user: User | null, id: string) {
  if (user) await deleteApplicationFS(user.uid, id);
  else saveLocal(loadLocal().filter((a) => a.id !== id));
}
