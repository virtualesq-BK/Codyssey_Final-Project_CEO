"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { type Idea, type IdeaReport, displayTitle } from "@/lib/idea";
import type { Program } from "@/lib/programs";
import { PINNED_PROGRAMS } from "@/lib/programs";
import type { ModeusAnswers } from "@/lib/application";

interface Props {
  /** 보고서까지 나온 아이템만 넘긴다 */
  ideas: Idea[];
  programs: Program[];
  presetIdeaId?: string | null;
  presetProgramId?: string | null;
  onCreate: (idea: Idea, program: Program, modeusAnswers?: ModeusAnswers) => Promise<void>;
  onClose: () => void;
  /** 최신 보고서 전문을 가져오는 콜백 (모두의 창업 자동 작성용) */
  fetchLatestReport?: (ideaId: string) => Promise<IdeaReport | null>;
}

const line = "#D7E0ED";

const MODUES_ID = "modues-changup";

const MODUES_QUESTIONS: { key: keyof ModeusAnswers; label: string; maxLen: number }[] = [
  { key: "q1", label: "Q1. 나의 아이디어를 한 줄로 소개해주세요.", maxLen: 100 },
  { key: "q2", label: "Q2. 아이디어를 떠올린 배경 이야기를 들려주세요.", maxLen: 1000 },
  { key: "q3_1", label: "Q3-1. 기존 제품 및 서비스 대비 차별점과 어떤 문제를 해결할 수 있나요?", maxLen: 1000 },
  { key: "q3_2", label: "Q3-2. 어떻게 수익을 창출할 계획인가요?", maxLen: 1000 },
  { key: "q4_1", label: "Q4-1. 아이디어를 어떻게 사업화 하실 계획인가요?", maxLen: 1000 },
  { key: "q4_2", label: "Q4-2. 책임멘토를 통해 어떤 도움을 받고싶은가요?", maxLen: 1000 },
];

const EMPTY_ANSWERS: ModeusAnswers = { q1: "", q2: "", q3_1: "", q3_2: "", q4_1: "", q4_2: "" };

