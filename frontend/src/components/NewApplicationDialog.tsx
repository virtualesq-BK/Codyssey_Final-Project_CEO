"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { type Idea, displayTitle } from "@/lib/idea";
import type { Program } from "@/lib/programs";

interface Props {
  /** 보고서까지 나온 아이템만 넘긴다 */
  ideas: Idea[];
  programs: Program[];
  presetIdeaId?: string | null;
  presetProgramId?: string | null;
  onCreate: (idea: Idea, program: Program) => Promise<void>;
  onClose: () => void;
}

const line = "#E5E7EB";

/** 아이템 × 지원사업을 골라 지원서 1건을 만든다 */
export default function NewApplicationDialog({ ideas, programs, presetIdeaId, presetProgramId, onCreate, onClose }: Props) {
  const [ideaId, setIdeaId] = useState<string | null>(presetIdeaId ?? null);
  const [programId, setProgramId] = useState<string | null>(presetProgramId ?? null);
  const [q, setQ] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const firstRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    firstRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const idea = ideas.find((i) => i.id === ideaId) ?? null;
  const program = programs.find((p) => p.id === programId) ?? null;
  const shownPrograms = programs.filter(
    (p) => !q.trim() || `${p.title} ${p.organization} ${p.category}`.toLowerCase().includes(q.trim().toLowerCase()),
  );

  async function submit() {
    if (!idea || !program) return;
    setSaving(true);
    setError(null);
    try {
      await onCreate(idea, program);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSaving(false);
    }
  }

  const choice = (active: boolean) => ({
    border: `1px solid ${active ? "#7270FF" : line}`,
    background: active ? "#EEEEFF" : "#fff",
    cursor: "pointer",
  });

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
                <div className="rounded-lg p-4 text-sm" style={{ background: "#F3F4F6", color: "#4B5563" }}>
                  아직 보고서가 있는 아이템이 없어요.{" "}
                  <Link href="/ideas" className="underline font-semibold" style={{ color: "#2F2B4A" }}>
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
                    <div className="text-sm font-semibold" style={{ color: "#2F2B4A" }}>
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
              {shownPrograms.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  aria-pressed={programId === p.id}
                  onClick={() => setProgramId(p.id)}
                  className="text-left rounded-lg px-4 py-3"
                  style={choice(programId === p.id)}
                >
                  <div className="text-sm font-semibold" style={{ color: "#2F2B4A" }}>
                    {p.title}
                  </div>
                  <div className="text-xs mt-0.5" style={{ color: "#6B7280" }}>
                    {p.organization} · {p.amount} · ~{p.ends_on}
                  </div>
                </button>
              ))}
              {shownPrograms.length === 0 && (
                <div className="text-sm p-4" style={{ color: "#6B7280" }}>
                  맞는 공고가 없어요.
                </div>
              )}
            </div>
          </section>
        </div>

        <div className="px-6 py-4 border-t flex items-center justify-between gap-3 flex-wrap" style={{ borderColor: line }}>
          <span className="text-sm" style={{ color: error ? "#B42318" : "#4B5563" }}>
            {error ?? (idea && program ? `${displayTitle(idea)} → ${program.title}` : "아이템과 지원사업을 하나씩 골라주세요")}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="min-h-[44px] px-5 rounded-xl text-sm font-semibold bg-white"
              style={{ border: `1px solid ${line}`, color: "#2F2B4A", cursor: "pointer" }}
            >
              취소
            </button>
            <button
              type="button"
              onClick={submit}
              disabled={!idea || !program || saving}
              className="min-h-[44px] px-5 rounded-xl text-sm font-bold text-white disabled:opacity-50"
              style={{ background: "#7270FF", border: "none", cursor: "pointer" }}
            >
              {saving ? "만드는 중…" : "지원서 만들기"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
