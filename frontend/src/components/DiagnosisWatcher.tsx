"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { onDiagnosisFinished, watchDiagnosis } from "@/lib/diagnosisRunner";
import { type Idea, displayTitle } from "@/lib/idea";
import { listIdeas } from "@/lib/ideaStore";

/**
 * 모든 화면에 붙어 있는 상세분석 감시자.
 * - 로그인하면 진단 중인 아이디어를 찾아 결과 감시를 다시 붙인다 (창을 닫았다 와도 이어짐)
 * - 끝나면 화면 아래에 알림을 띄운다 (그 아이디어 화면을 보고 있으면 띄우지 않음 — 모달이 알려줌)
 */
export default function DiagnosisWatcher() {
  const { user, loading } = useAuth();
  const pathname = usePathname();
  const [done, setDone] = useState<Idea | null>(null);

  useEffect(() => {
    if (loading || !user) return;
    listIdeas(user)
      .then((ideas) => ideas.forEach((i) => watchDiagnosis(user, i)))
      .catch(() => {});
  }, [user, loading]);

  useEffect(
    () =>
      onDiagnosisFinished((idea) => {
        if (window.location.pathname === `/ideas/${idea.id}`) return;
        setDone(idea);
      }),
    [],
  );

  // 알림은 8초 뒤 저절로 닫는다
  useEffect(() => {
    if (!done) return;
    const t = setTimeout(() => setDone(null), 8000);
    return () => clearTimeout(t);
  }, [done]);

  useEffect(() => {
    if (done && pathname === `/ideas/${done.id}`) setDone(null);
  }, [pathname, done]);

  if (!done) return null;
  const ok = done.status === "report";
  return (
    <div
      role="status"
      className="fixed left-1/2 -translate-x-1/2 bottom-6 z-[80] w-[calc(100%-32px)] max-w-[480px] rounded-2xl px-5 py-4 flex items-center gap-4"
      style={{ background: "#071B45", color: "#fff", boxShadow: "0 16px 40px rgba(8,24,63,0.35)" }}
    >
      <span className="w-9 h-9 rounded-full flex items-center justify-center shrink-0" style={{ background: ok ? "#134CD8" : "#B42318" }}>
        {ok ? "✓" : "!"}
      </span>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-bold truncate">{displayTitle(done)}</div>
        <div className="text-xs" style={{ color: "rgba(255,255,255,0.75)" }}>
          {ok ? "상세분석 보고서가 나왔어요" : "상세분석이 중간에 실패했어요"}
        </div>
      </div>
      <Link
        href={`/ideas/${done.id}${ok ? "#report" : ""}`}
        onClick={() => setDone(null)}
        className="text-sm font-bold no-underline shrink-0 px-3 py-2 rounded-lg"
        style={{ background: "#FFB91B", color: "#071B45", textDecoration: "none" }}
      >
        {ok ? "보고서 보기" : "확인하기"}
      </Link>
      <button
        type="button"
        onClick={() => setDone(null)}
        aria-label="알림 닫기"
        className="w-8 h-8 shrink-0"
        style={{ background: "none", border: "none", color: "rgba(255,255,255,0.6)", cursor: "pointer" }}
      >
        ✕
      </button>
    </div>
  );
}
