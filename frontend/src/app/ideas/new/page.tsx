"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Header from "@/components/Header";
import { useAuth } from "@/contexts/AuthContext";
import { analyze, type AnalyzeRequest } from "@/lib/api";
import { AGENT_ORDER } from "@/lib/agents";
import { saveIdea } from "@/lib/ideaStore";

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

export default function NewIdeaPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [form, setForm] = useState<FormState>(INITIAL);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function update(field: keyof FormState, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const t0 = Date.now();
    try {
      const req: AnalyzeRequest = { ...form, business_stage: "idea" };
      const res = await analyze(req);
      const dr = res.workflow_result.decision_result;
      // 판정이 없어도 상세에서 에이전트 결과는 볼 수 있도록 저장
      await saveIdea(
        user,
        {
          id: res.idea_id,
          title: form.title,
          industry: form.industry,
          decision: dr?.decision ?? "VALIDATE_MORE",
          confidence: dr?.confidence ?? 0,
          summary: dr?.summary ?? "",
          savedAt: new Date().toISOString(),
        },
        { input: req, response: res, elapsedMs: Date.now() - t0 },
      ).catch(() => {});
      router.push(`/ideas/${res.idea_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen" style={{ background: "#F4F5F7" }}>
      <Header activeNav="ideas" />

      <main className="max-w-[1200px] mx-auto px-6 py-12 flex flex-col gap-8">
        <section className="bg-white border border-border rounded-2xl p-8 flex flex-col gap-6">
          <div>
            <Link
              href="/"
              className="text-sm text-text-muted mb-4 inline-flex items-center gap-1 hover:text-text-secondary no-underline"
              style={{ textDecoration: "none" }}
            >
              ← 홈으로
            </Link>
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
      </main>
    </div>
  );
}
