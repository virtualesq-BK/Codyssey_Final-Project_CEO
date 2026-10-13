"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Header from "@/components/Header";
import StatusPill from "@/components/StatusPill";
import { useAuth } from "@/contexts/AuthContext";
import { DECISION_META, type Idea, displayTitle, effectiveStatus } from "@/lib/idea";
import { deleteIdea as removeIdea, listIdeas } from "@/lib/ideaStore";

export default function IdeasPage() {
  const { user, loading: authLoading } = useAuth();
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [dataLoading, setDataLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
    <div className="min-h-screen" style={{ background: "#F4F5F7" }}>
      <Header activeNav="ideas" />

      <div className="max-w-[1200px] mx-auto px-6 py-10">
        <div className="mb-8 flex items-end justify-between flex-wrap gap-4">
          <div>
            <div className="text-sm font-semibold mb-1" style={{ color: "#2F5BD3" }}>MY아이디어</div>
            <h1 className="text-3xl font-bold m-0">내 아이디어</h1>
            <p className="text-text-secondary mt-2 mb-0">메모부터 보고서까지, 단계와 상관없이 모두 모아뒀어요.</p>
          </div>
          <Link
            href="/ideas/new"
            className="px-5 py-2.5 rounded-xl text-sm font-bold text-white no-underline"
            style={{ background: "#2F5BD3", textDecoration: "none" }}
          >
            + 새 아이디어 메모
          </Link>
        </div>

        {!authLoading && !user && ideas.length > 0 && (
          <div
            className="mb-6 rounded-xl p-4 text-sm flex items-center justify-between gap-3 flex-wrap"
            style={{ background: "#EEF2FD", color: "#1F3F9E" }}
          >
            <span>이 브라우저에만 저장돼 있어요. 로그인하면 계정으로 옮겨져요.</span>
            <Link href="/login?next=/ideas" className="font-semibold" style={{ color: "#2F5BD3" }}>
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
            className="bg-white rounded-2xl p-16 flex flex-col items-center gap-5 text-center"
            style={{ border: "1px solid #E8EAEE" }}
          >
            <div>
              <div className="font-bold text-lg mb-2">아직 아이디어가 없어요</div>
              <div className="text-text-secondary text-sm">떠오른 아이디어를 한 줄로 메모해 두세요.</div>
            </div>
            <Link
              href="/ideas/new"
              className="px-6 py-3 rounded-xl font-bold text-sm text-white no-underline"
              style={{ background: "#2F5BD3", textDecoration: "none" }}
            >
              아이디어 메모하기
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {ideas.map((idea) => {
              const { status } = effectiveStatus(idea);
              const decision = idea.latestReport?.decision ? DECISION_META[idea.latestReport.decision] : null;
              const title = displayTitle(idea);
              // 이름이 없으면 메모가 제목이 되므로 본문에서 반복하지 않는다
              const body = idea.profile.oneLiner || idea.latestReport?.summary || (idea.memo.trim() !== title ? idea.memo : "");
              return (
                <Link
                  key={idea.id}
                  href={`/ideas/${idea.id}`}
                  className="bg-white rounded-2xl p-6 flex flex-col gap-4 no-underline text-text hover:shadow-sm transition-shadow"
                  style={{ border: "1px solid #E8EAEE", textDecoration: "none" }}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <StatusPill status={status} />
                      {idea.profileChangedSinceReport && (
                        <span className="text-xs" style={{ color: "#B45309" }}>
                          프로필 수정됨
                        </span>
                      )}
                    </div>
                    <button
                      onClick={(e) => {
                        // 카드 링크로 이동하지 않고 삭제만
                        e.preventDefault();
                        deleteIdea(idea);
                      }}
                      className="text-text-muted text-sm hover:text-danger"
                      style={{ background: "none", border: "none", cursor: "pointer" }}
                      title="삭제"
                      aria-label={`${displayTitle(idea)} 삭제`}
                    >
                      ✕
                    </button>
                  </div>

                  <div>
                    <div className="font-bold text-base mb-1">{title}</div>
                    {idea.profile.industry && (
                      <div className="text-xs text-text-muted">
                        {idea.profile.industry} · {idea.profile.location}
                      </div>
                    )}
                  </div>

                  {body && (
                    <p className="text-sm text-text-secondary leading-relaxed m-0 line-clamp-3">{body}</p>
                  )}

                  <div
                    className="mt-auto pt-3 flex items-center justify-between"
                    style={{ borderTop: "1px solid #E8EAEE" }}
                  >
                    <span className="text-xs font-semibold" style={{ color: decision?.color ?? "#8A909B" }}>
                      {idea.latestReport
                        ? `보고서 v${idea.latestReport.version} · ${decision?.label ?? "판정 없음"}`
                        : "보고서 전"}
                    </span>
                    <span className="text-xs text-text-muted">
                      {new Date(idea.updatedAt).toLocaleDateString("ko-KR")}
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
