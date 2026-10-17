"use client";

import { useState } from "react";
import { EmailAuthProvider, type User, reauthenticateWithCredential, verifyBeforeUpdateEmail } from "firebase/auth";

const line = "#E5E7EB";

const ERRORS: Record<string, string> = {
  "auth/wrong-password": "현재 비밀번호가 맞지 않아요.",
  "auth/invalid-credential": "현재 비밀번호가 맞지 않아요.",
  "auth/invalid-email": "새 이메일 주소 형식을 확인해 주세요.",
  "auth/email-already-in-use": "이미 다른 계정이 쓰고 있는 이메일이에요.",
  "auth/too-many-requests": "시도가 너무 많아요. 잠시 뒤 다시 해 주세요.",
  "auth/requires-recent-login": "보안을 위해 다시 로그인한 뒤 시도해 주세요.",
  "auth/operation-not-allowed": "지금은 이메일 변경을 쓸 수 없어요. 관리자에게 문의해 주세요.",
};

/**
 * 이메일 변경 — 현재 비밀번호로 본인 확인 → 새 주소로 인증 메일 → 링크를 누르면 바뀐다.
 * 아이디어·보고서는 uid에 묶여 있어 그대로 남는다. 구글 로그인 계정은 구글이 이메일을 관리해 여기서 못 바꾼다.
 */
export default function ChangeEmail({ user }: { user: User }) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const passwordLogin = user.providerData.some((p) => p.providerId === "password");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const next = email.trim();
    if (!next || !password || !user.email) return;
    if (next.toLowerCase() === user.email.toLowerCase()) {
      setError("지금 쓰는 이메일과 같아요.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await reauthenticateWithCredential(user, EmailAuthProvider.credential(user.email, password));
      await verifyBeforeUpdateEmail(user, next);
      setSentTo(next);
      setPassword("");
    } catch (err) {
      const code = (err as { code?: string }).code ?? "";
      setError(ERRORS[code] ?? "이메일을 바꾸지 못했어요. 잠시 뒤 다시 해 주세요.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-card p-6 mb-8 flex flex-col gap-3" style={{ border: `1px solid ${line}` }}>
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <b className="text-base">로그인 이메일</b>
          <div className="text-sm mt-0.5" style={{ color: "#485876" }}>
            {user.email}
          </div>
        </div>
        {passwordLogin && !open && !sentTo && (
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="min-h-[40px] px-4 rounded-xl text-sm font-semibold bg-white"
            style={{ border: `1px solid ${line}`, color: "#08183F", cursor: "pointer" }}
          >
            이메일 변경
          </button>
        )}
      </div>

      {!passwordLogin && (
        <p className="m-0 text-xs" style={{ color: "#6B7280" }}>
          구글로 로그인한 계정은 이메일을 구글 계정에서 관리해요.
        </p>
      )}

      {sentTo && (
        <div className="rounded-lg p-4 text-sm leading-relaxed" style={{ background: "#EAF0FD", color: "#08183F" }}>
          <b>{sentTo}</b>로 인증 메일을 보냈어요. 메일의 링크를 누르면 로그인 이메일이 바뀌어요.
          <br />
          <span className="text-xs" style={{ color: "#485876" }}>
            바뀐 뒤에는 다시 로그인해야 할 수 있어요. 아이디어와 보고서는 그대로 남아요. 메일이 안 오면 스팸함도 확인해 주세요.
          </span>
        </div>
      )}

      {open && !sentTo && (
        <form onSubmit={submit} className="flex flex-col gap-3 max-w-[420px]">
          <label className="flex flex-col gap-1 text-sm font-semibold">
            새 이메일
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="h-11 rounded-lg px-3 text-sm font-normal focus:outline-none"
              style={{ border: `1.5px solid ${line}` }}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm font-semibold">
            현재 비밀번호
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="h-11 rounded-lg px-3 text-sm font-normal focus:outline-none"
              style={{ border: `1.5px solid ${line}` }}
            />
            <span className="text-xs font-normal" style={{ color: "#6B7280" }}>
              본인 확인용이에요. 비밀번호는 바뀌지 않아요.
            </span>
          </label>
          {error && (
            <div role="alert" className="text-sm" style={{ color: "#B42318" }}>
              {error}
            </div>
          )}
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={busy || !email.trim() || !password}
              className="min-h-[44px] px-5 rounded-xl text-sm font-bold text-white disabled:opacity-50"
              style={{ background: "#1B57EA", border: "none", cursor: "pointer" }}
            >
              {busy ? "확인 중…" : "인증 메일 보내기"}
            </button>
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                setError(null);
              }}
              className="min-h-[44px] px-4 rounded-xl text-sm font-semibold bg-white"
              style={{ border: `1px solid ${line}`, color: "#485876", cursor: "pointer" }}
            >
              취소
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
