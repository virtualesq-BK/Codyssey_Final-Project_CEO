"use client";

import { useState } from "react";
import Header from "@/components/Header";
import AgentResultCard from "@/components/AgentResultCard";
import DecisionBanner from "@/components/DecisionBanner";
import { analyze, type AnalyzeRequest, type AnalyzeResponse, type AgentStatus } from "@/lib/api";

const IDEAS_STORAGE_KEY = "nadosajang_ideas";

function saveIdeaToStorage(idea: {
  id: string; title: string; industry: string;
  decision: string; confidence: number; summary: string; savedAt: string;
}) {
  try {
    const raw = localStorage.getItem(IDEAS_STORAGE_KEY);
    const list = raw ? JSON.parse(raw) : [];
    const filtered = list.filter((i: { id: string }) => i.id !== idea.id);
    filtered.unshift(idea);
    localStorage.setItem(IDEAS_STORAGE_KEY, JSON.stringify(filtered.slice(0, 20)));
  } catch {}
}

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

const STEPS = [
  { step: "01", title: "아이디어 메모", desc: "사업 아이디어를 한 줄로 입력하세요" },
  { step: "02", title: "AI 심층 분석", desc: "6개 에이전트가 병렬로 분석합니다" },
  { step: "03", title: "아이템 프로파일", desc: "시장·고객·경쟁·수익 모델 도출" },
  { step: "04", title: "사업성 진단", desc: "GO / PIVOT / VALIDATE / STOP 판정" },
  { step: "05", title: "공고 & 지원서", desc: "맞춤 창업 공고와 지원서 재료 제공" },
];

