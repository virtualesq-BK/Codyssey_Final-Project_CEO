"use client";

import { useEffect, useMemo, useState } from "react";
import { type FinanceInputs, type FinanceScenario, calcScenarios } from "@/lib/api";
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

const FIELDS: { key: keyof FinanceInputs; label: string; unit: string; hint: string }[] = [
  { key: "price", label: "고객 1명 월 결제액", unit: "원", hint: "예: 150000" },
  { key: "customers", label: "월 결제 고객 수", unit: "명", hint: "예: 40" },
  { key: "variable_cost_per_unit", label: "고객 1명당 월 변동비", unit: "원", hint: "서버·콘텐츠·결제 수수료 등" },
  { key: "fixed_cost", label: "월 고정비", unit: "원", hint: "인건비·임대료 등" },
  { key: "acquisition_cost", label: "월 마케팅·영업비", unit: "원", hint: "고객 데려오는 데 쓰는 돈" },
  { key: "new_customers", label: "월 신규 고객 수", unit: "명", hint: "예: 8" },
  { key: "monthly_churn_rate", label: "월 이탈률", unit: "%", hint: "예: 5" },
];

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
  saved?: FinanceInputs | null;
  onSave?: (inputs: FinanceInputs) => Promise<void> | void;
}) {
  // 처음 값: 직접 넣어 둔 값 → 없으면 분석이 대화에서 뽑은 값
  const extracted = useMemo(() => {
    const inp = findingOf(report, "FinancialAgent", "inputs") as Record<string, { value?: number | null }> | null;
    const out: FinanceInputs = {};
    if (inp) for (const f of FIELDS) out[f.key] = inp[f.key]?.value ?? null;
    return out;
  }, [report]);
  const initial = saved ?? extracted;
  const [form, setForm] = useState<Record<string, string>>(() => toForm(initial));
  const [scenarios, setScenarios] = useState<FinanceScenario[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const filled = FIELDS.filter((f) => form[f.key]?.trim()).length;

  async function run(inputs: FinanceInputs, persist: boolean) {
    setBusy(true);
    setError(null);
    try {
      setScenarios(await calcScenarios(inputs));
      if (persist) await onSave?.(inputs);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  // 저장된 값이 있으면 열 때 바로 계산해 보여준다
  useEffect(() => {
    if (FIELDS.some((f) => initial[f.key] != null)) run(initial, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const base = scenarios?.find((s) => s.scenario === "base")?.metrics;
  const maxAbs = Math.max(1, ...(scenarios ?? []).flatMap((s) => [Math.abs(s.metrics.revenue ?? 0), Math.abs(s.metrics.operating_profit ?? 0)]));

  return (
    <section className={card} style={{ border: `1px solid ${line}` }} aria-label="재무 시나리오">
      <SectionHead title="재무 시나리오" sub="숫자를 넣으면 보수 · 기본 · 낙관 3가지로 매출과 이익, 손익분기를 계산해요 (AI 추정이 아니라 계산식)" badge={`입력 ${filled}/7`} />
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(fromForm(form), true);
        }}
        className="grid gap-3"
        style={{ gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))" }}
      >
        {FIELDS.map((f) => (
          <label key={f.key} className="flex flex-col gap-1 text-xs font-semibold" style={{ color: slate }}>
            {f.label}
            <span className="flex items-center rounded-lg overflow-hidden" style={{ border: `1.5px solid ${form[f.key]?.trim() ? "#C9D6F5" : line}` }}>
              <input
                inputMode="decimal"
                value={form[f.key] ?? ""}
                onChange={(e) => setForm((p) => ({ ...p, [f.key]: e.target.value.replace(/[^0-9.]/g, "") }))}
                placeholder={f.hint}
                className="flex-1 min-w-0 h-10 px-3 text-sm font-normal focus:outline-none"
                style={{ border: "none", color: navy }}
              />
              <span className="px-2.5 text-xs font-normal" style={{ color: gray }}>
                {f.unit}
              </span>
            </span>
          </label>
        ))}
        <div className="flex items-end">
          <button
            type="submit"
            disabled={busy || filled === 0}
            className="w-full min-h-[40px] rounded-lg text-sm font-bold text-white disabled:opacity-50"
            style={{ background: blue, border: "none", cursor: "pointer" }}
          >
            {busy ? "계산 중…" : "계산하기"}
          </button>
        </div>
      </form>
      {error && (
        <div className="text-sm" style={{ color: "#B42318" }}>
          {error}
        </div>
      )}

      {scenarios && (
        <>
          <div className="grid gap-3 sm:grid-cols-4">
            <Kpi label="월 매출 (기본)" value={won(base?.revenue)} />
            <Kpi label="월 영업이익 (기본)" value={won(base?.operating_profit)} tone={(base?.operating_profit ?? 0) < 0 ? "bad" : "good"} />
            <Kpi label="손익분기 고객 수" value={base?.breakeven_units != null ? `${base.breakeven_units.toLocaleString()}명` : "—"} />
            <Kpi
              label="고객 가치 / 획득 비용"
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
          {base && Object.values(base).every((v) => v === null) && (
            <p className="m-0 text-xs" style={{ color: gray }}>
              값이 더 있어야 계산돼요. 최소한 결제액 · 고객 수 · 변동비 · 고정비를 넣어 보세요.
            </p>
          )}
          <p className="m-0 text-[11px]" style={{ color: gray }}>
            보수 = 고객 수 70% · 비용 110~120%, 낙관 = 고객 수 130% · 비용 90~95%로 바꿔 계산한 일반적인 민감도예요.
          </p>
        </>
      )}
    </section>
  );
}

function toForm(i: FinanceInputs): Record<string, string> {
  const out: Record<string, string> = {};
  for (const f of FIELDS) {
    const v = i[f.key];
    out[f.key] = v == null ? "" : f.key === "monthly_churn_rate" ? String(Math.round(v * 1000) / 10) : String(v);
  }
  return out;
}

function fromForm(form: Record<string, string>): FinanceInputs {
  const out: FinanceInputs = {};
  for (const f of FIELDS) {
    const raw = form[f.key]?.trim();
    const n = raw ? Number(raw) : null;
    out[f.key] = n == null || Number.isNaN(n) ? null : f.key === "monthly_churn_rate" ? n / 100 : n;
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
