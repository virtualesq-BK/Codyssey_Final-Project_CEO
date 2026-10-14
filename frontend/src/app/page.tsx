import Link from "next/link";
import Header from "@/components/Header";

const STEPS = [
  { step: "01", title: "아이디어 메모", desc: "사업 아이디어를 한 줄로 입력하세요" },
  { step: "02", title: "AI 심층 분석", desc: "6개 에이전트가 병렬로 분석합니다" },
  { step: "03", title: "아이템 프로파일", desc: "시장·고객·경쟁·수익 모델 도출" },
  { step: "04", title: "사업성 진단", desc: "GO / PIVOT / VALIDATE / STOP 판정" },
  { step: "05", title: "공고 & 지원서", desc: "맞춤 창업 공고와 지원서 재료 제공" },
];

export default function Home() {
  return (
    <div className="min-h-screen" style={{ background: "#F3F4F6" }}>
      <Header activeNav="analyze" />

      {/* Hero Section — 흰 바탕에 잉크 글자, 강조는 한 단어만 violet (레퍼런스: 차분한 도구형) */}
      <section className="bg-white border-b" style={{ borderColor: "#E5E7EB" }}>
        <div className="max-w-[1200px] mx-auto px-6 py-20 flex flex-col items-start gap-6">
          <div
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium"
            style={{ background: "#F3F4F6", color: "#4B5563" }}
          >
            <span className="w-2 h-2 rounded-full inline-block" style={{ background: "#7270FF" }} />
            AI 에이전트 6개 · 실시간 병렬 분석
          </div>

          <h1 className="text-4xl md:text-5xl font-bold leading-tight m-0 tracking-tight" style={{ color: "#1C1A2C" }}>
            아이디어 한 줄에서
            <br />
            <span style={{ color: "#7270FF" }}>지원서 재료</span>까지
          </h1>

          <p className="text-lg max-w-xl m-0 leading-relaxed" style={{ color: "#4B5563" }}>
            시장·고객·경쟁·수익모델·재무·리스크를 AI가 병렬 분석하고
            <br />
            맞춤 창업 공고와 지원서 초안까지 한번에 만들어 드립니다.
          </p>

          <div className="flex gap-3 flex-wrap">
            <Link
              href="/ideas"
              className="px-6 py-3 rounded-xl font-semibold text-base text-white transition-opacity hover:opacity-90 no-underline"
              style={{ background: "#7270FF", textDecoration: "none" }}
            >
              아이디어 메모하기
            </Link>
            <Link
              href="/ideas"
              className="px-6 py-3 rounded-xl font-semibold text-base transition-colors no-underline bg-white"
              style={{ border: "1px solid #E5E7EB", color: "#2F2B4A", textDecoration: "none" }}
            >
              샘플 결과 보기
            </Link>
          </div>

          <div className="flex gap-2 flex-wrap mt-2">
            {["GO", "PIVOT", "VALIDATE MORE", "STOP"].map((label) => (
              <span
                key={label}
                className="px-2.5 py-1 rounded text-xs font-semibold"
                style={{ background: "#F3F4F6", color: "#4B5563" }}
              >
                {label}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Process Steps */}
      <section className="max-w-[1200px] mx-auto px-6 py-14">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-bold m-0">이렇게 진행돼요</h2>
          <p className="text-text-secondary mt-2 mb-0">아이디어 입력부터 지원서 완성까지</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {STEPS.map((s, i) => (
            <div
              key={s.step}
              className="bg-white rounded-lg shadow-card p-5 flex flex-col gap-3 relative"
              style={{ border: "1px solid #E5E7EB" }}
            >
              {i < STEPS.length - 1 && (
                <div
                  className="hidden lg:block absolute top-[28px] right-[-12px] z-10 text-[#E5E7EB] font-bold"
                  style={{ fontSize: 18 }}
                >
                  →
                </div>
              )}
              <span
                className="text-xs font-bold px-2.5 py-1 rounded self-start"
                style={{ background: "#F3F4F6", color: "#4B5563" }}
              >
                STEP {s.step}
              </span>
              <div className="font-bold text-sm">{s.title}</div>
              <div className="text-xs text-text-muted leading-relaxed">{s.desc}</div>
            </div>
          ))}
        </div>

        <div className="flex justify-center mt-10">
          <Link
            href="/ideas"
            className="px-8 py-3.5 rounded-xl font-bold text-base text-white transition-opacity hover:opacity-90 no-underline"
            style={{ background: "#7270FF", textDecoration: "none" }}
          >
            지금 무료로 시작하기
          </Link>
        </div>
      </section>

      <footer className="border-t border-border bg-white mt-16">
        <div className="max-w-[1200px] mx-auto px-6 py-6 text-xs" style={{ color: "#6B7280" }}>
          나도사장 · AI 분석 결과는 의사결정 지원 목적이며 사업 성공을 보장하지 않습니다.
        </div>
      </footer>
    </div>
  );
}
