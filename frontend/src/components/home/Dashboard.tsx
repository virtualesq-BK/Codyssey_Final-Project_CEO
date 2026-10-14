"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { User } from "firebase/auth";
import PageHero from "@/components/PageHero";
import StatusPill from "@/components/StatusPill";
import { APPLICATION_STATUS, type Application } from "@/lib/application";
import { listApplications } from "@/lib/applicationStore";
import { DECISION_META, type Idea, type IdeaStatus, displayTitle, effectiveStatus, missingFields } from "@/lib/idea";
import { createMemo, listIdeas } from "@/lib/ideaStore";
import { type NewsItem, fetchNews } from "@/lib/news";
import { type Program, fetchPrograms } from "@/lib/programs";

const ink = "#2F2B4A";
const slate = "#4B5563";
const iron = "#6B7280";
const line = "#E5E7EB";
const violet = "#7270FF";
const card = "bg-white rounded-lg shadow-card p-5 flex flex-col gap-3";

type NextStep = { idea: Idea | null; title: string; desc: string; cta: string; href: string };

/** 아이디어 하나에서 지금 할 일. 우선순위가 낮을수록 먼저 (없으면 null) */
function stepFor(idea: Idea, apps: Application[]): (NextStep & { rank: number }) | null {
  const { status } = effectiveStatus(idea);
  const name = displayTitle(idea);
  const base = `/ideas/${idea.id}`;
  if (status === "failed")
    return { rank: 0, idea, title: `'${name}' 다시 시도하기`, desc: "진행 중에 끊겼어요. 이어서 다시 할 수 있어요.", cta: "다시 시도", href: base };
  if (status === "interviewing")
    return { rank: 1, idea, title: `'${name}' 인터뷰 이어하기`, desc: "답할 때마다 저장돼 있어요. 마저 답하면 프로필이 만들어져요.", cta: "인터뷰 이어하기", href: base };
  if (status === "profile") {
    const missing = missingFields(idea.profile).length;
    if (missing > 0)
      return { rank: 2, idea, title: `'${name}' 필수 항목 ${missing}개 채우기`, desc: "필수 칸을 채우면 상세분석을 받을 수 있어요.", cta: "프로필 채우기", href: `${base}#profile` };
    return { rank: 3, idea, title: `'${name}' 상세분석 받기`, desc: "시장·경쟁·재무·리스크까지 근거와 함께 진단하고 판정을 내려요.", cta: "상세분석하기", href: `${base}?action=diagnose` };
  }
  if (status === "report" && !apps.some((a) => a.ideaId === idea.id))
    return { rank: 4, idea, title: `'${name}'으로 지원서 만들기`, desc: "보고서가 나왔어요. 맞는 지원사업을 골라 지원서를 시작해 보세요.", cta: "지원서 만들기", href: `/applications?new=1&idea=${idea.id}` };
  if (status === "memo")
    return { rank: 5, idea, title: `'${name}' 인터뷰 시작하기`, desc: "AI 컨설턴트와 대화하며 메모를 아이템 프로필로 키워요.", cta: "인터뷰 시작", href: `${base}?action=interview` };
  return null;
}

/** 마감일까지 남은 날 (지났으면 음수, 날짜를 모르면 null) */
function daysLeft(date: string) {
  const t = Date.parse(date);
  if (Number.isNaN(t)) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.ceil((t - today.getTime()) / 86_400_000);
}

function dday(date: string) {
  const d = daysLeft(date);
  if (d === null) return "";
  if (d < 0) return "마감";
  return d === 0 ? "D-DAY" : `D-${d}`;
}

/** 아이템 지역·분야와 공고를 견줘 점수와 이유를 매긴다 */
function scoreProgram(p: Program, idea: Idea | null) {
  const reasons: string[] = [];
  let score = p.deadline_status === "마감" ? -10 : 0;
  if (idea) {
    const region = idea.profile.location || "전국";
    if (p.region === region && region !== "전국") {
      score += 3;
      reasons.push(`${region} 지역`);
    } else if (p.region === "전국") {
      score += 1;
      reasons.push("전국 대상");
    }
    const words = `${idea.profile.industry} ${idea.profile.oneLiner} ${idea.profile.name}`
      .split(/[\s,·/]+/)
      .filter((w) => w.length >= 2);
    const text = `${p.title} ${p.category} ${p.body} ${p.target}`;
    const hit = words.find((w) => text.includes(w));
    if (hit) {
      score += 3;
      reasons.push(`'${hit}' 관련`);
    }
  }
  if (p.deadline_status !== "마감") reasons.push(p.deadline_status);
  return { score, reasons };
}

