"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import Header from "@/components/Header";
import AgentResultCard from "@/components/AgentResultCard";
import DecisionBanner from "@/components/DecisionBanner";
import ProfileEditor from "@/components/ProfileEditor";
import StatusPill from "@/components/StatusPill";
import { useAuth } from "@/contexts/AuthContext";
import { AGENT_ORDER, STATUS_BG, STATUS_TEXT } from "@/lib/agents";
import {
  DECISION_META,
  type Idea,
  type IdeaProfile,
  type IdeaReport,
  type IdeaStatus,
  STATUS_META,
  displayTitle,
  effectiveStatus,
  missingFields,
} from "@/lib/idea";
import { getIdea, listReports, runDiagnosis, saveProfile, updateIdea } from "@/lib/ideaStore";

const card = "bg-white border border-border rounded-2xl p-8 flex flex-col gap-5";

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
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
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
        setSelectedReportId(foundReports[0]?.id ?? null);
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, [id, user, authLoading]);

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
      <div className="min-h-screen" style={{ background: "#F4F5F7" }}>
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
                <Link href="/ideas" className="text-sm font-semibold" style={{ color: "#2F5BD3" }}>
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
  const profileDirty = JSON.stringify(draft) !== JSON.stringify(current.profile);
  const missing = missingFields(draft);
  const hasReport = current.reportCount > 0 || current.latestReport !== null;
  const selectedReport = reports.find((r) => r.id === selectedReportId) ?? null;
  const loginHref = `/login?next=/ideas/${current.id}`;

  const saveMemo = () =>
    run(async () => {
      setIdea(await updateIdea(user, current, { memo: memoDraft.trim() }));
    });

  // 2단계(인터뷰·1차 분석) 전까지는 메모에서 바로 프로필 작성으로 넘어간다
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

  const saveDraft = () =>
    run(async () => {
      setIdea(await saveProfile(user, current, draft));
    });

  const diagnose = () =>
    run(async () => {
      const saved = profileDirty ? await saveProfile(user, current, draft) : current;
      setIdea({ ...saved, status: "diagnosing", statusChangedAt: new Date().toISOString() });
      const done = await runDiagnosis(user, saved);
      setIdea(done);
      if (done.status === "report") {
        const fresh = await listReports(user, done.id);
        setReports(fresh);
        setSelectedReportId(fresh[0]?.id ?? null);
      }
    });

  // 보고서가 있으면 프로필을 고쳤을 때만 새로 작성할 수 있다
  const canDiagnose =
    !!user &&
    !busy &&
    status !== "diagnosing" &&
    missing.length === 0 &&
    (!hasReport || current.profileChangedSinceReport || profileDirty || status === "failed");

  return (
    <div className="min-h-screen" style={{ background: "#F4F5F7" }}>
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
              <span className="text-sm font-semibold" style={{ color: "#2F5BD3" }}>
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
          <div className="rounded-xl p-4 text-sm" style={{ background: "#FDECEA", color: "#B42318" }}>
            {error}
          </div>
        )}

        {/* 메모 */}
        {atProfile ? (
          current.memo && (
            <section className="bg-white border border-border rounded-2xl px-6 py-4 text-sm">
              <span className="font-semibold mr-2" style={{ color: "#5A606B" }}>
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
              className="rounded-xl p-4 text-sm resize-y focus:outline-none leading-relaxed"
              style={{ border: "1.5px solid #D9DCE1" }}
            />
            <div className="flex gap-3 flex-wrap items-center">
              <button
                type="button"
                onClick={saveMemo}
                disabled={busy || memoDraft.trim() === current.memo}
                className="min-h-[44px] px-5 rounded-xl text-sm font-semibold bg-white disabled:opacity-50"
                style={{ border: "1.5px solid #D9DCE1", color: "#4A505B", cursor: "pointer" }}
              >
                메모 저장
              </button>
            </div>

            <div className="border-t pt-5 flex flex-col gap-3" style={{ borderColor: "#E8EAEE" }}>
              <div className="font-semibold">다음 단계 · 인터뷰</div>
              <p className="text-sm text-text-secondary m-0 leading-relaxed">
                AI 인터뷰어와 대화하며 아이디어를 구체화하고, 그 내용으로 아이템 프로필을 만들어요.
              </p>
              {user ? (
                <>
                  <p className="text-xs m-0" style={{ color: "#6B3FA0" }}>
                    인터뷰는 준비 중이에요. 지금은 프로필을 직접 채워서 진행할 수 있어요.
                  </p>
                  <button
                    type="button"
                    onClick={startProfile}
                    disabled={busy || !memoDraft.trim()}
                    className="self-start min-h-[48px] px-6 rounded-xl font-bold text-sm text-white disabled:opacity-60"
                    style={{ background: "#2F5BD3", border: "none", cursor: "pointer" }}
                  >
                    프로필 직접 작성하기
                  </button>
                </>
              ) : (
                <Link
                  href={loginHref}
                  className="self-start min-h-[48px] px-6 rounded-xl font-bold text-sm text-white no-underline inline-flex items-center"
                  style={{ background: "#2F5BD3", textDecoration: "none" }}
                >
                  로그인하고 인터뷰 시작
                </Link>
              )}
            </div>
          </section>
        )}

        {/* 아이템 프로필 + 상세 진단 */}
        {atProfile && (
          <section className={card}>
            <div className="flex items-baseline justify-between gap-3 flex-wrap">
              <h2 className="text-lg font-bold m-0">아이템 프로필</h2>
              {current.profileChangedSinceReport && (
                <span className="text-xs font-semibold" style={{ color: "#B45309" }}>
                  최신 보고서 이후 수정됐어요
                </span>
              )}
            </div>

            <ProfileEditor value={draft} onChange={setDraft} readOnly={!user || status === "diagnosing"} />

            {status === "failed" && (
              <div className="rounded-xl p-4 text-sm" style={{ background: "#FDECEA", color: "#B42318" }}>
                상세 진단에 실패했어요. {current.errorMessage ?? "분석이 중간에 끊겼어요."} 다시 시도해 주세요.
              </div>
            )}

            {status === "diagnosing" ? (
              <DiagnosingNotice />
            ) : (
              <div className="border-t pt-5 flex gap-3 flex-wrap items-center" style={{ borderColor: "#E8EAEE" }}>
                {user ? (
                  <>
                    <button
                      type="button"
                      onClick={saveDraft}
                      disabled={busy || !profileDirty}
                      className="min-h-[48px] px-5 rounded-xl text-sm font-semibold bg-white disabled:opacity-50"
                      style={{ border: "1.5px solid #D9DCE1", color: "#4A505B", cursor: "pointer" }}
                    >
                      프로필 저장
                    </button>
                    <button
                      type="button"
                      onClick={diagnose}
                      disabled={!canDiagnose}
                      className="min-h-[48px] px-6 rounded-xl font-bold text-sm text-white disabled:opacity-50"
                      style={{ background: "#2F5BD3", border: "none", cursor: "pointer" }}
                    >
                      {hasReport ? "보고서 새로 작성하기 (유료)" : "분석하기 (유료)"}
                    </button>
                    <span className="text-xs text-text-muted">
                      {missing.length > 0
                        ? "* 표시된 칸을 채우면 분석할 수 있어요"
                        : hasReport && !canDiagnose
                          ? "프로필을 고치면 보고서를 새로 작성할 수 있어요"
                          : "시장·고객·경쟁·수익·재무·위험 6개 분야를 근거와 함께 진단해요"}
                    </span>
                  </>
                ) : (
                  <Link href={loginHref} className="text-sm font-semibold" style={{ color: "#2F5BD3" }}>
                    로그인하면 프로필을 고치고 분석할 수 있어요 ›
                  </Link>
                )}
              </div>
            )}
          </section>
        )}

        {/* 분석 보고서 (버전별) */}
        {hasReport && (
          <section className="flex flex-col gap-5">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <h2 className="text-xl font-bold m-0">분석 보고서</h2>
              {reports.length > 1 && (
                <div className="flex gap-2 flex-wrap" role="tablist" aria-label="보고서 버전">
                  {reports.map((r) => (
                    <button
                      key={r.id}
                      type="button"
                      role="tab"
                      aria-selected={r.id === selectedReportId}
                      onClick={() => setSelectedReportId(r.id)}
                      className="min-h-[36px] px-3 rounded-lg text-xs font-semibold"
                      style={{
                        cursor: "pointer",
                        border: "1px solid #D9DCE1",
                        background: r.id === selectedReportId ? "#2F5BD3" : "#fff",
                        color: r.id === selectedReportId ? "#fff" : "#4A505B",
                      }}
                    >
                      v{r.version} · {new Date(r.createdAt).toLocaleDateString("ko-KR")}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {selectedReport ? (
              <ReportView report={selectedReport} />
            ) : (
              current.latestReport && (
                // 구조 개편 전 요약만 저장된 기록
                <section className="bg-white border border-border rounded-2xl p-8 flex flex-col gap-3">
                  <div className="font-bold">
                    {current.latestReport.decision
                      ? DECISION_META[current.latestReport.decision].label
                      : "판정 없음"}
                    {current.latestReport.confidence !== undefined &&
                      ` · 신뢰도 ${Math.round(current.latestReport.confidence * 100)}%`}
                  </div>
                  <p className="text-sm text-text-secondary leading-relaxed m-0">{current.latestReport.summary}</p>
                  <div className="text-xs text-text-muted">
                    예전에 요약만 저장된 기록이라 분야별 결과는 볼 수 없어요.
                  </div>
                </section>
              )
            )}
          </section>
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
              background: active ? "#EEF2FD" : "#fff",
              color: active ? "#2F5BD3" : done ? "#0F7B6C" : "#8A909B",
              border: `1px solid ${active ? "#2F5BD3" : "#E8EAEE"}`,
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

function DiagnosingNotice() {
  return (
    <div className="border-t pt-5 flex flex-col gap-3" style={{ borderColor: "#E8EAEE" }}>
      <div className="font-semibold">6개 분야를 진단하고 있어요</div>
      <p className="text-sm text-text-secondary m-0">보통 1~3분 걸려요. 지금은 이 화면을 닫지 말아주세요.</p>
      <div className="grid grid-cols-3 md:grid-cols-6 gap-2 text-xs text-center">
        {AGENT_ORDER.map((a) => (
          <div key={a} className="rounded-lg p-2 animate-pulse" style={{ background: "#EEF2FD", color: "#2F5BD3" }}>
            {a.replace("Agent", "")}
          </div>
        ))}
      </div>
    </div>
  );
}

function ReportView({ report }: { report: IdeaReport }) {
  const wf = report.response.workflow_result;
  const orderedAgents = AGENT_ORDER.filter((k) => k in wf.agent_results);
  return (
    <>
      <div
        className="rounded-2xl p-5 flex items-center justify-between gap-4 flex-wrap"
        style={{ background: STATUS_BG[wf.status] ?? "#F4F5F7" }}
      >
        <div>
          <span className="font-semibold">
            v{report.version} · {STATUS_TEXT[wf.status] ?? wf.status}
          </span>
          {report.elapsedMs && (
            <span className="text-sm ml-3" style={{ color: "#8A909B" }}>
              소요 {(report.elapsedMs / 1000).toFixed(1)}초
            </span>
          )}
        </div>
        <div className="text-xs" style={{ color: "#8A909B" }}>
          {new Date(report.createdAt).toLocaleString("ko-KR")} 작성
        </div>
      </div>

      {wf.decision_result ? (
        <DecisionBanner result={wf.decision_result} />
      ) : (
        <div className="rounded-xl p-4 text-sm" style={{ background: "#FFF7EB", color: "#B45309" }}>
          종합 판정을 내리지 못했어요. 분야별 결과만 확인할 수 있어요.
        </div>
      )}

      <div>
        <h3 className="text-lg font-bold mb-4 mt-0">분야별 진단</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {orderedAgents.map((agentName) => (
            <AgentResultCard key={agentName} agentName={agentName} result={wf.agent_results[agentName]} />
          ))}
        </div>
      </div>
    </>
  );
}
