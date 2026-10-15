"use client";

import { useEffect, useRef, useState } from "react";
import { INTERVIEW_MAX_QUESTIONS, type IdeaInterview } from "@/lib/idea";
import { useSpeechInput } from "@/lib/useSpeechInput";

interface Props {
  interview: IdeaInterview;
  /** 답변 전송 (실패하면 throw — 입력은 그대로 남긴다) */
  onAnswer: (answer: string) => Promise<void>;
  onFinish: () => void;
  busy: boolean;
  /** 프로필을 만드는 중이거나 실패해 대화를 더 할 수 없는 상태 */
  locked?: boolean;
}

export default function InterviewPanel({ interview, onAnswer, onFinish, busy, locked }: Props) {
  const [answer, setAnswer] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const speech = useSpeechInput(setAnswer);
  // 지금까지 받은 질문 수 (마무리 인사는 질문으로 세지 않음)
  const asked = interview.messages.filter((m) => m.role === "assistant").length - (interview.done ? 1 : 0);
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
    // 듣는 중에 보내면 마이크부터 끈다 (늦게 들어온 인식 결과가 다음 입력칸에 섞이지 않게)
    if (speech.listening) speech.stop();
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
                style={{ background: "#111111", borderRadius: "16px 4px 16px 16px" }}
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
                  style={{ border: "1px solid #D9DBDA", color: "#111111", cursor: "pointer" }}
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
                placeholder={speech.listening ? "듣고 있어요… 말을 마치면 마이크를 다시 눌러주세요" : "편하게 말하듯 적어주세요 (Enter로 보내기)"}
                rows={2}
                disabled={disabled}
                className="w-full rounded-lg p-3 text-sm resize-y focus:outline-none leading-relaxed disabled:bg-surface"
                style={{ border: `1.5px solid ${speech.listening ? "#134CD8" : "#E5E7EB"}` }}
              />
              {speech.error && (
                <span role="alert" className="block mt-1 text-xs" style={{ color: "#B42318" }}>
                  {speech.error}
                </span>
              )}
            </label>
            <button
              type="button"
              onClick={() => (speech.listening ? speech.stop() : speech.start(answer))}
              disabled={disabled || !speech.supported}
              aria-pressed={speech.listening}
              aria-label={speech.listening ? "음성 입력 멈추기" : "음성으로 답하기"}
              title={
                speech.supported
                  ? speech.listening
                    ? "음성 입력 멈추기"
                    : "음성으로 답하기"
                  : "이 브라우저나 주소(https 아님)에서는 음성 입력을 쓸 수 없어요"
              }
              className={`min-h-[48px] w-12 rounded-xl flex items-center justify-center disabled:opacity-40 ${speech.listening ? "animate-pulse" : ""}`}
              style={{
                border: `1px solid ${speech.listening ? "#134CD8" : "#E5E7EB"}`,
                background: speech.listening ? "#EAF0FD" : "#fff",
                cursor: "pointer",
              }}
            >
              <MicIcon active={speech.listening} />
            </button>
            <button
              type="submit"
              disabled={disabled || !answer.trim()}
              className="min-h-[48px] px-5 rounded-xl text-sm font-bold text-white disabled:opacity-50"
              style={{ background: "#111111", border: "none", cursor: "pointer" }}
            >
              보내기
            </button>
          </form>
        )}
      </section>

      <aside className="flex flex-col gap-4" style={{ flex: "1 1 280px", maxWidth: 360 }}>
        <div className="bg-white border border-border rounded-lg p-5 flex flex-col gap-2">
          <div className="flex justify-between items-baseline">
            <b className="text-sm">진행</b>
            <span className="text-xs text-text-muted">
              질문 {Math.min(asked, INTERVIEW_MAX_QUESTIONS)} / 최대 {INTERVIEW_MAX_QUESTIONS}
            </span>
          </div>
          <div className="h-1.5 rounded-full my-1" style={{ background: "#E5E7EB" }}>
            <div
              className="h-1.5 rounded-full transition-all"
              style={{ width: `${(Math.min(asked, INTERVIEW_MAX_QUESTIONS) / INTERVIEW_MAX_QUESTIONS) * 100}%`, background: "#134CD8" }}
            />
          </div>
          <p className="text-xs m-0 leading-relaxed" style={{ color: "#6B7280" }}>
            컨설턴트가 답을 따라가며 필요한 만큼 물어봐요. 충분히 파악하면 그 전에 끝나기도 해요.
          </p>
        </div>

        <div className="bg-white rounded-lg shadow-card p-5 flex flex-col gap-3" style={{ border: "1px solid #E5E7EB" }}>
          <button
            type="button"
            onClick={onFinish}
            disabled={disabled || !answered}
            className="min-h-[52px] rounded-xl text-base font-bold text-white disabled:opacity-50"
            style={{ background: "#134CD8", border: "none", cursor: "pointer" }}
          >
            {locked ? "프로필 만드는 중…" : "인터뷰 마치고 프로필 만들기"}
          </button>
          <p className="text-xs text-text-secondary m-0 leading-relaxed">
            언제든 마칠 수 있어요. 대화에서 나오지 않은 부분은 AI가 현실적으로 채워 넣고, 만든 프로필은 직접 고칠 수 있어요.
          </p>
        </div>
      </aside>
    </div>
  );
}

function MicIcon({ active }: { active: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={active ? "#134CD8" : "#4B5563"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0" />
      <path d="M12 18v3" />
    </svg>
  );
}
