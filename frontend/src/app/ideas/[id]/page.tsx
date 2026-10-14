"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import Header from "@/components/Header";
import InterviewPanel from "@/components/InterviewPanel";
import ProfileWorkspace from "@/components/ProfileWorkspace";
import StatusPill from "@/components/StatusPill";
import { useAuth } from "@/contexts/AuthContext";
import {
  type Idea,
  type IdeaProfile,
  type IdeaReport,
  type IdeaStatus,
  STATUS_META,
  displayTitle,
  effectiveStatus,
  missingFields,
} from "@/lib/idea";
import {
  answerInterview,
  finishInterview,
  getIdea,
  listReports,
  runDiagnosis,
  saveProfile,
  startInterview,
  updateIdea,
} from "@/lib/ideaStore";

const card = "bg-white border border-border rounded-lg p-8 flex flex-col gap-5";

// 인터뷰 화면을 보여줄 상태 (프로필 만들다 실패한 경우 포함)
function inInterview(status: IdeaStatus, failedStage: IdeaStatus | null) {
  return status === "interviewing" || status === "profiling" || (status === "failed" && failedStage === "profiling");
}

// 보고서 단계까지 온 아이디어인지 (진단 중 실패 포함)
function reachedProfile(status: IdeaStatus, failedStage: IdeaStatus | null) {
  return (
    status === "profile" ||
    status === "diagnosing" ||
    status === "report" ||
    (status === "failed" && failedStage === "diagnosing")
  );
}

