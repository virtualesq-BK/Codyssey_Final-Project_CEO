"use client";

import { useEffect, useRef, useState } from "react";
import type { AnalyzeJob, StageProgress } from "@/lib/api";
import { progressOf } from "@/lib/diagnosisRunner";

const blue = "#134CD8";
const navy = "#071B45";
const slate = "#53647A";
const gray = "#6B7280";
const line = "#D7E0ED";

/** 진단 단계 — 서버 작업(stages)의 키와 맞춘다 */
const STAGES: { key: string; label: string; fills: string; icon: keyof typeof ICONS }[] = [
  { key: "MarketAgent", label: "시장 분석", fills: "시장 규모 · 성장 추세", icon: "chart" },
  { key: "CustomerAgent", label: "고객 분석", fills: "고객 세그먼트 · 핵심 가정", icon: "users" },
  { key: "CompetitorAgent", label: "경쟁 분석", fills: "경쟁사 · 차별점", icon: "target" },
  { key: "BusinessModelAgent", label: "수익 구조", fills: "수익 방식 · 가격 · 채널", icon: "coins" },
  { key: "FinancialAgent", label: "재무 계산", fills: "비용 · 손익 · 필요 자금", icon: "calc" },
  { key: "RiskAgent", label: "리스크 분석", fills: "규제 · 실행 · 시장 위험", icon: "shield" },
  { key: "DecisionAgent", label: "종합 판정", fills: "GO · PIVOT · VALIDATE · STOP", icon: "flag" },
];

const ICONS = {
  chart: <path d="M4 19V5M4 19h16M8 15l3-4 3 2 5-6" />,
  users: (
    <>
      <circle cx="9" cy="8" r="3" />
      <path d="M3 19c0-3 3-5 6-5s6 2 6 5M16 5a3 3 0 0 1 0 6M21 19c0-2-1.5-3.5-3.5-4.3" />
    </>
  ),
  target: (
    <>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="12" cy="12" r="0.5" />
    </>
  ),
  coins: (
    <>
      <ellipse cx="12" cy="7" rx="7" ry="3" />
      <path d="M5 7v5c0 1.7 3.1 3 7 3s7-1.3 7-3V7M5 12v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5" />
    </>
  ),
  calc: (
    <>
      <rect x="5" y="3" width="14" height="18" rx="2" />
      <path d="M8 7h8M8 12h2M14 12h2M8 16h2M14 16h2" />
    </>
  ),
  shield: <path d="M12 3l7 3v5c0 5-3.5 8.5-7 10-3.5-1.5-7-5-7-10V6z" />,
  flag: <path d="M5 21V4M5 4h11l-2 4 2 4H5" />,
};

function Icon({ name, color, size = 20 }: { name: keyof typeof ICONS; color: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {ICONS[name]}
    </svg>
  );
}

/** 공통 모달 틀 — 바깥 클릭·Esc로 닫고, 열릴 때 첫 버튼에 포커스 */
export function ModalFrame({
  labelledBy,
  onClose,
  children,
  width = 640,
}: {
  labelledBy: string;
  onClose: () => void;
  children: React.ReactNode;
  width?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.querySelector<HTMLElement>("[data-autofocus]")?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      prev?.focus?.();
    };
  }, [onClose]);
  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center p-4"
      style={{ background: "rgba(8, 24, 63, 0.55)", backdropFilter: "blur(2px)" }}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        className="bg-white rounded-2xl w-full max-h-[92vh] overflow-y-auto flex flex-col"
        style={{ maxWidth: width, boxShadow: "0 24px 64px rgba(8, 24, 63, 0.28)" }}
      >
        {children}
      </div>
    </div>
  );
}

