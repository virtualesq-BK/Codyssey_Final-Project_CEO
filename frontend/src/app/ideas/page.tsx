"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Header from "@/components/Header";
import { useAuth } from "@/contexts/AuthContext";
import { type IdeaSummary, deleteIdea as removeIdea, listIdeas } from "@/lib/ideaStore";

const DECISION_CONFIG: Record<string, { label: string; bg: string; color: string }> = {
  GO: { label: "GO", bg: "#E6F9F0", color: "#1A7A4A" },
  PIVOT: { label: "PIVOT", bg: "#FFF3CD", color: "#856404" },
  VALIDATE_MORE: { label: "VALIDATE MORE", bg: "#EEF2FD", color: "#2F5BD3" },
  STOP: { label: "STOP", bg: "#FDECEA", color: "#B42318" },
};

export default function IdeasPage() {
  const { user, loading: authLoading } = useAuth();
  const [ideas, setIdeas] = useState<IdeaSummary[]>([]);
  const [dataLoading, setDataLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    setDataLoading(true);
    listIdeas(user)
      .then(setIdeas)
      .finally(() => setDataLoading(false));
  }, [user, authLoading]);

  async function deleteIdea(id: string) {
    setIdeas((prev) => prev.filter((i) => i.id !== id));
    await removeIdea(user, id).catch(() => {});
  }

  return (
    <div className="min-h-screen" style={{ background: "#F4F5F7" }}>
      <Header activeNav="ideas" />

      <div className="max-w-[1200px] mx-auto px-6 py-10">
        <div className="mb-8 flex items-end justify-between flex-wrap gap-4">
          <div>
            <div className="text-sm font-semibold mb-1" style={{ color: "#2F5BD3" }}>MY아이디어</div>
            <h1 className="text-3xl font-bold m-0">내가 분석한 아이디어</h1>
            <p className="text-text-secondary mt-2 mb-0">AI 진단을 완료한 아이디어 목록입니다.</p>
          </div>
          <Link
            href="/ideas/new"
            className="px-5 py-2.5 rounded-xl text-sm font-bold text-white no-underline"
            style={{ background: "#2F5BD3", textDecoration: "none" }}
          >
            + 새 아이디어 분석
          </Link>
        </div>

        {dataLoading ? (
          <div className="text-center py-16 text-text-muted text-sm">불러오는 중…</div>
        ) : ideas.length === 0 ? (
          <div
            className="bg-white rounded-2xl p-16 flex flex-col items-center gap-5 text-center"
            style={{ border: "1px solid #E8EAEE" }}
          >
            <div className="text-5xl">💡</div>
            <div>
              <div className="font-bold text-lg mb-2">아직 분석한 아이디어가 없어요</div>
              <div className="text-text-secondary text-sm">AI 지원서 탭에서 아이디어를 입력하고 진단을 시작하세요.</div>
            </div>
            <Link
              href="/ideas/new"
              className="px-6 py-3 rounded-xl font-bold text-sm text-white no-underline"
              style={{ background: "#2F5BD3", textDecoration: "none" }}
            >
              아이디어 분석 시작하기
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {ideas.map((idea) => {
              const cfg = DECISION_CONFIG[idea.decision] ?? DECISION_CONFIG["VALIDATE_MORE"];
              return (
                <Link
                  key={idea.id}
                  href={`/ideas/${idea.id}`}
                  className="bg-white rounded-2xl p-6 flex flex-col gap-4 no-underline text-text hover:shadow-sm transition-shadow"
                  style={{ border: "1px solid #E8EAEE", textDecoration: "none" }}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span
                      className="text-xs font-bold px-2.5 py-1 rounded-full"
                      style={{ background: cfg.bg, color: cfg.color }}
                    >
                      {cfg.label}
                    </span>
                    <button
                      onClick={(e) => {
                        // 카드 링크로 이동하지 않고 삭제만
                        e.preventDefault();
                        deleteIdea(idea.id);
                      }}
                      className="text-text-muted text-sm hover:text-danger"
                      style={{ background: "none", border: "none", cursor: "pointer" }}
                      title="삭제"
                    >
                      ✕
                    </button>
                  </div>

                  <div>
                    <div className="font-bold text-base mb-1">{idea.title}</div>
                    <div className="text-xs text-text-muted">{idea.industry}</div>
                  </div>

                  <p className="text-sm text-text-secondary leading-relaxed m-0 line-clamp-3">
                    {idea.summary}
                  </p>

                  <div className="mt-auto pt-3 flex items-center justify-between" style={{ borderTop: "1px solid #E8EAEE" }}>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-text-muted">신뢰도</span>
                      <div className="w-16 h-1.5 bg-[#E8EAEE] rounded-full overflow-hidden">
                        <div
                          className="h-1.5 rounded-full"
                          style={{ width: `${Math.round(idea.confidence * 100)}%`, background: cfg.color }}
                        />
                      </div>
                      <span className="text-xs font-semibold" style={{ color: cfg.color }}>
                        {Math.round(idea.confidence * 100)}%
                      </span>
                    </div>
                    <span className="text-xs text-text-muted">
                      {new Date(idea.savedAt).toLocaleDateString("ko-KR")}
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
