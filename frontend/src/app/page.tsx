"use client";

import { useState } from "react";
import Header from "@/components/Header";
import AgentResultCard from "@/components/AgentResultCard";
import DecisionBanner from "@/components/DecisionBanner";
import { analyze, type AnalyzeRequest, type AnalyzeResponse, type AgentStatus } from "@/lib/api";

const AGENT_ORDER = [
  "MarketAgent",
  "CustomerAgent",
  "CompetitorAgent",
  "BusinessModelAgent",
  "FinancialAgent",
  "RiskAgent",
];

const STATUS_BG: Record<AgentStatus, string> = {
  success: "#F0FFF4",
  partial: "#FFF7EB",
  failed: "#FDECEA",
  running: "#F4F5F7",
  pending: "#F4F5F7",
  skipped: "#F4F5F7",
};

const STATUS_TEXT: Record<string, string> = {
  success: "분석 완료",
  partial: "부분 완료 · 일부 근거 부족",
  failed: "분석 실패",
  running: "분석 중",
  pending: "대기",
  skipped: "건너뜀",
};

type FormState = {
  title: string;
  problem: string;
  customer: string;
  solution: string;
  industry: string;
  location: string;
};

const INITIAL: FormState = {
  title: "",
  problem: "",
  customer: "",
  solution: "",
  industry: "",
  location: "서울",
};

