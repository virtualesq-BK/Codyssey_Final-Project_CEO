"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Header from "@/components/Header";
import IdeaCard from "@/components/IdeaCard";
import { useAuth } from "@/contexts/AuthContext";
import { type Idea, displayTitle } from "@/lib/idea";
import { createMemo, deleteIdea as removeIdea, listIdeas } from "@/lib/ideaStore";

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
  const closeCard = useCallback(() => setOpenId(null), []);

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
    <div className="min-h-screen" style={{ background: "#F5F6F8" }}>
      <Header activeNav="ideas" />

      <div className="max-w-[1200px] mx-auto px-6 py-10">
        <div className="mb-6">
          <div className="text-sm font-semibold mb-1" style={{ color: "#6161FF" }}>MY아이디어</div>
          <h1 className="text-3xl font-bold m-0">내 아이디어</h1>
          <p className="text-text-secondary mt-2 mb-0">메모부터 보고서까지, 단계와 상관없이 모두 모아뒀어요.</p>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            addMemo();
          }}
          className="mb-8 bg-white rounded-3xl shadow-card p-4 flex gap-3 items-end"
          style={{ border: "1px solid #E6E7EA" }}
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
              className="rounded-md px-4 py-3 font-normal text-sm resize-y focus:outline-none leading-relaxed"
              style={{ border: "1.5px solid #DDDFEB", minHeight: 48 }}
            />
          </label>
          <button
            type="submit"
            disabled={saving || !memo.trim()}
            className="min-h-[48px] px-5 rounded-full text-sm font-bold text-white disabled:opacity-50 shrink-0"
            style={{ background: "#6161FF", border: "none", cursor: "pointer" }}
          >
            {saving ? "저장 중…" : "메모 추가"}
          </button>
        </form>
        {memoError && (
          <div className="-mt-5 mb-8 rounded-xl p-3 text-sm" style={{ background: "#FDECEA", color: "#B42318" }}>
            메모를 저장하지 못했어요: {memoError}
          </div>
        )}

        {!authLoading && !user && ideas.length > 0 && (
          <div
            className="mb-6 rounded-xl p-4 text-sm flex items-center justify-between gap-3 flex-wrap"
            style={{ background: "#E7ECFF", color: "#4B4BD9" }}
          >
            <span>이 브라우저에만 저장돼 있어요. 로그인하면 계정으로 옮겨져요.</span>
            <Link href="/login?next=/ideas" className="font-semibold" style={{ color: "#6161FF" }}>
              로그인 ›
            </Link>
          </div>
        )}

        {dataLoading ? (
          <div className="text-center py-16 text-text-muted text-sm">불러오는 중…</div>
        ) : error ? (
          <div className="rounded-xl p-4 text-sm" style={{ background: "#FDECEA", color: "#B42318" }}>
            아이디어를 불러오지 못했어요: {error}
          </div>
        ) : ideas.length === 0 ? (
          <div
            className="bg-white rounded-3xl shadow-card p-16 flex flex-col items-center gap-5 text-center"
            style={{ border: "1px solid #E6E7EA" }}
          >
            <div>
              <div className="font-bold text-lg mb-2">아직 아이디어가 없어요</div>
              <div className="text-text-secondary text-sm">위 칸에 떠오른 아이디어를 한 줄로 메모해 두세요.</div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {ideas.map((idea) => (
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
      </div>
    </div>
  );
}
