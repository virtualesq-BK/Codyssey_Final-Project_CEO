"use client";

import type { DecisionResult } from "@/lib/api";

const DECISION_CONFIG = {
  GO: {
    label: "GO · 진행 권장",
    color: "#2F5BD3",
    bg: "#EEF2FD",
    desc: "근거가 충분하고 리스크가 관리 가능합니다. 다음 단계로 진행하세요.",
  },
  PIVOT: {
    label: "PIVOT · 방향 수정",
    color: "#B45309",
    bg: "#FFF7EB",
    desc: "현재 방향에 중요한 문제가 있습니다. 핵심 가정을 재검토하세요.",
  },
  VALIDATE_MORE: {
    label: "VALIDATE MORE · 추가 검증",
    color: "#B45309",
    bg: "#FFF7EB",
    desc: "잠재력은 있지만 핵심 가정을 먼저 검증해야 합니다.",
  },
  STOP: {
    label: "STOP · 중단 권장",
    color: "#B42318",
    bg: "#FDECEA",
    desc: "현재 형태로는 사업성이 낮습니다. 근본적인 재검토가 필요합니다.",
  },
} as const;

interface Props {
  result: DecisionResult;
}

export default function DecisionBanner({ result }: Props) {
  const cfg = DECISION_CONFIG[result.decision];

  return (
    <section
      className="rounded-2xl p-7 flex flex-col gap-5"
      style={{ background: cfg.bg, border: `2px solid ${cfg.color}40` }}
    >
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-4">
          <span
            className="text-xl font-bold"
            style={{ color: cfg.color }}
          >
            {cfg.label}
          </span>
          <span className="text-sm text-text-muted">
            신뢰도 {result.confidence.toFixed(2)}
          </span>
        </div>
        <div className="flex-1 h-2 max-w-32 bg-white/60 rounded-full overflow-hidden">
          <div
            className="h-2 rounded-full"
            style={{
              width: `${Math.round(result.confidence * 100)}%`,
              backgroundColor: cfg.color,
            }}
          />
        </div>
      </div>

      <p className="text-lg font-semibold leading-relaxed m-0">{result.summary}</p>
      <p className="text-sm text-text-secondary m-0">{cfg.desc}</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm leading-relaxed">
        {result.strengths.length > 0 && (
          <div>
            <div className="font-semibold mb-2">강점</div>
            <ul className="m-0 pl-4 flex flex-col gap-1">
              {result.strengths.map((s, i) => <li key={i}>{s}</li>)}
            </ul>
          </div>
        )}
        {result.weaknesses.length > 0 && (
          <div>
            <div className="font-semibold mb-2">약점</div>
            <ul className="m-0 pl-4 flex flex-col gap-1">
              {result.weaknesses.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </div>
        )}
      </div>

      {result.action_plan.length > 0 && (
        <div>
          <div className="font-semibold mb-3">다음 행동</div>
          <ol className="m-0 pl-5 flex flex-col gap-2 text-sm leading-relaxed">
            {result.action_plan.map((action, i) => (
              <li key={i}>{action}</li>
            ))}
          </ol>
        </div>
      )}

      {result.validation_items.length > 0 && (
        <div>
          <div className="font-semibold mb-3">검증 필요 항목</div>
          <div className="flex flex-col gap-2">
            {result.validation_items.map((item, i) => (
              <label
                key={i}
                className="flex gap-3 p-4 bg-white/60 rounded-xl text-sm leading-relaxed cursor-pointer"
              >
                <input type="checkbox" className="mt-0.5 shrink-0" />
                <span>{item}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs text-text-muted border-t pt-3 m-0" style={{ borderColor: `${cfg.color}30` }}>
        {result.disclaimer}
      </p>
    </section>
  );
}
