"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Header from "@/components/Header";
import PageHero from "@/components/PageHero";
import type { Program } from "@/lib/programs";

const STATUS_COLOR: Record<string, { bg: string; text: string }> = {
  "모집중": { bg: "#E6F9F0", text: "#1A7A4A" },
  "마감임박(D-3)": { bg: "#FFF3CD", text: "#856404" },
  "마감": { bg: "#F5F7FB", text: "#6B7280" },
};

// K-Startup 공고의 지원 지역·분야 값과 맞춘다 (지역을 고르면 '전국' 공고도 함께 나온다)
const REGIONS = ["전체", "전국", "서울", "경기", "인천", "부산", "대구", "대전", "광주", "울산", "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"];
const CATEGORIES = ["전체", "사업화", "멘토링", "시설", "행사", "창업교육", "기술개발", "판로", "글로벌", "융자", "인력"];
const PAGE_SIZE = 30;

const selectStyle = { border: "1.5px solid #D7E0ED" };

export default function ProgramsPage() {
  const [programs, setPrograms] = useState<Program[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [region, setRegion] = useState("전체");
  // 창업자가 가장 많이 찾는 '사업화'를 기본으로 (전체로 바꿀 수 있음)
  const [category, setCategory] = useState("사업화");
  const [status, setStatus] = useState("모집중");
  const [selected, setSelected] = useState<Program | null>(null);
  const [page, setPage] = useState(1);

  async function fetchPrograms() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (status !== "전체") params.set("status", status);
      if (region !== "전체") params.set("region", region);
      if (category !== "전체") params.set("category", category);
      if (q) params.set("q", q);
      const res = await fetch(`/api/v1/programs?${params}`);
      const data = await res.json();
      setPrograms(data.items ?? []);
      setPage(1);
    } catch {
      setPrograms([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchPrograms(); }, [status, region, category]);

  const pageCount = Math.max(1, Math.ceil(programs.length / PAGE_SIZE));
  const current = Math.min(page, pageCount);
  function goPage(n: number) {
    setPage(n);
    window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    fetchPrograms();
  }

  return (
    <div className="min-h-screen" style={{ background: "#F5F7FB" }}>
      <Header activeNav="programs" />

      <PageHero eyebrow="창업 공고 찾기" title="내게 맞는 공고를 찾아보세요" description="정부·지자체 창업 지원 프로그램을 한눈에" />

      <div className="max-w-[1200px] mx-auto px-6 py-8">

        {/* 검색 바 — 1단: 검색어 / 2단: 모집상태 · 지역 · 분야 (이름이 붙어 있어 무엇을 고르는지 보이게) */}
        <form onSubmit={handleSearch} className="bg-white rounded-lg shadow-card p-5 mb-6 flex flex-col gap-4" style={{ border: "1px solid #D7E0ED" }}>
          <div className="flex gap-3">
            <input
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="공고명, 기관명 검색"
              aria-label="검색어"
              className="flex-1 min-w-0 h-11 rounded-lg px-4 text-sm focus:outline-none"
              style={selectStyle}
            />
            <button
              type="submit"
              className="h-11 px-6 rounded-xl text-sm font-bold text-white shrink-0"
              style={{ background: "#134CD8" }}
            >
              검색
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <FilterSelect label="모집상태" value={status} onChange={setStatus}>
              <option value="전체">전체</option>
              <option value="모집중">모집중</option>
              <option value="마감임박(D-3)">마감임박</option>
              <option value="마감">마감</option>
            </FilterSelect>
            <FilterSelect label="지역" value={region} onChange={setRegion}>
              {REGIONS.map((r) => <option key={r}>{r}</option>)}
            </FilterSelect>
            <FilterSelect label="분야" value={category} onChange={setCategory}>
              {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
            </FilterSelect>
          </div>
        </form>

        <div className="flex gap-6">
          {/* 목록 */}
          <div className="flex-1">
            {loading ? (
              <div className="text-center py-16 text-text-muted text-sm">불러오는 중…</div>
            ) : programs.length === 0 ? (
              <div className="text-center py-16 text-text-muted text-sm">검색 결과가 없습니다.</div>
            ) : (
              <div className="flex flex-col gap-3">
                <div className="text-sm text-text-muted mb-1">
                  {programs.length}개 공고
                  {pageCount > 1 && ` · ${(current - 1) * PAGE_SIZE + 1}~${Math.min(current * PAGE_SIZE, programs.length)}번째`}
                </div>
                {programs.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE).map((p) => {
                  const sc = STATUS_COLOR[p.deadline_status] ?? STATUS_COLOR["마감"];
                  return (
                    <div
                      key={p.id}
                      onClick={() => setSelected(p)}
                      className="bg-white rounded-lg shadow-card p-5 cursor-pointer hover:shadow-md transition-shadow"
                      style={{
                        border: selected?.id === p.id ? "2px solid #071B45" : "1px solid #D7E0ED",
                      }}
                    >
                      <div className="flex items-start justify-between gap-3 flex-wrap">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span
                              className="text-xs font-bold px-2 py-0.5 rounded"
                              style={{ background: sc.bg, color: sc.text }}
                            >
                              {p.deadline_status}
                            </span>
                            <span className="text-xs text-text-muted">{p.category}</span>
                            <span className="text-xs text-text-muted">·</span>
                            <span className="text-xs text-text-muted">{p.region}</span>
                          </div>
                          <div className="font-bold text-base mb-1">{p.title}</div>
                          <div className="text-sm text-text-secondary">{p.organization}</div>
                        </div>
                        <div className="text-right shrink-0">
                          <div className="text-xs text-text-muted">마감일</div>
                          <div className="text-sm font-semibold">{p.ends_on}</div>
                          {p.amount && <div className="text-xs font-bold mt-1" style={{ color: "#071B45" }}>{p.amount}</div>}
                        </div>
                      </div>
                    </div>
                  );
                })}
                {pageCount > 1 && <Pager page={current} count={pageCount} onChange={goPage} />}
              </div>
            )}
          </div>

          {/* 상세 패널 */}
          {selected && (
            <div
              className="w-80 shrink-0 bg-white rounded-lg shadow-card p-6 self-start sticky top-20 flex flex-col gap-4"
              style={{ border: "1px solid #D7E0ED" }}
            >
              <div className="flex items-center justify-between">
                <span
                  className="text-xs font-bold px-2 py-0.5 rounded"
                  style={{
                    background: STATUS_COLOR[selected.deadline_status]?.bg ?? "#F5F7FB",
                    color: STATUS_COLOR[selected.deadline_status]?.text ?? "#6B7280",
                  }}
                >
                  {selected.deadline_status}
                </span>
                <button
                  onClick={() => setSelected(null)}
                  className="text-text-muted text-lg leading-none"
                  style={{ background: "none", border: "none", cursor: "pointer" }}
                >
                  ✕
                </button>
              </div>

              <div>
                <div className="font-bold text-base leading-snug mb-1">{selected.title}</div>
                <div className="text-sm text-text-secondary">{selected.organization}</div>
              </div>

              <div className="flex flex-col gap-2 text-sm">
                {selected.amount && (
                  <div className="flex justify-between">
                    <span className="text-text-muted">지원금액</span>
                    <span className="font-semibold" style={{ color: "#071B45" }}>{selected.amount}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-text-muted">접수기간</span>
                  <span className="font-medium">{selected.starts_on} ~ {selected.ends_on}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">지역</span>
                  <span>{selected.region}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">분야</span>
                  <span>{selected.category}</span>
                </div>
              </div>

              <div>
                <div className="text-xs font-semibold text-text-muted mb-1">지원 대상</div>
                <div className="text-sm leading-relaxed">{selected.target}</div>
              </div>

              <div>
                <div className="text-xs font-semibold text-text-muted mb-1">사업 개요</div>
                <div className="text-sm leading-relaxed text-text-secondary">{selected.body}</div>
              </div>

              <Link
                href={`/applications?new=1&program=${selected.id}`}
                className="flex items-center justify-center h-11 rounded-xl font-bold text-sm text-white"
                style={{ background: "#134CD8", textDecoration: "none" }}
              >
                이 공고로 지원서 만들기
              </Link>
              <a
                href={selected.detail_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center h-11 rounded-xl font-semibold text-sm bg-white"
                style={{ border: "1px solid #D7E0ED", color: "#071B45", textDecoration: "none" }}
              >
                공고 원문 보기 →
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function FilterSelect({ label, value, onChange, children }: { label: string; value: string; onChange: (v: string) => void; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-semibold" style={{ color: "#53647A" }}>
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-11 rounded-lg px-3 text-sm bg-white focus:outline-none"
        style={selectStyle}
      >
        {children}
      </select>
    </label>
  );
}

/** 페이지 번호 — 현재 페이지 앞뒤 2개씩 + 처음·끝 */
function Pager({ page, count, onChange }: { page: number; count: number; onChange: (n: number) => void }) {
  const nums = Array.from({ length: count }, (_, i) => i + 1).filter((n) => n === 1 || n === count || Math.abs(n - page) <= 2);
  const btn = "min-w-[40px] h-10 px-2 rounded-lg text-sm font-semibold disabled:opacity-40";
  return (
    <nav aria-label="공고 페이지" className="flex items-center justify-center gap-1 mt-4 flex-wrap">
      <button type="button" onClick={() => onChange(page - 1)} disabled={page === 1} className={btn} style={{ background: "none", border: "none", color: "#53647A", cursor: "pointer" }}>
        ‹ 이전
      </button>
      {nums.map((n, i) => (
        <span key={n} className="flex items-center gap-1">
          {i > 0 && n - nums[i - 1] > 1 && <span style={{ color: "#6B7280" }}>…</span>}
          <button
            type="button"
            onClick={() => onChange(n)}
            aria-current={n === page ? "page" : undefined}
            className={btn}
            style={n === page ? { background: "#071B45", color: "#fff", border: "none", cursor: "pointer" } : { background: "#fff", color: "#071B45", border: "1px solid #D7E0ED", cursor: "pointer" }}
          >
            {n}
          </button>
        </span>
      ))}
      <button type="button" onClick={() => onChange(page + 1)} disabled={page === count} className={btn} style={{ background: "none", border: "none", color: "#53647A", cursor: "pointer" }}>
        다음 ›
      </button>
    </nav>
  );
}
