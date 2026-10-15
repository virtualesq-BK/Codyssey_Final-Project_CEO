"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Header from "@/components/Header";
import { useAuth } from "@/contexts/AuthContext";
import { displayTitle } from "@/lib/idea";
import { listIdeas } from "@/lib/ideaStore";

/** 마이페이지 통계는 판정이 나온 아이디어만 센다 */
type IdeaSummary = {
  id: string;
  title: string;
  industry: string;
  decision: string;
  confidence: number;
  savedAt: string;
};

const DECISION_LABEL: Record<string, string> = {
  GO: "GO", PIVOT: "PIVOT", VALIDATE_MORE: "VALIDATE MORE", STOP: "STOP",
};
const DECISION_COLOR: Record<string, string> = {
  GO: "#1A7A4A", PIVOT: "#856404", VALIDATE_MORE: "#1B57EA", STOP: "#B42318",
};

export default function MyPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [ideas, setIdeas] = useState<IdeaSummary[]>([]);
  const [dataLoading, setDataLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;

    setDataLoading(true);
    listIdeas(user)
      .then((all) =>
        setIdeas(
          all.flatMap((i) =>
            i.latestReport?.decision
              ? [
                  {
                    id: i.id,
                    title: displayTitle(i),
                    industry: i.profile.industry,
                    decision: i.latestReport.decision,
                    confidence: i.latestReport.confidence ?? 0,
                    savedAt: i.latestReport.createdAt,
                  },
                ]
              : [],
          ),
        ),
      )
      .catch(() => setIdeas([]))
      .finally(() => setDataLoading(false));
  }, [user, authLoading]);

  const total = ideas.length;
  const avgConfidence = total > 0
    ? ideas.reduce((s, i) => s + i.confidence, 0) / total
    : 0;
  const decisionCounts = ideas.reduce<Record<string, number>>((acc, i) => {
    acc[i.decision] = (acc[i.decision] ?? 0) + 1;
    return acc;
  }, {});
  const topDecision = Object.entries(decisionCounts).sort((a, b) => b[1] - a[1])[0]?.[0];

  const displayName = user?.displayName ?? user?.email?.split("@")[0] ?? "예비 창업자";
  const avatarLetter = displayName.charAt(0).toUpperCase();

  return (
    <div className="min-h-screen" style={{ background: "#F3F4F6" }}>
      <Header activeNav="mypage" />

      <div className="max-w-[1200px] mx-auto px-6 py-10">
        {/* 프로필 */}
        <div
          className="bg-white rounded-lg shadow-card p-6 mb-8 flex items-center gap-5 flex-wrap"
          style={{ border: "1px solid #E5E7EB" }}
        >
          <div
            className="w-16 h-16 rounded-lg flex items-center justify-center text-2xl font-bold text-white shrink-0"
            style={{ background: "#1B57EA" }}
          >
            {avatarLetter}
          </div>
          <div>
            <div className="font-bold text-xl">{displayName}</div>
            {user?.email && (
              <div className="text-sm text-text-muted mt-0.5">{user.email}</div>
            )}
            <div className="text-xs text-text-muted mt-0.5">나도사장 서비스 이용 중</div>
          </div>
          {!user && (
            <div className="ml-auto flex items-center gap-3">
              <span className="text-xs" style={{ color: "#6B7280" }}>로그인하면 분석 결과가 클라우드에 저장됩니다</span>
              <button
                onClick={() => router.push("/login")}
                className="px-4 py-2 rounded-xl text-sm font-semibold text-white"
                style={{ background: "#1B57EA", border: "none", cursor: "pointer" }}
              >
                로그인
              </button>
            </div>
          )}
          {user && (
            <div
              className="ml-auto px-3 py-1.5 rounded-full text-xs font-medium"
              style={{ background: "#F3F4F6", color: "#485876" }}
            >
              클라우드 저장 활성
            </div>
          )}
        </div>

        {/* 통계 카드 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: "총 분석 건수", value: dataLoading ? "…" : `${total}건`, sub: "누적 AI 진단" },
            {
              label: "평균 신뢰도",
              value: dataLoading ? "…" : total > 0 ? `${Math.round(avgConfidence * 100)}%` : "-",
              sub: "전체 아이디어 평균",
            },
            {
              label: "주요 판정",
              value: dataLoading ? "…" : topDecision ? DECISION_LABEL[topDecision] ?? topDecision : "-",
              sub: "가장 많은 결과",
              color: topDecision ? DECISION_COLOR[topDecision] : undefined,
            },
            { label: "이용 중인 기능", value: "3개", sub: "진단·공고·라운지" },
          ].map((stat) => (
            <div
              key={stat.label}
              className="bg-white rounded-lg shadow-card p-5 flex flex-col gap-1"
              style={{ border: "1px solid #E5E7EB" }}
            >
              <div className="text-xs text-text-muted">{stat.label}</div>
              <div
                className="text-2xl font-bold"
                style={{ color: stat.color ?? "#08183F" }}
              >
                {stat.value}
              </div>
              <div className="text-xs text-text-muted">{stat.sub}</div>
            </div>
          ))}
        </div>

        {/* 최근 아이디어 */}
        <div className="bg-white rounded-lg shadow-card p-6 mb-6" style={{ border: "1px solid #E5E7EB" }}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-bold m-0">최근 분석 아이디어</h2>
            <Link
              href="/ideas"
              className="text-sm font-semibold no-underline"
              style={{ color: "#08183F", textDecoration: "underline" }}
            >
              전체 보기 →
            </Link>
          </div>
          {dataLoading ? (
            <div className="text-center py-8 text-text-muted text-sm">불러오는 중…</div>
          ) : ideas.length === 0 ? (
            <div className="text-center py-8 text-text-muted text-sm">
              아직 분석한 아이디어가 없습니다.{" "}
              <Link href="/ideas" style={{ color: "#08183F" }}>지금 시작하기 →</Link>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {ideas.slice(0, 5).map((idea) => (
                <Link
                  key={idea.id}
                  href={`/ideas/${idea.id}`}
                  className="flex items-center justify-between gap-3 py-3 no-underline text-text"
                  style={{ borderBottom: "1px solid #F3F4F6", textDecoration: "none" }}
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <span
                      className="text-xs font-bold px-2 py-0.5 rounded shrink-0"
                      style={{
                        background: `${DECISION_COLOR[idea.decision] ?? "#6B7280"}18`,
                        color: DECISION_COLOR[idea.decision] ?? "#6B7280",
                      }}
                    >
                      {DECISION_LABEL[idea.decision] ?? idea.decision}
                    </span>
                    <span className="font-medium text-sm truncate">{idea.title}</span>
                    <span className="text-xs text-text-muted shrink-0">{idea.industry}</span>
                  </div>
                  <span className="text-xs text-text-muted shrink-0">
                    {new Date(idea.savedAt).toLocaleDateString("ko-KR")}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* 빠른 메뉴 */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { href: "/ideas", label: "AI 사업성 진단", desc: "새 아이디어 분석하기", icon: "🤖" },
            { href: "/programs", label: "공고 찾기", desc: "맞춤 창업 공고 탐색", icon: "📋" },
            { href: "/lounge", label: "스타트업라운지", desc: "창업 뉴스·리소스", icon: "🚀" },
          ].map((m) => (
            <Link
              key={m.href}
              href={m.href}
              className="bg-white rounded-lg shadow-card p-5 flex items-center gap-4 no-underline hover:shadow-sm transition-shadow"
              style={{ border: "1px solid #E5E7EB", textDecoration: "none" }}
            >
              <span className="text-2xl">{m.icon}</span>
              <div>
                <div className="font-bold text-sm text-text">{m.label}</div>
                <div className="text-xs text-text-muted mt-0.5">{m.desc}</div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
