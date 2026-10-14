"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { User } from "firebase/auth";
import ReportView from "@/components/ReportView";
import StatusPill from "@/components/StatusPill";
import { AGENT_LABELS, AGENT_ORDER } from "@/lib/agents";
import {
  DECISION_META,
  type Idea,
  type IdeaProfile,
  type IdeaReport,
  type IdeaStatus,
  REGIONS,
  displayTitle,
  effectiveStatus,
} from "@/lib/idea";
import { listIdeas } from "@/lib/ideaStore";
import { type ProfileRow, fieldRows, isUnknown, reportRows, updateRow } from "@/lib/profileRows";

type Tab = "overview" | "report" | "interview";

interface Section {
  no: number;
  title: string;
  question: string;
  badge: string;
  rows: ProfileRow[];
  /** 상세분석에서 채워지는 섹션 */
  fromReport?: boolean;
}

interface Props {
  idea: Idea;
  status: IdeaStatus;
  reports: IdeaReport[];
  user: User | null;
  busy: boolean;
  error: string | null;
  canDiagnose: boolean;
  missingCount: number;
  onSaveProfile: (profile: IdeaProfile) => Promise<void>;
  onDiagnose: () => void;
}

const ink = "#333333";
const slate = "#535768";
const iron = "#808080";
const line = "#E6E7EA";

