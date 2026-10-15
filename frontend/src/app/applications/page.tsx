"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Header from "@/components/Header";
import PageHero from "@/components/PageHero";
import NewApplicationDialog from "@/components/NewApplicationDialog";
import { useAuth } from "@/contexts/AuthContext";
import {
  APPLICATION_FILTERS,
  APPLICATION_STATUS,
  type Application,
  type ApplicationFilter,
  type ApplicationStatus,
  matchesFilter,
} from "@/lib/application";
import {
  canApply,
  createApplication,
  deleteApplication,
  listApplications,
  updateApplicationStatus,
} from "@/lib/applicationStore";
import type { Idea } from "@/lib/idea";
import { listIdeas } from "@/lib/ideaStore";
import { type Program, fetchPrograms } from "@/lib/programs";

const line = "#E5E7EB";

/** 마감일까지 남은 날 */
function dday(endsOn: string) {
  const end = Date.parse(`${endsOn}T23:59:59`);
  if (Number.isNaN(end)) return "";
  const days = Math.ceil((end - Date.now()) / 86_400_000);
  return days < 0 ? "마감" : days === 0 ? "D-day" : `D-${days}`;
}

export default function ApplicationsPage() {
  const { user, loading: authLoading } = useAuth();
  const [apps, setApps] = useState<Application[]>([]);
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<ApplicationFilter>("all");
  const [dialog, setDialog] = useState<{ ideaId?: string | null; programId?: string | null } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    setLoading(true);
    Promise.all([listApplications(user), listIdeas(user), fetchPrograms().catch(() => [] as Program[])])
      .then(([a, i, p]) => {
        setApps(a);
        setIdeas(i);
        setPrograms(p);
        // 아이디어 카드·공고 화면에서 넘어오면 (?new=1&idea=…|program=…) 바로 만들기 창을 연다
        const q = new URLSearchParams(window.location.search);
        if (q.get("new")) {
          setDialog({ ideaId: q.get("idea"), programId: q.get("program") });
          window.history.replaceState(null, "", "/applications");
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, [user, authLoading]);

  const eligible = ideas.filter(canApply);
  const visible = apps.filter((a) => matchesFilter(a, filter));

  async function create(idea: Idea, program: Program) {
    const app = await createApplication(user, apps, idea, program);
    setApps((prev) => [app, ...prev]);
    setDialog(null);
    setFilter("all");
  }

  async function changeStatus(app: Application, status: ApplicationStatus) {
    const next = await updateApplicationStatus(user, app, status);
    setApps((prev) => prev.map((a) => (a.id === app.id ? next : a)));
  }

  async function remove(app: Application) {
    if (!confirm(`'${app.programTitle}' 지원서를 삭제할까요?`)) return;
    setApps((prev) => prev.filter((a) => a.id !== app.id));
    await deleteApplication(user, app.id).catch(() => {});
  }

  return (
    <div className="min-h-screen" style={{ background: "#F3F4F6" }}>
      <Header activeNav="applications" />

      <PageHero
        eyebrow="MY지원서"
        title="내 지원서"
        description="아이템 하나로 여러 지원사업에 지원할 수 있어요."
        actions={
          <button
            type="button"
            onClick={() => (user ? setDialog({}) : (window.location.href = "/login?next=/applications"))}
            className="min-h-[44px] px-5 rounded-xl text-sm font-bold bg-white"
            style={{ color: "#134CD8", border: "none", cursor: "pointer" }}
          >
            + 새 지원서
          </button>
        }
      />

      <div className="max-w-[1200px] mx-auto px-6 py-8">

        {notice && (
          <div role="status" className="mb-5 rounded-lg p-4 text-sm flex justify-between gap-3" style={{ background: "#fff", border: `1px solid ${line}`, color: "#4B5563" }}>
            <span>{notice}</span>
            <button type="button" onClick={() => setNotice(null)} aria-label="닫기" style={{ background: "none", border: "none", cursor: "pointer", color: "#6B7280" }}>
              ✕
            </button>
          </div>
        )}

        {loading ? (
          <div className="text-center py-16 text-text-muted text-sm">불러오는 중…</div>
        ) : error ? (
          <div className="rounded-xl p-4 text-sm" style={{ background: "#FEF2F2", color: "#B42318" }}>
            지원서를 불러오지 못했어요: {error}
          </div>
        ) : apps.length === 0 ? (
          <div className="bg-white rounded-lg p-16 flex flex-col items-center gap-3 text-center" style={{ border: `1px solid ${line}` }}>
            <div className="font-bold text-lg">아직 지원서가 없어요</div>
            <div className="text-text-secondary text-sm">
              보고서가 나온 아이템으로 지원사업을 골라 지원서를 만들어 보세요.
            </div>
            <div className="flex gap-2 mt-2">
              <Link href="/programs" className="min-h-[40px] px-4 rounded-xl text-sm font-semibold no-underline inline-flex items-center bg-white" style={{ border: `1px solid ${line}`, color: "#111111", textDecoration: "none" }}>
                공고 찾기
              </Link>
              <Link href="/ideas" className="min-h-[40px] px-4 rounded-xl text-sm font-semibold no-underline inline-flex items-center bg-white" style={{ border: `1px solid ${line}`, color: "#111111", textDecoration: "none" }}>
                MY아이디어
              </Link>
            </div>
          </div>
        ) : (
          <>
            <div className="flex gap-2 flex-wrap mb-5" role="tablist" aria-label="지원서 상태 필터">
              {APPLICATION_FILTERS.map((f) => {
                const count = apps.filter((a) => matchesFilter(a, f.key)).length;
                const active = filter === f.key;
                return (
                  <button
                    key={f.key}
                    type="button"
                    role="tab"
                    aria-selected={active}
                    onClick={() => setFilter(f.key)}
                    className="min-h-[36px] px-4 rounded-xl text-sm font-semibold"
                    style={{
                      cursor: "pointer",
                      border: `1px solid ${active ? "#134CD8" : line}`,
                      background: active ? "#EAF0FD" : "#fff",
                      color: active ? "#0F3DB0" : "#4B5563",
                    }}
                  >
                    {f.label}
                    <span className="ml-1.5 text-xs font-medium" style={{ color: active ? "#134CD8" : "#6B7280" }}>
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>

            {visible.length === 0 ? (
              <div className="bg-white rounded-lg p-12 text-center text-sm" style={{ border: `1px solid ${line}`, color: "#6B7280" }}>
                이 상태의 지원서가 없어요.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {visible.map((a) => {
                  const st = APPLICATION_STATUS[a.status];
                  const left = dday(a.programDeadline);
                  return (
                    <article key={a.id} className="relative bg-white rounded-lg h-[232px] flex flex-col" style={{ border: `1px solid ${line}` }}>
                      {/* 카드 전체 — 상세 화면은 다음 작업 */}
                      <button
                        type="button"
                        onClick={() => setNotice("지원서 상세 화면은 준비 중이에요.")}
                        aria-label={`${a.programTitle} 지원서 열기`}
                        className="absolute inset-0 w-full h-full rounded-lg"
                        style={{ background: "transparent", border: "none", cursor: "pointer" }}
                      />
                      <div className="relative p-6 flex flex-col gap-3 h-full pointer-events-none">
                        <div className="flex items-start justify-between gap-2">
                          <span className="inline-flex text-xs font-semibold px-2 py-0.5 rounded whitespace-nowrap" style={{ background: st.bg, color: st.color }}>
                            {st.label}
                          </span>
                          <button
                            type="button"
                            onClick={() => remove(a)}
                            aria-label={`${a.programTitle} 지원서 삭제`}
                            title="삭제"
                            className="pointer-events-auto text-text-muted text-sm hover:text-danger -mr-1 -mt-1 w-8 h-8"
                            style={{ background: "none", border: "none", cursor: "pointer" }}
                          >
                            ✕
                          </button>
                        </div>

                        <div className="min-w-0">
                          <div className="font-bold text-base line-clamp-2" style={{ color: "#111111" }}>
                            {a.programTitle}
                          </div>
                          <div className="text-xs mt-1" style={{ color: "#6B7280" }}>
                            {a.programOrg} · {a.programAmount}
                          </div>
                        </div>

                        <div className="text-sm flex items-center gap-1.5 min-w-0" style={{ color: "#4B5563" }}>
                          <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded shrink-0" style={{ background: "#F3F4F6", color: "#4B5563" }}>
                            아이템
                          </span>
                          <span className="truncate">{a.ideaName}</span>
                        </div>

                        <div className="mt-auto pt-3 flex items-center justify-between gap-2" style={{ borderTop: `1px solid ${line}` }}>
                          <span className="text-xs" style={{ color: left === "마감" ? "#B42318" : "#4B5563" }}>
                            마감 {a.programDeadline} {left && `· ${left}`}
                          </span>
                          <label className="pointer-events-auto text-xs" style={{ color: "#6B7280" }}>
                            <span className="sr-only">상태 바꾸기</span>
                            <select
                              value={a.status}
                              onChange={(e) => changeStatus(a, e.target.value as ApplicationStatus)}
                              className="h-8 rounded-lg px-2 text-xs bg-white focus:outline-none"
                              style={{ border: `1px solid ${line}`, color: "#111111" }}
                            >
                              {(Object.keys(APPLICATION_STATUS) as ApplicationStatus[]).map((k) => (
                                <option key={k} value={k}>
                                  {APPLICATION_STATUS[k].label}
                                </option>
                              ))}
                            </select>
                          </label>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </>
        )}
      </div>

      {dialog && (
        <NewApplicationDialog
          ideas={eligible}
          programs={programs}
          presetIdeaId={dialog.ideaId}
          presetProgramId={dialog.programId}
          onCreate={create}
          onClose={() => setDialog(null)}
        />
      )}
    </div>
  );
}
