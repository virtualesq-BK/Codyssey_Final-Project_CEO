"use client";

import { useEffect, useRef, useState } from "react";
import { EMPTY_COVERAGE, INTERVIEW_SLOTS, type IdeaInterview } from "@/lib/idea";

interface Props {
  interview: IdeaInterview;
  /** 답변 전송 (실패하면 throw — 입력은 그대로 남긴다) */
  onAnswer: (answer: string) => Promise<void>;
  onFinish: () => void;
  busy: boolean;
  /** 프로필을 만드는 중이거나 실패해 대화를 더 할 수 없는 상태 */
  locked?: boolean;
}

const SLOT_MARK = { filled: "✓", skipped: "–", empty: "○" } as const;
const SLOT_COLOR = { filled: "#2F2B4A", skipped: "#6B7280", empty: "#6B7280" } as const;

export default function InterviewPanel({ interview, onAnswer, onFinish, busy, locked }: Props) {
  const [answer, setAnswer] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const covered = { ...EMPTY_COVERAGE, ...interview.covered };
  const doneCount = INTERVIEW_SLOTS.filter((s) => covered[s.key] !== "empty").length;
  const answered = interview.messages.some((m) => m.role === "user");
  const disabled = busy || locked;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "nearest" });
  }, [interview.messages.length]);

  // 보내는 동안 입력칸이 잠기며 포커스가 빠지므로, 끝나면 다시 입력칸으로 돌려놓는다
  useEffect(() => {
    if (!busy && !locked) inputRef.current?.focus();
  }, [busy, locked]);

  async function send(text: string) {
    if (!text.trim() || disabled) return;
    try {
      await onAnswer(text);
      setAnswer("");
    } catch {
      // 에러 문구는 상위에서 보여주고, 입력은 다시 보낼 수 있게 남긴다
    }
  }

  return (
    <div className="flex gap-5 flex-wrap items-start">
      <section
        className="bg-white border border-border rounded-lg shadow-card flex flex-col min-w-0"
        style={{ flex: "999 1 520px" }}
        aria-label="딥 인터뷰 대화"
      >
        <div className="px-6 py-4 border-b flex items-center justify-between gap-3 flex-wrap" style={{ borderColor: "#E5E7EB" }}>
          <b>딥 인터뷰</b>
          <span className="text-xs text-text-muted">답할 때마다 저장돼요 · 나중에 이어서 할 수 있어요</span>
        </div>

        <div className="p-6 flex flex-col gap-4 overflow-y-auto" style={{ maxHeight: 560 }}>
          {interview.messages.map((m, i) =>
            m.role === "assistant" ? (
              <div key={i} className="self-start max-w-[80%]">
                <div className="text-xs mb-1" style={{ color: "#4B5563" }}>
                  나도사장 인터뷰어
                </div>
                <div
                  className="px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap"
                  style={{ background: "#F3F4F6", border: "1px solid #E5E7EB", borderRadius: "4px 16px 16px 16px" }}
                >
                  {m.content}
                </div>
              </div>
            ) : (
              <div
                key={i}
                className="self-end max-w-[80%] px-4 py-3 text-sm leading-relaxed text-white whitespace-pre-wrap"
                style={{ background: "#7270FF", borderRadius: "16px 4px 16px 16px" }}
              >
                {m.content}
              </div>
            ),
          )}
          {busy && !locked && (
            <div className="self-start text-xs animate-pulse" style={{ color: "#4B5563" }}>
              인터뷰어가 다음 질문을 고르는 중…
            </div>
          )}
          {!disabled && !interview.done && interview.quickReplies.length > 0 && (
            <div className="flex gap-2 flex-wrap">
              {interview.quickReplies.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => send(q)}
                  className="min-h-[36px] px-3 rounded-full text-xs bg-white"
                  style={{ border: "1px solid #D9DBDA", color: "#2F2B4A", cursor: "pointer" }}
                >
                  {q}
                </button>
              ))}
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {!locked && !interview.done && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(answer);
            }}
            className="px-6 py-4 border-t flex gap-3 items-end"
            style={{ borderColor: "#E5E7EB" }}
          >
            <label className="flex-1 text-sm">
              <span className="sr-only">답변 입력</span>
              <textarea
                ref={inputRef}
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                onKeyDown={(e) => {
                  // Enter로 보내기, Shift+Enter는 줄바꿈. 한글 조합 중 Enter는 무시
                  if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                    e.preventDefault();
                    send(answer);
                  }
                }}
                placeholder="편하게 말하듯 적어주세요 (Enter로 보내기)"
                rows={2}
                disabled={disabled}
                className="w-full rounded-lg p-3 text-sm resize-y focus:outline-none leading-relaxed disabled:bg-surface"
                style={{ border: "1.5px solid #E5E7EB" }}
              />
            </label>
            <button
              type="submit"
              disabled={disabled || !answer.trim()}
              className="min-h-[48px] px-5 rounded-xl text-sm font-bold text-white disabled:opacity-50"
              style={{ background: "#7270FF", border: "none", cursor: "pointer" }}
            >
              보내기
            </button>
          </form>
        )}
      </section>

      <aside className="flex flex-col gap-4" style={{ flex: "1 1 280px", maxWidth: 360 }}>
        <div className="bg-white border border-border rounded-lg shadow-card p-5 flex flex-col gap-2">
          <div className="flex justify-between items-baseline">
            <b className="text-sm">지금까지 들은 것</b>
            <span className="text-xs text-text-muted">
              {INTERVIEW_SLOTS.length}개 중 {doneCount}개
            </span>
          </div>
          <div className="h-1.5 rounded-full my-1" style={{ background: "#E5E7EB" }}>
            <div
              className="h-1.5 rounded-full transition-all"
              style={{ width: `${(doneCount / INTERVIEW_SLOTS.length) * 100}%`, background: "#7270FF" }}
            />
          </div>
          <ul className="m-0 p-0 list-none flex flex-col gap-1.5">
            {INTERVIEW_SLOTS.map((s) => (
              <li key={s.key} className="flex gap-2 text-sm items-center">
                <span className="w-4 font-bold" style={{ color: SLOT_COLOR[covered[s.key]] }} aria-hidden="true">
                  {SLOT_MARK[covered[s.key]]}
                </span>
                <span style={{ color: covered[s.key] === "empty" ? "#4B5563" : "#2F2B4A" }}>{s.label}</span>
                {covered[s.key] === "skipped" && <span className="text-xs text-text-muted">건너뜀</span>}
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-white rounded-lg shadow-card p-5 flex flex-col gap-3" style={{ border: "2px solid #7270FF" }}>
          <button
            type="button"
            onClick={onFinish}
            disabled={disabled || !answered}
            className="min-h-[52px] rounded-xl text-base font-bold text-white disabled:opacity-50"
            style={{ background: "#7270FF", border: "none", cursor: "pointer" }}
          >
            {locked ? "프로필 만드는 중…" : "인터뷰 마치고 프로필 만들기"}
          </button>
          <p className="text-xs text-text-secondary m-0 leading-relaxed">
            덜 답해도 돼요. 답하지 않은 부분은 AI가 추정해서 채우고 'AI 추정'으로 표시해요. 만든 프로필은 직접 고칠 수 있어요.
          </p>
        </div>
      </aside>
    </div>
  );
}
