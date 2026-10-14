"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import StatusPill from "@/components/StatusPill";
import { DECISION_META, type Idea, type IdeaStatus, displayTitle, effectiveStatus } from "@/lib/idea";

type CardAction = {
  label: string;
  href?: string;
  /** 버튼 아래 작은 글씨 (예: 유료, 준비 중) */
  note?: string;
  /** 로그인해야 쓸 수 있는 동작 */
  needsLogin?: boolean;
};

/** 단계별 카드 버튼. ?action=은 상세 화면이 받아서 바로 실행한다 */
function actionsFor(idea: Idea, status: IdeaStatus, failedStage: IdeaStatus | null): CardAction[] {
  const base = `/ideas/${idea.id}`;
  switch (status) {
    case "memo":
      return [
        { label: "AI 인터뷰", href: `${base}?action=interview`, needsLogin: true },
        { label: "직접 작성", href: `${base}?action=write`, needsLogin: true },
      ];
    case "interviewing":
      return [
        { label: "인터뷰 이어하기", href: base },
        { label: "직접 작성", href: `${base}?action=write`, needsLogin: true },
      ];
    case "profiling":
    case "diagnosing":
      return [{ label: "진행 보기", href: base }];
    case "profile":
      return [
        { label: "프로필 보기", href: `${base}#profile` },
        { label: "상세분석하기", href: `${base}?action=diagnose`, note: "유료", needsLogin: true },
      ];
    case "report":
      return [
        { label: "보고서 보기", href: `${base}#report` },
        { label: "지원서 쓰기", href: `/applications?new=1&idea=${idea.id}`, needsLogin: true },
      ];
    case "failed":
      return failedStage === "diagnosing"
        ? [
            { label: "프로필 보기", href: `${base}#profile` },
            { label: "다시 분석", href: `${base}?action=diagnose`, note: "유료", needsLogin: true },
          ]
        : [{ label: "다시 시도", href: base }];
  }
}

interface Props {
  idea: Idea;
  open: boolean;
  loggedIn: boolean;
  onToggle: () => void;
  onClose: () => void;
  onDelete: () => void;
}

export default function IdeaCard({ idea, open, loggedIn, onToggle, onClose, onDelete }: Props) {
  const ref = useRef<HTMLElement>(null);
  const { status, failedStage } = effectiveStatus(idea);
  const decision = idea.latestReport?.decision ? DECISION_META[idea.latestReport.decision] : null;
  const title = displayTitle(idea);
  // 이름이 없으면 메모가 제목이 되므로 본문에서 반복하지 않는다
  const body = idea.profile.oneLiner || idea.latestReport?.summary || (idea.memo.trim() !== title ? idea.memo : "");
  const actions = actionsFor(idea, status, failedStage);

  // 열린 카드는 바깥을 누르거나 Esc를 누르면 닫는다
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  return (
    <article
      ref={ref}
      className="relative bg-white rounded-lg shadow-card overflow-hidden h-[232px] transition-shadow hover:shadow-sm"
      style={{ border: "1px solid #E5E7EB" }}
    >
      {/* 카드 전체를 덮는 투명 버튼 — 눌러서 동작 버튼을 연다 */}
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        aria-label={`${title} — 할 일 보기`}
        className="absolute inset-0 w-full h-full"
        style={{ background: "transparent", border: "none", cursor: "pointer" }}
      />

      <div className="relative h-full p-6 flex flex-col gap-3 pointer-events-none">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <StatusPill status={status} />
            {idea.profileChangedSinceReport && (
              <span className="text-xs" style={{ color: "#B45309" }}>
                프로필 수정됨
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={onDelete}
            className="pointer-events-auto text-text-muted text-sm hover:text-danger -mr-1 -mt-1 w-8 h-8"
            style={{ background: "none", border: "none", cursor: "pointer" }}
            title="삭제"
            aria-label={`${title} 삭제`}
          >
            ✕
          </button>
        </div>

        <div className="min-w-0">
          <div className="font-bold text-base mb-1 line-clamp-1">{title}</div>
          {idea.profile.industry && (
            <div className="text-xs text-text-muted line-clamp-1">
              {idea.profile.industry} · {idea.profile.location}
            </div>
          )}
        </div>

        {body && <p className="text-sm text-text-secondary leading-relaxed m-0 line-clamp-2">{body}</p>}

        <div className="mt-auto pt-3 flex items-center justify-between" style={{ borderTop: "1px solid #E5E7EB" }}>
          <span className="text-xs font-semibold" style={{ color: decision?.color ?? "#6B7280" }}>
            {idea.latestReport
              ? `보고서 v${idea.latestReport.version} · ${decision?.label ?? "판정 없음"}`
              : "보고서 전"}
          </span>
          <span className="text-xs text-text-muted">{new Date(idea.updatedAt).toLocaleDateString("ko-KR")}</span>
        </div>
      </div>

      {open && (
        <div
          className="absolute inset-0 flex items-center justify-center gap-5"
          style={{ background: "rgba(28, 26, 44, 0.45)" }}
          onClick={(e) => {
            // 버튼 사이 빈 곳을 누르면 닫는다
            if (e.target === e.currentTarget) onClose();
          }}
        >
          {actions.map((a) => {
            const inner = (
              <>
                <span className="text-sm font-bold leading-tight">{a.label}</span>
                {a.note && <span className="text-[11px] font-medium mt-0.5 opacity-70">{a.note}</span>}
              </>
            );
            const circle =
              "w-[104px] h-[104px] rounded-full flex flex-col items-center justify-center text-center px-3 no-underline transition-transform";
            if (!a.href) {
              return (
                <span
                  key={a.label}
                  aria-disabled="true"
                  className={circle}
                  style={{ background: "rgba(255,255,255,0.7)", color: "#4B5563", cursor: "not-allowed" }}
                >
                  {inner}
                </span>
              );
            }
            const href =
              a.needsLogin && !loggedIn ? `/login?next=${encodeURIComponent(a.href)}` : a.href;
            return (
              <Link
                key={a.label}
                href={href}
                className={`${circle} hover:scale-105`}
                style={{ background: "#fff", color: "#2F2B4A", textDecoration: "none" }}
              >
                {inner}
              </Link>
            );
          })}
        </div>
      )}
    </article>
  );
}
