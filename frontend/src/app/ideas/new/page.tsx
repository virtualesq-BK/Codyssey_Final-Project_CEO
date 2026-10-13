"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Header from "@/components/Header";
import { useAuth } from "@/contexts/AuthContext";
import { createMemo } from "@/lib/ideaStore";

export default function NewIdeaPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [memo, setMemo] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 홈에서 적은 한 줄 메모 이어받기
  useEffect(() => {
    const fromHome = new URLSearchParams(window.location.search).get("memo");
    if (fromHome) setMemo(fromHome);
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!memo.trim()) return;
    setError(null);
    setSaving(true);
    try {
      const idea = await createMemo(user, memo);
      router.push(`/ideas/${idea.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSaving(false);
    }
  }

  return (
    <div className="min-h-screen" style={{ background: "#F4F5F7" }}>
      <Header activeNav="ideas" />

      <main className="max-w-[800px] mx-auto px-6 py-12 flex flex-col gap-8">
        <section className="bg-white border border-border rounded-2xl p-8 flex flex-col gap-6">
          <div>
            <Link
              href="/ideas"
              className="text-sm text-text-muted mb-4 inline-flex items-center gap-1 hover:text-text-secondary no-underline"
              style={{ textDecoration: "none" }}
            >
              ← MY아이디어
            </Link>
            <div className="text-sm font-semibold mb-1" style={{ color: "#2F5BD3" }}>
              아이디어 메모
            </div>
            <h1 className="text-3xl font-bold m-0">떠오른 아이디어를 적어두세요</h1>
            <p className="text-text-secondary mt-2 mb-0 leading-relaxed">
              한 줄이면 충분해요. 다음 단계에서 인터뷰로 함께 구체화해요.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <label className="flex flex-col gap-1.5 text-sm font-semibold">
              메모 <span className="sr-only">(필수)</span>
              <textarea
                required
                autoFocus
                value={memo}
                onChange={(e) => setMemo(e.target.value)}
                placeholder="예: 다문화 아이들 학교 수업 따라가게 돕는 한국어 앱"
                rows={4}
                className="rounded-xl p-4 font-normal text-sm resize-y focus:outline-none leading-relaxed"
                style={{ border: "1.5px solid #D9DCE1" }}
                onFocus={(e) => (e.target.style.borderColor = "#2F5BD3")}
                onBlur={(e) => (e.target.style.borderColor = "#D9DCE1")}
              />
            </label>

            {!user && (
              <p className="text-xs text-text-muted m-0">
                로그인하지 않으면 이 브라우저에만 저장돼요. 인터뷰부터는 로그인이 필요해요.
              </p>
            )}

            {error && (
              <div className="rounded-xl p-4 text-sm" style={{ background: "#FDECEA", color: "#B42318" }}>
                저장하지 못했어요: {error}
              </div>
            )}

            <button
              type="submit"
              disabled={saving || !memo.trim()}
              className="self-start min-h-[52px] px-8 rounded-xl font-bold text-base text-white transition-opacity disabled:opacity-60"
              style={{ background: "#2F5BD3", border: "none", cursor: "pointer" }}
            >
              {saving ? "저장 중…" : "메모 저장"}
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}