/** 상세분석 시작 확인 */
export function DiagnoseStartModal({
  ideaName,
  again,
  onConfirm,
  onClose,
}: {
  ideaName: string;
  again: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <ModalFrame labelledBy="diag-start-title" onClose={onClose}>
      {/* 머리 — 키컬러 띠 */}
      <div className="relative overflow-hidden px-7 pt-7 pb-6" style={{ background: "linear-gradient(110deg, #134CD8 0%, #0F3DB0 100%)", color: "#fff" }}>
        <div aria-hidden="true" className="absolute pointer-events-none" style={{ right: -80, top: -120, width: 300, height: 300, borderRadius: "50%", background: "radial-gradient(circle, rgba(255,255,255,0.22), rgba(255,255,255,0) 70%)" }} />
        <div className="relative flex items-center gap-2 text-xs font-semibold" style={{ color: "rgba(255,255,255,0.85)" }}>
          <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#FFB91B" }} />
          {again ? "보고서 새 버전" : "상세분석"} · 유료
        </div>
        <h2 id="diag-start-title" className="relative text-2xl font-bold m-0 mt-2 tracking-tight">
          {again ? "보고서를 새로 작성할까요?" : "상세분석을 시작할까요?"}
        </h2>
        <p className="relative m-0 mt-1.5 text-sm" style={{ color: "rgba(255,255,255,0.85)" }}>
          &lsquo;{ideaName}&rsquo;을 6개 분야 전문 에이전트가 근거와 함께 진단하고 판정을 내려요.
        </p>
      </div>

      {/* 무엇을 하나 */}
      <div className="px-7 py-6 flex flex-col gap-4">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
          {STAGES.slice(0, 6).map((s) => (
            <div key={s.key} className="rounded-xl p-3 flex flex-col gap-1.5" style={{ background: "#F5F7FC", border: `1px solid #E3E9F7` }}>
              <span className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "#fff" }}>
                <Icon name={s.icon} color={blue} size={18} />
              </span>
              <b className="text-sm" style={{ color: navy }}>
                {s.label}
              </b>
              <span className="text-xs leading-snug" style={{ color: slate }}>
                {s.fills}
              </span>
            </div>
          ))}
        </div>

        <div className="rounded-xl px-4 py-3 flex items-center gap-3 flex-wrap text-sm" style={{ background: "#FFF6DE", color: navy }}>
          <Icon name="flag" color="#B7791F" size={18} />
          <span>
            마지막에 <b>GO · PIVOT · VALIDATE MORE · STOP</b> 중 하나로 판정해요
          </span>
        </div>

        <ul className="m-0 p-0 list-none flex flex-col gap-1.5 text-sm" style={{ color: slate }}>
          <li className="flex gap-2">
            <Dot /> 보통 <b style={{ color: navy }}>2~3분</b> 걸려요
          </li>
          <li className="flex gap-2">
            <Dot /> <span><b style={{ color: navy }}>다른 화면으로 가거나 창을 닫아도</b> 분석은 계속돼요. 끝나면 알려드려요</span>
          </li>
          <li className="flex gap-2">
            <Dot /> 결과는 버전별 보고서로 남아요
          </li>
        </ul>
      </div>

      <div className="px-7 py-4 flex justify-end gap-2 border-t" style={{ borderColor: line }}>
        <button
          type="button"
          onClick={onClose}
          className="min-h-[46px] px-5 rounded-xl text-sm font-semibold bg-white"
          style={{ border: `1px solid ${line}`, color: slate, cursor: "pointer" }}
        >
          취소
        </button>
        <button
          type="button"
          data-autofocus
          onClick={onConfirm}
          className="min-h-[46px] px-6 rounded-xl text-sm font-bold text-white"
          style={{ background: blue, border: "none", cursor: "pointer" }}
        >
          {again ? "새 보고서 작성 시작" : "상세분석 시작"}
        </button>
      </div>
    </ModalFrame>
  );
}

function Dot() {
  return <span className="mt-2 w-1 h-1 rounded-full shrink-0" style={{ background: blue }} />;
}

