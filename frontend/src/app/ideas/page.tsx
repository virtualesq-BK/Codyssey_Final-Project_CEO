"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Header from "@/components/Header";
import PageHero from "@/components/PageHero";
import IdeaCard from "@/components/IdeaCard";
import { useAuth } from "@/contexts/AuthContext";
import { type Idea, type IdeaStatus, displayTitle, effectiveStatus } from "@/lib/idea";
import { createMemo, deleteIdea as removeIdea, listIdeas } from "@/lib/ideaStore";

type Filter = "all" | "memo" | "profile" | "report";

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "전체보기" },
  { key: "memo", label: "메모" },
  { key: "profile", label: "프로필" },
  { key: "report", label: "보고서" },
];

/** 필터 묶음: 프로필이 나오기 전은 '메모', 프로필~진단 중은 '프로필' */
function filterOf(idea: Idea): Exclude<Filter, "all"> {
  const { status, failedStage } = effectiveStatus(idea);
  const s: IdeaStatus = status === "failed" ? (failedStage ?? "memo") : status;
  if (s === "report") return "report";
  if (s === "profile" || s === "diagnosing") return "profile";
  return "memo";
}

export default function IdeasPage() {
  const { user, loading: authLoading } = useAuth();
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [dataLoading, setDataLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [memo, setMemo] = useState("");
  const [saving, setSaving] = useState(false);
  const [memoError, setMemoError] = useState<string | null>(null);
  // 동작 버튼이 열린 카드 (한 번에 하나)
  const [openId, setOpenId] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const closeCard = useCallback(() => setOpenId(null), []);
  const visible = filter === "all" ? ideas : ideas.filter((i) => filterOf(i) === filter);

  // 홈 등에서 ?memo=로 넘어온 한 줄 메모 이어받기
  useEffect(() => {
    const fromLink = new URLSearchParams(window.location.search).get("memo");
    if (fromLink) setMemo(fromLink);
  }, []);

  async function addMemo() {
    if (!memo.trim() || saving) return;
    setSaving(true);
    setMemoError(null);
    try {
      const idea = await createMemo(user, memo);
      setIdeas((prev) => [idea, ...prev]);
      setMemo("");
    } catch (err) {
      setMemoError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    if (authLoading) return;
    setDataLoading(true);
    setError(null);
    listIdeas(user)
      .then(setIdeas)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setDataLoading(false));
  }, [user, authLoading]);

  async function deleteIdea(idea: Idea) {
    if (!confirm(`'${displayTitle(idea)}'을(를) 삭제할까요? 보고서도 함께 지워져요.`)) return;
    setIdeas((prev) => prev.filter((i) => i.id !== idea.id));
    await removeIdea(user, idea.id).catch(() => {});
  }

  return (
    <div className="min-h-screen" style={{ background: "#F3F4F6" }}>
      <Header activeNav="ideas" />

      <PageHero eyebrow="MY아이디어" title="내 아이디어" description="메모부터 보고서까지, 단계와 상관없이 모두 모아뒀어요." />

      <div className="max-w-[1200px] mx-auto px-6 py-8">

        <form
          onSubmit={(e) => {
            e.preventDefault();
            addMemo();
          }}
          className="mb-8 bg-white rounded-lg shadow-card p-4 flex gap-3 items-end"
          style={{ border: "1px solid #E5E7EB" }}
        >
          <label className="flex-1 flex flex-col gap-1.5 text-sm font-semibold">
            새 아이디어 메모
            <textarea
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
              onKeyDown={(e) => {
                // Enter로 저장, Shift+Enter는 줄바꿈. 한글 조합 중 Enter는 무시
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  addMemo();
                }
              }}
              placeholder="떠오른 아이디어를 한 줄로 적어두세요 (Enter로 저장)"
              rows={1}
              className="rounded-lg px-4 py-3 font-normal text-sm resize-y focus:outline-none leading-relaxed"
              style={{ border: "1.5px solid #E5E7EB", minHeight: 48 }}
            />
          </label>
          <button
            type="submit"
            disabled={saving || !memo.trim()}
            className="min-h-[48px] px-5 rounded-xl text-sm font-bold text-white disabled:opacity-50 shrink-0"
            style={{ background: "#134CD8", border: "none", cursor: "pointer" }}
          >
            {saving ? "저장 중…" : "메모 추가"}
          </button>
        </form>
        {memoError && (
          <div className="-mt-5 mb-8 rounded-xl p-3 text-sm" style={{ background: "#FEF2F2", color: "#B42318" }}>
            메모를 저장하지 못했어요: {memoError}
          </div>
        )}

        {!authLoading && !user && ideas.length > 0 && (
          <div
            className="mb-6 rounded-xl p-4 text-sm flex items-center justify-between gap-3 flex-wrap"
            style={{ background: "#FFFFFF", border: "1px solid #E5E7EB", color: "#4B5563" }}
          >
            <span>이 브라우저에만 저장돼 있어요. 로그인하면 계정으로 옮겨져요.</span>
            <Link href="/login?next=/ideas" className="font-semibold underline" style={{ color: "#111111" }}>
              로그인 ›
            </Link>
          </div>
        )}

        {dataLoading ? (
          <div className="text-center py-16 text-text-muted text-sm">불러오는 중…</div>
        ) : error ? (
          <div className="rounded-xl p-4 text-sm" style={{ background: "#FEF2F2", color: "#B42318" }}>
            아이디어를 불러오지 못했어요: {error}
          </div>
        ) : ideas.length === 0 ? (
          <div
            className="bg-white rounded-lg shadow-card p-16 flex flex-col items-center gap-5 text-center"
            style={{ border: "1px solid #E5E7EB" }}
          >
            <div>
              <div className="font-bold text-lg mb-2">아직 아이디어가 없어요</div>
              <div className="text-text-secondary text-sm">위 칸에 떠오른 아이디어를 한 줄로 메모해 두세요.</div>
            </div>
          </div>
        ) : (
          <>
          <div className="flex gap-2 flex-wrap mb-5" role="tablist" aria-label="아이디어 단계 필터">
            {FILTERS.map((f) => {
              const count = f.key === "all" ? ideas.length : ideas.filter((i) => filterOf(i) === f.key).length;
              const active = filter === f.key;
              return (
                <button
                  key={f.key}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  onClick={() => {
                    setFilter(f.key);
                    setOpenId(null);
                  }}
                  className="min-h-[36px] px-4 rounded-xl text-sm font-semibold"
                  style={{
                    cursor: "pointer",
                    border: `1px solid ${active ? "#134CD8" : "#E5E7EB"}`,
                    background: active ? "#EAF0FD" : "#fff",
                    color: active ? "#0F3DB0" : "#4B5563",
                  }}
                >
                  {f.label}
                  <span className="ml-1.5 text-xs font-medium" style={{ color: active ? "#134CD8" : "#6B7280" }}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
          {visible.length === 0 ? (
            <div className="bg-white rounded-lg p-12 text-center text-sm" style={{ border: "1px solid #E5E7EB", color: "#6B7280" }}>
              이 단계의 아이디어가 없어요.
            </div>
          ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {visible.map((idea) => (
              <IdeaCard
                key={idea.id}
                idea={idea}
                open={openId === idea.id}
                loggedIn={!!user}
                onToggle={() => setOpenId((prev) => (prev === idea.id ? null : idea.id))}
                onClose={closeCard}
                onDelete={() => deleteIdea(idea)}
              />
            ))}
          </div>
          )}
          </>
        )}
      </div>
    </div>
  );
}