export default function Dashboard({ user }: { user: User }) {
  const router = useRouter();
  const [ideas, setIdeas] = useState<Idea[] | null>(null);
  const [apps, setApps] = useState<Application[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [newsIdeaId, setNewsIdeaId] = useState<string | null>(null);
  const [news, setNews] = useState<NewsItem[] | null>(null);
  const [memo, setMemo] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    listIdeas(user).then(setIdeas).catch(() => setIdeas([]));
    listApplications(user).then(setApps).catch(() => setApps([]));
    fetchPrograms().then(setPrograms).catch(() => setPrograms([]));
  }, [user]);

  const recent = useMemo(() => [...(ideas ?? [])].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)), [ideas]);

  // 뉴스·공고 추천의 기준 아이템: 분야나 이름이 있는 최근 아이디어
  const topicIdeas = recent.filter((i) => i.profile.industry.trim() || i.profile.name.trim()).slice(0, 3);
  const topic = topicIdeas.find((i) => i.id === newsIdeaId) ?? topicIdeas[0] ?? null;
  const newsQuery = topic ? [topic.profile.industry.trim(), topic.profile.industry.trim() ? "창업" : topic.profile.name.trim()].filter(Boolean).join(" ") : "";

  useEffect(() => {
    if (ideas === null) return;
    setNews(null);
    fetchNews(newsQuery || "예비창업 지원사업", 5).then(setNews).catch(() => setNews([]));
  }, [ideas, newsQuery]);

  const steps = recent
    .map((i) => stepFor(i, apps))
    .filter((s): s is NextStep & { rank: number } => s !== null)
    .sort((a, b) => a.rank - b.rank);
  const next: NextStep = steps[0] ?? {
    idea: null,
    title: "첫 아이디어를 메모해 보세요",
    desc: "떠오른 아이디어 한 줄이면 충분해요. 인터뷰로 아이템 프로필까지 키워 드려요.",
    cta: "아이디어 메모하기",
    href: "/ideas",
  };

  const counts = (s: IdeaStatus[]) => recent.filter((i) => s.includes(effectiveStatus(i).status)).length;
  const stages = [
    { label: "메모", n: counts(["memo"]) },
    { label: "인터뷰", n: counts(["interviewing", "profiling"]) },
    { label: "프로필", n: counts(["profile", "diagnosing"]) },
    { label: "보고서", n: counts(["report"]) },
  ];

  const openApps = apps
    .filter((a) => a.status === "draft" || a.status === "submitted")
    .sort((a, b) => (daysLeft(a.programDeadline) ?? 9999) - (daysLeft(b.programDeadline) ?? 9999))
    .slice(0, 4);

  const recommended = programs
    .map((p) => ({ p, ...scoreProgram(p, topic) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);

  async function addMemo() {
    if (!memo.trim() || saving) return;
    setSaving(true);
    try {
      const idea = await createMemo(user, memo);
      router.push(`/ideas/${idea.id}`);
    } catch {
      setSaving(false);
    }
  }

  const name = user.displayName || user.email?.split("@")[0] || "사장";

  return (
    <>
      <PageHero
        eyebrow="내 홈"
        title={`${name}님, 오늘은 여기서부터`}
        description={
          ideas === null
            ? "불러오는 중…"
            : `아이디어 ${recent.length}개 · 진행 중인 지원서 ${openApps.length}개`
        }
        actions={
          <Link
            href="/ideas"
            className="min-h-[44px] px-5 rounded-xl text-sm font-bold text-white no-underline inline-flex items-center"
            style={{ background: violet, textDecoration: "none" }}
          >
            + 새 아이디어
          </Link>
        }
      />

      <div className="max-w-[1200px] mx-auto px-6 py-8 grid gap-5 grid-cols-1 lg:grid-cols-[minmax(0,1fr)_360px] items-start">
        {/* ── 왼쪽 ── */}
        <div className="flex flex-col gap-5 min-w-0">
          {/* 다음 할 일 */}
          <section className="bg-white rounded-lg shadow-card p-6 flex flex-col gap-3" style={{ border: `1.5px solid ${violet}` }}>
            <span className="text-xs font-bold" style={{ color: violet }}>
              다음 할 일
            </span>
            <h2 className="text-xl font-bold m-0" style={{ color: ink }}>
              {ideas === null ? "불러오는 중…" : next.title}
            </h2>
            {ideas !== null && (
              <>
                <p className="text-sm m-0 leading-relaxed" style={{ color: slate }}>
                  {next.desc}
                </p>
                <div className="flex items-center gap-3 flex-wrap">
                  <Link
                    href={next.href}
                    className="min-h-[44px] px-5 rounded-xl text-sm font-bold text-white no-underline inline-flex items-center"
                    style={{ background: violet, textDecoration: "none" }}
                  >
                    {next.cta} ›
                  </Link>
                  {steps.length > 1 && (
                    <span className="text-xs" style={{ color: iron }}>
                      그다음: {steps
                        .slice(1, 3)
                        .map((s) => s.title)
                        .join(" · ")}
                    </span>
                  )}
                </div>
              </>
            )}
          </section>

          {/* 내 아이디어 현황 */}
          <section className={card} style={{ border: `1px solid ${line}` }}>
            <div className="flex items-center justify-between">
              <b style={{ color: ink }}>내 아이디어</b>
              <Link href="/ideas" className="text-sm underline" style={{ color: ink }}>
                전체 보기 ›
              </Link>
            </div>
            <div className="grid grid-cols-4 gap-2">
              {stages.map((s) => (
                <div key={s.label} className="rounded-lg py-3 text-center" style={{ background: "#F7F7FB" }}>
                  <div className="text-2xl font-bold" style={{ color: s.n ? ink : "#C4C4D0" }}>
                    {s.n}
                  </div>
                  <div className="text-xs" style={{ color: iron }}>
                    {s.label}
                  </div>
                </div>
              ))}
            </div>
            {recent.slice(0, 3).map((i) => {
              const decision = i.latestReport?.decision ? DECISION_META[i.latestReport.decision] : null;
              return (
                <Link
                  key={i.id}
                  href={`/ideas/${i.id}`}
                  className="flex items-center justify-between gap-3 py-2.5 no-underline border-t"
                  style={{ borderColor: line, color: ink, textDecoration: "none" }}
                >
                  <span className="min-w-0 flex flex-col">
                    <span className="text-sm font-semibold truncate">{displayTitle(i)}</span>
                    <span className="text-xs" style={{ color: iron }}>
                      {new Date(i.updatedAt).toLocaleDateString("ko-KR")} 수정
                    </span>
                  </span>
                  <span className="flex items-center gap-2 shrink-0">
                    {decision && (
                      <span className="text-xs font-bold" style={{ color: decision.color }}>
                        {decision.label}
                      </span>
                    )}
                    <StatusPill status={effectiveStatus(i).status} />
                  </span>
                </Link>
              );
            })}
            {ideas !== null && recent.length === 0 && (
              <p className="text-sm m-0" style={{ color: iron }}>
                아직 아이디어가 없어요.
              </p>
            )}
          </section>

          {/* 관련 뉴스 */}
          <section className={card} style={{ border: `1px solid ${line}` }}>
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <b style={{ color: ink }}>{topic ? "내 아이템 관련 소식" : "창업 관련 소식"}</b>
              {topicIdeas.length > 1 && (
                <div className="flex gap-1.5 flex-wrap">
                  {topicIdeas.map((i) => (
                    <button
                      key={i.id}
                      type="button"
                      onClick={() => setNewsIdeaId(i.id)}
                      className="px-2.5 py-1 rounded-full text-xs font-semibold"
                      style={{
                        cursor: "pointer",
                        border: `1px solid ${i.id === topic?.id ? ink : line}`,
                        background: i.id === topic?.id ? ink : "#fff",
                        color: i.id === topic?.id ? "#fff" : slate,
                      }}
                    >
                      {displayTitle(i)}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {newsQuery && (
              <span className="text-xs" style={{ color: iron }}>
                검색어 &lsquo;{newsQuery}&rsquo;
              </span>
            )}
            {news === null ? (
              <span className="text-sm animate-pulse" style={{ color: iron }}>
                소식을 찾는 중…
              </span>
            ) : news.length === 0 ? (
              <span className="text-sm" style={{ color: iron }}>
                지금은 관련 소식을 불러오지 못했어요.
              </span>
            ) : (
              news.map((n) => (
                <a
                  key={n.url}
                  href={n.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex flex-col gap-0.5 py-2 border-t no-underline"
                  style={{ borderColor: line, color: ink, textDecoration: "none" }}
                >
                  <span className="text-sm font-semibold leading-snug">{n.title}</span>
                  <span className="text-xs" style={{ color: iron }}>
                    {n.source}
                    {n.published_at && ` · ${new Date(n.published_at).toLocaleDateString("ko-KR")}`}
                  </span>
                </a>
              ))
            )}
          </section>
        </div>

        {/* ── 오른쪽 ── */}
        <aside className="flex flex-col gap-5">
          {/* 빠른 메모 */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              addMemo();
            }}
            className={card}
            style={{ border: `1px solid ${line}` }}
          >
            <b style={{ color: ink }}>빠른 메모</b>
            <textarea
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  addMemo();
                }
              }}
              rows={2}
              aria-label="빠른 메모"
              placeholder="떠오른 아이디어를 한 줄로 (Enter로 저장)"
              className="rounded-lg p-3 text-sm resize-none focus:outline-none"
              style={{ border: `1.5px solid ${line}` }}
            />
            <button
              type="submit"
              disabled={!memo.trim() || saving}
              className="min-h-[40px] rounded-xl text-sm font-bold text-white disabled:opacity-50"
              style={{ background: violet, border: "none", cursor: "pointer" }}
            >
              {saving ? "저장 중…" : "메모 저장"}
            </button>
          </form>

          {/* 지원서 진행 */}
          <section className={card} style={{ border: `1px solid ${line}` }}>
            <div className="flex items-center justify-between">
              <b style={{ color: ink }}>진행 중인 지원서</b>
              <Link href="/applications" className="text-sm underline" style={{ color: ink }}>
                전체 ›
              </Link>
            </div>
            {openApps.length === 0 ? (
              <p className="text-sm m-0" style={{ color: iron }}>
                진행 중인 지원서가 없어요.
              </p>
            ) : (
              openApps.map((a) => {
                const st = APPLICATION_STATUS[a.status];
                const d = dday(a.programDeadline);
                const urgent = (daysLeft(a.programDeadline) ?? 99) <= 7 && d !== "마감";
                return (
                  <Link
                    key={a.id}
                    href="/applications"
                    className="flex items-center justify-between gap-2 py-2 border-t no-underline"
                    style={{ borderColor: line, color: ink, textDecoration: "none" }}
                  >
                    <span className="min-w-0 flex flex-col">
                      <span className="text-sm font-semibold truncate">{a.programTitle}</span>
                      <span className="text-xs truncate" style={{ color: iron }}>
                        {a.ideaName}
                      </span>
                    </span>
                    <span className="flex flex-col items-end gap-1 shrink-0">
                      <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded" style={{ background: st.bg, color: st.color }}>
                        {st.label}
                      </span>
                      {d && (
                        <span className="text-xs font-bold" style={{ color: urgent ? "#B42318" : iron }}>
                          {d}
                        </span>
                      )}
                    </span>
                  </Link>
                );
              })
            )}
          </section>

          {/* 추천 공고 */}
          <section className={card} style={{ border: `1px solid ${line}` }}>
            <div className="flex items-center justify-between">
              <b style={{ color: ink }}>{topic ? `'${displayTitle(topic)}'에 맞는 공고` : "모집 중인 공고"}</b>
              <Link href="/programs" className="text-sm underline shrink-0" style={{ color: ink }}>
                더 보기 ›
              </Link>
            </div>
            {recommended.length === 0 ? (
              <p className="text-sm m-0" style={{ color: iron }}>
                공고를 불러오지 못했어요.
              </p>
            ) : (
              recommended.map(({ p, reasons }) => (
                <Link
                  key={p.id}
                  href="/programs"
                  className="flex flex-col gap-1 py-2 border-t no-underline"
                  style={{ borderColor: line, color: ink, textDecoration: "none" }}
                >
                  <span className="text-sm font-semibold leading-snug">{p.title}</span>
                  <span className="text-xs" style={{ color: iron }}>
                    {p.organization} · {p.amount}
                  </span>
                  <span className="flex gap-1 flex-wrap">
                    {reasons.map((r) => (
                      <span key={r} className="text-[11px] px-1.5 py-0.5 rounded" style={{ background: "#F3F4F6", color: slate }}>
                        {r}
                      </span>
                    ))}
                  </span>
                </Link>
              ))
            )}
          </section>
        </aside>
      </div>
    </>
  );
}