export default function ProfileWorkspace(props: Props) {
  const { idea, status, reports, user, busy, error, canDiagnose, missingCount, onSaveProfile, onDiagnose } = props;
  const [tab, setTab] = useState<Tab>("overview");
  const [selectedReportId, setSelectedReportId] = useState<string | null>(reports[0]?.id ?? null);
  const [editing, setEditing] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [ideas, setIdeas] = useState<Idea[]>([]);

  // 카드의 '보고서 보기'(#report)로 들어오면 보고서 탭부터
  useEffect(() => {
    if (window.location.hash === "#report") setTab("report");
  }, []);
  useEffect(() => {
    setSelectedReportId(reports[0]?.id ?? null);
  }, [reports]);
  useEffect(() => {
    listIdeas(user).then(setIdeas).catch(() => setIdeas([]));
  }, [user, idea.updatedAt]);

  const latest = reports[0] ?? null;
  const selectedReport = reports.find((r) => r.id === selectedReportId) ?? latest;
  const hasReport = idea.reportCount > 0 || idea.latestReport !== null;
  const fromInterview = !!idea.interview?.messages.length;
  const p = idea.profile;
  const fromReport = reportRows(latest);
  const canEdit = !!user && status !== "diagnosing";

  const sections: Section[] = [
    {
      no: 1,
      title: "기본",
      question: "공고 분야·단계 매칭",
      badge: "",
      rows: [
        ...fieldRows(p, "name", "이름", true),
        ...fieldRows(p, "oneLiner", "한 줄 정의", false),
        ...fieldRows(p, "industry", "분야", true),
        ...fieldRows(p, "location", "시작 지역", false),
      ],
    },
    {
      no: 2,
      title: "문제 · 고객",
      question: "누가, 얼마나 아픈가",
      badge: "P 문제인식",
      rows: [...fieldRows(p, "customer", "고객 정의", true), ...fieldRows(p, "problem", "고객 문제 정의", true)],
    },
    {
      no: 3,
      title: "해결 · 솔루션",
      question: "무엇으로, 왜 우리인가",
      badge: "S 실현가능성",
      rows: fieldRows(p, "solution", "문제 해결 방법", true),
    },
    {
      no: 4,
      title: "수익 모델",
      question: "누가, 얼마를, 어떻게 내나",
      badge: "S 비즈니스 모델",
      rows: fieldRows(p, "revenueModel", "수익 모델", false),
    },
    { no: 5, title: "시장", question: "돈 낼 곳이 얼마나 있나", badge: "P 목표시장", rows: fromReport.market, fromReport: true },
    { no: 6, title: "경쟁", question: "왜 우리여야 하나", badge: "S 차별성", rows: fromReport.competition, fromReport: true },
  ];

  const filled = (rows: ProfileRow[]) => rows.filter((r) => !isUnknown(r.value)).length;
  const toFill = sections
    .filter((s) => !s.fromReport)
    .flatMap((s) => s.rows)
    .filter((r) => isUnknown(r.value))
    .map((r) => r.label);

  async function save(row: ProfileRow) {
    await onSaveProfile(updateRow(p, row, editValue));
    setEditing(null);
  }

  function startEdit(row: ProfileRow) {
    setEditing(row.id);
    setEditValue(row.value.replace(/\(미확인\)/g, "").trim());
  }

  const diagnoseLabel = hasReport ? "보고서 새로 작성 (유료)" : "상세분석하기 (유료)";

  return (
    <div className="max-w-[1440px] mx-auto px-6 py-8 grid gap-6 grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px] xl:grid-cols-[220px_minmax(0,1fr)_320px] items-start">
      {/* ── 왼쪽: 내 아이디어 ── */}
      <aside className="hidden xl:flex flex-col gap-2 bg-white rounded-3xl shadow-card p-4" style={{ border: `1px solid ${line}` }}>
        <div className="text-xs px-2 pb-1" style={{ color: iron }}>
          내 아이디어
        </div>
        {ideas.map((i) => {
          const active = i.id === idea.id;
          return (
            <Link
              key={i.id}
              href={`/ideas/${i.id}`}
              className="rounded-2xl px-3 py-3 no-underline flex flex-col gap-1.5"
              style={{ background: active ? "#E7ECFF" : "transparent", textDecoration: "none", color: ink }}
            >
              <span className="text-sm font-semibold leading-snug line-clamp-2">{displayTitle(i)}</span>
              <span className="self-start">
                <StatusPill status={effectiveStatus(i).status} />
              </span>
            </Link>
          );
        })}
        <Link
          href="/ideas"
          className="mt-2 rounded-2xl py-3 text-center text-sm font-semibold no-underline"
          style={{ border: "1.5px dashed #6161FF", color: "#6161FF", textDecoration: "none" }}
        >
          + 새 아이디어
        </Link>
      </aside>

      {/* ── 가운데: 프로필 ── */}
      <main className="min-w-0 flex flex-col gap-5">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="min-w-0">
            <div className="text-xs mb-1" style={{ color: iron }}>
              아이템 프로필 · {fromInterview ? "인터뷰로 자동 생성" : "직접 작성"} · 모든 문서의 원본
            </div>
            <h1 className="text-3xl font-bold m-0 tracking-tight" style={{ color: ink }}>
              {displayTitle(idea)}
            </h1>
          </div>
          <div className="flex gap-2 flex-wrap">
            {user && status !== "diagnosing" && (
              <button
                type="button"
                onClick={onDiagnose}
                disabled={!canDiagnose}
                title={!canDiagnose && missingCount > 0 ? "필수 항목을 채우면 분석할 수 있어요" : undefined}
                className="min-h-[44px] px-5 rounded-full text-sm font-semibold bg-white disabled:opacity-50"
                style={{ border: `1px solid ${slate}`, color: ink, cursor: "pointer" }}
              >
                {diagnoseLabel}
              </button>
            )}
            <Link
              href="/programs"
              className="min-h-[44px] px-5 rounded-full text-sm font-bold text-white no-underline inline-flex items-center"
              style={{ background: "#6161FF", textDecoration: "none" }}
            >
              이 아이템으로 공고 찾기
            </Link>
          </div>
        </div>

        {/* 탭 */}
        <div className="flex gap-1 border-b" style={{ borderColor: line }} role="tablist">
          {(
            [
              ["overview", "개요", null],
              ["report", "진단 보고서", reports.length || (idea.latestReport ? 1 : 0)],
              ["interview", "인터뷰 기록", idea.interview?.messages.filter((m) => m.role === "user").length ?? 0],
            ] as [Tab, string, number | null][]
          ).map(([key, label, count]) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={tab === key}
              onClick={() => setTab(key)}
              className="px-4 py-3 text-sm font-semibold -mb-px"
              style={{
                background: "none",
                border: "none",
                borderBottom: `2px solid ${tab === key ? "#6161FF" : "transparent"}`,
                color: tab === key ? "#6161FF" : slate,
                cursor: "pointer",
              }}
            >
              {label}
              {count !== null && <span className="ml-1.5 text-xs" style={{ color: iron }}>{count}</span>}
            </button>
          ))}
        </div>

        {error && (
          <div className="rounded-xl p-4 text-sm" style={{ background: "#FDECEA", color: "#B42318" }}>
            {error}
          </div>
        )}

        {tab === "overview" && (
          <section id="profile" className="bg-white rounded-3xl shadow-card px-6 py-4 scroll-mt-20" style={{ border: `1px solid ${line}` }}>
            {sections.map((s) => (
              <div key={s.no} className="py-4">
                <div className="flex items-baseline justify-between gap-3 flex-wrap pb-3" style={{ borderBottom: `2px solid ${ink}` }}>
                  <div className="flex items-baseline gap-2 flex-wrap">
                    <h2 className="text-base font-bold m-0" style={{ color: ink }}>
                      {s.no} · {s.title}
                    </h2>
                    <span className="text-xs" style={{ color: iron }}>
                      {s.question}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {s.badge && (
                      <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded-md" style={{ background: "#E7ECFF", color: "#4B4BD9" }}>
                        {s.badge}
                      </span>
                    )}
                    <span className="text-xs" style={{ color: iron }}>
                      {filled(s.rows)}/{s.rows.length}
                    </span>
                  </div>
                </div>

                {s.rows.map((r) => {
                  const empty = isUnknown(r.value);
                  const isEditing = editing === r.id;
                  return (
                    <div
                      key={r.id}
                      className="grid gap-x-4 gap-y-2 py-4 grid-cols-1 md:grid-cols-[150px_minmax(0,1fr)_110px_64px] items-start"
                      style={{ borderBottom: `1px solid ${line}` }}
                    >
                      <div className="text-sm font-semibold" style={{ color: ink }}>
                        {r.label}
                        {r.required && <span style={{ color: "#B42318" }}> *</span>}
                      </div>

                      <div className="text-sm leading-relaxed min-w-0" style={{ color: empty ? iron : ink }}>
                        {isEditing ? (
                          <div className="flex flex-col gap-2">
                            {r.field === "location" ? (
                              <select
                                value={editValue}
                                onChange={(e) => setEditValue(e.target.value)}
                                aria-label={r.label}
                                className="h-10 rounded-md px-3 text-sm bg-white focus:outline-none"
                                style={{ border: "1.5px solid #DDDFEB" }}
                              >
                                {REGIONS.map((x) => (
                                  <option key={x}>{x}</option>
                                ))}
                              </select>
                            ) : (
                              <textarea
                                autoFocus
                                value={editValue}
                                onChange={(e) => setEditValue(e.target.value)}
                                aria-label={r.label}
                                placeholder={r.hint}
                                rows={Math.min(6, Math.max(2, Math.ceil(editValue.length / 40)))}
                                className="rounded-md p-3 text-sm resize-y focus:outline-none leading-relaxed"
                                style={{ border: "1.5px solid #6161FF" }}
                              />
                            )}
                            <div className="flex gap-2">
                              <button
                                type="button"
                                onClick={() => save(r)}
                                disabled={busy}
                                className="min-h-[36px] px-4 rounded-full text-xs font-bold text-white disabled:opacity-50"
                                style={{ background: "#6161FF", border: "none", cursor: "pointer" }}
                              >
                                저장
                              </button>
                              <button
                                type="button"
                                onClick={() => setEditing(null)}
                                className="min-h-[36px] px-4 rounded-full text-xs font-semibold bg-white"
                                style={{ border: "1px solid #DDDFEB", color: slate, cursor: "pointer" }}
                              >
                                취소
                              </button>
                            </div>
                          </div>
                        ) : empty && !r.value.includes("(미확인)") ? (
                          <span>{r.fromReport === undefined && s.fromReport ? "상세분석 후 채워져요" : r.hint || "미입력"}</span>
                        ) : (
                          <RowValue value={r.value} />
                        )}
                      </div>

                      <div>
                        <SourceBadge row={r} sectionFromReport={!!s.fromReport} fromInterview={fromInterview} empty={empty} />
                      </div>

                      <div className="md:text-right">
                        {r.field && canEdit && !isEditing && (
                          <button
                            type="button"
                            onClick={() => startEdit(r)}
                            className="min-h-[36px] px-3 rounded-full text-xs font-semibold bg-white"
                            style={{ border: "1px solid #DDDFEB", color: ink, cursor: "pointer" }}
                          >
                            {empty ? "입력" : "수정"}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ))}
          </section>
        )}

        {tab === "report" && (
          <section id="report" className="flex flex-col gap-4 scroll-mt-20">
            {reports.length > 1 && (
              <div className="flex gap-2 flex-wrap" aria-label="보고서 버전">
                {reports.map((r) => (
                  <button
                    key={r.id}
                    type="button"
                    onClick={() => setSelectedReportId(r.id)}
                    className="min-h-[36px] px-3 rounded-full text-xs font-semibold"
                    style={{
                      cursor: "pointer",
                      border: "1px solid #DDDFEB",
                      background: r.id === selectedReport?.id ? "#6161FF" : "#fff",
                      color: r.id === selectedReport?.id ? "#fff" : slate,
                    }}
                  >
                    v{r.version} · {new Date(r.createdAt).toLocaleDateString("ko-KR")}
                  </button>
                ))}
              </div>
            )}
            {selectedReport ? (
              <ReportView report={selectedReport} />
            ) : idea.latestReport ? (
              <div className="bg-white rounded-3xl shadow-card p-8 flex flex-col gap-3" style={{ border: `1px solid ${line}` }}>
                <div className="font-bold">
                  {idea.latestReport.decision ? DECISION_META[idea.latestReport.decision].label : "판정 없음"}
                </div>
                <p className="text-sm m-0 leading-relaxed" style={{ color: slate }}>
                  {idea.latestReport.summary}
                </p>
                <div className="text-xs" style={{ color: iron }}>
                  예전에 요약만 저장된 기록이라 분야별 결과는 볼 수 없어요.
                </div>
              </div>
            ) : (
              <EmptyCard text="아직 진단 보고서가 없어요. 오른쪽에서 상세분석을 시작해 보세요." />
            )}
          </section>
        )}

        {tab === "interview" &&
          (idea.interview?.messages.length ? (
            <section className="bg-white rounded-3xl shadow-card p-6 flex flex-col gap-3" style={{ border: `1px solid ${line}` }}>
              <p className="text-xs m-0" style={{ color: iron }}>
                AI가 이 대화로 프로필 초안을 채웠어요 · 처음 메모: {idea.memo}
              </p>
              {idea.interview.messages.map((m, i) => (
                <p key={i} className="m-0 text-sm leading-relaxed whitespace-pre-wrap">
                  <b style={{ color: m.role === "user" ? "#6161FF" : slate }}>{m.role === "user" ? "나" : "인터뷰어"}</b>{" "}
                  {m.content}
                </p>
              ))}
            </section>
          ) : (
            <EmptyCard text="인터뷰 없이 직접 작성한 프로필이에요." />
          ))}
      </main>

      {/* ── 오른쪽: 진단 · 채워진 정도 ── */}
      <aside className="flex flex-col gap-4">
        <DiagnosisCard
          idea={idea}
          status={status}
          latest={latest}
          loggedIn={!!user}
          canDiagnose={canDiagnose}
          missingCount={missingCount}
          label={diagnoseLabel}
          onDiagnose={onDiagnose}
          onOpenReport={() => setTab("report")}
        />

        <div className="bg-white rounded-3xl shadow-card p-5 flex flex-col gap-2" style={{ border: `1px solid ${line}` }}>
          <b className="text-sm" style={{ color: ink }}>
            채워진 정도
          </b>
          {sections.map((s) => {
            const n = filled(s.rows);
            return (
              <div key={s.no} className="flex justify-between text-sm" style={{ color: slate }}>
                <span>{s.title}</span>
                <span className="font-semibold" style={{ color: n === s.rows.length ? "#0F7B6C" : ink }}>
                  {n}/{s.rows.length}
                </span>
              </div>
            );
          })}
          {toFill.length > 0 && (
            <div className="mt-2 rounded-2xl p-3 text-xs leading-relaxed" style={{ background: "#FFF7EB", color: "#8A4B08" }}>
              <b className="block mb-1">직접 채워야 할 것</b>
              {toFill.join(" · ")}
            </div>
          )}
        </div>

        <div className="bg-white rounded-3xl shadow-card p-5 flex flex-col gap-3 text-sm" style={{ border: `1px solid ${line}` }}>
          <b style={{ color: ink }}>이 프로필이 쓰이는 곳</b>
          <div className="flex justify-between" style={{ color: slate }}>
            <span>작성 중인 지원서</span>
            <span>준비 중</span>
          </div>
          <Link href="/programs" className="flex justify-between no-underline" style={{ color: slate, textDecoration: "none" }}>
            <span>맞춤 공고 추천</span>
            <span style={{ color: "#6161FF" }}>보기 ›</span>
          </Link>
        </div>
      </aside>
    </div>
  );
}

/** "· "로 이어진 값은 칩으로, "— 한계:"는 줄을 나눠 보여준다 */
function RowValue({ value }: { value: string }) {
  // "· 기능1\n· 기능2"처럼 목록으로 온 값만 칩으로 보여준다
  const parts = value.trim().startsWith("·") ? value.split(/\s*·\s+/).filter((t) => t.trim()) : [];
  const highlight = (t: string) =>
    t.split(/(\(미확인\))/).map((x, i) =>
      x === "(미확인)" ? (
        <span key={i} className="text-[11px] font-semibold px-1.5 py-0.5 rounded-md mx-0.5" style={{ background: "#FFF7EB", color: "#B45309" }}>
          미확인
        </span>
      ) : (
        <span key={i}>{x}</span>
      ),
    );
  if (parts.length >= 2) {
    return (
      <div className="flex flex-wrap gap-1.5">
        {parts.map((t, i) => (
          <span key={i} className="px-2.5 py-1 rounded-full text-[13px]" style={{ background: "#F5F6F8", color: "#333333" }}>
            {highlight(t.trim())}
          </span>
        ))}
      </div>
    );
  }
  return <div className="whitespace-pre-wrap">{highlight(value.replace(/\s+—\s+(한계:)/, "\n$1"))}</div>;
}

function SourceBadge({
  row,
  sectionFromReport,
  fromInterview,
  empty,
}: {
  row: ProfileRow;
  sectionFromReport: boolean;
  fromInterview: boolean;
  empty: boolean;
}) {
  const base = "inline-block text-[11px] font-semibold px-1.5 py-0.5 rounded-md whitespace-nowrap";
  if (sectionFromReport) {
    return row.fromReport && !empty ? (
      <span className={base} style={{ background: "#BCFE90", color: "#2A5C4E" }}>
        상세분석 v{row.fromReport}
      </span>
    ) : (
      <span className={base} style={{ border: "1px dashed #CACBCD", color: "#808080" }}>
        분석 전
      </span>
    );
  }
  if (empty) {
    return row.required ? (
      <span className={base} style={{ background: "#FCD0F8", color: "#B42318" }}>
        필수 · 미입력
      </span>
    ) : (
      <span className={base} style={{ background: "#FFF7EB", color: "#B45309" }}>
        사용자 입력
      </span>
    );
  }
  return (
    <span className={base} style={{ background: fromInterview ? "#EDDFF7" : "#F5F6F8", color: fromInterview ? "#6B3FA0" : "#535768" }}>
      {fromInterview ? "인터뷰 · AI" : "직접 입력"}
    </span>
  );
}

function DiagnosisCard({
  idea,
  status,
  latest,
  loggedIn,
  canDiagnose,
  missingCount,
  label,
  onDiagnose,
  onOpenReport,
}: {
  idea: Idea;
  status: IdeaStatus;
  latest: IdeaReport | null;
  loggedIn: boolean;
  canDiagnose: boolean;
  missingCount: number;
  label: string;
  onDiagnose: () => void;
  onOpenReport: () => void;
}) {
  const dr = latest?.response.workflow_result.decision_result;
  const decision = dr ? DECISION_META[dr.decision] : idea.latestReport?.decision ? DECISION_META[idea.latestReport.decision] : null;

  return (
    <div className="bg-white rounded-3xl p-5 flex flex-col gap-4" style={{ border: "2px solid #333333" }}>
      <div className="flex items-center justify-between gap-2">
        <b className="text-lg" style={{ color: "#333333" }}>
          진단
        </b>
        {status === "diagnosing" ? (
          <StatusPill status="diagnosing" />
        ) : decision ? (
          <span className="text-xs font-bold px-2 py-0.5 rounded-md" style={{ background: "#F5F6F8", color: decision.color }}>
            {decision.label}
          </span>
        ) : (
          <span className="text-xs px-2 py-0.5 rounded-md" style={{ border: "1px dashed #CACBCD", color: "#808080" }}>
            판정 준비 중
          </span>
        )}
      </div>

      {status === "diagnosing" ? (
        <>
          <p className="text-sm m-0 leading-relaxed" style={{ color: "#535768" }}>
            6개 분야를 근거와 함께 진단하고 있어요. 보통 2~3분 걸려요. 이 화면을 닫지 말아주세요.
          </p>
          <div className="grid grid-cols-3 gap-1.5 text-xs text-center">
            {AGENT_ORDER.map((a) => (
              <span key={a} className="rounded-md py-1.5 animate-pulse" style={{ background: "#D1FAFF", color: "#0B6377" }}>
                {AGENT_LABELS[a] ?? a}
              </span>
            ))}
          </div>
        </>
      ) : dr ? (
        <>
          <div>
            <div className="flex justify-between text-xs mb-1" style={{ color: "#535768" }}>
              <span>확신도</span>
              <span className="font-semibold">{dr.confidence.toFixed(2)}</span>
            </div>
            <div className="h-1.5 rounded-full" style={{ background: "#E6E7EA" }}>
              <div className="h-1.5 rounded-full" style={{ width: `${Math.round(dr.confidence * 100)}%`, background: decision?.color }} />
            </div>
          </div>
          <p className="text-sm m-0 leading-relaxed" style={{ color: "#333333" }}>
            {dr.summary}
          </p>
          {[
            ["가장 강한 점", dr.strengths[0], "#BCFE90", "#2A5C4E"],
            ["가장 큰 약점", dr.weaknesses[0], "#FCD0F8", "#9D1C6A"],
            ["지금 할 일", dr.action_plan[0], "#FFF7EB", "#8A4B08"],
          ]
            .filter(([, text]) => text)
            .map(([title, text, bg, fg]) => (
              <div key={title} className="rounded-2xl p-3 text-sm leading-relaxed" style={{ background: bg }}>
                <b className="block text-xs mb-1" style={{ color: fg }}>
                  {title}
                </b>
                <span style={{ color: "#333333" }}>{text}</span>
              </div>
            ))}
          <button
            type="button"
            onClick={onOpenReport}
            className="min-h-[48px] rounded-full text-sm font-bold text-white"
            style={{ background: "#333333", border: "none", cursor: "pointer" }}
          >
            진단 전체 보기 ›
          </button>
        </>
      ) : (
        <p className="text-sm m-0 leading-relaxed" style={{ color: "#535768" }}>
          {status === "failed"
            ? `상세 진단에 실패했어요. ${idea.errorMessage ?? "분석이 중간에 끊겼어요."}`
            : idea.latestReport?.summary ||
              "시장·고객·경쟁·수익·재무·위험 6개 분야를 외부 자료와 함께 진단하고, GO / PIVOT / VALIDATE MORE / STOP 판정을 내려요."}
        </p>
      )}

      {status !== "diagnosing" && loggedIn && (!dr || idea.profileChangedSinceReport || status === "failed") && (
        <div className="flex flex-col gap-1.5">
          <button
            type="button"
            onClick={onDiagnose}
            disabled={!canDiagnose}
            className="min-h-[48px] rounded-full text-sm font-bold text-white disabled:opacity-50"
            style={{ background: "#6161FF", border: "none", cursor: "pointer" }}
          >
            {status === "failed" ? "다시 분석 (유료)" : label}
          </button>
          <span className="text-xs text-center" style={{ color: "#808080" }}>
            {missingCount > 0
              ? "* 필수 항목을 채우면 분석할 수 있어요"
              : idea.profileChangedSinceReport
                ? "프로필이 바뀌었어요. 새 보고서를 만들 수 있어요"
                : "보통 2~3분 걸려요"}
          </span>
        </div>
      )}
      {!loggedIn && (
        <Link href={`/login?next=/ideas/${idea.id}`} className="text-sm font-semibold" style={{ color: "#6161FF" }}>
          로그인하면 고치고 분석할 수 있어요 ›
        </Link>
      )}
    </div>
  );
}

function EmptyCard({ text }: { text: string }) {
  return (
    <div className="bg-white rounded-3xl shadow-card p-10 text-center text-sm" style={{ border: "1px solid #E6E7EA", color: "#808080" }}>
      {text}
    </div>
  );
}
