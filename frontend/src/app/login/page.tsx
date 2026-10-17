"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";

type Mode = "login" | "signup";

// 로그인 후 돌아갈 곳 (?next=/ideas/...). 다른 사이트로 튀지 않게 내부 경로만 허용
function nextPath() {
  const next = new URLSearchParams(window.location.search).get("next");
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
}

export default function LoginPage() {
  const router = useRouter();
  const { signIn, signUp, signInWithGoogle, resetPassword } = useAuth();

  const [mode, setMode] = useState<Mode>("login");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "login") {
        await signIn(email, password);
      } else {
        if (!displayName.trim()) throw new Error("이름을 입력해 주세요.");
        await signUp(email, password, displayName.trim());
      }
      router.push(nextPath());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(translateFirebaseError(msg));
    } finally {
      setLoading(false);
    }
  }

  async function handleReset() {
    setError(null);
    setNotice(null);
    if (!email.trim()) {
      setError("위에 가입한 이메일을 먼저 입력해 주세요.");
      return;
    }
    setLoading(true);
    try {
      await resetPassword(email.trim());
      // 없는 이메일이어도 보안상 같은 결과를 보여준다 (Firebase도 구분해주지 않음)
      setNotice(`${email.trim()}로 비밀번호 재설정 메일을 보냈어요. 메일이 안 보이면 스팸함도 확인해 주세요.`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(translateFirebaseError(msg));
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogle() {
    setError(null);
    setLoading(true);
    try {
      await signInWithGoogle();
      router.push(nextPath());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(translateFirebaseError(msg));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: "#F5F7FB" }}>
      <div className="w-full max-w-md px-4">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2 no-underline" style={{ textDecoration: "none" }}>
            <span
              className="inline-flex items-center justify-center w-10 h-10 rounded-xl text-white text-lg font-bold"
              style={{ background: "#134CD8" }}
            >
              나
            </span>
            <span className="text-2xl font-bold" style={{ color: "#071B45" }}>나도사장</span>
          </Link>
          <p className="text-sm mt-2" style={{ color: "#6B7280" }}>AI 창업 사업성 진단 서비스</p>
        </div>

        <div className="bg-white rounded-lg shadow-card p-8" style={{ border: "1px solid #D7E0ED" }}>
          {/* 탭 */}
          <div className="flex rounded-xl p-1 mb-6" style={{ background: "#F5F7FB" }}>
            {(["login", "signup"] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setError(null); setNotice(null); }}
                className="flex-1 py-2 rounded-xl text-sm font-semibold transition-all"
                style={{
                  background: mode === m ? "#fff" : "transparent",
                  color: mode === m ? "#071B45" : "#6B7280",
                  border: "none",
                  cursor: "pointer",
                  boxShadow: mode === m ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
                }}
              >
                {m === "login" ? "로그인" : "회원가입"}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {mode === "signup" && (
              <label className="flex flex-col gap-1.5 text-sm font-semibold">
                이름
                <input
                  type="text"
                  required
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="홍길동"
                  className="h-12 rounded-lg px-4 font-normal text-sm focus:outline-none"
                  style={{ border: "1.5px solid #D7E0ED" }}
                  onFocus={(e) => (e.target.style.borderColor = "#134CD8")}
                  onBlur={(e) => (e.target.style.borderColor = "#D7E0ED")}
                />
              </label>
            )}

            <label className="flex flex-col gap-1.5 text-sm font-semibold">
              이메일
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="h-12 rounded-lg px-4 font-normal text-sm focus:outline-none"
                style={{ border: "1.5px solid #D7E0ED" }}
                onFocus={(e) => (e.target.style.borderColor = "#134CD8")}
                onBlur={(e) => (e.target.style.borderColor = "#D7E0ED")}
              />
            </label>

            <label className="flex flex-col gap-1.5 text-sm font-semibold">
              비밀번호
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={mode === "signup" ? "6자 이상" : "비밀번호"}
                minLength={mode === "signup" ? 6 : undefined}
                className="h-12 rounded-lg px-4 font-normal text-sm focus:outline-none"
                style={{ border: "1.5px solid #D7E0ED" }}
                onFocus={(e) => (e.target.style.borderColor = "#134CD8")}
                onBlur={(e) => (e.target.style.borderColor = "#D7E0ED")}
              />
            </label>

            {mode === "login" && (
              <button
                type="button"
                onClick={handleReset}
                disabled={loading}
                className="self-end -mt-2 text-xs font-medium disabled:opacity-60"
                style={{ background: "none", border: "none", color: "#53647A", cursor: "pointer", textDecoration: "underline" }}
              >
                비밀번호를 잊으셨나요?
              </button>
            )}

            {error && (
              <div className="rounded-xl p-3 text-sm" style={{ background: "#FEF2F2", color: "#B42318" }}>
                {error}
              </div>
            )}

            {notice && (
              <div role="status" className="rounded-xl p-3 text-sm" style={{ background: "#F5F7FB", color: "#071B45" }}>
                {notice}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="h-12 rounded-xl font-bold text-sm text-white transition-opacity disabled:opacity-60"
              style={{ background: "#134CD8", border: "none", cursor: loading ? "not-allowed" : "pointer" }}
            >
              {loading ? "처리 중…" : mode === "login" ? "로그인" : "회원가입"}
            </button>
          </form>

          <div className="flex items-center gap-3 my-4">
            <div className="flex-1 h-px" style={{ background: "#D7E0ED" }} />
            <span className="text-xs" style={{ color: "#6B7280" }}>또는</span>
            <div className="flex-1 h-px" style={{ background: "#D7E0ED" }} />
          </div>

          <button
            onClick={handleGoogle}
            disabled={loading}
            className="w-full h-12 rounded-xl font-semibold text-sm flex items-center justify-center gap-3 transition-colors disabled:opacity-60"
            style={{ border: "1.5px solid #D7E0ED", background: "#fff", cursor: loading ? "not-allowed" : "pointer", color: "#071B45" }}
          >
            <GoogleIcon />
            Google로 계속하기
          </button>
        </div>

        <p className="text-center text-xs mt-4" style={{ color: "#6B7280" }}>
          로그인하면 AI 분석 결과가 클라우드에 저장됩니다.
        </p>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
    </svg>
  );
}

function translateFirebaseError(msg: string): string {
  if (msg.includes("user-not-found") || msg.includes("wrong-password") || msg.includes("invalid-credential"))
    return "이메일 또는 비밀번호가 올바르지 않습니다.";
  if (msg.includes("email-already-in-use")) return "이미 사용 중인 이메일입니다.";
  if (msg.includes("weak-password")) return "비밀번호는 6자 이상이어야 합니다.";
  if (msg.includes("invalid-email")) return "이메일 형식이 올바르지 않습니다.";
  if (msg.includes("popup-closed-by-user")) return "Google 로그인 창이 닫혔습니다. 다시 시도해 주세요.";
  if (msg.includes("too-many-requests")) return "요청이 너무 많아요. 잠시 뒤 다시 시도해 주세요.";
  if (msg.includes("missing-email")) return "이메일을 입력해 주세요.";
  if (msg.includes("network-request-failed")) return "네트워크 오류. 인터넷 연결을 확인해 주세요.";
  return msg;
}
