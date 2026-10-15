"use client";

import { useEffect, useRef, useState } from "react";
import AgentResultCard from "@/components/AgentResultCard";
import DecisionBanner from "@/components/DecisionBanner";
import { AreaScores, CompetitionPanel, EvidenceOverview, FinancePanel, MarketPanel, RiskPanel } from "@/components/ReportVisuals";
import type { AgentResult, AreaScore, MarketSizing } from "@/lib/api";
import { type FinancePlan, financeConfidence, financeSummary } from "@/lib/financePlan";
import type { IdeaReport } from "@/lib/idea";

/** 상세 진단 보고서 한 버전 — 판정 요약 → 시장 · 고객 · 경쟁 · 수익 구조 · 재무 · 리스크 → 근거 한눈에 보기 */
export default function ReportView({
  report,
  financePlan,
  onSaveFinancePlan,
  marketSizing,
  onSaveMarketSizing,
  areaScores,
  onSaveAreaScores,
}: {
  report: IdeaReport;
  financePlan?: FinancePlan | null;
  onSaveFinancePlan?: (plan: FinancePlan) => Promise<void> | void;
  marketSizing?: { reportId: string; data: MarketSizing } | null;
  onSaveMarketSizing?: (v: { reportId: string; data: MarketSizing }) => Promise<void> | void;
  areaScores?: { reportId: string; data: AreaScore[] } | null;
  onSaveAreaScores?: (v: { reportId: string; data: AreaScore[] }) => Promise<void> | void;
}) {
  const wf = report.response.workflow_result;
  return (
    <div className="flex flex-col gap-5">
      <div
        className="rounded-lg p-5 flex items-center justify-between gap-4 flex-wrap"
        style={{ background: "#fff", border: "1px solid #E5E7EB" }}
      >
        <div>
          <span className="font-semibold">보고서 v{report.version}</span>
          {report.elapsedMs && (
            <span className="text-sm ml-3" style={{ color: "#6B7280" }}>
              소요 {(report.elapsedMs / 1000).toFixed(1)}초
            </span>
          )}
        </div>
        <div className="text-xs" style={{ color: "#6B7280" }}>
          {new Date(report.createdAt).toLocaleString("ko-KR")} 작성
        </div>
      </div>

      {/* 넓은 화면은 왼쪽 세로 목차(ProfileWorkspace), 좁은 화면은 여기 가로 목차 */}
      <div className="xl:hidden sticky top-[60px] z-20">
        <SectionNav items={reportNavItems(report)} />
      </div>

      <div id="rv-summary" className="scroll-mt-32" />
      {wf.decision_result ? (
        <DecisionBanner result={wf.decision_result}>
          <AreaScores report={report} financeSummary={financeSummary(financePlan)} saved={areaScores} onSave={onSaveAreaScores} />
        </DecisionBanner>
      ) : (
        <div className="rounded-xl p-4 text-sm" style={{ background: "#FFFBEB", color: "#B45309" }}>
          종합 판정을 내리지 못했어요. 분야별 결과만 확인할 수 있어요.
        </div>
      )}

      {/* 분야마다 시각화를 그 분야 카드 안에 넣어 한 덩어리로 — 시장부터 리스크까지 */}
      {SECTIONS.filter((sec) => sec.agent in wf.agent_results).map((sec) => (
        <section
          key={sec.agent}
          id={`rv-${sec.agent}`}
          className="flex flex-col gap-4 pt-7 mt-2 scroll-mt-32"
          style={{ borderTop: "2px solid #08183F" }}
          aria-label={sec.title}
        >
          <div className="flex items-baseline gap-3 flex-wrap">
            <span className="self-center w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold text-white shrink-0" style={{ background: "#1B57EA" }}>
              {sec.no}
            </span>
            <h3 className="text-2xl font-bold m-0 tracking-tight" style={{ color: "#08183F" }}>
              {sec.title}
            </h3>
            <span className="text-sm" style={{ color: "#6B7280" }}>
              {sec.sub}
            </span>
          </div>
          <AgentResultCard
            agentName={sec.agent}
            hideLabel
            hideSummary={sec.agent === "FinancialAgent"}
            result={withFinancePlan(sec.agent, wf.agent_results[sec.agent], financePlan)}
          >
            {sec.agent === "MarketAgent" && <MarketPanel report={report} saved={marketSizing} onSave={onSaveMarketSizing} />}
            {sec.agent === "CompetitorAgent" && <CompetitionPanel report={report} embedded />}
            {/* 보고서 버전이 바뀌면 입력칸도 새로 */}
            {sec.agent === "FinancialAgent" && <FinancePanel key={report.id} report={report} saved={financePlan} onSave={onSaveFinancePlan} embedded />}
            {sec.agent === "RiskAgent" && <RiskPanel report={report} embedded />}
          </AgentResultCard>
        </section>
      ))}

      {/* 참고 자료 성격이라 맨 뒤 */}
      <div id="rv-evidence" className="scroll-mt-32">
        <EvidenceOverview report={report} />
      </div>
    </div>
  );
}

