"use client";

import Link from "next/link";
import Header from "@/components/Header";

const RESOURCES = [
  {
    category: "정부 포털",
    items: [
      { name: "K-스타트업", desc: "창업진흥원 공식 창업 지원 포털", url: "https://www.k-startup.go.kr" },
      { name: "기업마당", desc: "중소벤처기업부 지원사업 통합 안내", url: "https://www.bizinfo.go.kr" },
      { name: "창업기업 확인서", desc: "벤처·이노비즈 확인 신청", url: "https://www.smes.go.kr" },
    ],
  },
  {
    category: "투자·엑셀러레이터",
    items: [
      { name: "스타트업 얼라이언스", desc: "국내 스타트업 생태계 리포트 & 네트워킹", url: "https://startupall.kr" },
      { name: "KIC 창업기획자", desc: "초기 스타트업 발굴 및 보육", url: "https://www.kic.kr" },
      { name: "D.CAMP", desc: "은행권청년창업재단 스타트업 지원", url: "https://dcamp.kr" },
    ],
  },
  {
    category: "교육·커뮤니티",
    items: [
      { name: "TIPS 프로그램", desc: "민간투자 연계 R&D 지원", url: "https://www.jointips.or.kr" },
      { name: "스파크랩", desc: "글로벌 스타트업 액셀러레이터", url: "https://sparklab.co" },
      { name: "퓨처플레이", desc: "딥테크 스타트업 투자·보육", url: "https://futureplay.co" },
    ],
  },
];

const NEWS = [
  {
    tag: "창업 트렌드",
    title: "2025년 정부 창업 지원 예산 역대 최대 규모 편성",
    summary: "중소벤처기업부는 2025년 창업 지원 예산으로 전년 대비 15% 증가한 1.2조원을 편성했다고 밝혔습니다.",
    date: "2025-01-15",
  },
  {
    tag: "투자 동향",
    title: "AI·바이오 스타트업 투자 집중… 2024년 VC 투자 결산",
    summary: "2024년 국내 벤처투자는 AI와 바이오 분야에 집중되며 전체 투자의 약 40%를 차지했습니다.",
    date: "2025-01-10",
  },
  {
    tag: "정책",
    title: "창업 3년 이내 기업 세금 감면 혜택 확대 추진",
    summary: "기획재정부는 창업 초기 기업의 법인세 감면 기간을 5년으로 연장하는 방안을 검토 중입니다.",
    date: "2025-01-08",
  },
  {
    tag: "성공사례",
    title: "초기창업패키지 출신 스타트업 3개사 코스닥 상장",
    summary: "창업진흥원 지원을 받은 스타트업 3개사가 2024년 코스닥에 상장하며 주목받고 있습니다.",
    date: "2025-01-05",
  },
];

export default function LoungePage() {
  return (
    <div className="min-h-screen" style={{ background: "#F4F5F7" }}>
      <Header activeNav="lounge" />

      <div className="max-w-[1200px] mx-auto px-6 py-10">
        <div className="mb-10">
          <div className="text-sm font-semibold mb-1" style={{ color: "#2F5BD3" }}>스타트업라운지</div>
          <h1 className="text-3xl font-bold m-0">창업 생태계 정보 한곳에</h1>
          <p className="text-text-secondary mt-2 mb-0">최신 창업 뉴스, 정부 자원, 투자 트렌드를 확인하세요.</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 뉴스 */}
          <div className="lg:col-span-2 flex flex-col gap-4">
            <h2 className="text-lg font-bold m-0">창업 뉴스</h2>
            {NEWS.map((n, i) => (
              <div
                key={i}
                className="bg-white rounded-2xl p-5 flex flex-col gap-2"
                style={{ border: "1px solid #E8EAEE" }}
              >
                <div className="flex items-center gap-2">
                  <span
                    className="text-xs font-bold px-2 py-0.5 rounded-full"
                    style={{ background: "#EEF2FD", color: "#2F5BD3" }}
                  >
                    {n.tag}
                  </span>
                  <span className="text-xs text-text-muted">{n.date}</span>
                </div>
                <div className="font-bold text-base">{n.title}</div>
                <div className="text-sm text-text-secondary leading-relaxed">{n.summary}</div>
              </div>
            ))}
          </div>

          {/* 리소스 */}
          <div className="flex flex-col gap-6">
            {RESOURCES.map((group) => (
              <div key={group.category}>
                <h2 className="text-base font-bold mb-3">{group.category}</h2>
                <div className="flex flex-col gap-2">
                  {group.items.map((item) => (
                    <a
                      key={item.name}
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="bg-white rounded-xl p-4 flex items-start gap-3 hover:shadow-sm transition-shadow no-underline"
                      style={{ border: "1px solid #E8EAEE", textDecoration: "none" }}
                    >
                      <div
                        className="w-8 h-8 rounded-lg shrink-0 flex items-center justify-center font-bold text-sm text-white"
                        style={{ background: "#2F5BD3" }}
                      >
                        {item.name[0]}
                      </div>
                      <div>
                        <div className="font-semibold text-sm text-text">{item.name}</div>
                        <div className="text-xs text-text-muted leading-relaxed mt-0.5">{item.desc}</div>
                      </div>
                    </a>
                  ))}
                </div>
              </div>
            ))}

            {/* CTA */}
            <div
              className="rounded-2xl p-5 flex flex-col gap-3"
              style={{ background: "linear-gradient(135deg, #1B2B6B 0%, #2F5BD3 100%)" }}
            >
              <div className="text-white font-bold">내 아이디어 AI 진단받기</div>
              <div className="text-white/70 text-sm leading-relaxed">
                6개 에이전트가 내 아이디어의 시장성, 경쟁력, 재무를 분석합니다.
              </div>
              <Link
                href="/"
                className="bg-white text-center rounded-xl py-2.5 text-sm font-bold no-underline"
                style={{ color: "#2F5BD3", textDecoration: "none" }}
              >
                무료로 시작하기
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
