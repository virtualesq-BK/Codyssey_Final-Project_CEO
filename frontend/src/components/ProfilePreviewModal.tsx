"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ModalFrame } from "@/components/DiagnosisModals";
import { PreviewLimitError } from "@/lib/api";
import type { Idea } from "@/lib/idea";

const blue = "#134CD8";
const navy = "#071B45";
const slate = "#53647A";
const gray = "#6B7280";
const line = "#D7E0ED";

// AI 인터뷰가 어떤 식인지 보여주는 고정 예시 2턴 — 실제 인터뷰는 이렇게 10~15분 대화한다
const SCRIPT: { role: "ai" | "me"; text: string }[] = [
  { role: "ai", text: "이 문제를 가장 자주 겪는 사람은 누구인가요?" },
  { role: "me", text: "낮에 집을 비우는 1인 가구 직장인이요." },
  { role: "ai", text: "지금은 그 문제를 어떻게 해결하고 있나요?" },
  { role: "me", text: "틈틈이 홈캠을 보는데, 계속 볼 수는 없어요." },
];
const STEP_MS = 1000;

/**
 * 비로그인 '프로필 미리보기'
 * 인터뷰 예시를 4초쯤 자동 재생하는 동안 메모로 프로필 1~3을 만든다 (같은 IP 하루 1회).
 */
export default function ProfilePreviewModal({
  idea,
  onMake,
  onDone,
  onClose,
}: {
  idea: Idea;
  /** 프로필을 만들어 저장하고 저장된 아이디어를 돌려준다 */
  onMake: () => Promise<Idea>;
  onDone: (idea: Idea) => void;
  onClose: () => void;
}) {
  const reduce = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const [shown, setShown] = useState(reduce ? SCRIPT.length : 0);
  const [result, setResult] = useState<Idea | null>(null);
  const [error, setError] = useState<{ message: string; limit: boolean } | null>(null);
  const started = useRef(false);

  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const close = useCallback(() => closeRef.current(), []);

  const make = useCallback(() => {
    setError(null);
    onMake()
      .then(setResult)
      .catch((err) => setError({ message: err instanceof Error ? err.message : String(err), limit: err instanceof PreviewLimitError }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 열리자마자 생성을 시작하고, 그동안 예시 대화를 한 줄씩 보여준다
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    make();
  }, [make]);
  useEffect(() => {
    if (shown >= SCRIPT.length) return;
    const t = window.setTimeout(() => setShown((n) => n + 1), STEP_MS);
    return () => window.clearTimeout(t);
  }, [shown]);

  const replayDone = shown >= SCRIPT.length;
  // 재생이 끝났고 결과도 왔으면 프로필로 넘어간다
  useEffect(() => {
    if (replayDone && result) {
      const t = window.setTimeout(() => onDone(result), reduce ? 0 : 400);
      return () => window.clearTimeout(t);
    }
  }, [replayDone, result, onDone, reduce]);

  return (
    <ModalFrame labelledBy="preview-title" onClose={close} width={520}>
      <div className="px-6 pt-6 pb-4 flex flex-col gap-1" style={{ borderBottom: `1px solid ${line}` }}>
        <h2 id="preview-title" className="text-lg font-bold m-0" style={{ color: navy }}>
          프로필 미리보기
        </h2>
        <p className="text-sm m-0 leading-relaxed" style={{ color: slate }}>
          실제 AI 인터뷰는 이렇게 대화하며 프로필을 채워요. 미리보기는 메모만으로 바로 만들어요.
        </p>
      </div>

      <div className="px-6 py-5 flex flex-col gap-2.5 min-h-[220px]" aria-live="polite">
        <span className="self-start text-[11px] font-bold px-2 py-0.5 rounded" style={{ background: "#F5F7FB", color: gray }}>
          AI 인터뷰 예시
        </span>
        {SCRIPT.slice(0, shown).map((m, i) => (
          <div
            key={i}
            className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${reduce ? "" : "animate-[fadeUp_.35s_ease-out]"}`}
            style={
              m.role === "ai"
                ? { alignSelf: "flex-start", background: "#F5F7FB", color: navy }
                : { alignSelf: "flex-end", background: blue, color: "#fff" }
            }
          >
            {m.text}
          </div>
        ))}
        {!replayDone && (
          <span className="text-xs" style={{ color: gray }}>
            …
          </span>
        )}
      </div>

      <div className="px-6 py-4 flex flex-col gap-3" style={{ borderTop: `1px solid ${line}` }}>
        {error ? (
          <>
            <p className="m-0 text-sm leading-relaxed" style={{ color: error.limit ? navy : "#B42318" }} role="alert">
              {error.message}
            </p>
            <div className="flex gap-2 justify-end flex-wrap">
              {!error.limit && (
                <button
                  type="button"
                  onClick={make}
                  className="min-h-[44px] px-4 rounded-xl text-sm font-semibold bg-white"
                  style={{ border: `1px solid ${line}`, color: slate, cursor: "pointer" }}
                >
                  다시 시도
                </button>
              )}
              <Link
                href={`/login?next=/ideas/${idea.id}`}
                className="min-h-[44px] px-4 rounded-xl text-sm font-bold text-white no-underline inline-flex items-center"
                style={{ background: blue, textDecoration: "none" }}
              >
                로그인하고 AI 인터뷰 시작
              </Link>
            </div>
          </>
        ) : (
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm" style={{ color: slate }}>
              {result ? "프로필이 준비됐어요" : replayDone ? "메모로 프로필을 정리하는 중… (10~20초)" : "메모를 읽는 중…"}
            </span>
            {!replayDone && (
              <button
                type="button"
                onClick={() => setShown(SCRIPT.length)}
                className="text-xs font-semibold underline p-0"
                style={{ background: "none", border: "none", color: gray, cursor: "pointer" }}
              >
                건너뛰기
              </button>
            )}
          </div>
        )}
      </div>
    </ModalFrame>
  );
}
