"use client";

import AgentResultCard from "@/components/AgentResultCard";
import DecisionBanner from "@/components/DecisionBanner";
import { CompetitionPanel, EvidenceOverview, FinancePanel, RiskPanel } from "@/components/ReportVisuals";
import type { AgentResult } from "@/lib/api";
import { type FinancePlan, financeConfidence, financeSummary } from "@/lib/financePlan";
import type { IdeaReport } from "@/lib/idea";

/** 상세 진단 보고서 한 버전 — 판정 요약 → 시장 · 고객 · 경쟁 · 수익 구조 · 재무 · 리스크 → 근거 한눈에 보기 */
export default function ReportView({
  report,
  financePlan,
  onSaveFinancePlan,
}: {
  report: IdeaReport;
  financePlan?: FinancePlan | null;
  onSaveFinancePlan?: (plan: FinancePlan) => Promise<void> | void;
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

      {wf.decision_result ? (
        <DecisionBanner result={wf.decision_result} />
      ) : (
        <div className="rounded-xl p-4 text-sm" style={{ background: "#FFFBEB", color: "#B45309" }}>
          종합 판정을 내리지 못했어요. 분야별 결과만 확인할 수 있어요.
        </div>
      )}

      {/* 분야마다 시각화를 그 분야 카드 안에 넣어 한 덩어리로 — 시장부터 리스크까지 */}
      {SECTIONS.filter((sec) => sec.agent in wf.agent_results).map((sec) => (
        <section key={sec.agent} className="flex flex-col gap-4 pt-7 mt-2" style={{ borderTop: "2px solid #08183F" }} aria-label={sec.title}>
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
            {sec.agent === "CompetitorAgent" && <CompetitionPanel report={report} embedded />}
            {/* 보고서 버전이 바뀌면 입력칸도 새로 */}
            {sec.agent === "FinancialAgent" && <FinancePanel key={report.id} report={report} saved={financePlan} onSave={onSaveFinancePlan} embedded />}
            {sec.agent === "RiskAgent" && <RiskPanel report={report} embedded />}
          </AgentResultCard>
        </section>
      ))}

      {/* 참고 자료 성격이라 맨 뒤 */}
      <EvidenceOverview report={report} />
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