/** 진행 중 화면 — 와이어프레임 '분석 중' 화면 기준 */
export function DiagnosisProgressModal({
  ideaName,
  job,
  startedAt,
  finished,
  onMinimize,
  onOpenReport,
}: {
  ideaName: string;
  job: AnalyzeJob | null;
  startedAt: string;
  /** 저장까지 끝났으면 true */
  finished: boolean;
  onMinimize: () => void;
  onOpenReport: () => void;
}) {
  // 진행 표시가 멈춰 보이지 않게 1초마다 다시 그린다
  const [, tick] = useState(0);
  useEffect(() => {
    if (finished) return;
    const t = setInterval(() => tick((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, [finished]);
  const { percent, remainingSec } = finished ? { percent: 100, remainingSec: 0 } : progressOf(job, startedAt);

  return (
    <ModalFrame labelledBy="diag-progress-title" onClose={onMinimize} width={880}>
      <div className="px-7 pt-7 pb-5 flex flex-col gap-4">
        <div className="flex justify-between items-end gap-4 flex-wrap">
          <div className="min-w-0">
            <div className="text-xs font-bold" style={{ color: blue }}>
              {finished ? "상세분석 완료" : "상세분석 진행 중"}
            </div>
            <h2 id="diag-progress-title" className="text-2xl font-bold m-0 mt-1 tracking-tight" style={{ color: navy }}>
              {ideaName}
            </h2>
            <p className="m-0 mt-1 text-sm" style={{ color: slate }}>
              6개 분야 에이전트가 근거를 찾아 분석하고, 다 모이면 종합 판정을 내려요
            </p>
          </div>
          <div className="text-right">
            <div className="text-4xl font-bold leading-none tabular-nums" style={{ color: navy }} aria-live="polite">
              {percent}%
            </div>
            <div className="text-xs mt-1.5" style={{ color: slate }}>
              {finished ? "보고서가 나왔어요" : remainingSec > 0 ? `약 ${Math.ceil(remainingSec / 60)}분 남음 · 창을 닫아도 계속돼요` : "거의 다 됐어요 · 창을 닫아도 계속돼요"}
            </div>
          </div>
        </div>
        <div
          className="h-2 rounded-full overflow-hidden"
          style={{ background: "#E6EAF2" }}
          role="progressbar"
          aria-label="상세분석 진행"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
        >
          <div className="h-2 rounded-full transition-all duration-700" style={{ width: `${percent}%`, background: `linear-gradient(90deg, ${blue}, #3E7BFF)` }} />
        </div>
      </div>

      <div className="px-7 pb-6 grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))" }}>
        {STAGES.map((s) => (
          <StageCard key={s.key} meta={s} stage={job?.stages[s.key]} finished={finished} />
        ))}
      </div>

      <div className="px-7 py-4 flex justify-between items-center gap-3 flex-wrap border-t" style={{ borderColor: line, background: "#FAFBFD" }}>
        <span className="text-xs" style={{ color: slate }}>
          {finished ? "보고서 탭에서 분야별 결과와 근거를 볼 수 있어요" : "다른 화면으로 가도 돼요. 끝나면 화면 아래에 알려드려요"}
        </span>
        <div className="flex gap-2">
          {finished ? (
            <button
              type="button"
              data-autofocus
              onClick={onOpenReport}
              className="min-h-[48px] px-5 rounded-xl text-sm font-bold text-white"
              style={{ background: blue, border: "none", cursor: "pointer" }}
            >
              보고서 보기
            </button>
          ) : (
            <button
              type="button"
              data-autofocus
              onClick={onMinimize}
              className="min-h-[48px] px-5 rounded-xl text-sm font-semibold bg-white"
              style={{ border: `1px solid ${line}`, color: navy, cursor: "pointer" }}
            >
              닫고 계속 진행하기
            </button>
          )}
        </div>
      </div>
    </ModalFrame>
  );
}

function StageCard({ meta, stage, finished }: { meta: (typeof STAGES)[number]; stage?: StageProgress; finished: boolean }) {
  const state = stage?.state ?? (finished ? "done" : "waiting");
  // 완료·부분 완료 구분은 개발 중 임시로 숨긴다 (부분 완료도 완료로 표시)
  const partial = false;
  const look =
    state === "running"
      ? { bg: "#fff", border: `2px solid ${blue}`, head: blue, mark: "분석 중" }
      : state === "failed"
        ? { bg: "#FEF2F2", border: "1px solid #F5C2C0", head: "#B42318", mark: "실패" }
        : partial
          ? { bg: "#FFF8E8", border: "1px solid #F3D9A4", head: "#8A4B08", mark: "근거 보강 필요" }
          : state === "done"
            ? { bg: "#fff", border: `1px solid ${line}`, head: "#0F7B6C", mark: "완료" }
            : { bg: "#F7F8FA", border: `1px solid ${line}`, head: gray, mark: "대기" };
  return (
    <div className="rounded-xl p-4 flex flex-col gap-2 min-h-[132px]" style={{ background: look.bg, border: look.border }}>
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-2 font-bold text-sm" style={{ color: state === "waiting" ? gray : navy }}>
          <Icon name={meta.icon} color={look.head} size={18} />
          {meta.label}
        </span>
        <span className="text-[11px] font-bold flex items-center gap-1" style={{ color: look.head }}>
          {state === "done" && !partial && "✓ "}
          {look.mark}
        </span>
      </div>
      <div className="text-xs leading-snug line-clamp-2" style={{ color: slate }}>
        {stage?.summary || `→ ${meta.fills}`}
      </div>
      <div className="mt-auto">
        {state === "running" ? (
          <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "#E6EAF2" }}>
            <div className="h-1.5 w-1/3 rounded-full animate-[indeterminate_1.4s_ease-in-out_infinite]" style={{ background: blue }} />
          </div>
        ) : state !== "waiting" && stage ? (
          <span className="text-[11px]" style={{ color: gray }}>
            {(stage.elapsed_ms / 1000).toFixed(0)}초{stage.evidence ? ` · 근거 ${stage.evidence}건` : ""}
          </span>
        ) : null}
      </div>
    </div>
  );
}
