"use client";

import { useEffect, useMemo, useState } from "react";
import { type LineGroup, suggestStatement } from "@/lib/api";
import {
  type FinancePlan,
  GROUPS,
  REVENUE_TYPES,
  type RevenueType,
  SCENARIOS,
  type StatementLine,
  TYPE_ORDER,
  guessRevenueType,
  newLineId,
  totalsOf,
} from "@/lib/financePlan";
import { AGENT_LABELS, AGENT_ORDER } from "@/lib/agents";
import type { IdeaReport } from "@/lib/idea";

const blue = "#1B57EA";
const navy = "#08183F";
const slate = "#485876";
const gray = "#6B7280";
const line = "#E5E7EB";
const card = "bg-white rounded-xl p-5 flex flex-col gap-4";

type Obj = Record<string, unknown>;
type Claim = { text?: string; kind?: string };

/* ───────────── 보고서 데이터 꺼내기 ───────────── */

function findingOf(report: IdeaReport, agent: string, key: string): Obj | null {
  for (const f of report.response.workflow_result.agent_results[agent]?.findings ?? []) {
    if (f && typeof f === "object" && key in f) return (f as Obj)[key] as Obj;
  }
  return null;
}

/** 결과 안의 모든 주장(kind: fact/hypothesis)을 센다 */
function countClaims(value: unknown, acc = { fact: 0, hypothesis: 0 }) {
  if (Array.isArray(value)) value.forEach((v) => countClaims(v, acc));
  else if (value && typeof value === "object") {
    const o = value as Obj;
    if (o.kind === "fact") acc.fact += 1;
    else if (o.kind === "hypothesis") acc.hypothesis += 1;
    Object.values(o).forEach((v) => countClaims(v, acc));
  }
  return acc;
}

const textOf = (c: unknown) => ((c as Claim)?.text ?? (typeof c === "string" ? c : "")).trim();

/* ───────────── 공통 ───────────── */

function SectionHead({ title, sub, badge }: { title: string; sub?: string; badge?: string }) {
  return (
    <div className="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h4 className="m-0 text-base font-bold" style={{ color: navy }}>
          {title}
        </h4>
        {sub && (
          <p className="m-0 mt-0.5 text-xs" style={{ color: gray }}>
            {sub}
          </p>
        )}
      </div>
      {badge && (
        <span className="text-[11px] font-bold px-2 py-0.5 rounded-md" style={{ background: "#EAF0FD", color: "#1446C4" }}>
          {badge}
        </span>
      )}
    </div>
  );
}

function KindTag({ kind }: { kind?: string }) {
  if (kind !== "fact" && kind !== "hypothesis") return null;
  return kind === "fact" ? (
    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded whitespace-nowrap" style={{ background: "#E7F6EF", color: "#0F7B6C" }}>
      근거 있음
    </span>
  ) : (
    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded whitespace-nowrap" style={{ background: "#FFF6DE", color: "#8A4B08" }}>
      가설
    </span>
  );
}

/* ───────────── 1. 근거 한눈에 ───────────── */

