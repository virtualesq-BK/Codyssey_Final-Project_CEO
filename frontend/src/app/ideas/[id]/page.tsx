"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import Header from "@/components/Header";
import AgentResultCard from "@/components/AgentResultCard";
import DecisionBanner from "@/components/DecisionBanner";
import { useAuth } from "@/contexts/AuthContext";
import { AGENT_ORDER, STATUS_BG, STATUS_TEXT } from "@/lib/agents";
import { getIdea, type IdeaDetail, type IdeaSummary } from "@/lib/ideaStore";

export default function IdeaDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuth();
  const [summary, setSummary] = useState<IdeaSummary | null>(null);
  const [detail, setDetail] = useState<IdeaDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    setLoading(true);
    getIdea(user, id)
      .then((found) => {
        setSummary(found?.summary ?? null);
        setDetail(found?.detail ?? null);
      })
      .finally(() => setLoading(false));
  }, [id, user, authLoading]);

  const wf = detail?.response.workflow_result;
  const orderedAgents = AGENT_ORDER.filter((k) => k in (wf?.agent_results ?? {}));

  return (
    <div className="min-h-screen" style={{ background: "#F4F5F7" }}>
      <Header activeNav="ideas" />

      <main className="max-w-[1200px] mx-auto px-6 py-12 flex flex-col gap-8">
        <Link
          href="/ideas"
          className="text-sm text-text-muted inline-flex items-center gap-1 hover:text-text-secondary no-underline self-start"
          style={{ textDecoration: "none" }}
        >
          ← MY아이디어
        </Link>

        {loading ? (
          <section className="bg-white border border-border rounded-2xl p-16 text-center text-text-muted text-sm">
            불러오는 중…
          </section>
        ) : !summary ? (
          <section className="bg-white border border-border rounded-2xl p-16 flex flex-col items-center gap-4 text-center">
            <div className="text-5xl">🔍</div>
            <div className="font-bold text-lg">아이디어를 찾을 수 없어요</div>
            <div className="text-text-secondary text-sm">
              삭제됐거나 다른 계정·브라우저에서 분석한 아이디어일 수 있어요.
            </div>
          </section>
        ) : (
          <>
            <div>
              <div className="text-sm font-semibold mb-1" style={{ color: "#2F5BD3" }}>
                {summary.industry}
              </div>
              <h1 className="text-3xl font-bold m-0">{summary.title}</h1>
              <div className="text-xs text-text-muted mt-2">
                {new Date(summary.savedAt).toLocaleString("ko-KR")} 분석
              </div>
            </div>

            {!wf ? (
              // 상세 저장 이전에 분석된 아이디어는 요약만 남아 있음
              <section className="bg-white border border-border rounded-2xl p-8 flex flex-col gap-3">
                <div className="font-bold">{summary.decision} · 신뢰도 {Math.round(summary.confidence * 100)}%</div>
                <p className="text-sm text-text-secondary leading-relaxed m-0">{summary.summary}</p>
                <div className="text-xs text-text-muted">
                  이 아이디어는 요약만 저장되어 있어 에이전트별 상세 결과를 볼 수 없어요.
                </div>
              </section>
            ) : (
              <>
                <div
                  className="rounded-2xl p-5 flex items-center justify-between gap-4 flex-wrap"
                  style={{ background: STATUS_BG[wf.status] ?? "#F4F5F7" }}
                >
                  <div>
                    <span className="font-semibold">{STATUS_TEXT[wf.status] ?? wf.status}</span>
                    {detail?.elapsedMs && (
                      <span className="text-sm ml-3" style={{ color: "#8A909B" }}>
                        소요 {(detail.elapsedMs / 1000).toFixed(1)}초
                      </span>
                    )}
                  </div>
                  <div className="text-xs" style={{ color: "#8A909B" }}>
                    에이전트 {Object.keys(wf.agent_results).length}개 · {summary.title}
                  </div>
                </div>

                {wf.decision_result && <DecisionBanner result={wf.decision_result} />}

                <div>
                  <h2 className="text-xl font-bold mb-4">에이전트별 진단</h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {orderedAgents.map((agentName) => (
                      <AgentResultCard
                        key={agentName}
                        agentName={agentName}
                        result={wf.agent_results[agentName]}
                      />
                    ))}
                  </div>
                </div>
              </>
            )}
          </>
        )}

        <div className="flex justify-center pt-4">
          <Link
            href="/ideas/new"
            className="px-8 py-3 rounded-xl text-sm font-semibold bg-white hover:bg-surface no-underline"
            style={{ border: "1.5px solid #D9DCE1", color: "#4A505B", textDecoration: "none" }}
          >
            다른 아이디어 분석하기
          </Link>
        </div>
      </main>
    </div>
  );
}