export default function Home() {
  const [form, setForm] = useState<FormState>(INITIAL);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [elapsed, setElapsed] = useState<number | null>(null);

  function update(field: keyof FormState, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);
    const t0 = Date.now();
    try {
      const req: AnalyzeRequest = { ...form, business_stage: "idea" };
      const res = await analyze(req);
      setResult(res);
      setElapsed(Date.now() - t0);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  const wf = result?.workflow_result;
  const orderedAgents = AGENT_ORDER.filter((k) => k in (wf?.agent_results ?? {}));

  return (
    <div className="min-h-screen" style={{ background: "#F4F5F7" }}>
      <Header activeNav="analyze" />

      <main className="max-w-[1200px] mx-auto px-6 py-12 flex flex-col gap-8">

        {/* 입력 폼 */}
        <section className="bg-white border border-border rounded-2xl p-8 flex flex-col gap-6">
          <div>
            <div className="text-sm text-primary font-semibold mb-1">AI 사업성 진단</div>
            <h1 className="text-3xl font-bold m-0">내 아이디어는 될까?</h1>
            <p className="text-text-secondary mt-2 mb-0 leading-relaxed">
              아이디어를 입력하면 6개 에이전트가 시장·고객·경쟁·수익모델·재무·리스크를 병렬 분석합니다.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <label className="flex flex-col gap-1.5 text-sm font-semibold">
                아이디어 이름 <span className="text-danger">*</span>
                <input
                  type="text"
                  required
                  value={form.title}
                  onChange={(e) => update("title", e.target.value)}
                  placeholder="예: 구독형 반려동물 용품 배송 서비스"
                  className="h-12 border border-border-light rounded-xl px-4 font-normal text-sm focus:outline-none focus:border-primary"
                />
              </label>

              <label className="flex flex-col gap-1.5 text-sm font-semibold">
                산업 분야 <span className="text-danger">*</span>
                <input
                  type="text"
                  required
                  value={form.industry}
                  onChange={(e) => update("industry", e.target.value)}
                  placeholder="예: 반려동물, 교육, 헬스케어"
                  className="h-12 border border-border-light rounded-xl px-4 font-normal text-sm focus:outline-none focus:border-primary"
                />
              </label>
            </div>

            <label className="flex flex-col gap-1.5 text-sm font-semibold">
              해결하려는 문제 <span className="text-danger">*</span>
              <textarea
                required
                value={form.problem}
                onChange={(e) => update("problem", e.target.value)}
                placeholder="누구의 어떤 문제인지 구체적으로"
                rows={3}
                className="border border-border-light rounded-xl p-4 font-normal text-sm resize-y focus:outline-none focus:border-primary leading-relaxed"
              />
            </label>

            <label className="flex flex-col gap-1.5 text-sm font-semibold">
              타겟 고객 <span className="text-danger">*</span>
              <input
                type="text"
                required
                value={form.customer}
                onChange={(e) => update("customer", e.target.value)}
                placeholder="예: 20~40대 직장인 반려동물 보호자"
                className="h-12 border border-border-light rounded-xl px-4 font-normal text-sm focus:outline-none focus:border-primary"
              />
            </label>

            <label className="flex flex-col gap-1.5 text-sm font-semibold">
              제안 솔루션 <span className="text-danger">*</span>
              <textarea
                required
                value={form.solution}
                onChange={(e) => update("solution", e.target.value)}
                placeholder="어떻게 문제를 해결하는지"
                rows={3}
                className="border border-border-light rounded-xl p-4 font-normal text-sm resize-y focus:outline-none focus:border-primary leading-relaxed"
              />
            </label>

            <label className="flex flex-col gap-1.5 text-sm font-semibold">
              사업 지역
              <select
                value={form.location}
                onChange={(e) => update("location", e.target.value)}
                className="h-12 border border-border-light rounded-xl px-4 font-normal text-sm focus:outline-none focus:border-primary"
              >
                {["전국","서울","경기","부산","인천","대구","대전","광주","울산","세종"].map((r) => (
                  <option key={r}>{r}</option>
                ))}
              </select>
            </label>

            {error && (
              <div
                className="rounded-xl p-4 text-sm"
                style={{ background: "#FDECEA", color: "#B42318" }}
              >
                오류: {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="self-start min-h-[52px] px-8 rounded-xl font-bold text-base text-white transition-opacity disabled:opacity-60"
              style={{ background: loading ? "#8A909B" : "#2F5BD3" }}
            >
              {loading ? "분석 중…" : "AI 사업성 진단 시작"}
            </button>
          </form>
        </section>

        {/* 로딩 인디케이터 */}
        {loading && (
          <section className="bg-white border border-border rounded-2xl p-8 flex flex-col gap-4 items-center">
            <div className="text-text-secondary text-sm">6개 에이전트가 병렬 분석 중입니다…</div>
            <div className="w-full max-w-sm">
              <div className="h-2 bg-[#E8EAEE] rounded-full overflow-hidden">
                <div
                  className="h-2 rounded-full bg-primary animate-pulse"
                  style={{ width: "60%" }}
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3 text-xs text-text-muted text-center w-full max-w-sm">
              {AGENT_ORDER.map((a) => (
                <div key={a} className="bg-surface rounded-lg p-2">
                  {a.replace("Agent", "")}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 결과 */}
        {wf && (
          <>
            {/* 상태 헤더 */}
            <div
              className="rounded-2xl p-5 flex items-center justify-between gap-4 flex-wrap"
              style={{ background: STATUS_BG[wf.status] ?? "#F4F5F7" }}
            >
              <div>
                <span className="font-semibold">{STATUS_TEXT[wf.status] ?? wf.status}</span>
                {elapsed && (
                  <span className="text-sm text-text-muted ml-3">
                    소요 {(elapsed / 1000).toFixed(1)}초
                  </span>
                )}
              </div>
              <div className="text-xs text-text-muted">
                에이전트 {Object.keys(wf.agent_results).length}개 · {form.title}
              </div>
            </div>

            {/* 종합 판정 */}
            {wf.decision_result && (
              <DecisionBanner result={wf.decision_result} />
            )}

            {/* 에이전트별 결과 */}
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

            {/* 다시 분석하기 */}
            <div className="flex justify-center pt-4">
              <button
                onClick={() => { setResult(null); setElapsed(null); }}
                className="px-8 py-3 border border-border-light rounded-xl text-sm font-semibold text-text-secondary bg-white hover:bg-surface"
              >
                다른 아이디어 분석하기
              </button>
            </div>
          </>
        )}
      </main>

      <footer className="border-t border-border bg-white mt-16">
        <div className="max-w-[1200px] mx-auto px-6 py-6 text-xs text-text-muted">
          나도사장 · AI 분석 결과는 의사결정 지원 목적이며 사업 성공을 보장하지 않습니다.
        </div>
      </footer>
    </div>
  );
}
