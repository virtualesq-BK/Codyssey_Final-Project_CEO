"use client";

import { useEffect, useMemo, useState } from "react";
import { type FinanceInputs, type FinanceScenario, calcScenarios, estimateFinance } from "@/lib/api";
import {
  type FinancePlan,
  type PlanField,
  REVENUE_TYPES,
  type RevenueType,
  TYPE_ORDER,
  guessRevenueType,
  planFromExtracted,
  toCalculatorInputs,
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

export function RiskPanel({ report }: { report: IdeaReport }) {
  const risks = risksOf(report);
  if (!risks.length) return null;
  const high = risks.filter((r) => r.score >= 15).length;
  return (
    <section className={card} style={{ border: `1px solid ${line}` }} aria-label="리스크 지도">
      <SectionHead title="리스크 지도" sub="가능성(1~5) × 영향(1~5) = 점수. 오른쪽 위로 갈수록 먼저 대비할 위험" badge={`높음 ${high} · 전체 ${risks.length}`} />
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

export function CompetitionPanel({ report }: { report: IdeaReport }) {
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
    <section className={card} style={{ border: `1px solid ${line}` }} aria-label="경쟁 구도">
      <SectionHead title="경쟁 구도" sub="같은 문제를 푸는 서비스와 우리가 설 자리" badge={`경쟁사 ${competitors.length}`} />
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

/* ───────────── 4. 재무 시나리오 ───────────── */

const won = (v: number | null | undefined) => {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const abs = Math.abs(v);
  const s = abs >= 1e8 ? `${(abs / 1e8).toFixed(1)}억` : abs >= 1e4 ? `${Math.round(abs / 1e4).toLocaleString()}만` : Math.round(abs).toLocaleString();
  return `${v < 0 ? "-" : ""}${s}원`;
};

const SCEN = { conservative: "보수", base: "기본", optimistic: "낙관" } as const;

export function FinancePanel({
  report,
  saved,
  onSave,
}: {
  report: IdeaReport;
  saved?: FinancePlan | null;
  onSave?: (plan: FinancePlan) => Promise<void> | void;
}) {
  // 분석이 대화에서 뽑아 둔 계산기 값
  const extracted = useMemo(() => {
    const inp = findingOf(report, "FinancialAgent", "inputs") as Record<string, { value?: number | null }> | null;
    const out: FinanceInputs = {};
    if (inp) for (const k of Object.keys(inp)) (out as Record<string, number | null>)[k] = inp[k]?.value ?? null;
    return out;
  }, [report]);
  const guessed = guessRevenueType(report.profile?.revenueModel ?? "");
  const initial = saved ?? planFromExtracted(guessed, extracted);

  const [type, setType] = useState<RevenueType>(initial.type);
  // 유형마다 입력·AI 예시 표시·근거를 따로 기억해 둔다 (유형을 바꿨다 돌아와도 남게)
  const [forms, setForms] = useState<Partial<Record<RevenueType, Record<string, string>>>>(() =>
    saved ? { [initial.type]: toForm(initial.values) } : {},
  );
  const [aiKeys, setAiKeys] = useState<Partial<Record<RevenueType, string[]>>>(() => (saved?.aiKeys ? { [saved.type]: saved.aiKeys } : {}));
  const [basis, setBasis] = useState<Partial<Record<RevenueType, Record<string, string>>>>(() => (saved?.basis ? { [saved.type]: saved.basis } : {}));
  const [estimating, setEstimating] = useState<RevenueType | null>(null);
  const def = REVENUE_TYPES[type];
  const form = forms[type] ?? toForm(planFromExtracted(type, extracted).values);
  const ai = aiKeys[type] ?? [];
  const setField = (k: string, v: string) => {
    setForms((p) => ({ ...p, [type]: { ...form, [k]: v.replace(/[^0-9.]/g, "") } }));
    // 직접 고친 칸은 더 이상 AI 예시가 아니다
    setAiKeys((p) => ({ ...p, [type]: (p[type] ?? []).filter((x) => x !== k) }));
  };
  const planOf = (t: RevenueType, f: Record<string, string>): FinancePlan => ({
    type: t,
    values: fromForm(REVENUE_TYPES[t].fields, f),
    aiKeys: aiKeys[t] ?? [],
    basis: basis[t] ?? {},
  });
  const [scenarios, setScenarios] = useState<FinanceScenario[] | null>(null);
  const [calcType, setCalcType] = useState<RevenueType>(initial.type);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const required = def.fields.filter((f) => !f.optional);
  const filled = def.fields.filter((f) => form[f.key]?.trim()).length;

  async function run(plan: FinancePlan, persist: boolean) {
    setBusy(true);
    setError(null);
    try {
      setScenarios(await calcScenarios(toCalculatorInputs(plan)));
      setCalcType(plan.type);
      if (persist) await onSave?.(plan);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  /** AI가 이 아이템에 맞는 예시 수치를 채운다 → 바로 계산 (저장도 해서 다음엔 다시 부르지 않음) */
  async function fillExample(t: RevenueType) {
    setEstimating(t);
    setError(null);
    try {
      const d = REVENUE_TYPES[t];
      const est = await estimateFinance({
        revenue_type: `${d.label} (${d.desc})`,
        fields: d.fields.map((f) => ({ key: f.key, label: f.label, unit: f.unit })),
        idea: {
          name: report.profile?.name ?? "",
          customer: report.profile?.customer ?? "",
          problem: report.profile?.problem ?? "",
          solution: report.profile?.solution ?? "",
          revenue_model: report.profile?.revenueModel ?? "",
          industry: report.profile?.industry ?? "",
        },
        context: reportContext(report),
      });
      const values: Record<string, string> = {};
      const why: Record<string, string> = {};
      for (const e of est) {
        if (e.value == null) continue;
        values[e.key] = String(Math.round(e.value * 100) / 100);
        why[e.key] = e.basis;
      }
      const keys = Object.keys(values);
      setForms((p) => ({ ...p, [t]: values }));
      setAiKeys((p) => ({ ...p, [t]: keys }));
      setBasis((p) => ({ ...p, [t]: why }));
      const plan: FinancePlan = { type: t, values: fromForm(d.fields, values), aiKeys: keys, basis: why };
      await run(plan, true);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setEstimating(null);
    }
  }

  // 처음 열 때: 저장된 값이 있으면 그걸로 계산, 없으면 AI 예시 수치를 채운다
  useEffect(() => {
    if (saved && Object.values(saved.values).some((v) => v != null)) run(saved, false);
    else fillExample(initial.type);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function pickType(t: RevenueType) {
    setType(t);
    // 처음 고른 유형이면 그 유형의 예시 수치도 채운다
    if (!forms[t] && estimating !== t) fillExample(t);
    else if (forms[t]) run(planOf(t, forms[t]!), true);
  }

  const base = scenarios?.find((s) => s.scenario === "base")?.metrics;
  const maxAbs = Math.max(1, ...(scenarios ?? []).flatMap((s) => [Math.abs(s.metrics.revenue ?? 0), Math.abs(s.metrics.operating_profit ?? 0)]));
  const calcDef = REVENUE_TYPES[calcType];

  return (
    <section className={card} style={{ border: `1px solid ${line}` }} aria-label="재무 시나리오">
      <SectionHead title="재무 시나리오" sub="수익 방식을 고르고 숫자를 넣으면 보수 · 기본 · 낙관 3가지로 계산해요 (AI 추정이 아니라 계산식)" badge={`입력 ${filled}/${def.fields.length}`} />

      <div role="radiogroup" aria-label="수익 방식" className="grid gap-2" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))" }}>
        {TYPE_ORDER.map((t) => {
          const d = REVENUE_TYPES[t];
          const on = t === type;
          return (
            <button
              key={t}
              type="button"
              role="radio"
              aria-checked={on}
              onClick={() => pickType(t)}
              className="rounded-lg px-3 py-2.5 text-left flex flex-col gap-0.5"
              style={{ border: `1.5px solid ${on ? blue : line}`, background: on ? "#EAF0FD" : "#fff", cursor: "pointer" }}
            >
              <span className="text-sm font-bold flex items-center gap-1.5" style={{ color: on ? "#1446C4" : navy }}>
                {d.label}
                {t === guessed && !saved && (
                  <span className="text-[10px] font-semibold px-1 rounded" style={{ background: "#FFF6DE", color: "#8A4B08" }}>
                    추천
                  </span>
                )}
              </span>
              <span className="text-[11px]" style={{ color: gray }}>
                {d.desc}
              </span>
            </button>
          );
        })}
      </div>

      {!saved && report.profile?.revenueModel && (
        <p className="m-0 -mt-1 text-xs leading-relaxed" style={{ color: slate }}>
          프로필의 수익 모델 &lsquo;{report.profile.revenueModel.split("\n")[0].slice(0, 40)}&rsquo;을 보고{" "}
          <b style={{ color: "#1446C4" }}>{REVENUE_TYPES[guessed].label}</b>으로 골라 뒀어요. 다르면 바꿔 주세요.
        </p>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(planOf(type, form), true);
        }}
        className="grid gap-3"
        style={{ gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))" }}
      >
        {def.fields.map((f) => (
          <label key={`${type}-${f.key}`} className="flex flex-col gap-1 text-xs font-semibold" style={{ color: slate }}>
            <span className="flex items-center gap-1.5">
              {f.label}
              {f.optional && (
                <span className="font-normal" style={{ color: gray }}>
                  (선택)
                </span>
              )}
              {ai.includes(f.key) && (
                <span className="text-[10px] font-bold px-1 rounded" style={{ background: "#FFF6DE", color: "#8A4B08" }} title={basis[type]?.[f.key]}>
                  AI 예시
                </span>
              )}
            </span>
            <span className="flex items-center rounded-lg overflow-hidden bg-white" style={{ border: `1.5px solid ${form[f.key]?.trim() ? "#C9D6F5" : line}` }}>
              <input
                inputMode="decimal"
                value={form[f.key] ?? ""}
                onChange={(e) => setField(f.key, e.target.value)}
                placeholder={f.hint}
                className="flex-1 min-w-0 h-10 px-3 text-sm font-normal focus:outline-none"
                style={{ border: "none", color: navy }}
              />
              <span className="px-2.5 text-xs font-normal" style={{ color: gray }}>
                {f.unit}
              </span>
            </span>
            {ai.includes(f.key) && basis[type]?.[f.key] && (
              <span className="text-[11px] font-normal leading-snug" style={{ color: gray }}>
                {basis[type]![f.key]}
              </span>
            )}
          </label>
        ))}
        <div className="flex items-end">
          <button
            type="submit"
            disabled={busy || filled === 0}
            className="w-full min-h-[40px] rounded-lg text-sm font-bold text-white disabled:opacity-50"
            style={{ background: blue, border: "none", cursor: "pointer" }}
          >
            {busy ? "계산 중…" : "다시 계산하기"}
          </button>
        </div>
      </form>
      <div className="flex items-center gap-3 flex-wrap -mt-1">
        {estimating === type ? (
          <span className="text-xs animate-pulse" style={{ color: blue }}>
            AI가 이 아이템에 맞는 예시 수치를 채우는 중…
          </span>
        ) : (
          <>
            {ai.length > 0 && (
              <span className="text-xs" style={{ color: slate }}>
                <b style={{ color: "#8A4B08" }}>AI 예시</b> 칸은 시장·경쟁 근거로 잡은 출발점이에요. 아는 숫자로 고치면 &lsquo;직접 입력&rsquo;이 돼요.
              </span>
            )}
            <button
              type="button"
              onClick={() => fillExample(type)}
              className="text-xs font-semibold"
              style={{ background: "none", border: "none", color: blue, cursor: "pointer", padding: 0 }}
            >
              ↻ AI 예시값 다시 채우기
            </button>
          </>
        )}
      </div>
      {error && (
        <div className="text-sm" style={{ color: "#B42318" }}>
          {error}
        </div>
      )}

      {scenarios && (
        <>
          <div className="grid gap-3 sm:grid-cols-4">
            <Kpi label="월 매출 (기본)" value={won(base?.revenue)} />
            <Kpi label="월 영업이익 (기본)" value={won(base?.operating_profit)} tone={base?.operating_profit == null ? undefined : base.operating_profit < 0 ? "bad" : "good"} />
            <Kpi label={`손익분기 ${calcDef.unitNoun} 수`} value={base?.breakeven_units != null ? `${base.breakeven_units.toLocaleString()}` : "—"} />
            <Kpi
              label={`${calcDef.unitNoun} 가치 / 획득 비용`}
              value={base?.ltv_cac_ratio != null ? `${base.ltv_cac_ratio.toFixed(1)}배` : "—"}
              tone={base?.ltv_cac_ratio == null ? undefined : base.ltv_cac_ratio >= 3 ? "good" : "bad"}
            />
          </div>
          <div className="flex flex-col gap-3" aria-label="시나리오별 매출과 영업이익">
            {scenarios.map((s) => (
              <div key={s.scenario} className="grid grid-cols-[44px_minmax(0,1fr)] gap-3 items-center">
                <span className="text-xs font-bold" style={{ color: s.scenario === "base" ? blue : slate }}>
                  {SCEN[s.scenario]}
                </span>
                <div className="flex flex-col gap-1">
                  <Bar value={s.metrics.revenue} max={maxAbs} color="#9DB8F5" label={`매출 ${won(s.metrics.revenue)}`} />
                  <Bar
                    value={s.metrics.operating_profit}
                    max={maxAbs}
                    color={(s.metrics.operating_profit ?? 0) < 0 ? "#E5735C" : blue}
                    label={`영업이익 ${won(s.metrics.operating_profit)}`}
                  />
                </div>
              </div>
            ))}
          </div>
          {base?.unit_contribution != null && base.unit_contribution <= 0 && (
            <p className="m-0 text-xs rounded-lg px-3 py-2" style={{ background: "#FDECEA", color: "#B42318" }}>
              {calcDef.unitNoun} 1단위당 비용이 매출보다 커서 팔수록 손해인 구조예요. 그래서 손익분기가 없어요. 가격을 올리거나 단위당 비용을 줄여 보세요.
            </p>
          )}
          {base && base.revenue == null && (
            <p className="m-0 text-xs" style={{ color: gray }}>
              값이 더 있어야 계산돼요. {required.slice(0, 3).map((f) => f.label).join(" · ")}부터 넣어 보세요.
            </p>
          )}
          <p className="m-0 text-[11px] leading-relaxed" style={{ color: gray }}>
            {calcDef.label}: {calcDef.note} 보수 = {calcDef.unitNoun} 수 70% · 비용 110~120%, 낙관 = {calcDef.unitNoun} 수 130% · 비용 90~95%로 바꾼 일반적인 민감도예요.
          </p>
        </>
      )}
    </section>
  );
}

/** 예시 수치 추정에 넘길 보고서 요약 — 시장·경쟁·수익 요약과 근거 몇 줄 */
function reportContext(report: IdeaReport): string {
  const ar = report.response.workflow_result.agent_results;
  const sums = ["MarketAgent", "CompetitorAgent", "BusinessModelAgent"].map((a) => (ar[a]?.summary ?? "").slice(0, 400));
  const ev = ["CompetitorAgent", "BusinessModelAgent", "MarketAgent"].flatMap((a) => ar[a]?.evidence ?? []).slice(0, 10).map((e) => `- ${e.content.slice(0, 220)}`);
  return [...sums, ...ev].filter(Boolean).join("\n").slice(0, 5500);
}

function toForm(values: Record<string, number | null>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(values)) out[k] = v == null ? "" : String(Math.round(v * 1000) / 1000);
  return out;
}

function fromForm(fields: PlanField[], form: Record<string, string>): Record<string, number | null> {
  const out: Record<string, number | null> = {};
  for (const f of fields) {
    const raw = form[f.key]?.trim();
    const v = raw ? Number(raw) : null;
    out[f.key] = v == null || Number.isNaN(v) ? null : v;
  }
  return out;
}

function Kpi({ label, value, tone }: { label: string; value: string; tone?: "good" | "bad" }) {
  return (
    <div className="rounded-lg p-3" style={{ background: "#F5F7FC" }}>
      <div className="text-[11px]" style={{ color: gray }}>
        {label}
      </div>
      <div className="text-lg font-bold tabular-nums" style={{ color: tone === "bad" ? "#C2341C" : tone === "good" ? "#0F7B6C" : navy }}>
        {value}
      </div>
    </div>
  );
}

function Bar({ value, max, color, label }: { value: number | null | undefined; max: number; color: string; label: string }) {
  const pct = value == null ? 0 : Math.max(2, (Math.abs(value) / max) * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="h-3.5 rounded" style={{ width: `${pct * 0.7}%`, background: value == null ? "#EEF0F4" : color, minWidth: 4 }} />
      <span className="text-[11px] whitespace-nowrap tabular-nums" style={{ color: slate }}>
        {label}
      </span>
    </div>
  );
}
