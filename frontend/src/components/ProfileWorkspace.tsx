"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { User } from "firebase/auth";
import ReportView, { SectionNav, reportNavItems } from "@/components/ReportView";
import StatusPill from "@/components/StatusPill";
import { type AnalyzeJob, type AreaScore, type MarketSizing, profileDigest } from "@/lib/api";
import { type FinancePlan, financeSummary } from "@/lib/financePlan";
import { RiskMatrix, risksOf } from "@/components/ReportVisuals";
import { AGENT_LABELS, AGENT_ORDER, SHOW_CONFIDENCE } from "@/lib/agents";
import { progressOf } from "@/lib/diagnosisRunner";
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
import { deleteIdea, deleteValidation, listIdeas, listValidations, saveValidation } from "@/lib/ideaStore";
import ValidationBoard from "@/components/ValidationBoard";
import ValidationForm, { type ValidationDraft, type ValidationPrefill } from "@/components/ValidationForm";
import { type Validation, pendingValidations } from "@/lib/validation";
import { type ProfileRow, isUnknown, profileFieldRows, reportRows, updateRow } from "@/lib/profileRows";

type Tab = "overview" | "report" | "validation" | "interview";

interface Section {
  no: number;
  title: string;
  badge: string;
  rows: ProfileRow[];
  /** 상세분석에서 채워지는 섹션 */
  fromReport?: boolean;
  /** 이 섹션을 채우는 에이전트 (근거 수 표시용) */
  agent?: string;
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
  /** 진행 중인 상세분석 작업 (단계별 진행) */
  diagnosisJob?: AnalyzeJob | null;
  onShowProgress?: () => void;
  /** 값이 바뀌면 보고서 탭으로 넘긴다 (진행 모달의 '보고서 보기') */
  openReportSignal?: number;
  /** 보고서 재무 시나리오에 넣은 숫자 저장 */
  onSaveFinance?: (plan: FinancePlan) => Promise<void>;
  onSaveMarket?: (v: { reportId: string; data: MarketSizing }) => Promise<void>;
  onSaveScores?: (v: { reportId: string; data: AreaScore[] }) => Promise<void>;
  onSaveDigest?: (v: { reportId: string; rows: Record<string, string> }) => Promise<void>;
}

const IDEA_LIMIT = 3;
const ink = "#071B45";
const slate = "#53647A";
const iron = "#6B7280";
const line = "#D7E0ED";