export default function Home() {
  const [form, setForm] = useState<FormState>(INITIAL);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [elapsed, setElapsed] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);

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
      // localStorage에 결과 저장
      const dr = res.workflow_result.decision_result;
      if (dr) {
        saveIdeaToStorage({
          id: res.idea_id,
          title: form.title,
          industry: form.industry,
          decision: dr.decision,
          confidence: dr.confidence,
          summary: dr.summary,
          savedAt: new Date().toISOString(),
        });
      }
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

      {/* Hero Section */}
      {!showForm && !result && (
        <section
          className="relative overflow-hidden"
          style={{ background: "linear-gradient(135deg, #1B2B6B 0%, #2F5BD3 60%, #5B8EF5 100%)" }}
        >
          <div className="max-w-[1200px] mx-auto px-6 py-20 flex flex-col items-start gap-6">
            <div
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium"
              style={{ background: "rgba(255,255,255,0.15)", color: "#fff" }}
            >
              <span
                className="w-2 h-2 rounded-full inline-block animate-pulse"
                style={{ background: "#5BEE9A" }}
              />
              AI 에이전트 6개 · 실시간 병렬 분석
            </div>

            <h1 className="text-4xl md:text-5xl font-bold text-white leading-tight m-0">
              아이디어 한 줄에서<br />
              <span style={{ color: "#A5C4FF" }}>지원서 재료까지</span>
            </h1>

            <p className="text-lg text-white/70 max-w-xl m-0 leading-relaxed">
              시장·고객·경쟁·수익모델·재무·리스크를 AI가 병렬 분석하고<br />
              맞춤 창업 공고와 지원서 초안까지 한번에 만들어 드립니다.
            </p>

            <div className="flex gap-3 flex-wrap">
              <button
                onClick={() => setShowForm(true)}
                className="px-6 py-3 rounded-xl font-bold text-base transition-all hover:opacity-90"
                style={{ background: "#fff", color: "#2F5BD3" }}
              >
                아이디어 메모하기
              </button>
              <button
                onClick={() => setShowForm(true)}
                className="px-6 py-3 rounded-xl font-bold text-base border transition-all hover:bg-white/10"
                style={{ borderColor: "rgba(255,255,255,0.4)", color: "#fff" }}
              >
                샘플 결과 보기
              </button>
            </div>

            {/* Diagnosis labels */}
            <div className="flex gap-2 flex-wrap mt-2">
              {[
                { label: "GO", color: "#2ecc71" },
                { label: "PIVOT", color: "#f39c12" },
                { label: "VALIDATE MORE", color: "#3498db" },
                { label: "STOP", color: "#e74c3c" },
              ].map((d) => (
                <span
                  key={d.label}
                  className="px-2.5 py-1 rounded-full text-xs font-bold"
                  style={{ background: `${d.color}25`, color: d.color, border: `1px solid ${d.color}50` }}
                >
                  {d.label}
                </span>
              ))}
            </div>
          </div>

          {/* Decorative circles */}
          <div
            className="absolute top-[-80px] right-[-80px] w-72 h-72 rounded-full opacity-10"
            style={{ background: "#fff" }}
          />
          <div
            className="absolute bottom-[-40px] right-[15%] w-40 h-40 rounded-full opacity-10"
            style={{ background: "#A5C4FF" }}
          />
        </section>
      )}

      {/* Process Steps */}
      {!showForm && !result && (
        <section className="max-w-[1200px] mx-auto px-6 py-14">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-bold m-0">이렇게 진행돼요</h2>
            <p className="text-text-secondary mt-2 mb-0">아이디어 입력부터 지원서 완성까지</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {STEPS.map((s, i) => (
              <div
                key={s.step}
                className="bg-white rounded-2xl p-5 flex flex-col gap-3 relative"
                style={{ border: "1px solid #E8EAEE" }}
              >
                {i < STEPS.length - 1 && (
                  <div
                    className="hidden lg:block absolute top-[28px] right-[-12px] z-10 text-[#D9DCE1] font-bold"
                    style={{ fontSize: 18 }}
                  >
                    →
                  </div>
                )}
                <span
                  className="text-xs font-bold px-2.5 py-1 rounded-full self-start"
                  style={{ background: "#EEF2FD", color: "#2F5BD3" }}
                >
                  STEP {s.step}
                </span>
                <div className="font-bold text-sm">{s.title}</div>
                <div className="text-xs text-text-muted leading-relaxed">{s.desc}</div>
              </div>
            ))}
          </div>

          <div className="flex justify-center mt-10">
            <button
              onClick={() => setShowForm(true)}
              className="px-8 py-3.5 rounded-xl font-bold text-base text-white transition-opacity hover:opacity-90"
              style={{ background: "#2F5BD3" }}
            >
              지금 무료로 시작하기
            </button>
          </div>
        </section>
      )}

      <main className="max-w-[1200px] mx-auto px-6 py-12 flex flex-col gap-8">

        {/* 입력 폼 */}
        {showForm && !result && (
          <section className="bg-white border border-border rounded-2xl p-8 flex flex-col gap-6">
            <div>
              <button
                onClick={() => setShowForm(false)}
                className="text-sm text-text-muted mb-4 flex items-center gap-1 hover:text-text-secondary"
                style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}
              >
                ← 홈으로
              </button>
              <div className="text-sm font-semibold mb-1" style={{ color: "#2F5BD3" }}>
                AI 사업성 진단
              </div>
              <h1 className="text-3xl font-bold m-0">내 아이디어는 될까?</h1>
              <p className="text-text-secondary mt-2 mb-0 leading-relaxed">
                아이디어를 입력하면 6개 에이전트가 시장·고객·경쟁·수익모델·재무·리스크를 병렬 분석합니다.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <label className="flex flex-col gap-1.5 text-sm font-semibold">
                  아이디어 이름 <span style={{ color: "#B42318" }}>*</span>
                  <input
                    type="text"
                    required
                    value={form.title}
                    onChange={(e) => update("title", e.target.value)}
                    placeholder="예: 구독형 반려동물 용품 배송 서비스"
                    className="h-12 rounded-xl px-4 font-normal text-sm focus:outline-none"
                    style={{ border: "1.5px solid #D9DCE1" }}
                    onFocus={(e) => (e.target.style.borderColor = "#2F5BD3")}
                    onBlur={(e) => (e.target.style.borderColor = "#D9DCE1")}
                  />
                </label>

                <label className="flex flex-col gap-1.5 text-sm font-semibold">
                  산업 분야 <span style={{ color: "#B42318" }}>*</span>
                  <input
                    type="text"
                    required
                    value={form.industry}
                    onChange={(e) => update("industry", e.target.value)}
                    placeholder="예: 반려동물, 교육, 헬스케어"
                    className="h-12 rounded-xl px-4 font-normal text-sm focus:outline-none"
                    style={{ border: "1.5px solid #D9DCE1" }}
                    onFocus={(e) => (e.target.style.borderColor = "#2F5BD3")}
                    onBlur={(e) => (e.target.style.borderColor = "#D9DCE1")}
                  />
                </label>
              </div>

              <label className="flex flex-col gap-1.5 text-sm font-semibold">
                해결하려는 문제 <span style={{ color: "#B42318" }}>*</span>
                <textarea
                  required
                  value={form.problem}
                  onChange={(e) => update("problem", e.target.value)}
                  placeholder="누구의 어떤 문제인지 구체적으로"
                  rows={3}
                  className="rounded-xl p-4 font-normal text-sm resize-y focus:outline-none leading-relaxed"
                  style={{ border: "1.5px solid #D9DCE1" }}
                  onFocus={(e) => (e.target.style.borderColor = "#2F5BD3")}
                  onBlur={(e) => (e.target.style.borderColor = "#D9DCE1")}
                />
              </label>

              <label className="flex flex-col gap-1.5 text-sm font-semibold">
                타겟 고객 <span style={{ color: "#B42318" }}>*</span>
                <input
                  type="text"
                  required
                  value={form.customer}
                  onChange={(e) => update("customer", e.target.value)}
                  placeholder="예: 20~40대 직장인 반려동물 보호자"
                  className="h-12 rounded-xl px-4 font-normal text-sm focus:outline-none"
                  style={{ border: "1.5px solid #D9DCE1" }}
                  onFocus={(e) => (e.target.style.borderColor = "#2F5BD3")}
                  onBlur={(e) => (e.target.style.borderColor = "#D9DCE1")}
                />
              </label>

              <label className="flex flex-col gap-1.5 text-sm font-semibold">
                제안 솔루션 <span style={{ color: "#B42318" }}>*</span>
                <textarea
                  required
                  value={form.solution}
                  onChange={(e) => update("solution", e.target.value)}
                  placeholder="어떻게 문제를 해결하는지"
                  rows={3}
                  className="rounded-xl p-4 font-normal text-sm resize-y focus:outline-none leading-relaxed"
                  style={{ border: "1.5px solid #D9DCE1" }}
                  onFocus={(e) => (e.target.style.borderColor = "#2F5BD3")}
                  onBlur={(e) => (e.target.style.borderColor = "#D9DCE1")}
                />
              </label>

              <label className="flex flex-col gap-1.5 text-sm font-semibold">
                사업 지역
                <select
                  value={form.location}
                  onChange={(e) => update("location", e.target.value)}
                  className="h-12 rounded-xl px-4 font-normal text-sm focus:outline-none"
                  style={{ border: "1.5px solid #D9DCE1" }}
                  onFocus={(e) => (e.target.style.borderColor = "#2F5BD3")}
                  onBlur={(e) => (e.target.style.borderColor = "#D9DCE1")}
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
        )}

        {/* 로딩 인디케이터 */}
        {loading && (
          <section className="bg-white border border-border rounded-2xl p-8 flex flex-col gap-4 items-center">
            <div className="text-text-secondary text-sm">6개 에이전트가 병렬 분석 중입니다…</div>
            <div className="w-full max-w-sm">
              <div className="h-2 bg-[#E8EAEE] rounded-full overflow-hidden">
                <div
                  className="h-2 rounded-full animate-pulse"
                  style={{ width: "60%", background: "#2F5BD3" }}
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3 text-xs text-center w-full max-w-sm" style={{ color: "#8A909B" }}>
              {AGENT_ORDER.map((a) => (
                <div key={a} className="rounded-lg p-2" style={{ background: "#F4F5F7" }}>
                  {a.replace("Agent", "")}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 결과 */}
        {wf && (
          <>
            <div
              className="rounded-2xl p-5 flex items-center justify-between gap-4 flex-wrap"
              style={{ background: STATUS_BG[wf.status] ?? "#F4F5F7" }}
            >
              <div>
                <span className="font-semibold">{STATUS_TEXT[wf.status] ?? wf.status}</span>
                {elapsed && (
                  <span className="text-sm ml-3" style={{ color: "#8A909B" }}>
                    소요 {(elapsed / 1000).toFixed(1)}초
                  </span>
                )}
              </div>
              <div className="text-xs" style={{ color: "#8A909B" }}>
                에이전트 {Object.keys(wf.agent_results).length}개 · {form.title}
              </div>
            </div>

            {wf.decision_result && (
              <DecisionBanner result={wf.decision_result} />
            )}

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

            <div className="flex justify-center pt-4">
              <button
                onClick={() => { setResult(null); setElapsed(null); setShowForm(false); }}
                className="px-8 py-3 rounded-xl text-sm font-semibold bg-white hover:bg-surface"
                style={{ border: "1.5px solid #D9DCE1", color: "#4A505B" }}
              >
                다른 아이디어 분석하기
              </button>
            </div>
          </>
        )}
      </main>

      <footer className="border-t border-border bg-white mt-16">
        <div className="max-w-[1200px] mx-auto px-6 py-6 text-xs" style={{ color: "#8A909B" }}>
          나도사장 · AI 분석 결과는 의사결정 지원 목적이며 사업 성공을 보장하지 않습니다.
        </div>
      </footer>
    </div>
  );
}
