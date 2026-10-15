"use client";

import { useState } from "react";
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
  success: "#08183F",
  partial: "#B45309",
  failed: "#B42318",
  running: "#485876",
  pending: "#6B7280",
  skipped: "#6B7280",
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
  const color = value >= 0.7 ? "#08183F" : value >= 0.4 ? "#B45309" : "#B42318";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-[#E5E7EB] rounded-full overflow-hidden">
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
  const [showAll, setShowAll] = useState(false);
  const label = AGENT_LABELS[agentName] ?? agentName;
  const statusColor = STATUS_COLORS[result.status];
  const statusLabel = STATUS_LABELS[result.status];

  const isFailed = result.status === "failed" || result.status === "skipped";

  return (
    <div
      className="bg-white border rounded-lg shadow-card p-6 flex flex-col gap-4"
      style={{ borderColor: "#E5E7EB" }}
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
          <ul className="m-0 pl-5 list-disc flex flex-col gap-1">
            {result.recommendations.slice(0, 3).map((rec, i) => (
              <li key={i} className="text-sm text-text-secondary leading-relaxed">
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.evidence.length > 0 && (
        <div className="border-t pt-3" style={{ borderColor: "#E5E7EB" }}>
          <div className="text-xs font-semibold text-text-muted mb-2">
            근거 자료 {result.evidence.length}건
          </div>
          <ul className="m-0 p-0 list-none flex flex-col gap-2">
            {(showAll ? result.evidence : result.evidence.slice(0, 3)).map((ev, i) => (
              <li key={i} className="text-xs flex flex-col gap-0.5">
                <span className="flex gap-2 items-baseline">
                  <span className="font-medium shrink-0" style={{ color: "#1B57EA" }}>
                    [{ev.source}]
                  </span>
                  {ev.url ? (
                    <a href={ev.url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2 min-w-0 break-words" style={{ color: "#08183F" }}>
                      {ev.title} <span aria-hidden="true">↗</span>
                      <span className="sr-only"> (새 창에서 열림)</span>
                    </a>
                  ) : (
                    <span className="min-w-0" style={{ color: "#08183F" }}>
                      {ev.title}
                    </span>
                  )}
                </span>
                {showAll && ev.content && (
                  <span className="pl-1 leading-relaxed line-clamp-2" style={{ color: "#6B7280" }}>
                    {ev.content}
                  </span>
                )}
              </li>
            ))}
          </ul>
          {result.evidence.length > 3 && (
            <button
              type="button"
              onClick={() => setShowAll((v) => !v)}
              aria-expanded={showAll}
              className="mt-2 text-xs font-semibold"
              style={{ background: "none", border: "none", color: "#1B57EA", cursor: "pointer", padding: 0 }}
            >
              {showAll ? "▴ 접기" : `▾ 전체 ${result.evidence.length}건 보기 (내용 포함)`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