export function EvidenceOverview({ report }: { report: IdeaReport }) {
  const wf = report.response.workflow_result;
  const [open, setOpen] = useState(false);
  const rows = AGENT_ORDER.filter((a) => wf.agent_results[a]).map((a) => {
    const r = wf.agent_results[a];
    return { agent: a, evidence: r.evidence ?? [], claims: countClaims(r.findings) };
  });
  const total = rows.reduce((s, r) => s + r.evidence.length, 0);
  const facts = rows.reduce((s, r) => s + r.claims.fact, 0);
  const hyps = rows.reduce((s, r) => s + r.claims.hypothesis, 0);
  const factPct = facts + hyps ? Math.round((facts / (facts + hyps)) * 100) : 0;
  const max = Math.max(1, ...rows.map((r) => r.evidence.length));
  // 출처 목록 (URL 기준 중복 제거)
  const sources = useMemo(() => {
    const seen = new Map<string, { title: string; source: string; url?: string | null; agents: Set<string> }>();
    rows.forEach((r) =>
      r.evidence.forEach((e) => {
        const key = e.url || `${e.source}:${e.title}`;
        const hit = seen.get(key) ?? { title: e.title, source: e.source, url: e.url, agents: new Set<string>() };
        hit.agents.add(AGENT_LABELS[r.agent] ?? r.agent);
        seen.set(key, hit);
      }),
    );
    return Array.from(seen.values());
  }, [rows]);

  return (
    <section className={card} style={{ border: `1px solid ${line}` }} aria-label="근거 한눈에 보기">
      <SectionHead title="근거 한눈에 보기" sub="이 보고서가 기대고 있는 자료와, 확인된 사실 · 가설의 비율" />
      <div className="grid gap-4 md:grid-cols-[220px_minmax(0,1fr)] items-center">
        <div className="flex md:flex-col gap-4">
          <Stat label="수집한 근거" value={`${total}건`} />
          <div className="flex-1">
            <div className="text-xs mb-1.5" style={{ color: gray }}>
              사실 {facts} · 가설 {hyps}
            </div>
            <div className="h-2.5 rounded-full overflow-hidden flex" style={{ background: "#FFF6DE" }} aria-label={`근거 있는 사실 비율 ${factPct}%`}>
              <div style={{ width: `${factPct}%`, background: "#0F7B6C" }} />
            </div>
            <div className="text-xs mt-1 font-semibold" style={{ color: "#0F7B6C" }}>
              근거 있는 사실 {factPct}%
            </div>
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          {rows.map((r) => (
            <div key={r.agent} className="grid grid-cols-[64px_minmax(0,1fr)_40px] items-center gap-2 text-xs">
              <span style={{ color: slate }}>{AGENT_LABELS[r.agent] ?? r.agent}</span>
              <div className="h-2 rounded-full" style={{ background: "#F1F3F7" }}>
                <div className="h-2 rounded-full" style={{ width: `${(r.evidence.length / max) * 100}%`, background: r.evidence.length ? blue : "transparent" }} />
              </div>
              <span className="text-right font-semibold tabular-nums" style={{ color: r.evidence.length ? navy : "#B5BAC4" }}>
                {r.evidence.length}건
              </span>
            </div>
          ))}
        </div>
      </div>
      {sources.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            className="text-sm font-semibold"
            style={{ background: "none", border: "none", color: blue, cursor: "pointer", padding: 0 }}
          >
            {open ? "▾" : "▸"} 출처 {sources.length}곳 {open ? "접기" : "보기"}
          </button>
          {open && (
            <ul className="m-0 mt-2 p-0 list-none flex flex-col divide-y" style={{ borderColor: line }}>
              {sources.map((s, i) => (
                <li key={i} className="py-2 flex items-start justify-between gap-3 text-sm">
                  <span className="min-w-0">
                    {s.url ? (
                      <a href={s.url} target="_blank" rel="noopener noreferrer" className="font-semibold" style={{ color: navy }}>
                        {s.title}
                      </a>
                    ) : (
                      <span className="font-semibold" style={{ color: navy }}>
                        {s.title}
                      </span>
                    )}
                    <span className="block text-xs" style={{ color: gray }}>
                      {s.source}
                    </span>
                  </span>
                  <span className="text-[11px] shrink-0" style={{ color: slate }}>
                    {Array.from(s.agents).join(" · ")}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs" style={{ color: gray }}>
        {label}
      </div>
      <div className="text-3xl font-bold tabular-nums leading-tight" style={{ color: navy }}>
        {value}
      </div>
    </div>
  );
}

/* ───────────── 2. 리스크 지도 ───────────── */

interface Risk {
  label: string;
  risk: string;
  likelihood: number;
  impact: number;
  score: number;
  level: string;
  mitigation?: string;
}

export function risksOf(report: IdeaReport): Risk[] {
  const f = report.response.workflow_result.agent_results.RiskAgent?.findings ?? [];
  for (const x of f) {
    const risks = (x as Obj)?.risks;
    if (Array.isArray(risks)) return (risks as Risk[]).filter((r) => r.likelihood && r.impact).sort((a, b) => b.score - a.score);
  }
  return [];
}

const zone = (score: number) => (score >= 15 ? "#FDE2DF" : score >= 8 ? "#FFF1D6" : "#E7F6EF");
const dotColor = (score: number) => (score >= 15 ? "#C2341C" : score >= 8 ? "#C27A0E" : "#0F7B6C");

/** 5×5 리스크 지도 — 세로 영향, 가로 가능성. 점 번호 = 점수 순위 */
export function RiskMatrix({ risks, size = "lg" }: { risks: Risk[]; size?: "sm" | "lg" }) {
  const cell = size === "sm" ? 26 : 52;
  const byCell = new Map<string, number[]>();
  risks.forEach((r, i) => {
    const k = `${r.likelihood}-${r.impact}`;
    byCell.set(k, [...(byCell.get(k) ?? []), i + 1]);
  });
  return (
    <div className="flex gap-2 items-stretch" role="img" aria-label={`리스크 지도: 위험 ${risks.length}개, 최고 점수 ${risks[0]?.score ?? 0}`}>
      <div>
        {size === "lg" && (
          <div className="text-[11px] font-semibold mb-1.5" style={{ color: gray }}>
            ↑ 영향
          </div>
        )}
        <div className="grid" style={{ gridTemplateColumns: `repeat(5, ${cell}px)`, gap: 3 }}>
          {[5, 4, 3, 2, 1].map((impact) =>
            [1, 2, 3, 4, 5].map((lik) => {
              const nums = byCell.get(`${lik}-${impact}`) ?? [];
              return (
                <div
                  key={`${lik}-${impact}`}
                  className="rounded-md flex items-center justify-center flex-wrap gap-0.5"
                  style={{ width: cell, height: cell, background: zone(lik * impact) }}
                >
                  {nums.slice(0, size === "sm" ? 1 : 4).map((n) => (
                    <span
                      key={n}
                      className="rounded-full flex items-center justify-center font-bold text-white"
                      style={{
                        width: size === "sm" ? 14 : 20,
                        height: size === "sm" ? 14 : 20,
                        fontSize: size === "sm" ? 8 : 11,
                        background: dotColor(lik * impact),
                      }}
                    >
                      {n}
                    </span>
                  ))}
                </div>
              );
            }),
          )}
        </div>
        {size === "lg" && (
          <div className="text-[11px] font-semibold text-center mt-1.5" style={{ color: gray }}>
            일어날 가능성 →
          </div>
        )}
      </div>
    </div>
  );
}

export function RiskPanel({ report, embedded }: { report: IdeaReport; embedded?: boolean }) {
  const risks = risksOf(report);
  if (!risks.length) return null;
  const high = risks.filter((r) => r.score >= 15).length;
  return (
    <section className={embedded ? "flex flex-col gap-4" : card} style={embedded ? undefined : { border: `1px solid ${line}` }} aria-label="리스크 지도">
      {!embedded && <SectionHead title="리스크 지도" sub="가능성(1~5) × 영향(1~5) = 점수. 오른쪽 위로 갈수록 먼저 대비할 위험" badge={`높음 ${high} · 전체 ${risks.length}`} />}
      <div className="grid gap-5 lg:grid-cols-[auto_minmax(0,1fr)] items-start">
        <RiskMatrix risks={risks} />
        <ol className="m-0 p-0 list-none flex flex-col gap-2.5">
          {risks.slice(0, 4).map((r, i) => (
            <li key={i} className="rounded-lg p-3 flex gap-3" style={{ background: "#FAFBFD", border: `1px solid ${line}` }}>
              <span className="w-6 h-6 rounded-full shrink-0 flex items-center justify-center text-xs font-bold text-white" style={{ background: dotColor(r.score) }}>
                {i + 1}
              </span>
              <div className="min-w-0 flex flex-col gap-1">
                <div className="text-sm font-semibold leading-snug" style={{ color: navy }}>
                  {r.risk || r.label}
                </div>
                <div className="text-[11px]" style={{ color: gray }}>
                  {r.label} · 가능성 {r.likelihood} × 영향 {r.impact} = <b style={{ color: dotColor(r.score) }}>{r.score}</b>
                </div>
                {r.mitigation && (
                  <div className="text-xs leading-relaxed" style={{ color: slate }}>
                    <b style={{ color: "#0F7B6C" }}>대응</b> {r.mitigation}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

/* ───────────── 3. 경쟁 ───────────── */

export function CompetitionPanel({ report, embedded }: { report: IdeaReport; embedded?: boolean }) {
  const c = findingOf(report, "CompetitorAgent", "competition_analysis");
  if (!c) return null;
  const competitors: (Obj & { kind: string })[] = [
    ...((c.direct_competitors as Obj[]) ?? []).map((x) => ({ ...x, kind: "직접" })),
    ...((c.indirect_competitors as Obj[]) ?? []).map((x) => ({ ...x, kind: "간접" })),
  ];
  const diff = (c.differentiation as unknown[]) ?? [];
  const barriers = (c.entry_barriers as unknown[]) ?? [];
  const position = c.competitive_position as Claim | undefined;
  return (
    <section className={embedded ? "flex flex-col gap-4" : card} style={embedded ? undefined : { border: `1px solid ${line}` }} aria-label="경쟁 구도">
      {!embedded && <SectionHead title="경쟁 구도" sub="같은 문제를 푸는 서비스와 우리가 설 자리" badge={`경쟁사 ${competitors.length}`} />}
      {position?.text && (
        <div className="rounded-lg px-4 py-3 text-sm leading-relaxed flex gap-2 items-start" style={{ background: "#EAF0FD", color: navy }}>
          <span className="font-bold shrink-0" style={{ color: "#1446C4" }}>
            우리 자리
          </span>
          <span className="min-w-0">
            {position.text} <KindTag kind={position.kind} />
          </span>
        </div>
      )}
      {competitors.length > 0 && (
        <div className="grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
          {competitors.map((x, i) => (
            <div key={i} className="rounded-lg p-4 flex flex-col gap-2" style={{ border: `1px solid ${line}` }}>
              <div className="flex items-center justify-between gap-2">
                <b className="text-sm" style={{ color: navy }}>
                  {String(x.name ?? "")}
                </b>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ background: "#F3F4F6", color: slate }}>
                  {x.kind} 경쟁
                </span>
              </div>
              <p className="m-0 text-xs leading-relaxed line-clamp-3" style={{ color: slate }}>
                {textOf(x.description)}
              </p>
              {((x.strengths as unknown[]) ?? []).slice(0, 2).map((s, j) => (
                <div key={`s${j}`} className="text-xs flex gap-1.5" style={{ color: navy }}>
                  <span style={{ color: "#0F7B6C" }}>＋</span>
                  <span className="min-w-0">{textOf(s)}</span>
                </div>
              ))}
              {((x.weaknesses as unknown[]) ?? []).slice(0, 2).map((s, j) => (
                <div key={`w${j}`} className="text-xs flex gap-1.5" style={{ color: navy }}>
                  <span style={{ color: "#C2341C" }}>－</span>
                  <span className="min-w-0">{textOf(s)}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {diff.length > 0 && (
          <div>
            <div className="text-xs font-bold mb-2" style={{ color: "#0F7B6C" }}>
              우리 차별점
            </div>
            <ul className="m-0 p-0 list-none flex flex-col gap-1.5 text-sm">
              {diff.map((d, i) => (
                <li key={i} className="flex gap-2 items-start" style={{ color: navy }}>
                  <span style={{ color: "#0F7B6C" }}>✓</span>
                  <span className="min-w-0 leading-snug">
                    {textOf(d)} <KindTag kind={(d as Claim)?.kind} />
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {barriers.length > 0 && (
          <div>
            <div className="text-xs font-bold mb-2" style={{ color: "#8A4B08" }}>
              진입장벽
            </div>
            <ul className="m-0 p-0 list-none flex flex-col gap-1.5 text-sm">
              {barriers.map((d, i) => (
                <li key={i} className="flex gap-2 items-start" style={{ color: navy }}>
                  <span style={{ color: "#C27A0E" }}>▲</span>
                  <span className="min-w-0 leading-snug">{textOf(d)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

/* ───────────── 4. 월 손익계산서 ───────────── */

export const won = (v: number | null | undefined) => {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const abs = Math.abs(v);
  const s = abs >= 1e8 ? `${(abs / 1e8).toFixed(1)}억` : abs >= 1e4 ? `${Math.round(abs / 1e4).toLocaleString()}만` : Math.round(abs).toLocaleString();
  return `${v < 0 ? "-" : ""}${s}원`;
};

/** 예시 항목 요청에 넘길 보고서 요약 — 시장·경쟁·수익 요약과 근거 몇 줄 */
function reportContext(report: IdeaReport): string {
  const ar = report.response.workflow_result.agent_results;
  const sums = ["MarketAgent", "CompetitorAgent", "BusinessModelAgent"].map((a) => (ar[a]?.summary ?? "").slice(0, 400));
  const ev = ["CompetitorAgent", "BusinessModelAgent", "MarketAgent"].flatMap((a) => ar[a]?.evidence ?? []).slice(0, 10).map((e) => `- ${e.content.slice(0, 220)}`);
  return [...sums, ...ev].filter(Boolean).join("\n").slice(0, 5500);
}

export function FinancePanel({
  report,
  saved,
  onSave,
  embedded,
}: {
  report: IdeaReport;
  saved?: FinancePlan | null;
  onSave?: (plan: FinancePlan) => Promise<void> | void;
  embedded?: boolean;
}) {
  const guessed = guessRevenueType(report.profile?.revenueModel ?? "");
  // 예전 형식(칸 7개)으로 저장된 값은 손익계산서로 다시 만든다
  const valid = saved && Array.isArray(saved.lines) ? saved : null;
  const [plan, setPlan] = useState<FinancePlan | null>(valid);
  const [type, setType] = useState<RevenueType>(valid?.type ?? guessed);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  async function generate(t: RevenueType) {
    setLoading(true);
    setError(null);
    try {
      const d = REVENUE_TYPES[t];
      const res = await suggestStatement({
        revenue_type: `${d.label} (${d.desc})`,
        idea: {
          name: report.profile?.name ?? "",
          industry: report.profile?.industry ?? "",
          customer: report.profile?.customer ?? "",
          problem: report.profile?.problem ?? "",
          solution: report.profile?.solution ?? "",
          revenue_model: report.profile?.revenueModel ?? "",
        },
        context: reportContext(report),
      });
      const next: FinancePlan = {
        type: t,
        unitLabel: res.unit_label || "고객",
        unitCount: res.unit_count || 0,
        lines: res.lines.map((l) => ({ id: newLineId(), group: l.group, label: l.label, amount: Math.round(l.amount), basis: l.basis, ai: true })),
      };
      setPlan(next);
      setDirty(false);
      await onSave?.(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  // 처음 열 때 저장된 손익표가 없으면 AI가 업종에 맞는 항목을 만든다
  useEffect(() => {
    if (!valid) generate(type);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 고친 내용은 1초 뒤 저장
  useEffect(() => {
    if (!plan || !dirty) return;
    const t = setTimeout(() => {
      onSave?.(plan);
      setDirty(false);
    }, 1000);
    return () => clearTimeout(t);
  }, [plan, dirty, onSave]);

  const edit = (fn: (p: FinancePlan) => FinancePlan) => {
    setPlan((p) => (p ? fn(p) : p));
    setDirty(true);
  };
  const setLine = (id: string, patch: Partial<StatementLine>) =>
    edit((p) => ({ ...p, lines: p.lines.map((l) => (l.id === id ? { ...l, ...patch, ai: false } : l)) }));
  const removeLine = (id: string) => edit((p) => ({ ...p, lines: p.lines.filter((l) => l.id !== id) }));
  const addLine = (group: LineGroup) => edit((p) => ({ ...p, lines: [...p.lines, { id: newLineId(), group, label: "", amount: 0 }] }));

  const t = plan ? totalsOf(plan.lines, plan.unitCount) : null;

  return (
    <section className={embedded ? "flex flex-col gap-4" : card} style={embedded ? undefined : { border: `1px solid ${line}` }} aria-label="월 손익계산서">
      {embedded ? (
        <b className="text-sm" style={{ color: navy }}>
          월 손익계산서 <span className="font-normal text-xs" style={{ color: gray }}>출시 6~12개월 차 한 달 기준</span>
        </b>
      ) : (
        <SectionHead title="월 손익계산서" sub="출시 6~12개월 차 한 달 기준" />
      )}

      <div role="radiogroup" aria-label="수익 방식" className="flex gap-2 flex-wrap items-center">
        <span className="text-xs font-semibold mr-1" style={{ color: slate }}>
          수익 방식
        </span>
        {TYPE_ORDER.map((k) => {
          const on = k === type;
          return (
            <button
              key={k}
              type="button"
              role="radio"
              aria-checked={on}
              title={REVENUE_TYPES[k].desc}
              onClick={() => {
                if (on || loading) return;
                setType(k);
                generate(k);
              }}
              className="px-3 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1"
              style={{ border: `1.5px solid ${on ? blue : line}`, background: on ? "#EAF0FD" : "#fff", color: on ? "#1446C4" : slate, cursor: "pointer" }}
            >
              {REVENUE_TYPES[k].label}
              {k === guessed && <span style={{ color: "#C27A0E" }}>·추천</span>}
            </button>
          );
        })}
        <button
          type="button"
          onClick={() => generate(type)}
          disabled={loading}
          className="ml-auto text-xs font-semibold disabled:opacity-50"
          style={{ background: "none", border: "none", color: blue, cursor: "pointer", padding: 0 }}
        >
          ↻ AI로 항목 다시 만들기
        </button>
      </div>

      {loading && (
        <div className="rounded-lg px-4 py-6 text-sm text-center animate-pulse" style={{ background: "#F5F7FC", color: blue }}>
          AI가 &lsquo;{report.profile?.name || "이 아이템"}&rsquo;에 맞는 매출·비용 항목과 예시 금액을 만드는 중…
        </div>
      )}
      {error && (
        <div className="text-sm" style={{ color: "#B42318" }}>
          {error}
        </div>
      )}

      {plan && t && !loading && (
        <>
          <div className="grid gap-3 sm:grid-cols-4">
            <Kpi label="월 매출" value={won(t.revenue)} />
            <Kpi label="월 비용 (원가 + 판관비)" value={won(t.cogs + t.opex)} />
            <Kpi
              label={`영업이익${t.margin != null ? ` (${Math.round(t.margin * 100)}%)` : ""}`}
              value={won(t.operating)}
              tone={t.operating < 0 ? "bad" : "good"}
            />
            <Kpi
              label="손익분기"
              value={t.breakevenRevenue != null ? `월 ${won(t.breakevenRevenue)}` : "—"}
              sub={t.breakevenUnits != null ? `${plan.unitLabel} ${t.breakevenUnits.toLocaleString()} 필요 (지금 ${plan.unitCount.toLocaleString()})` : undefined}
            />
          </div>

          <div className="grid gap-3 lg:grid-cols-3">
            {GROUPS.map((g) => {
              const rows = plan.lines.filter((l) => l.group === g.key);
              const subtotal = g.key === "revenue" ? t.revenue : g.key === "cogs" ? t.cogs : t.opex;
              const tone = g.key === "revenue" ? blue : "#C2341C";
              return (
                <div key={g.key} className="rounded-xl p-4 flex flex-col gap-2.5" style={{ background: "#FAFBFD", border: `1px solid ${line}` }}>
                  <div className="flex items-baseline justify-between gap-2">
                    <b className="text-sm" style={{ color: tone }}>
                      {g.key === "revenue" ? "＋ " : "－ "}
                      {g.label}
                    </b>
                    <span className="text-sm font-bold tabular-nums" style={{ color: navy }}>
                      {won(subtotal)}
                    </span>
                  </div>
                  {rows.map((l) => (
                    <div key={l.id} className="flex flex-col gap-1 rounded-lg bg-white p-2.5" style={{ border: `1px solid ${line}` }}>
                      <div className="flex items-center gap-1.5">
                        <input
                          value={l.label}
                          onChange={(e) => setLine(l.id, { label: e.target.value })}
                          placeholder="항목 이름"
                          aria-label={`${g.label} 항목 이름`}
                          className="flex-1 min-w-0 text-[13px] font-semibold focus:outline-none bg-transparent"
                          style={{ border: "none", color: navy }}
                        />
                        <button
                          type="button"
                          onClick={() => removeLine(l.id)}
                          aria-label={`${l.label || "항목"} 삭제`}
                          className="w-6 h-6 shrink-0 rounded"
                          style={{ background: "none", border: "none", color: gray, cursor: "pointer" }}
                        >
                          ×
                        </button>
                      </div>
                      <label className="flex items-center rounded-md overflow-hidden" style={{ border: `1px solid ${line}` }} title={l.basis || undefined}>
                        <span className="sr-only">{l.label} 월 금액</span>
                        <input
                          inputMode="numeric"
                          value={l.amount ? l.amount.toLocaleString() : ""}
                          onChange={(e) => setLine(l.id, { amount: Number(e.target.value.replace(/[^0-9]/g, "")) || 0 })}
                          placeholder="0"
                          className="flex-1 min-w-0 h-8 px-2 text-sm text-right tabular-nums focus:outline-none"
                          style={{ border: "none", color: navy }}
                        />
                        <span className="px-2 text-xs" style={{ color: gray }}>
                          원/월
                        </span>
                      </label>
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={() => addLine(g.key)}
                    className="min-h-[32px] rounded-lg text-xs font-semibold"
                    style={{ border: `1px dashed #C9D0DC`, background: "transparent", color: slate, cursor: "pointer" }}
                  >
                    + 항목 추가
                  </button>
                </div>
              );
            })}
          </div>

          <div className="rounded-xl overflow-hidden" style={{ border: `1px solid ${line}` }}>
            <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
              <caption className="sr-only">시나리오별 손익</caption>
              <thead>
                <tr style={{ background: "#F5F7FC", color: slate }}>
                  <th className="text-left font-semibold px-3 py-2 text-xs">시나리오</th>
                  <th className="text-right font-semibold px-3 py-2 text-xs">매출</th>
                  <th className="text-right font-semibold px-3 py-2 text-xs">매출총이익</th>
                  <th className="text-right font-semibold px-3 py-2 text-xs">영업이익</th>
                </tr>
              </thead>
              <tbody>
                {SCENARIOS.map((sc) => {
                  const x = totalsOf(plan.lines, plan.unitCount, sc.factor);
                  return (
                    <tr key={sc.key} style={{ borderTop: `1px solid ${line}`, fontWeight: sc.key === "base" ? 700 : 400 }}>
                      <td className="px-3 py-2">
                        <span style={{ color: sc.key === "base" ? blue : navy }} title={sc.desc}>
                          {sc.label}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums">{won(x.revenue)}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{won(x.gross)}</td>
                      <td className="px-3 py-2 text-right tabular-nums" style={{ color: x.operating < 0 ? "#C2341C" : "#0F7B6C" }}>
                        {won(x.operating)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}

function Kpi({ label, value, tone, sub }: { label: string; value: string; tone?: "good" | "bad"; sub?: string }) {
  return (
    <div className="rounded-lg p-3" style={{ background: "#F5F7FC" }}>
      <div className="text-[11px]" style={{ color: gray }}>
        {label}
      </div>
      <div className="text-lg font-bold tabular-nums" style={{ color: tone === "bad" ? "#C2341C" : tone === "good" ? "#0F7B6C" : navy }}>
        {value}
      </div>
      {sub && (
        <div className="text-[11px] mt-0.5" style={{ color: slate }}>
          {sub}
        </div>
      )}
    </div>
  );
}

