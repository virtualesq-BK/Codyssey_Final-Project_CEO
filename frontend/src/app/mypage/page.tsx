"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Header from "@/components/Header";

const STORAGE_KEY = "nadosajang_ideas";

type SavedIdea = {
  id: string;
  title: string;
  industry: string;
  decision: string;
  confidence: number;
  summary: string;
  savedAt: string;
};

const DECISION_LABEL: Record<string, string> = {
  GO: "GO", PIVOT: "PIVOT", VALIDATE_MORE: "VALIDATE MORE", STOP: "STOP",
};
const DECISION_COLOR: Record<string, string> = {
  GO: "#1A7A4A", PIVOT: "#856404", VALIDATE_MORE: "#2F5BD3", STOP: "#B42318",
};

export default function MyPage() {
  const [ideas, setIdeas] = useState<SavedIdea[]>([]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      setIdeas(raw ? JSON.parse(raw) : []);
    } catch { setIdeas([]); }
  }, []);

  const total = ideas.length;
  const avgConfidence = total > 0
    ? ideas.reduce((s, i) => s + i.confidence, 0) / total
    : 0;
  const decisionCounts = ideas.reduce<Record<string, number>>((acc, i) => {
    acc[i.decision] = (acc[i.decision] ?? 0) + 1;
    return acc;
  }, {});
  const topDecision = Object.entries(decisionCounts).sort((a, b) => b[1] - a[1])[0]?.[0];

  return (
    <div className="min-h-screen" style={{ background: "#F4F5F7" }}>
      <Header activeNav="mypage" />

      <div className="max-w-[1200px] mx-auto px-6 py-10">
        {/* 프로필 */}
        <div
          className="bg-white rounded-2xl p-6 mb-8 flex items-center gap-5 flex-wrap"
          style={{ border: "1px solid #E8EAEE" }}
        >
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center text-2xl font-bold text-white shrink-0"
            style={{ background: "linear-gradient(135deg, #1B2B6B, #2F5BD3)" }}
          >
            나
          </div>
          <div>
            <div className="font-bold text-xl">예비 창업자</div>
            <div className="text-sm text-text-muted mt-0.5">나도사장 서비스 이용 중</div>
          </div>
          <div
            className="ml-auto px-3 py-1.5 rounded-full text-xs font-medium"
            style={{ background: "#EEF2FD", color: "#2F5BD3" }}
          >
            샘플 데이터 모드
          </div>
        </div>

        {/* 통계 카드 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: "총 분석 건수", value: `${total}건`, sub: "누적 AI 진단" },
            {
              label: "평균 신뢰도",
              value: total > 0 ? `${Math.round(avgConfidence * 100)}%` : "-",
              sub: "전체 아이디어 평균",
            },
            {
              label: "주요 판정",
              value: topDecision ? DECISION_LABEL[topDecision] ?? topDecision : "-",
              sub: "가장 많은 결과",
              color: topDecision ? DECISION_COLOR[topDecision] : undefined,
            },
            { label: "이용 중인 기능", value: "3개", sub: "진단·공고·라운지" },
          ].map((stat) => (
            <div
              key={stat.label}
              className="bg-white rounded-2xl p-5 flex flex-col gap-1"
              style={{ border: "1px solid #E8EAEE" }}
            >
              <div className="text-xs text-text-muted">{stat.label}</div>
              <div
                className="text-2xl font-bold"
                style={{ color: stat.color ?? "#1B1D21" }}
              >
                {stat.value}
              </div>
              <div className="text-xs text-text-muted">{stat.sub}</div>
            </div>
          ))}
        </div>

        {/* 최근 아이디어 */}
        <div className="bg-white rounded-2xl p-6 mb-6" style={{ border: "1px solid #E8EAEE" }}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-bold m-0">최근 분석 아이디어</h2>
            <Link
              href="/ideas"
              className="text-sm font-semibold no-underline"
              style={{ color: "#2F5BD3", textDecoration: "none" }}
            >
              전체 보기 →
            </Link>
          </div>
          {ideas.length === 0 ? (
            <div className="text-center py-8 text-text-muted text-sm">아직 분석한 아이디어가 없습니다.</div>
          ) : (
            <div className="flex flex-col gap-3">
              {ideas.slice(0, 5).map((idea) => (
                <div
                  key={idea.id}
                  className="flex items-center justify-between gap-3 py-3"
                  style={{ borderBottom: "1px solid #F4F5F7" }}
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <span
                      className="text-xs font-bold px-2 py-0.5 rounded-full shrink-0"
                      style={{
                        background: `${DECISION_COLOR[idea.decision] ?? "#8A909B"}18`,
                        color: DECISION_COLOR[idea.decision] ?? "#8A909B",
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
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 빠른 메뉴 */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { href: "/", label: "AI 사업성 진단", desc: "새 아이디어 분석하기", icon: "🤖" },
            { href: "/programs", label: "공고 찾기", desc: "맞춤 창업 공고 탐색", icon: "📋" },
            { href: "/lounge", label: "스타트업라운지", desc: "창업 뉴스·리소스", icon: "🚀" },
          ].map((m) => (
            <Link
              key={m.href}
              href={m.href}
              className="bg-white rounded-2xl p-5 flex items-center gap-4 no-underline hover:shadow-sm transition-shadow"
              style={{ border: "1px solid #E8EAEE", textDecoration: "none" }}
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