const SECTIONS = [
  { no: 1, agent: "MarketAgent", title: "시장", sub: "시장 규모 · 성장 추세" },
  { no: 2, agent: "CustomerAgent", title: "고객", sub: "고객 세그먼트 · 핵심 가정" },
  { no: 3, agent: "CompetitorAgent", title: "경쟁", sub: "경쟁 서비스와 우리 자리" },
  { no: 4, agent: "BusinessModelAgent", title: "수익 구조", sub: "수익 방식 · 가격 · 채널" },
  { no: 5, agent: "FinancialAgent", title: "재무", sub: "월 손익 · 손익분기" },
  { no: 6, agent: "RiskAgent", title: "리스크", sub: "가능성 × 영향" },
];

/** 재무 카드는 사용자가 채운 손익계산서가 있으면 그 결과로 보여준다 (보고서를 새로 만들지 않아도) */
function withFinancePlan(agentName: string, result: AgentResult, plan?: FinancePlan | null): AgentResult {
  const summary = agentName === "FinancialAgent" ? financeSummary(plan) : null;
  if (!summary || !plan) return result;
  return {
    ...result,
    status: "success",
    confidence: financeConfidence(plan),
    summary: `${summary} — 아래 '월 손익계산서' 기준이에요.`,
    recommendations: [],
  };
}

export function reportNavItems(report: IdeaReport) {
  const results = report.response.workflow_result.agent_results;
  return [
    { id: "rv-summary", label: "요약", no: "" },
    ...SECTIONS.filter((sec) => sec.agent in results).map((sec) => ({ id: `rv-${sec.agent}`, label: sec.title, no: String(sec.no) })),
    { id: "rv-evidence", label: "근거 자료", no: "" },
  ];
}

/** 보고서 섹션 바로가기 — 지금 보고 있는 섹션을 표시한다. vertical이면 왼쪽 세로 목차 */
export function SectionNav({ items, vertical }: { items: { id: string; label: string; no?: string }[]; vertical?: boolean }) {
  const [active, setActive] = useState(items[0]?.id);
  // 목차를 눌러 스크롤하는 동안은 지나가는 섹션으로 표시가 깜빡이지 않게 감지를 멈춘다
  const lockRef = useRef(false);
  useEffect(() => {
    const els = items.map((i) => document.getElementById(i.id)).filter((e): e is HTMLElement => !!e);
    const io = new IntersectionObserver(
      (entries) => {
        if (lockRef.current) return;
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: "-130px 0px -60% 0px" },
    );
    els.forEach((e) => io.observe(e));
    return () => io.disconnect();
    // 섹션 목록이 바뀔 때만 다시 관찰한다
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items.map((i) => i.id).join()]);
  const go = (id: string) => {
    const el = document.getElementById(id);
    if (!el) return;
    setActive(id);
    lockRef.current = true;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    // 스크롤이 멈추면(또는 늦어도 1.2초 뒤) 다시 감지
    let timer = window.setTimeout(unlock, 1200);
    function unlock() {
      lockRef.current = false;
      window.clearTimeout(timer);
      window.removeEventListener("scroll", onScroll);
    }
    function onScroll() {
      window.clearTimeout(timer);
      timer = window.setTimeout(unlock, 150);
    }
    window.addEventListener("scroll", onScroll, { passive: true });
  };
  if (vertical) {
    return (
      <nav aria-label="보고서 목차" className="flex flex-col">
        <div className="text-xs px-2 pb-2" style={{ color: "#6B7280" }}>
          보고서 목차
        </div>
        {items.map((i) => {
          const on = i.id === active;
          return (
            <a
              key={i.id}
              href={`#${i.id}`}
              onClick={(e) => {
                e.preventDefault();
                go(i.id);
              }}
              aria-current={on ? "true" : undefined}
              className="flex items-center gap-2.5 px-2 py-2 rounded-lg text-sm no-underline"
              style={{
                background: on ? "#EAF0FD" : "transparent",
                color: on ? "#1446C4" : "#485876",
                fontWeight: on ? 700 : 500,
                borderLeft: `3px solid ${on ? "#1B57EA" : "transparent"}`,
                textDecoration: "none",
              }}
            >
              <span
                className="w-5 h-5 rounded-md shrink-0 flex items-center justify-center text-[11px] font-bold"
                style={{ background: on ? "#1B57EA" : "#F3F4F6", color: on ? "#fff" : "#6B7280" }}
              >
                {i.no || "·"}
              </span>
              {i.label}
            </a>
          );
        })}
      </nav>
    );
  }
  return (
    <nav
      aria-label="보고서 바로가기"
      className="-mx-1 px-1 py-2 flex gap-1.5 overflow-x-auto"
      style={{ background: "rgba(243,244,246,0.95)", backdropFilter: "blur(6px)" }}
    >
      {items.map((i) => {
        const on = i.id === active;
        return (
          <a
            key={i.id}
            href={`#${i.id}`}
            onClick={(e) => {
              e.preventDefault();
              go(i.id);
            }}
            aria-current={on ? "true" : undefined}
            className="shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold no-underline whitespace-nowrap"
            style={{
              background: on ? "#1B57EA" : "#fff",
              color: on ? "#fff" : "#485876",
              border: `1px solid ${on ? "#1B57EA" : "#E5E7EB"}`,
              textDecoration: "none",
            }}
          >
            {i.no ? `${i.no} ` : ""}
            {i.label}
          </a>
        );
      })}
    </nav>
  );
}