async function callModeusAutoFill(idea: Idea, report: IdeaReport | null): Promise<ModeusAnswers> {
  const dr = report?.response?.workflow_result?.decision_result;
  const body = {
    name: idea.profile.name,
    one_liner: idea.profile.oneLiner,
    memo: idea.memo,
    problem: idea.profile.problem,
    customer: idea.profile.customer,
    solution: idea.profile.solution,
    revenue_model: idea.profile.revenueModel,
    industry: idea.profile.industry,
    decision_summary: dr?.summary ?? idea.latestReport?.summary ?? "",
    strengths: dr?.strengths ?? [],
    weaknesses: dr?.weaknesses ?? [],
    opportunities: dr?.opportunities ?? [],
    risks: dr?.risks ?? [],
    action_plan: dr?.action_plan ?? [],
    validation_items: dr?.validation_items ?? [],
    financial_summary: dr?.financial_summary ?? "",
  };
  const res = await fetch("/api/v1/report/modues-application", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("자동 작성 요청에 실패했어요.");
  return res.json() as Promise<ModeusAnswers>;
}

/** 아이템 × 지원사업을 골라 지원서 1건을 만든다 */
export default function NewApplicationDialog({ ideas, programs, presetIdeaId, presetProgramId, onCreate, onClose, fetchLatestReport }: Props) {
  const [ideaId, setIdeaId] = useState<string | null>(presetIdeaId ?? null);
  const [programId, setProgramId] = useState<string | null>(presetProgramId ?? null);
  const [q, setQ] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<"select" | "modues-form">("select");
  const [answers, setAnswers] = useState<ModeusAnswers>(EMPTY_ANSWERS);
  const [autoFilling, setAutoFilling] = useState(false);
  const firstRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    firstRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (step === "modues-form") setStep("select");
        else onClose();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, step]);

  const idea = ideas.find((i) => i.id === ideaId) ?? null;
  const allPrograms = [...PINNED_PROGRAMS, ...programs];
  const program = allPrograms.find((p) => p.id === programId) ?? null;
  const shownPrograms = allPrograms.filter(
    (p) => !q.trim() || `${p.title} ${p.organization} ${p.category}`.toLowerCase().includes(q.trim().toLowerCase()),
  );

  function updateAnswer(key: keyof ModeusAnswers, val: string) {
    setAnswers((prev) => ({ ...prev, [key]: val }));
  }

  async function handleSelectSubmit() {
    if (!idea || !program) return;
    if (program.id === MODUES_ID) {
      setAutoFilling(true);
      setError(null);
      try {
        const report = fetchLatestReport ? await fetchLatestReport(idea.id) : null;
        const filled = await callModeusAutoFill(idea, report);
        setAnswers(filled);
      } catch {
        // 자동 작성 실패 시 빈 폼으로 진행
        setAnswers(EMPTY_ANSWERS);
      } finally {
        setAutoFilling(false);
      }
      setStep("modues-form");
    } else {
      submitApplication();
    }
  }

  async function submitApplication(modeusAnswers?: ModeusAnswers) {
    if (!idea || !program) return;
    setSaving(true);
    setError(null);
    try {
      await onCreate(idea, program, modeusAnswers);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSaving(false);
    }
  }

  const choice = (active: boolean) => ({
    border: `1px solid ${active ? "#134CD8" : line}`,
    background: active ? "#EAF0FD" : "#fff",
    cursor: "pointer",
  });

  if (step === "modues-form") {
    return (
      <div
        className="fixed inset-0 z-[60] flex items-center justify-center p-4"
        style={{ background: "rgba(28, 26, 44, 0.45)" }}
        onMouseDown={(e) => {
          if (e.target === e.currentTarget) onClose();
        }}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="modues-form-title"
          className="bg-white rounded-lg w-full max-w-[680px] max-h-[90vh] flex flex-col"
          style={{ border: `1px solid ${line}` }}
        >
          <div className="px-6 py-4 flex items-center justify-between border-b" style={{ borderColor: line }}>
            <div>
              <button
                type="button"
                onClick={() => setStep("select")}
                className="text-xs font-semibold mb-1 flex items-center gap-1"
                style={{ background: "none", border: "none", cursor: "pointer", color: "#6B7280", padding: 0 }}
              >
                ← 뒤로
              </button>
              <h2 id="modues-form-title" className="text-lg font-bold m-0">
                모두의 창업 지원서
              </h2>
              {idea && (
                <p className="text-xs m-0 mt-0.5" style={{ color: "#6B7280" }}>
                  아이템: {displayTitle(idea)}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="닫기"
              className="w-9 h-9 rounded-lg"
              style={{ background: "none", border: "none", cursor: "pointer", color: "#6B7280" }}
            >
              ✕
            </button>
          </div>

          <div className="overflow-y-auto flex-1 px-6 py-5 flex flex-col gap-5">
            {MODUES_QUESTIONS.map(({ key, label, maxLen }) => {
              const val = answers[key];
              const over = val.length > maxLen;
              return (
                <div key={key} className="flex flex-col gap-1.5">
                  <label className="text-sm font-semibold" style={{ color: "#071B45" }}>
                    {label}
                    <span className="font-normal ml-1" style={{ color: "#6B7280" }}>
                      ({maxLen}자 이내)
                    </span>
                  </label>
                  <textarea
                    value={val}
                    onChange={(e) => updateAnswer(key, e.target.value)}
                    rows={maxLen === 100 ? 2 : 5}
                    className="rounded-lg px-4 py-3 text-sm resize-y focus:outline-none leading-relaxed"
                    style={{
                      border: `1.5px solid ${over ? "#B42318" : line}`,
                      minHeight: maxLen === 100 ? 52 : 100,
                    }}
                  />
                  <div className="text-xs text-right" style={{ color: over ? "#B42318" : "#6B7280" }}>
                    {val.length} / {maxLen}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="px-6 py-4 border-t flex items-center justify-between gap-3 flex-wrap" style={{ borderColor: line }}>
            <span className="text-sm" style={{ color: error ? "#B42318" : "#53647A" }}>
              {error ?? "모든 항목을 작성한 뒤 제출해주세요."}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStep("select")}
                className="min-h-[48px] px-5 rounded-xl text-sm font-semibold bg-white"
                style={{ border: `1px solid ${line}`, color: "#071B45", cursor: "pointer" }}
              >
                취소
              </button>
              <button
                type="button"
                onClick={() => submitApplication(answers)}
                disabled={
                  saving ||
                  MODUES_QUESTIONS.some(({ key, maxLen }) => !answers[key].trim() || answers[key].length > maxLen)
                }
                className="min-h-[48px] px-5 rounded-xl text-sm font-bold text-white disabled:opacity-50"
                style={{ background: "#134CD8", border: "none", cursor: "pointer" }}
              >
                {saving ? "제출 중…" : "지원서 제출"}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center p-4"
      style={{ background: "rgba(28, 26, 44, 0.45)" }}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="new-app-title"
        className="bg-white rounded-lg w-full max-w-[880px] max-h-[90vh] flex flex-col"
        style={{ border: `1px solid ${line}` }}
      >
        <div className="px-6 py-4 flex items-center justify-between border-b" style={{ borderColor: line }}>
          <h2 id="new-app-title" className="text-lg font-bold m-0">
            새 지원서
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="닫기"
            className="w-9 h-9 rounded-lg"
            style={{ background: "none", border: "none", cursor: "pointer", color: "#6B7280" }}
          >
            ✕
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-0 min-h-0 flex-1 overflow-hidden">
          {/* 아이템 */}
          <section className="p-5 flex flex-col gap-3 min-h-0 md:border-r" style={{ borderColor: line }} aria-label="아이템 선택">
            <div>
              <b className="text-sm">1. 아이템</b>
              <p className="text-xs m-0 mt-0.5" style={{ color: "#6B7280" }}>
                상세분석 보고서가 있는 아이템만 고를 수 있어요
              </p>
            </div>
            <div className="flex flex-col gap-2 overflow-y-auto" style={{ maxHeight: 360 }}>
              {ideas.length === 0 ? (
                <div className="rounded-lg p-4 text-sm" style={{ background: "#F5F7FB", color: "#53647A" }}>
                  아직 보고서가 있는 아이템이 없어요.{" "}
                  <Link href="/ideas" className="underline font-semibold" style={{ color: "#071B45" }}>
                    MY아이디어에서 상세분석하기 ›
                  </Link>
                </div>
              ) : (
                ideas.map((i, idx) => (
                  <button
                    key={i.id}
                    ref={idx === 0 ? firstRef : undefined}
                    type="button"
                    aria-pressed={ideaId === i.id}
                    onClick={() => setIdeaId(i.id)}
                    className="text-left rounded-lg px-4 py-3"
                    style={choice(ideaId === i.id)}
                  >
                    <div className="text-sm font-semibold" style={{ color: "#071B45" }}>
                      {displayTitle(i)}
                    </div>
                    <div className="text-xs mt-0.5" style={{ color: "#6B7280" }}>
                      {[i.profile.industry, i.profile.location].filter(Boolean).join(" · ")}
                      {i.latestReport?.decision ? ` · 보고서 v${i.latestReport.version} ${i.latestReport.decision.replace("_", " ")}` : ""}
                    </div>
                  </button>
                ))
              )}
            </div>
          </section>

          {/* 지원사업 */}
          <section className="p-5 flex flex-col gap-3 min-h-0" aria-label="지원사업 선택">
            <div>
              <b className="text-sm">2. 지원사업</b>
              <p className="text-xs m-0 mt-0.5" style={{ color: "#6B7280" }}>
                한 아이템으로 여러 사업에 지원할 수 있어요
              </p>
            </div>
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="사업명·기관 검색"
              aria-label="지원사업 검색"
              className="h-10 rounded-lg px-3 text-sm focus:outline-none"
              style={{ border: `1px solid ${line}` }}
            />
            <div className="flex flex-col gap-2 overflow-y-auto" style={{ maxHeight: 310 }}>
              {shownPrograms.map((p) => {
                const isPinned = p.id === MODUES_ID;
                return (
                  <button
                    key={p.id}
                    type="button"
                    aria-pressed={programId === p.id}
                    onClick={() => setProgramId(p.id)}
                    className="text-left rounded-lg px-4 py-3"
                    style={choice(programId === p.id)}
                  >
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-semibold" style={{ color: "#071B45" }}>
                        {p.title}
                      </span>
                      {isPinned && (
                        <span
                          className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                          style={{ background: "#EAF0FD", color: "#134CD8" }}
                        >
                          상시
                        </span>
                      )}
                    </div>
                    <div className="text-xs mt-0.5" style={{ color: "#6B7280" }}>
                      {p.organization}
                      {!isPinned && ` · ${p.amount} · ~${p.ends_on}`}
                    </div>
                  </button>
                );
              })}
              {shownPrograms.length === 0 && (
                <div className="text-sm p-4" style={{ color: "#6B7280" }}>
                  맞는 공고가 없어요.
                </div>
              )}
            </div>
          </section>
        </div>

        <div className="px-6 py-4 border-t flex items-center justify-between gap-3 flex-wrap" style={{ borderColor: line }}>
          <span className="text-sm" style={{ color: error ? "#B42318" : "#53647A" }}>
            {error ?? (idea && program ? `${displayTitle(idea)} → ${program.title}` : "아이템과 지원사업을 하나씩 골라주세요")}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="min-h-[48px] px-5 rounded-xl text-sm font-semibold bg-white"
              style={{ border: `1px solid ${line}`, color: "#071B45", cursor: "pointer" }}
            >
              취소
            </button>
            <button
              type="button"
              onClick={handleSelectSubmit}
              disabled={!idea || !program || saving || autoFilling}
              className="min-h-[48px] px-5 rounded-xl text-sm font-bold text-white disabled:opacity-50"
              style={{ background: "#134CD8", border: "none", cursor: "pointer" }}
            >
              {autoFilling ? "자동 작성 중…" : saving ? "만드는 중…" : program?.id === MODUES_ID ? "지원서 작성하기" : "지원서 만들기"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