export default function ProfileWorkspace(props: Props) {
  const { idea, status, reports, user, busy, error, canDiagnose, missingCount, onSaveProfile, onDiagnose, diagnosisJob, onShowProgress, openReportSignal, onSaveFinance, onSaveMarket, onSaveScores, onSaveDigest } = props;
  const [tab, setTab] = useState<Tab>("overview");
  const [selectedReportId, setSelectedReportId] = useState<string | null>(reports[0]?.id ?? null);
  // 프로필 전체를 한 번에 고친다: 편집 모드 + 칸별 초안
  const [editing, setEditing] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [ideas, setIdeas] = useState<Idea[]>([]);
  // 왼쪽 '내 아이디어'는 3개까지만 — 보고서 목차가 화면 안에 보이도록
  const [showAllIdeas, setShowAllIdeas] = useState(false);
  const router = useRouter();
  // 가설 검증 기록 — 다음 보고서의 '창업가 검증' 근거
  const [validations, setValidations] = useState<Validation[]>([]);
  const [validationsLoading, setValidationsLoading] = useState(true);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [form, setForm] = useState<ValidationPrefill | null>(null);

  // 카드의 '보고서 보기'(#report)로 들어오면 보고서 탭부터
  useEffect(() => {
    if (window.location.hash === "#report") setTab("report");
  }, []);
  useEffect(() => {
    setSelectedReportId(reports[0]?.id ?? null);
  }, [reports]);
  useEffect(() => {
    if (openReportSignal) setTab("report");
  }, [openReportSignal]);
  useEffect(() => {
    listIdeas(user).then(setIdeas).catch(() => setIdeas([]));
  }, [user, idea.updatedAt]);
  useEffect(() => {
    let alive = true;
    setValidationsLoading(true);
    listValidations(user, idea.id)
      .then((list) => alive && (setValidations(list), setValidationError(null)))
      .catch((err) => alive && setValidationError(err instanceof Error ? err.message : String(err)))
      .finally(() => alive && setValidationsLoading(false));
    return () => {
      alive = false;
    };
  }, [user, idea.id]);

  async function submitValidation(draft: ValidationDraft) {
    const saved = await saveValidation(user, idea.id, draft);
    setValidations((list) => [saved, ...list.filter((v) => v.id !== saved.id)]);
    setValidationError(null);
    setForm(null);
    // 보고서에서 시작했어도 저장 뒤엔 검증 기록 탭에서 '보고서에 반영'으로 이어지게
    setTab("validation");
  }

  async function removeValidation(v: Validation) {
    if (!confirm("이 검증 기록을 삭제할까요? 이미 만든 보고서에는 그대로 남아 있어요.")) return;
    try {
      await deleteValidation(user, idea.id, v.id);
      setValidations((list) => list.filter((x) => x.id !== v.id));
    } catch (err) {
      setValidationError(err instanceof Error ? err.message : String(err));
    }
  }

  const latest = reports[0] ?? null;
  const selectedReport = reports.find((r) => r.id === selectedReportId) ?? latest;
  const hasReport = idea.reportCount > 0 || idea.latestReport !== null;
  const fromInterview = !!idea.interview?.messages.length;
  const p = idea.profile;
  const rawFromReport = reportRows(latest);
  // 보고서 문장을 1~3번과 같은 '짧은 요약 + 명사형 근거'로 다시 쓴 것이 있으면 그걸 보여준다 (없으면 문장 나누기)
  const digest = latest && idea.reportDigest?.reportId === latest.id ? idea.reportDigest.rows : null;
  const withDigest = (rows: ProfileRow[]) => rows.map((r) => (digest?.[r.id] ? { ...r, value: digest[r.id] } : r));
  const fromReport = {
    market: withDigest(rawFromReport.market),
    competition: withDigest(rawFromReport.competition),
    finance: withDigest(rawFromReport.finance),
    risk: rawFromReport.risk,
  };
  const digestAsked = useRef<string | null>(null);
  useEffect(() => {
    if (!latest || digest || !onSaveDigest || digestAsked.current === latest.id) return;
    digestAsked.current = latest.id;
    const rows = [...rawFromReport.market, ...rawFromReport.competition, ...rawFromReport.finance]
      .filter((r) => r.raw)
      .map((r) => ({ id: r.id, label: r.label, text: r.raw!.slice(0, 2500) }));
    if (!rows.length) return;
    profileDigest(rows)
      .then((res) => {
        const map = Object.fromEntries(res.map((d) => [d.id, [d.summary, ...d.points.map((p) => `· ${p}`)].join("\n")]));
        return onSaveDigest({ reportId: latest.id, rows: map });
      })
      .catch(() => {});
    // 보고서 버전이 바뀔 때만
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latest?.id, !!digest]);
  const canEdit = !!user && status !== "diagnosing";

  const base = profileFieldRows(p);
  // 4~7은 상세분석(유료) 결과 — 보고서가 없으면 가려 둔다
  const locked = !latest;
  const sections: Section[] = [
    { no: 1, title: "아이템", badge: "", rows: base.item },
    { no: 2, title: "문제 · 고객", badge: "P 문제인식", rows: base.customer },
    { no: 3, title: "해결 · 솔루션", badge: "S 실현가능성 · BM", rows: base.solution },
    { no: 4, title: "시장", badge: "P 목표시장", rows: fromReport.market, fromReport: true, agent: "MarketAgent" },
    { no: 5, title: "경쟁", badge: "S 차별성", rows: fromReport.competition, fromReport: true, agent: "CompetitorAgent" },
    { no: 6, title: "재무", badge: "S 자금 소요", rows: fromReport.finance, fromReport: true, agent: "FinancialAgent" },
    { no: 7, title: "리스크", badge: "", rows: fromReport.risk, fromReport: true, agent: "RiskAgent" },
  ];
  const filled = (rows: ProfileRow[]) => rows.filter((r) => !isUnknown(r.value)).length;
  const toFill = sections
    .filter((s) => !s.fromReport)
    .flatMap((s) => s.rows)
    .filter((r) => isUnknown(r.value))
    .map((r) => r.label);

  const editableRows = sections.filter((s) => !s.fromReport).flatMap((s) => s.rows).filter((r) => r.field);
  // 사용자가 직접 고치면 확인된 내용이므로 AI 추정·미확인 표시를 지운다
  const cleaned = (v: string) => v.replace(/\((미확인|AI 추정)\)\s*/g, "").trim();

  async function removeProfile() {
    if (!confirm(`'${displayTitle(idea)}'을(를) 삭제할까요? 보고서도 함께 지워져요.`)) return;
    await deleteIdea(user, idea.id).catch(() => {});
    router.push("/ideas");
  }

  function startEdit() {
    setTab("overview");
    setDrafts(Object.fromEntries(editableRows.map((r) => [r.id, cleaned(r.value)])));
    setEditing(true);
  }

  async function saveAll() {
    // 바뀐 칸만 반영 — 손대지 않은 칸의 AI 추정 표시는 그대로 둔다
    const next = editableRows.reduce(
      (acc, r) => (drafts[r.id] !== undefined && drafts[r.id] !== cleaned(r.value) ? updateRow(acc, r, drafts[r.id]) : acc),
      p,
    );
    try {
      if (next !== p) await onSaveProfile(next);
      setEditing(false);
    } catch {
      // 실패하면 고치던 내용을 그대로 둔다
    }
  }

  const renderSection = (s: Section, sectionLocked: boolean) => (
    <div key={s.no} className="py-4" aria-hidden={sectionLocked || undefined}>
      <div className="flex items-baseline justify-between gap-3 flex-wrap pb-3" style={{ borderBottom: `2px solid ${sectionLocked ? "#D9DBDA" : ink}` }}>
        <h2 className="text-base font-bold m-0 flex items-center gap-1.5" style={{ color: sectionLocked ? iron : ink }}>
          {s.no} · {s.title}
          {s.fromReport && (
            <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded" style={{ background: "#F5F7FB", color: iron }}>
              유료
            </span>
          )}
        </h2>
        <div className="flex items-center gap-2">
          {s.badge && (
            <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded" style={{ background: "#F5F7FB", color: "#071B45" }}>
              {s.badge}
            </span>
          )}
          {!sectionLocked && s.fromReport && s.agent && latest && (
            <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded" style={{ background: "#E7F6EF", color: "#0F7B6C" }}>
              근거 {latest.response.workflow_result.agent_results[s.agent]?.evidence?.length ?? 0}건
            </span>
          )}
          {!sectionLocked && s.fromReport ? (
            <button
              type="button"
              onClick={() => setTab("report")}
              className="text-xs font-semibold"
              style={{ background: "none", border: "none", color: "#134CD8", cursor: "pointer", padding: 0 }}
            >
              보고서에서 자세히 ›
            </button>
          ) : (
            !sectionLocked && (
              <span className="text-xs" style={{ color: iron }}>
                {filled(s.rows)}/{s.rows.length}
              </span>
            )
          )}
        </div>
      </div>

      {s.rows.map((r) => {
        const empty = isUnknown(r.value);
        const isEditing = editing && !!r.field && !sectionLocked && !s.fromReport;
        const editValue = drafts[r.id] ?? "";
        const setEditValue = (v: string) => setDrafts((d) => ({ ...d, [r.id]: v }));
        return (
          <div
            key={r.id}
            className="grid gap-x-4 gap-y-2 py-4 pl-4 grid-cols-1 md:grid-cols-[130px_minmax(0,1fr)_110px] items-start"
            style={{ borderBottom: `1px solid ${line}` }}
          >
            <div className="text-sm font-semibold" style={{ color: sectionLocked ? iron : ink }}>
              {r.label}
              {r.required && <span style={{ color: "#B42318" }}> *</span>}
            </div>

            <div className="text-sm leading-relaxed min-w-0" style={{ color: empty ? iron : ink }}>
              {sectionLocked ? (
                // 잠긴 칸: 실제 내용 대신 흐린 자리 표시
                <span className="select-none" style={{ filter: "blur(4px)", color: slate }}>
                  {r.hint} — 상세분석 결과가 여기에 들어가요. 근거 자료와 함께 정리돼요.
                </span>
              ) : isEditing ? (
                <div className="flex flex-col">
                  {r.field === "location" ? (
                    <select
                      value={editValue || "전국"}
                      onChange={(e) => setEditValue(e.target.value)}
                      aria-label={r.label}
                      className="h-10 rounded-lg px-3 text-sm bg-white focus:outline-none self-start"
                      style={{ border: "1.5px solid #134CD8" }}
                    >
                      {REGIONS.map((x) => (
                        <option key={x}>{x}</option>
                      ))}
                    </select>
                  ) : (
                  <textarea
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    aria-label={r.label}
                    placeholder={r.hint}
                    rows={Math.min(10, Math.max(2, editValue.split("\n").length + 1, Math.ceil(editValue.length / 45)))}
                    className="rounded-lg p-3 text-sm resize-y focus:outline-none leading-relaxed"
                    style={{ border: "1.5px solid #134CD8" }}
                  />
                  )}
                </div>
              ) : r.id === "fin:summary" ? (
                <div className="flex flex-col gap-2 items-start">
                  {financeSummary(idea.financePlan) ? (
                    <RowValue value={financeBullets(financeSummary(idea.financePlan)!)} />
                  ) : r.value ? (
                    <RowValue value={r.value} />
                  ) : (
                    <span>이번 분석에서 나오지 않았어요</span>
                  )}
                  <button
                    type="button"
                    onClick={() => setTab("report")}
                    className="min-h-[36px] px-3 rounded-lg text-xs font-bold"
                    style={{ background: "#EAF0FD", color: "#0F3DB0", border: "none", cursor: "pointer" }}
                  >
                    {financeSummary(idea.financePlan) ? "손익계산서 보기 ›" : "손익계산서 만들기 ›"}
                  </button>
                </div>
              ) : r.id === "risk:top" && latest && risksOf(latest).length > 0 ? (
                <div className="flex gap-4 items-start flex-wrap">
                  <RiskMatrix risks={risksOf(latest)} size="sm" />
                  <ol className="m-0 p-0 list-none flex flex-col gap-1 min-w-0 flex-1">
                    {risksOf(latest)
                      .slice(0, 3)
                      .map((x, i) => (
                        <li key={i} className="flex gap-2 items-baseline">
                          <span className="text-[11px] font-bold shrink-0" style={{ color: x.score >= 15 ? "#C2341C" : x.score >= 8 ? "#C27A0E" : "#0F7B6C" }}>
                            {i + 1}. {x.score}점
                          </span>
                          <span className="min-w-0">{x.risk || x.label}</span>
                        </li>
                      ))}
                  </ol>
                </div>
              ) : empty && !r.value.includes("(미확인)") ? (
                <span>{s.fromReport ? "이번 분석에서 나오지 않았어요" : "미입력"}</span>
              ) : (
                <RowValue field={r.field} value={r.value} />
              )}
            </div>

            <div>
              {!sectionLocked && <SourceBadge row={r} sectionFromReport={!!s.fromReport} fromInterview={fromInterview} fromMemo={!!idea.previewProfile} empty={empty} />}
            </div>
          </div>
        );
      })}
    </div>
  );

  // 지금 보고 있는 아이디어는 3개 안에 늘 들어가게 한다
  const visibleIdeas = (() => {
    if (showAllIdeas || ideas.length <= IDEA_LIMIT) return ideas;
    const top = ideas.slice(0, IDEA_LIMIT);
    const current = ideas.find((i) => i.id === idea.id);
    return current && !top.includes(current) ? [...top.slice(0, IDEA_LIMIT - 1), current] : top;
  })();

  const diagnoseLabel = hasReport ? "보고서 새로 작성 (유료)" : "상세분석하기 (유료)";

  return (
    <div className="max-w-[1440px] mx-auto px-6 py-8 grid gap-6 grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px] xl:grid-cols-[220px_minmax(0,1fr)_320px] items-start">
      {/* ── 왼쪽: 내 아이디어 ── */}
      <div className="hidden xl:flex flex-col gap-4 self-stretch">
      <aside className="flex flex-col gap-2 bg-white rounded-lg shadow-card p-4" style={{ border: `1px solid ${line}` }}>
        <div className="text-xs px-2 pb-1" style={{ color: iron }}>
          내 아이디어
        </div>
        {visibleIdeas.map((i) => {
          const active = i.id === idea.id;
          return (
            <Link
              key={i.id}
              href={`/ideas/${i.id}`}
              className="rounded-lg px-3 py-3 no-underline flex flex-col gap-1.5"
              style={{ background: active ? "#F5F7FB" : "transparent", textDecoration: "none", color: ink }}
            >
              <span className="text-sm font-semibold leading-snug line-clamp-2">{displayTitle(i)}</span>
              <span className="self-start">
                <StatusPill status={effectiveStatus(i).status} />
              </span>
            </Link>
          );
        })}
        {ideas.length > IDEA_LIMIT && (
          <button
            type="button"
            onClick={() => setShowAllIdeas((v) => !v)}
            aria-expanded={showAllIdeas}
            className="rounded-lg py-2 text-xs font-semibold"
            style={{ background: "none", border: "none", color: slate, cursor: "pointer" }}
          >
            {showAllIdeas ? "접기 ▴" : `더보기 (${ideas.length - IDEA_LIMIT}) ▾`}
          </button>
        )}
        <Link
          href="/ideas"
          className="mt-2 rounded-lg py-3 text-center text-sm font-semibold no-underline"
          style={{ border: "1.5px dashed #D9DBDA", color: "#53647A", textDecoration: "none" }}
        >
          + 새 아이디어
        </Link>
      </aside>
      {/* 보고서를 볼 때는 섹션 목차가 스크롤을 따라온다 */}
      {tab === "report" && selectedReport && (
        <div className="sticky top-[76px] bg-white rounded-lg shadow-card p-3" style={{ border: `1px solid ${line}` }}>
          <SectionNav vertical items={reportNavItems(selectedReport)} />
        </div>
      )}
      </div>

      {/* ── 가운데: 프로필 ── */}
      <main className="min-w-0 flex flex-col gap-5">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="min-w-0">
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
                className="min-h-[48px] px-5 rounded-xl text-sm font-semibold bg-white disabled:opacity-50"
                style={{ border: `1px solid ${slate}`, color: ink, cursor: "pointer" }}
              >
                {diagnoseLabel}
              </button>
            )}
            <Link
              href="/programs"
              className="min-h-[48px] px-5 rounded-xl text-sm font-bold no-underline inline-flex items-center"
              // 보고서가 나온 뒤의 다음 할 일이라 그때만 강조색
              style={
                latest
                  ? { background: "#134CD8", color: "#fff", textDecoration: "none" }
                  : { background: "#fff", border: "1px solid #D9DBDA", color: "#071B45", textDecoration: "none" }
              }
            >
              이 아이템으로 공고 찾기
            </Link>
          </div>
        </div>

        {/* 탭 */}
        <div className="flex items-center gap-1 border-b" style={{ borderColor: line }}>
          <div className="flex gap-1" role="tablist">
          {(
            [
              ["overview", "프로필", null],
              ["report", "진단 보고서", reports.length || (idea.latestReport ? 1 : 0)],
              ["validation", "검증 기록", validations.length],
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
                borderBottom: `2px solid ${tab === key ? "#134CD8" : "transparent"}`,
                color: tab === key ? "#0F3DB0" : slate,
                cursor: "pointer",
              }}
            >
              {label}
              {count !== null && <span className="ml-1.5 text-xs" style={{ color: iron }}>{count}</span>}
            </button>
          ))}
          </div>

          {canEdit && (
            <div className="ml-auto flex gap-2 pb-1.5">
              {editing ? (
                <>
                  <button
                    type="button"
                    onClick={() => setEditing(false)}
                    disabled={busy}
                    className="min-h-[36px] px-4 rounded-xl text-xs font-semibold bg-white"
                    style={{ border: "1px solid #D7E0ED", color: slate, cursor: "pointer" }}
                  >
                    취소
                  </button>
                  <button
                    type="button"
                    onClick={saveAll}
                    disabled={busy}
                    className="min-h-[36px] px-4 rounded-xl text-xs font-bold text-white disabled:opacity-50"
                    style={{ background: "#134CD8", border: "none", cursor: "pointer" }}
                  >
                    모두 저장
                  </button>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={startEdit}
                    className="min-h-[36px] px-4 rounded-xl text-xs font-semibold bg-white"
                    style={{ border: "1px solid #D7E0ED", color: ink, cursor: "pointer" }}
                  >
                    프로필 수정
                  </button>
                  <button
                    type="button"
                    onClick={removeProfile}
                    className="min-h-[36px] px-4 rounded-xl text-xs font-semibold bg-white"
                    style={{ border: "1px solid #D7E0ED", color: "#B42318", cursor: "pointer" }}
                  >
                    프로필 삭제
                  </button>
                </>
              )}
            </div>
          )}
        </div>

        {error && (
          <div className="rounded-xl p-4 text-sm" style={{ background: "#FEF2F2", color: "#B42318" }}>
            {error}
          </div>
        )}

        {!user && (
          <div
            className="rounded-xl p-4 text-sm flex items-center justify-between gap-3 flex-wrap"
            style={{ background: "#FFF6DE", color: "#8A4B08" }}
          >
            <span className="leading-relaxed">
              <b>{idea.previewProfile ? "메모만으로 만든 미리보기 프로필이에요." : "로그인하지 않으셨네요."}</b> 이 브라우저에만 저장돼 있어요. 로그인하면
              계정에 저장되고, AI 인터뷰로 더 정확하게 다듬을 수 있어요.
            </span>
            <Link href={`/login?next=/ideas/${idea.id}`} className="font-bold underline whitespace-nowrap" style={{ color: "#071B45" }}>
              로그인하고 저장하기 ›
            </Link>
          </div>
        )}

        {tab === "overview" && (
          <section id="profile" className="bg-white rounded-lg shadow-card px-6 py-4 scroll-mt-20" style={{ border: `1px solid ${line}` }}>
            {sections.filter((s) => !s.fromReport).map((s) => renderSection(s, false))}

            {/* 상세분석(유료) 섹션 — 분석 전엔 흐리게 가리고 잠근다 */}
            <div className="relative">
              {sections.filter((s) => s.fromReport).map((s) => renderSection(s, locked))}
              {locked && (
                <div className="absolute inset-0 flex items-start justify-center pt-24">
                  <div
                    className="bg-white rounded-lg p-6 max-w-[360px] w-full flex flex-col items-center gap-3 text-center"
                    style={{ border: "1px solid #D7E0ED" }}
                  >
                    <span className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: "#F5F7FB" }}>
                      <LockIcon />
                    </span>
                    <b className="text-base" style={{ color: ink }}>
                      상세분석(유료)에서 열려요
                    </b>
                    <p className="text-sm m-0 leading-relaxed" style={{ color: slate }}>
                      시장 · 경쟁 · 재무 · 리스크를 외부 자료와 함께 분석해 이 칸들을 채워요.
                    </p>
                    {user && status !== "diagnosing" && (
                      <button
                        type="button"
                        onClick={onDiagnose}
                        disabled={!canDiagnose}
                        className="min-h-[48px] px-6 rounded-xl text-sm font-bold bg-white disabled:opacity-50"
                        style={{ border: "1px solid #071B45", color: "#071B45", cursor: "pointer" }}
                      >
                        상세분석하기 (유료)
                      </button>
                    )}
                    {!user && (
                      <Link
                        href={`/login?next=/ideas/${idea.id}`}
                        className="min-h-[48px] px-6 rounded-xl text-sm font-bold no-underline inline-flex items-center"
                        style={{ border: "1px solid #071B45", color: "#071B45", textDecoration: "none" }}
                      >
                        로그인하고 상세분석하기
                      </Link>
                    )}
                    {status === "diagnosing" && <StatusPill status="diagnosing" />}
                    {missingCount > 0 && (
                      <span className="text-xs" style={{ color: iron }}>
                        * 필수 항목을 먼저 채워주세요
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
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
                    className="min-h-[36px] px-3 rounded-xl text-xs font-semibold"
                    style={{
                      cursor: "pointer",
                      border: "1px solid #D7E0ED",
                      background: r.id === selectedReport?.id ? "#071B45" : "#fff",
                      color: r.id === selectedReport?.id ? "#fff" : slate,
                    }}
                  >
                    v{r.version} · {new Date(r.createdAt).toLocaleDateString("ko-KR")}
                  </button>
                ))}
              </div>
            )}
            {selectedReport ? (
              <ReportView report={selectedReport} financePlan={idea.financePlan}
                onSaveFinancePlan={onSaveFinance}
                marketSizing={idea.marketSizing}
                onSaveMarketSizing={onSaveMarket}
                areaScores={idea.areaScores}
                onSaveAreaScores={onSaveScores}
                onValidate={user ? (prefill) => setForm(prefill) : undefined}
                validationCounts={validations.reduce<Record<string, number>>((acc, v) => ({ ...acc, [v.area]: (acc[v.area] ?? 0) + 1 }), {})}
                onOpenValidations={() => setTab("validation")}
              />
            ) : idea.latestReport ? (
              <div className="bg-white rounded-lg shadow-card p-8 flex flex-col gap-3" style={{ border: `1px solid ${line}` }}>
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

        {tab === "validation" &&
          (user ? (
            <ValidationBoard
              validations={validations}
              reports={reports}
              loading={validationsLoading}
              error={validationError}
              canDiagnose={canDiagnose}
              diagnosing={status === "diagnosing"}
              onAdd={(prefill) => setForm(prefill)}
              onEdit={(v) => setForm(v)}
              onDelete={removeValidation}
              onDiagnose={onDiagnose}
            />
          ) : (
            <EmptyCard text="검증 기록은 로그인한 뒤에 남길 수 있어요." />
          ))}

        {form && <ValidationForm initial={form} onSave={submitValidation} onClose={() => setForm(null)} />}

        {tab === "interview" &&
          (idea.interview?.messages.length ? (
            <section className="bg-white rounded-lg shadow-card p-6 flex flex-col gap-3" style={{ border: `1px solid ${line}` }}>
              <p className="text-xs m-0" style={{ color: iron }}>
                AI가 이 대화로 프로필 초안을 채웠어요 · 처음 메모: {idea.memo}
              </p>
              {idea.interview.messages.map((m, i) => (
                <p key={i} className="m-0 text-sm leading-relaxed whitespace-pre-wrap">
                  <b style={{ color: m.role === "user" ? "#071B45" : slate }}>{m.role === "user" ? "나" : "인터뷰어"}</b>{" "}
                  {m.content}
                </p>
              ))}
            </section>
          ) : (
            <EmptyCard
              text={
                idea.previewProfile
                  ? "메모만으로 만든 미리보기 프로필이에요. 로그인하면 AI 인터뷰로 더 정확하게 다듬을 수 있어요."
                  : "인터뷰 없이 직접 작성한 프로필이에요."
              }
            />
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
          job={diagnosisJob ?? null}
          onShowProgress={onShowProgress}
          pendingValidationCount={latest ? pendingValidations(validations, latest).length : 0}
        />

        <div className="bg-white rounded-lg shadow-card p-5 flex flex-col gap-2" style={{ border: `1px solid ${line}` }}>
          <b className="text-sm" style={{ color: ink }}>
            채워진 정도
          </b>
          {sections.map((s) => {
            const n = filled(s.rows);
            const isLocked = s.fromReport && locked;
            return (
              <div key={s.no} className="flex justify-between text-sm" style={{ color: isLocked ? iron : slate }}>
                <span>
                  {s.title}
                  {s.fromReport && <span className="text-[11px] ml-1">(유료)</span>}
                </span>
                {isLocked ? (
                  <span className="text-xs">잠김</span>
                ) : (
                  <span className="font-semibold" style={{ color: n === s.rows.length ? "#071B45" : ink }}>
                    {n}/{s.rows.length}
                  </span>
                )}
              </div>
            );
          })}
          {toFill.length > 0 && (
            <div className="mt-2 rounded-lg p-3 text-xs leading-relaxed" style={{ background: "#FFFBEB", color: "#8A4B08" }}>
              <b className="block mb-1">직접 채워야 할 것</b>
              {toFill.join(" · ")}
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg shadow-card p-5 flex flex-col gap-3 text-sm" style={{ border: `1px solid ${line}` }}>
          <b style={{ color: ink }}>이 프로필이 쓰이는 곳</b>
          <Link
            href={latest ? `/applications?new=1&idea=${idea.id}` : "/applications"}
            className="flex justify-between no-underline"
            style={{ color: slate, textDecoration: "none" }}
          >
            <span>{latest ? "이 아이템으로 지원서 만들기" : "MY지원서"}</span>
            <span className="underline" style={{ color: "#071B45" }}>
              {latest ? "만들기 ›" : "보기 ›"}
            </span>
          </Link>
          <Link href="/programs" className="flex justify-between no-underline" style={{ color: slate, textDecoration: "none" }}>
            <span>맞춤 공고 추천</span>
            <span className="underline" style={{ color: "#071B45" }}>보기 ›</span>
          </Link>
        </div>
      </aside>
    </div>
  );
}

/** 칸 하나는 소제목 없이 그대로 풀어서 보여준다 */
function RowValue({ value }: { field?: keyof IdeaProfile; value: string }) {
  return <Plain value={value} />;
}

/** "· "로 시작하는 목록은 칩으로, "— 한계:"는 줄을 나눠 보여준다 */
function Plain({ value }: { value: string }) {
  // "· 기능1\n· 기능2"처럼 목록으로 온 값만 칩으로 보여준다
  const parts = value.trim().startsWith("·") ? value.split(/\s*·\s+/).filter((t) => t.trim()) : [];
  // "(AI 추정)" 뒤 문장(마침표·줄바꿈까지)만 점선 밑줄로 — 글 중간에 배지를 넣지 않는다
  const highlight = (t: string) =>
    t.split(/(\(AI 추정\)\s*[^.!?\n]*[.!?]?|\(미확인\))/).map((x, i) => {
      if (x === "(미확인)") {
        return (
          <span key={i} className="text-[11px] font-semibold px-1.5 py-0.5 rounded mx-0.5" style={{ background: "#FFFBEB", color: "#B45309" }}>
            미확인
          </span>
        );
      }
      if (x.startsWith("(AI 추정)")) {
        return (
          <span
            key={i}
            title="점선 밑줄은 AI가 추정한 내용이에요"
            style={{ color: "#071B45", textDecoration: "underline dotted", textUnderlineOffset: 3 }}
          >
            {x.replace(/^\(AI 추정\)\s*/, "")}
          </span>
        );
      }
      return <span key={i}>{x}</span>;
    });
  // "요약 한 줄\n· 근거\n· 근거" 모양: 요약은 굵게, 근거는 목록으로
  const lines = value.split("\n").map((l) => l.trim()).filter(Boolean);
  const bullets = lines.filter((l) => /^[·•\-]\s/.test(l));
  if (lines.length >= 2 && !/^[·•\-]\s/.test(lines[0]) && bullets.length === lines.length - 1) {
    return (
      <div>
        <div className="font-bold leading-snug" style={{ color: "#071B45" }}>
          {highlight(lines[0])}
        </div>
        <ul className="m-0 mt-1.5 pl-4 list-disc flex flex-col gap-0.5" style={{ color: "#53647A" }}>
          {bullets.map((b, i) => (
            <li key={i}>{highlight(b.replace(/^[·•\-]\s+/, ""))}</li>
          ))}
        </ul>
      </div>
    );
  }
  if (parts.length >= 2) {
    return (
      <div className="flex flex-wrap gap-1.5">
        {parts.map((t, i) => (
          <span key={i} className="px-2.5 py-1 rounded-full text-[13px]" style={{ background: "#F5F7FB", color: "#071B45" }}>
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
  fromMemo,
  empty,
}: {
  row: ProfileRow;
  sectionFromReport: boolean;
  fromInterview: boolean;
  /** 비로그인 미리보기 — 메모만 보고 AI가 쓴 프로필 */
  fromMemo?: boolean;
  empty: boolean;
}) {
  const base = "inline-block text-[11px] font-semibold px-1.5 py-0.5 rounded whitespace-nowrap";
  if (sectionFromReport) {
    return row.fromReport && !empty ? (
      <span className={base} style={{ background: "#F5F7FB", color: "#071B45" }}>
        상세분석 v{row.fromReport}
      </span>
    ) : (
      <span className={base} style={{ border: "1px dashed #D9DBDA", color: "#6B7280" }}>
        분석 전
      </span>
    );
  }
  if (empty) {
    return row.required ? (
      <span className={base} style={{ background: "#FEF2F2", color: "#B42318" }}>
        필수 · 미입력
      </span>
    ) : (
      <span className={base} style={{ background: "#FFFBEB", color: "#B45309" }}>
        사용자 입력
      </span>
    );
  }
  return (
    row.value.includes("(AI 추정)") ? (
      <span className={base} title="점선 밑줄은 AI가 추정한 내용이에요" style={{ background: "#F5F7FB", color: "#071B45" }}>
        AI 추정 포함
      </span>
    ) : (
    <span className={base} style={{ background: fromInterview ? "#F5F7FB" : "#F5F7FB", color: fromInterview ? "#071B45" : "#53647A" }}>
      {fromInterview ? "인터뷰 · AI" : fromMemo ? "메모 · AI" : "직접 입력"}
    </span>
    )
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
  job,
  onShowProgress,
  pendingValidationCount = 0,
}: {
  pendingValidationCount?: number;
  idea: Idea;
  status: IdeaStatus;
  latest: IdeaReport | null;
  loggedIn: boolean;
  canDiagnose: boolean;
  missingCount: number;
  label: string;
  onDiagnose: () => void;
  onOpenReport: () => void;
  job: AnalyzeJob | null;
  onShowProgress?: () => void;
}) {
  const dr = latest?.response.workflow_result.decision_result;
  const decision = dr ? DECISION_META[dr.decision] : idea.latestReport?.decision ? DECISION_META[idea.latestReport.decision] : null;

  return (
    <div className="bg-white rounded-lg p-5 flex flex-col gap-4" style={{ border: "1px solid #071B45" }}>
      <div className="flex items-center justify-between gap-2">
        <b className="text-lg" style={{ color: "#071B45" }}>
          진단
        </b>
        {status === "diagnosing" ? (
          <StatusPill status="diagnosing" />
        ) : decision ? (
          <span className="text-xs font-bold px-2 py-0.5 rounded" style={{ background: "#F5F7FB", color: decision.color }}>
            {decision.label}
          </span>
        ) : (
          <span className="text-xs px-2 py-0.5 rounded" style={{ border: "1px dashed #D9DBDA", color: "#6B7280" }}>
            판정 준비 중
          </span>
        )}
      </div>

      {status === "diagnosing" ? (
        <DiagnosingMini job={job} startedAt={idea.statusChangedAt} onShowProgress={onShowProgress} />
      ) : dr ? (
        <>
          {SHOW_CONFIDENCE && (
            <div>
              <div className="flex justify-between text-xs mb-1" style={{ color: "#53647A" }}>
                <span>확신도</span>
                <span className="font-semibold">{dr.confidence.toFixed(2)}</span>
              </div>
              <div className="h-1.5 rounded-full" style={{ background: "#D7E0ED" }}>
                <div className="h-1.5 rounded-full" style={{ width: `${Math.round(dr.confidence * 100)}%`, background: decision?.color }} />
              </div>
            </div>
          )}
          <p className="text-sm m-0 leading-relaxed" style={{ color: "#071B45" }}>
            {dr.summary}
          </p>
          {[
            ["가장 강한 점", dr.strengths[0], "#F9FAFB", "#071B45"],
            ["가장 큰 약점", dr.weaknesses[0], "#F9FAFB", "#071B45"],
            ["지금 할 일", dr.action_plan[0], "#F5F7FB", "#071B45"],
          ]
            .filter(([, text]) => text)
            .map(([title, text, bg, fg]) => (
              <div key={title} className="rounded-lg p-3 text-sm leading-relaxed" style={{ background: bg }}>
                <b className="block text-xs mb-1" style={{ color: fg }}>
                  {title}
                </b>
                <span style={{ color: "#071B45" }}>{text}</span>
              </div>
            ))}
          <button
            type="button"
            onClick={onOpenReport}
            className="min-h-[48px] rounded-xl text-sm font-bold bg-white"
            style={{ border: "1px solid #D9DBDA", color: "#071B45", cursor: "pointer" }}
          >
            진단 전체 보기 ›
          </button>
        </>
      ) : (
        <p className="text-sm m-0 leading-relaxed" style={{ color: "#53647A" }}>
          {status === "failed"
            ? `상세 진단에 실패했어요. ${idea.errorMessage ?? "분석이 중간에 끊겼어요."}`
            : idea.latestReport?.summary ||
              "시장·고객·경쟁·수익·재무·위험 6개 분야를 외부 자료와 함께 진단하고, GO / PIVOT / VALIDATE MORE / STOP 판정을 내려요."}
        </p>
      )}

      {status !== "diagnosing" && loggedIn && (
        <div className="flex flex-col gap-1.5">
          <button
            type="button"
            onClick={onDiagnose}
            disabled={!canDiagnose}
            className="min-h-[48px] rounded-xl text-sm font-bold disabled:opacity-50"
            // 보고서가 있고 프로필이 그대로면 보조 버튼으로 (강조는 진짜 다음 할 일에만)
            style={
              dr && !idea.profileChangedSinceReport && !pendingValidationCount && status !== "failed"
                ? { background: "#fff", color: "#071B45", border: "1px solid #D9DBDA", cursor: "pointer" }
                : { background: "#134CD8", color: "#fff", border: "none", cursor: "pointer" }
            }
          >
            {status === "failed" ? "다시 분석 (유료)" : label}
          </button>
          <span className="text-xs text-center" style={{ color: "#6B7280" }}>
            {missingCount > 0
              ? "* 필수 항목을 채우면 분석할 수 있어요"
              : idea.profileChangedSinceReport
                ? "프로필이 바뀌었어요. 새 보고서를 만들 수 있어요"
                : dr && pendingValidationCount
                  ? `반영 전 검증 ${pendingValidationCount}건 — 새 보고서에 근거로 들어가요`
                : dr
                  ? "이전 보고서는 버전으로 남아요 · 3분 안팎"
                  : "보통 3분 안팎 걸려요"}
          </span>
        </div>
      )}
      {!loggedIn && (
        <Link href={`/login?next=/ideas/${idea.id}`} className="text-sm font-semibold underline" style={{ color: "#071B45" }}>
          로그인하면 고치고 분석할 수 있어요 ›
        </Link>
      )}
    </div>
  );
}

function EmptyCard({ text }: { text: string }) {
  return (
    <div className="bg-white rounded-lg shadow-card p-10 text-center text-sm" style={{ border: "1px solid #D7E0ED", color: "#6B7280" }}>
      {text}
    </div>
  );
}

function LockIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6B7280" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="4" y="11" width="16" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  );
}

/** 진단 카드 안의 작은 진행 표시 — 단계별 상태 + 진행 모달 열기 */
function DiagnosingMini({ job, startedAt, onShowProgress }: { job: AnalyzeJob | null; startedAt: string; onShowProgress?: () => void }) {
  const [, tick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => tick((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, []);
  const { percent } = progressOf(job, startedAt);
  return (
    <>
      <div>
        <div className="flex justify-between text-xs mb-1" style={{ color: "#53647A" }}>
          <span>6개 분야 진단 중</span>
          <span className="font-semibold tabular-nums">{percent}%</span>
        </div>
        <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "#D7E0ED" }}>
          <div className="h-1.5 rounded-full transition-all duration-700" style={{ width: `${percent}%`, background: "#134CD8" }} />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-1.5 text-xs text-center">
        {AGENT_ORDER.map((a) => {
          const st = job?.stages[a]?.state ?? "waiting";
          const style =
            st === "done"
              ? { background: "#EAF0FD", color: "#0F3DB0" }
              : st === "running"
                ? { background: "#fff", color: "#134CD8", boxShadow: "inset 0 0 0 1.5px #134CD8" }
                : st === "failed"
                  ? { background: "#FEF2F2", color: "#B42318" }
                  : { background: "#F5F7FB", color: "#6B7280" };
          return (
            <span key={a} className={`rounded py-1.5 font-semibold ${st === "running" ? "animate-pulse" : ""}`} style={style}>
              {st === "done" ? "✓ " : ""}
              {AGENT_LABELS[a] ?? a}
            </span>
          );
        })}
      </div>
      <p className="text-xs m-0 leading-relaxed" style={{ color: "#53647A" }}>
        다른 화면으로 가거나 창을 닫아도 계속돼요. 끝나면 알려드려요.
      </p>
      {onShowProgress && (
        <button
          type="button"
          onClick={onShowProgress}
          className="min-h-[48px] rounded-xl text-sm font-bold bg-white"
          style={{ border: "1px solid #D9DBDA", color: "#071B45", cursor: "pointer" }}
        >
          진행 상황 크게 보기
        </button>
      )}
    </>
  );
}

/** "월 매출 169만원 · 비용 112만원 · 영업이익 58만원 (34%) · 손익분기 …" → 영업이익을 요약으로, 나머지는 불렛 */
function financeBullets(summary: string) {
  const parts = summary.split(" · ").map((x) => x.trim()).filter(Boolean);
  const head = parts.find((x) => x.startsWith("영업이익")) ?? parts[0];
  return [head, ...parts.filter((x) => x !== head).map((x) => `· ${x}`)].join("\n");
}
