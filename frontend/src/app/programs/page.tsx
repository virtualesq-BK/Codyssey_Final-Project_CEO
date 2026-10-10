"use client";

import { useEffect, useState } from "react";
import Header from "@/components/Header";

type Program = {
  id: string;
  title: string;
  organization: string;
  category: string;
  region: string;
  deadline_status: string;
  ends_on: string;
  starts_on: string;
  target: string;
  body: string;
  detail_url: string;
  amount: string;
};

const STATUS_COLOR: Record<string, { bg: string; text: string }> = {
  "모집중": { bg: "#E6F9F0", text: "#1A7A4A" },
  "마감임박(D-3)": { bg: "#FFF3CD", text: "#856404" },
  "마감": { bg: "#F4F5F7", text: "#8A909B" },
};

const REGIONS = ["전체", "전국", "서울", "경기", "부산", "인천", "대구", "대전", "광주"];
const CATEGORIES = ["전체", "창업지원", "청년창업", "기술창업", "공간지원", "소셜임팩트", "글로벌", "헬스케어"];

export default function ProgramsPage() {
  const [programs, setPrograms] = useState<Program[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [region, setRegion] = useState("전체");
  const [category, setCategory] = useState("전체");
  const [status, setStatus] = useState("모집중");
  const [selected, setSelected] = useState<Program | null>(null);

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
    } catch {
      setPrograms([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchPrograms(); }, [status, region, category]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    fetchPrograms();
  }

  return (
    <div className="min-h-screen" style={{ background: "#F4F5F7" }}>
      <Header activeNav="programs" />

      <div className="max-w-[1200px] mx-auto px-6 py-10">
        <div className="mb-8">
          <div className="text-sm font-semibold mb-1" style={{ color: "#2F5BD3" }}>창업 공고 찾기</div>
          <h1 className="text-3xl font-bold m-0">내게 맞는 공고를 찾아보세요</h1>
          <p className="text-text-secondary mt-2 mb-0">정부·지자체 창업 지원 프로그램을 한눈에</p>
        </div>

        {/* 검색 바 */}
        <form onSubmit={handleSearch} className="bg-white rounded-2xl p-5 mb-6 flex gap-3 flex-wrap" style={{ border: "1px solid #E8EAEE" }}>
          <input
            type="text"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="공고명, 기관명 검색"
            className="flex-1 min-w-[200px] h-11 rounded-xl px-4 text-sm focus:outline-none"
            style={{ border: "1.5px solid #D9DCE1" }}
          />
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="h-11 rounded-xl px-3 text-sm focus:outline-none"
            style={{ border: "1.5px solid #D9DCE1" }}
          >
            <option value="전체">전체 상태</option>
            <option value="모집중">모집중</option>
            <option value="마감임박(D-3)">마감임박</option>
            <option value="마감">마감</option>
          </select>
          <select
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className="h-11 rounded-xl px-3 text-sm focus:outline-none"
            style={{ border: "1.5px solid #D9DCE1" }}
          >
            {REGIONS.map((r) => <option key={r}>{r}</option>)}
          </select>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="h-11 rounded-xl px-3 text-sm focus:outline-none"
            style={{ border: "1.5px solid #D9DCE1" }}
          >
            {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
          </select>
          <button
            type="submit"
            className="h-11 px-6 rounded-xl text-sm font-bold text-white"
            style={{ background: "#2F5BD3" }}
          >
            검색
          </button>
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
                <div className="text-sm text-text-muted mb-1">{programs.length}개 공고</div>
                {programs.map((p) => {
                  const sc = STATUS_COLOR[p.deadline_status] ?? STATUS_COLOR["마감"];
                  return (
                    <div
                      key={p.id}
                      onClick={() => setSelected(p)}
                      className="bg-white rounded-2xl p-5 cursor-pointer hover:shadow-md transition-shadow"
                      style={{
                        border: selected?.id === p.id ? "2px solid #2F5BD3" : "1px solid #E8EAEE",
                      }}
                    >
                      <div className="flex items-start justify-between gap-3 flex-wrap">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span
                              className="text-xs font-bold px-2 py-0.5 rounded-full"
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
                          <div className="text-xs font-bold mt-1" style={{ color: "#2F5BD3" }}>{p.amount}</div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* 상세 패널 */}
          {selected && (
            <div
              className="w-80 shrink-0 bg-white rounded-2xl p-6 self-start sticky top-20 flex flex-col gap-4"
              style={{ border: "1px solid #E8EAEE" }}
            >
              <div className="flex items-center justify-between">
                <span
                  className="text-xs font-bold px-2 py-0.5 rounded-full"
                  style={{
                    background: STATUS_COLOR[selected.deadline_status]?.bg ?? "#F4F5F7",
                    color: STATUS_COLOR[selected.deadline_status]?.text ?? "#8A909B",
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
                <div className="flex justify-between">
                  <span className="text-text-muted">지원금액</span>
                  <span className="font-semibold" style={{ color: "#2F5BD3" }}>{selected.amount}</span>
                </div>
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

              <a
                href={selected.detail_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center h-11 rounded-xl font-bold text-sm text-white"
                style={{ background: "#2F5BD3", textDecoration: "none" }}
              >
                공고 상세 보기 →
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
