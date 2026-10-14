"use client";

import AgentResultCard from "@/components/AgentResultCard";
import DecisionBanner from "@/components/DecisionBanner";
import { AGENT_ORDER, STATUS_BG, STATUS_TEXT } from "@/lib/agents";
import type { IdeaReport } from "@/lib/idea";

/** 상세 진단 보고서 한 버전 — 판정 배너 + 분야별 카드 */
export default function ReportView({ report }: { report: IdeaReport }) {
  const wf = report.response.workflow_result;
  const orderedAgents = AGENT_ORDER.filter((k) => k in wf.agent_results);
  return (
    <div className="flex flex-col gap-5">
      <div
        className="rounded-3xl p-5 flex items-center justify-between gap-4 flex-wrap"
        style={{ background: STATUS_BG[wf.status] ?? "#F5F6F8" }}
      >
        <div>
          <span className="font-semibold">
            v{report.version} · {STATUS_TEXT[wf.status] ?? wf.status}
          </span>
          {report.elapsedMs && (
            <span className="text-sm ml-3" style={{ color: "#808080" }}>
              소요 {(report.elapsedMs / 1000).toFixed(1)}초
            </span>
          )}
        </div>
        <div className="text-xs" style={{ color: "#808080" }}>
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {orderedAgents.map((agentName) => (
            <AgentResultCard key={agentName} agentName={agentName} result={wf.agent_results[agentName]} />
          ))}
        </div>
      </div>
    </div>
  );
}
