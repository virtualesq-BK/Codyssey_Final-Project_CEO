"use client";

import { SHOW_CONFIDENCE } from "@/lib/agents";
import type { DecisionResult } from "@/lib/api";

const DECISION_CONFIG = {
  GO: {
    label: "GO · 진행 권장",
    color: "#1B57EA",
    bg: "#F3F4F6",
    desc: "근거가 충분하고 리스크가 관리 가능합니다. 다음 단계로 진행하세요.",
  },
  PIVOT: {
    label: "PIVOT · 방향 수정",
    color: "#B45309",
    bg: "#FFFBEB",
    desc: "현재 방향에 중요한 문제가 있습니다. 핵심 가정을 재검토하세요.",
  },
  VALIDATE_MORE: {
    label: "VALIDATE MORE · 추가 검증",
    color: "#B45309",
    bg: "#FFFBEB",
    desc: "잠재력은 있지만 핵심 가정을 먼저 검증해야 합니다.",
  },
  STOP: {
    label: "STOP · 중단 권장",
    color: "#B42318",
    bg: "#FEF2F2",
    desc: "현재 형태로는 사업성이 낮습니다. 근본적인 재검토가 필요합니다.",
  },
} as const;

interface Props {
  result: DecisionResult;
  /** 종합 평가 아래에 넣을 내용 (영역별 점수) */
  children?: React.ReactNode;
}

export default function DecisionBanner({ result, children }: Props) {
  const cfg = DECISION_CONFIG[result.decision];

  return (
    <section
      className="rounded-lg p-7 flex flex-col gap-5"
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
          {SHOW_CONFIDENCE && (
            <span className="text-sm text-text-muted">
              신뢰도 {result.confidence.toFixed(2)}
            </span>
          )}
        </div>
        <div className={`flex-1 h-2 max-w-32 bg-white/60 rounded-full overflow-hidden ${SHOW_CONFIDENCE ? "" : "hidden"}`}>
          <div
            className="h-2 rounded-full"
            style={{
              width: `${Math.round(result.confidence * 100)}%`,
              backgroundColor: cfg.color,
            }}
          />
        </div>
      </div>

      <div>
        <div className="text-xs font-bold mb-1.5" style={{ color: cfg.color }}>
          종합 평가
        </div>
        <p className="text-base font-semibold leading-relaxed m-0" style={{ color: "#08183F" }}>
          {withoutConfidence(result.summary)}
        </p>
      </div>

      {children}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm leading-relaxed">
        {[
          { title: "강점", items: result.strengths, mark: "＋", tone: "#0F7B6C", bg: "#F1FAF6", border: "#CDEBDD" },
          { title: "약점", items: result.weaknesses, mark: "－", tone: "#B42318", bg: "#FFF6F5", border: "#F5D3CF" },
        ]
          .filter((g) => g.items.length > 0)
          .map((g) => (
            <div key={g.title} className="rounded-xl p-4 flex flex-col gap-2.5 bg-white" style={{ border: `1px solid ${g.border}` }}>
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-md flex items-center justify-center text-sm font-bold" style={{ background: g.bg, color: g.tone }}>
                  {g.mark}
                </span>
                <b style={{ color: g.tone }}>{g.title}</b>
              </div>
              <ul className="m-0 p-0 list-none flex flex-col gap-2">
                {g.items.map((t, i) => (
                  <li key={i} className="rounded-lg px-3 py-2" style={{ background: g.bg, color: "#485876" }}>
                    <LeadBold text={stripConfidence(t)} />
                  </li>
                ))}
              </ul>
            </div>
          ))}
      </div>

      {result.action_plan.length > 0 && (
        <div>
          <div className="font-semibold mb-3">다음 행동</div>
          <div className="rounded-xl overflow-x-auto bg-white" style={{ border: "1px solid #E5E7EB" }}>
            <table className="w-full text-sm" style={{ borderCollapse: "collapse", minWidth: 560 }}>
              <caption className="sr-only">다음 행동 단계별 계획</caption>
              <thead>
                <tr style={{ background: "#F5F7FC", color: "#485876" }}>
                  <th scope="col" className="text-left font-semibold text-xs px-3 py-2 w-[72px]">단계</th>
                  <th scope="col" className="text-left font-semibold text-xs px-3 py-2 w-[84px]">기간</th>
                  <th scope="col" className="text-left font-semibold text-xs px-3 py-2">할 일</th>
                </tr>
              </thead>
              <tbody>
                {result.action_plan.map((action, i) => {
                  const step = parseStep(action, i);
                  return (
                    <tr key={i} style={{ borderTop: "1px solid #E5E7EB" }}>
                      <td className="px-3 py-2.5 align-top">
                        <span className="text-xs font-bold px-2 py-0.5 rounded-md whitespace-nowrap" style={{ background: "#EAF0FD", color: "#1446C4" }}>
                          {step.step}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 align-top text-xs whitespace-nowrap" style={{ color: "#485876" }}>
                        {step.when || "—"}
                      </td>
                      <td className="px-3 py-2.5 align-top leading-relaxed">
                        {step.title && (
                          <b className="block" style={{ color: "#08183F" }}>
                            {step.title}
                          </b>
                        )}
                        <span className="text-[13px]" style={{ color: step.title ? "#485876" : "#08183F" }}>
                          {step.detail}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <p className="text-xs text-text-muted border-t pt-3 m-0" style={{ borderColor: `${cfg.color}30` }}>
        {result.disclaimer}
      </p>
    </section>
  );
}

/** "1단계(1개월): 고객 검증 시작 - 담임 인터뷰…" → 단계 · 기간 · 제목 · 세부 */
function parseStep(action: string, i: number) {
  const m = action.match(/^\s*(\d+)\s*단계\s*(?:\(([^)]*)\))?\s*[:：]\s*([\s\S]*)$/);
  const body = (m ? m[3] : action).trim();
  // 제목과 세부는 " - " 또는 첫 ": " 로 나뉘어 오는 경우가 많다
  const cut = body.search(/\s[-–—]\s|[:：]\s/);
  const title = cut > 0 && cut <= 40 ? body.slice(0, cut).trim() : "";
  const detail = title ? body.slice(cut).replace(/^\s*[-–—:：]\s*/, "") : body;
  return { step: `${m ? m[1] : i + 1}단계`, when: m?.[2]?.trim() ?? "", title, detail };
}

/** "명확한 타겟 고객: 유초등 학부모…" → 콜론 앞 요약만 굵게 */
function LeadBold({ text }: { text: string }) {
  const i = text.search(/[:：]/);
  if (i <= 0 || i > 40) return <>{text}</>;
  return (
    <>
      <b style={{ color: "#08183F" }}>{text.slice(0, i)}</b>
      {text.slice(i)}
    </>
  );
}

/** 예전 보고서의 종합 평가에 섞인 신뢰도·확신도 문장을 뺀다 */
function withoutConfidence(text: string) {
  const sentences = text.split(/(?<=[.!?。])\s+/);
  const kept = sentences.filter((t) => !/신뢰도|확신도|confidence/i.test(t));
  return (kept.length ? kept : sentences).join(" ");
}

/** 항목 안의 "(신뢰도 0%)" 같은 꼬리를 뗀다 */
function stripConfidence(text: string) {
  return text
    .replace(/\s*\(?\s*(신뢰도|확신도)\s*[\d.]+%?\s*\)?/g, "")
    .replace(/(신뢰도|확신도)(가|이)?\s*(\S+\s*)?(없음|낮음|부족)/g, "근거 부족")
    .replace(/신뢰도|확신도/g, "근거")
    .trim();
}
