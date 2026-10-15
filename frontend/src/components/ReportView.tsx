"use client";

import AgentResultCard from "@/components/AgentResultCard";
import DecisionBanner from "@/components/DecisionBanner";
import { CompetitionPanel, EvidenceOverview, FinancePanel, RiskPanel } from "@/components/ReportVisuals";
import type { FinanceInputs } from "@/lib/api";
import { AGENT_ORDER, STATUS_BG, STATUS_TEXT } from "@/lib/agents";
import type { IdeaReport } from "@/lib/idea";

/** 상세 진단 보고서 한 버전 — 판정 배너 + 한눈에 보기(근거·리스크·경쟁·재무) + 분야별 카드 */
export default function ReportView({
  report,
  financeInputs,
  onSaveFinanceInputs,
}: {
  report: IdeaReport;
  financeInputs?: FinanceInputs | null;
  onSaveFinanceInputs?: (inputs: FinanceInputs) => Promise<void> | void;
}) {
  const wf = report.response.workflow_result;
  const orderedAgents = AGENT_ORDER.filter((k) => k in wf.agent_results);
  return (
    <div className="flex flex-col gap-5">
      <div
        className="rounded-lg p-5 flex items-center justify-between gap-4 flex-wrap"
        style={{ background: STATUS_BG[wf.status] ?? "#F3F4F6" }}
      >
        <div>
          <span className="font-semibold">
            v{report.version} · {STATUS_TEXT[wf.status] ?? wf.status}
          </span>
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

      <div className="flex flex-col gap-4">
        <h3 className="text-lg font-bold m-0">한눈에 보기</h3>
        <EvidenceOverview report={report} />
        <RiskPanel report={report} />
        <CompetitionPanel report={report} />
        {/* 보고서 버전이 바뀌면 입력칸도 새로 */}
        <FinancePanel key={report.id} report={report} saved={financeInputs} onSave={onSaveFinanceInputs} />
      </div>

      <div>
        <h3 className="text-lg font-bold mb-4 mt-0">분야별 진단</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {orderedAgents.map((agentName) => (
            <AgentResultCard key={agentName} agentName={agentName} result={wf.agent_results[agentName]} />
          ))}
        </div>
      </div>
    </div>
  );
}
