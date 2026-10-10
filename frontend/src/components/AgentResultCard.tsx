"use client";

import type { AgentResult, AgentStatus } from "@/lib/api";

const AGENT_LABELS: Record<string, string> = {
  MarketAgent: "시장",
  CustomerAgent: "고객",
  CompetitorAgent: "경쟁",
  BusinessModelAgent: "수익 모델",
  FinancialAgent: "재무",
  RiskAgent: "리스크",
};

const STATUS_COLORS: Record<AgentStatus, string> = {
  success: "#2F5BD3",
  partial: "#B45309",
  failed: "#B42318",
  running: "#4A505B",
  pending: "#8A909B",
  skipped: "#8A909B",
};

const STATUS_LABELS: Record<AgentStatus, string> = {
  success: "완료",
  partial: "부분 완료",
  failed: "실패",
  running: "분석 중",
  pending: "대기",
  skipped: "건너뜀",
};

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = value >= 0.7 ? "#2F5BD3" : value >= 0.4 ? "#B45309" : "#B42318";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-[#E8EAEE] rounded-full overflow-hidden">
        <div
          className="h-2 rounded-full transition-all"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-xs text-text-muted w-8 text-right">{value.toFixed(2)}</span>
    </div>
  );
}

interface Props {
  agentName: string;
  result: AgentResult;
}

export default function AgentResultCard({ agentName, result }: Props) {
  const label = AGENT_LABELS[agentName] ?? agentName;
  const statusColor = STATUS_COLORS[result.status];
  const statusLabel = STATUS_LABELS[result.status];

  const isFailed = result.status === "failed" || result.status === "skipped";

  return (
    <div
      className="bg-white border rounded-2xl p-6 flex flex-col gap-4"
      style={{ borderColor: "#D9DCE1" }}
    >
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <span className="font-bold text-base">{label}</span>
          <span
            className="text-xs font-semibold px-2 py-0.5 rounded"
            style={{
              color: statusColor,
              background: `${statusColor}18`,
            }}
          >
            {statusLabel}
          </span>
        </div>
        {result.execution_time_ms && (
          <span className="text-xs text-text-muted">{result.execution_time_ms}ms</span>
        )}
      </div>

      <ConfidenceBar value={result.confidence} />

      <p className="text-sm leading-relaxed text-text-secondary m-0">
        {result.summary}
      </p>

      {!isFailed && result.recommendations.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-text-muted mb-2">권장 사항</div>
          <ul className="m-0 pl-4 flex flex-col gap-1">
            {result.recommendations.slice(0, 3).map((rec, i) => (
              <li key={i} className="text-sm text-text-secondary leading-relaxed">
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.evidence.length > 0 && (
        <div className="border-t pt-3" style={{ borderColor: "#D9DCE1" }}>
          <div className="text-xs font-semibold text-text-muted mb-2">
            근거 자료 {result.evidence.length}건
          </div>
          <div className="flex flex-col gap-1">
            {result.evidence.slice(0, 3).map((ev, i) => (
              <div key={i} className="text-xs text-text-muted flex gap-2">
                <span className="text-primary font-medium">[{ev.source}]</span>
                <span>{ev.title}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