export default function IdeaDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuth();
  const [idea, setIdea] = useState<Idea | null>(null);
  const [reports, setReports] = useState<IdeaReport[]>([]);
  const [memoDraft, setMemoDraft] = useState("");
  const [draft, setDraft] = useState<IdeaProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    setLoading(true);
    Promise.all([getIdea(user, id), listReports(user, id)])
      .then(([found, foundReports]) => {
        setIdea(found);
        setMemoDraft(found?.memo ?? "");
        setDraft(found?.profile ?? null);
        setReports(foundReports);
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, [id, user, authLoading]);

  // MY아이디어 카드 버튼에서 넘어온 동작(?action=)과 위치(#profile·#report)를 한 번만 처리한다.
  // 동작 함수는 아래 렌더에서 만들어지므로 ref로 최신 것을 넘겨받는다
  const handlersRef = useRef<{
    beginInterview: () => void;
    startProfile: () => void;
    diagnose: () => void;
    canDiagnose: boolean;
  } | null>(null);
  const actionHandled = useRef(false);

  useEffect(() => {
    if (loading || !idea || actionHandled.current) return;
    actionHandled.current = true;
    const action = new URLSearchParams(window.location.search).get("action");
    let target = window.location.hash.slice(1);
    // 새로고침 때 다시 실행되지 않도록 주소에서 action을 지운다
    if (action) window.history.replaceState(null, "", `/ideas/${idea.id}${window.location.hash}`);

    const h = handlersRef.current;
    const { status } = effectiveStatus(idea);
    if (h && user) {
      if (action === "interview" && status === "memo") h.beginInterview();
      else if (action === "write" && (status === "memo" || status === "interviewing")) h.startProfile();
      else if (action === "diagnose") {
        if (h.canDiagnose) h.diagnose();
        else {
          target = "profile";
          setError("필수 칸(*)을 채운 뒤 '분석하기'를 눌러주세요.");
        }
      }
    }
    if (target) {
      setTimeout(() => document.getElementById(target)?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
    }
  }, [loading, idea, user]);

  async function run(task: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await task();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  if (loading || !idea || !draft) {
    return (
      <div className="min-h-screen" style={{ background: "#F3F4F6" }}>
        <Header activeNav="ideas" />
        <main className="max-w-[1200px] mx-auto px-6 py-12">
          <section className={`${card} items-center text-center`}>
            {loading ? (
              <span className="text-text-muted text-sm">불러오는 중…</span>
            ) : (
              <>
                <div className="font-bold text-lg">아이디어를 찾을 수 없어요</div>
                <div className="text-text-secondary text-sm">
                  {error ?? "삭제됐거나 다른 계정·브라우저에 저장된 아이디어일 수 있어요."}
                </div>
                <Link href="/ideas" className="text-sm font-semibold underline" style={{ color: "#2F2B4A" }}>
                  MY아이디어로 ›
                </Link>
              </>
            )}
          </section>
        </main>
      </div>
    );
  }

  const current = idea;
  const { status, failedStage } = effectiveStatus(current);
  const atProfile = reachedProfile(status, failedStage);
  const atInterview = inInterview(status, failedStage) && !!current.interview;
  const profileDirty = JSON.stringify(draft) !== JSON.stringify(current.profile);
  const missing = missingFields(draft);
  const hasReport = current.reportCount > 0 || current.latestReport !== null;
  const loginHref = `/login?next=/ideas/${current.id}`;

  const saveMemo = () =>
    run(async () => {
      setIdea(await updateIdea(user, current, { memo: memoDraft.trim() }));
    });

  const beginInterview = () =>
    run(async () => {
      const saved =
        memoDraft.trim() !== current.memo ? await updateIdea(user, current, { memo: memoDraft.trim() }) : current;
      setIdea(await startInterview(user, saved));
    });

  // 실패하면 InterviewPanel이 입력을 남겨두도록 에러를 다시 던진다
  const sendAnswer = async (answer: string) => {
    setBusy(true);
    setError(null);
    try {
      setIdea(await answerInterview(user, current, answer));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      throw err;
    } finally {
      setBusy(false);
    }
  };

  const makeProfile = () =>
    run(async () => {
      setIdea({ ...current, status: "profiling", statusChangedAt: new Date().toISOString() });
      const next = await finishInterview(user, current);
      setIdea(next);
      setDraft(next.profile);
    });

  // 인터뷰 없이 프로필을 바로 채우는 길 (LLM이 안 될 때 대비)
  const startProfile = () =>
    run(async () => {
      const name = current.profile.name || memoDraft.trim().split("\n")[0].slice(0, 40);
      const next = await updateIdea(user, current, {
        memo: memoDraft.trim(),
        status: "profile",
        profile: { ...current.profile, name },
      });
      setIdea(next);
      setDraft(next.profile);
    });


  // 유료 분석이라 시작 전에 한 번 묻는다 (버튼·카드에서 넘어온 경우 모두)
  const diagnose = () => {
    const again = hasReport ? "보고서를 새로 작성할까요?" : "상세분석을 시작할까요?";
    if (!confirm(`${again}\n\n시장·고객·경쟁·수익·재무·위험 6개 분야를 근거와 함께 진단해요 (유료).\n보통 1~3분 걸려요.`)) return;
    return runDiagnose();
  };

  const runDiagnose = () =>
    run(async () => {
      const saved = profileDirty ? await saveProfile(user, current, draft) : current;
      setIdea({ ...saved, status: "diagnosing", statusChangedAt: new Date().toISOString() });
      const done = await runDiagnosis(user, saved);
      setIdea(done);
      if (done.status === "report") {
        const fresh = await listReports(user, done.id);
        setReports(fresh);
      }
    });

  // 보고서가 있으면 프로필을 고쳤을 때만 새로 작성할 수 있다
  const canDiagnose =
    !!user &&
    !busy &&
    status !== "diagnosing" &&
    missing.length === 0 &&
    (!hasReport || current.profileChangedSinceReport || profileDirty || status === "failed");

  handlersRef.current = { beginInterview, startProfile, diagnose, canDiagnose };

  // 줄 단위 수정 저장 — 실패하면 편집 상태를 유지하도록 에러를 다시 던진다
  const saveProfileRow = async (profile: IdeaProfile) => {
    setBusy(true);
    setError(null);
    try {
      const next = await saveProfile(user, current, profile);
      setIdea(next);
      setDraft(next.profile);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      throw err;
    } finally {
      setBusy(false);
    }
  };

  if (atProfile) {
    return (
      <div className="min-h-screen" style={{ background: "#F3F4F6" }}>
        <Header activeNav="ideas" />
        <ProfileWorkspace
          idea={current}
          status={status}
          reports={reports}
          user={user}
          busy={busy}
          error={error}
          canDiagnose={canDiagnose}
          missingCount={missing.length}
          onSaveProfile={saveProfileRow}
          onDiagnose={diagnose}
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: "#F3F4F6" }}>
      <Header activeNav="ideas" />

      <main className="max-w-[1200px] mx-auto px-6 py-12 flex flex-col gap-8">
        <Link
          href="/ideas"
          className="text-sm text-text-muted inline-flex items-center gap-1 hover:text-text-secondary no-underline self-start"
          style={{ textDecoration: "none" }}
        >
          ← MY아이디어
        </Link>

        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <StatusPill status={status} />
            {current.profile.industry && (
              <span className="text-sm font-semibold" style={{ color: "#4B5563" }}>
                {current.profile.industry} · {current.profile.location}
              </span>
            )}
          </div>
          <h1 className="text-3xl font-bold m-0">{displayTitle(current)}</h1>
          <div className="text-xs text-text-muted">
            {new Date(current.createdAt).toLocaleDateString("ko-KR")} 메모 · 마지막 수정{" "}
            {new Date(current.updatedAt).toLocaleString("ko-KR")}
          </div>
        </div>

        <StageBar status={status} failedStage={failedStage} />

        {error && (
          <div className="rounded-xl p-4 text-sm" style={{ background: "#FEF2F2", color: "#B42318" }}>
            {error}
          </div>
        )}

        {/* 메모 */}
        {atProfile || atInterview ? (
          current.memo && (
            <section className="bg-white border border-border rounded-lg shadow-card px-6 py-4 text-sm">
              <span className="font-semibold mr-2" style={{ color: "#4B5563" }}>
                처음 메모
              </span>
              <span className="text-text-secondary whitespace-pre-wrap">{current.memo}</span>
            </section>
          )
        ) : (
          <section className={card}>
            <h2 className="text-lg font-bold m-0">메모</h2>
            <textarea
              value={memoDraft}
              onChange={(e) => setMemoDraft(e.target.value)}
              rows={4}
              aria-label="메모"
              className="rounded-lg p-4 text-sm resize-y focus:outline-none leading-relaxed"
              style={{ border: "1.5px solid #E5E7EB" }}
            />
            <div className="flex gap-3 flex-wrap items-center">
              <button
                type="button"
                onClick={saveMemo}
                disabled={busy || memoDraft.trim() === current.memo}
                className="min-h-[44px] px-5 rounded-xl text-sm font-semibold bg-white disabled:opacity-50"
                style={{ border: "1.5px solid #E5E7EB", color: "#4B5563", cursor: "pointer" }}
              >
                메모 저장
              </button>
            </div>

            <div className="border-t pt-5 flex flex-col gap-3" style={{ borderColor: "#E5E7EB" }}>
              <div className="font-semibold">다음 단계 · 인터뷰</div>
              <p className="text-sm text-text-secondary m-0 leading-relaxed">
                AI 인터뷰어와 대화하며 아이디어를 구체화하고, 그 내용으로 아이템 프로필을 만들어요.
              </p>
              {user ? (
                <div className="flex items-center gap-4 flex-wrap">
                  <button
                    type="button"
                    onClick={beginInterview}
                    disabled={busy || !memoDraft.trim()}
                    className="min-h-[48px] px-6 rounded-xl font-bold text-sm text-white disabled:opacity-60"
                    style={{ background: "#7270FF", border: "none", cursor: "pointer" }}
                  >
                    {busy ? "첫 질문 준비 중…" : "인터뷰 시작"}
                  </button>
                  <button
                    type="button"
                    onClick={startProfile}
                    disabled={busy || !memoDraft.trim()}
                    className="text-sm underline disabled:opacity-50"
                    style={{ background: "none", border: "none", color: "#4B5563", cursor: "pointer" }}
                  >
                    인터뷰 없이 직접 작성
                  </button>
                </div>
              ) : (
                <Link
                  href={loginHref}
                  className="self-start min-h-[48px] px-6 rounded-xl font-bold text-sm text-white no-underline inline-flex items-center"
                  style={{ background: "#7270FF", textDecoration: "none" }}
                >
                  로그인하고 인터뷰 시작
                </Link>
              )}
            </div>
          </section>
        )}

        {/* 딥 인터뷰 → 1차 분석 */}
        {atInterview && current.interview && (
          <>
            {status === "failed" && (
              <div
                className="rounded-xl p-4 text-sm flex items-center justify-between gap-3 flex-wrap"
                style={{ background: "#FEF2F2", color: "#B42318" }}
              >
                <span>프로필을 만들지 못했어요. {current.errorMessage ?? "중간에 끊겼어요."}</span>
                <button
                  type="button"
                  onClick={makeProfile}
                  disabled={busy}
                  className="min-h-[40px] px-4 rounded-xl text-sm font-semibold bg-white"
                  style={{ border: "1px solid #B42318", color: "#B42318", cursor: "pointer" }}
                >
                  다시 만들기
                </button>
              </div>
            )}
            <InterviewPanel
              interview={current.interview}
              onAnswer={sendAnswer}
              onFinish={makeProfile}
              busy={busy}
              locked={status !== "interviewing"}
            />
          </>
        )}

      </main>
    </div>
  );
}

const STAGES: { key: IdeaStatus; label: string }[] = [
  { key: "memo", label: "메모" },
  { key: "interviewing", label: "인터뷰" },
  { key: "profile", label: "아이템 프로필" },
  { key: "report", label: "분석 보고서" },
];

// 진행 중·실패 상태를 단계 표시 위치로 바꾼다
const STAGE_INDEX: Record<IdeaStatus, number> = {
  memo: 0,
  interviewing: 1,
  profiling: 1,
  profile: 2,
  diagnosing: 2,
  report: 3,
  failed: 0,
};

function StageBar({ status, failedStage }: { status: IdeaStatus; failedStage: IdeaStatus | null }) {
  const index = status === "failed" ? STAGE_INDEX[failedStage ?? "memo"] : STAGE_INDEX[status];
  return (
    <ol className="m-0 p-0 list-none grid grid-cols-2 md:grid-cols-4 gap-2">
      {STAGES.map((s, i) => {
        const done = i < index;
        const active = i === index;
        return (
          <li
            key={s.key}
            aria-current={active ? "step" : undefined}
            className="rounded-xl px-4 py-3 text-sm font-semibold"
            style={{
              background: active ? "#F3F4F6" : "#fff",
              color: active ? "#1C1A2C" : done ? "#2F2B4A" : "#6B7280",
              border: `1px solid ${active ? "#2F2B4A" : "#E5E7EB"}`,
            }}
          >
            {done ? "✓ " : `${i + 1}. `}
            {s.label}
            {active && status !== s.key && (
              <span className="block text-xs font-medium mt-0.5" style={{ color: STATUS_META[status].color }}>
                {STATUS_META[status].label}
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
