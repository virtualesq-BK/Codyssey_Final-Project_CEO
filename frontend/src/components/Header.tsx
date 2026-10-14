"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

interface HeaderProps {
  activeNav?: string;
}

export default function Header({ activeNav }: HeaderProps) {
  const router = useRouter();
  const { user, loading, logout } = useAuth();

  const navItems = [
    { label: "공고 찾기", href: "/programs", key: "programs" },
    { label: "MY아이디어", href: "/ideas", key: "ideas" },
    { label: "MY지원서", href: "/applications", key: "applications" },
    { label: "스타트업라운지", href: "/lounge", key: "lounge" },
    { label: "마이페이지", href: "/mypage", key: "mypage" },
  ];

  async function handleLogout() {
    await logout();
    router.push("/");
  }

  return (
    <header className="bg-white border-b border-border sticky top-0 z-50">
      <div className="max-w-[1200px] mx-auto px-6 min-h-[60px] flex items-center gap-8 flex-wrap">
        <Link
          href="/"
          className="font-bold text-xl no-underline flex items-center gap-2"
          style={{ textDecoration: "none", color: "#2F2B4A" }}
        >
          <span
            className="inline-flex items-center justify-center w-7 h-7 rounded-lg text-white text-sm font-bold"
            style={{ background: "#7270FF" }}
          >
            나
          </span>
          나도사장
        </Link>

        <span
          className="text-xs px-2 py-0.5 rounded font-medium"
          style={{ background: "#F3F4F6", color: "#4B5563" }}
        >
          창업자판 사람인
        </span>

        <nav className="flex gap-1 flex-wrap flex-1 text-sm">
          {navItems.map((item) => (
            <Link
              key={item.key}
              href={item.href}
              className="no-underline font-medium px-3 py-1.5 rounded-xl transition-colors"
              style={{
                color: activeNav === item.key ? "#5B59E0" : "#4B5563",
                fontWeight: activeNav === item.key ? 700 : 500,
                background: activeNav === item.key ? "#EEEEFF" : "transparent",
                textDecoration: "none",
              }}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          {!loading && (
            user ? (
              <>
                <span className="text-sm font-medium" style={{ color: "#4B5563" }}>
                  {user.displayName ?? user.email?.split("@")[0]}
                </span>
                <button
                  onClick={handleLogout}
                  className="text-xs px-3 py-1.5 rounded-xl font-medium transition-colors hover:bg-surface"
                  style={{ border: "1px solid #E5E7EB", color: "#4B5563", background: "#fff", cursor: "pointer" }}
                >
                  로그아웃
                </button>
              </>
            ) : (
              <Link
                href="/login"
                className="text-xs px-3 py-1.5 rounded-xl font-semibold no-underline bg-white"
                style={{ border: "1px solid #E5E7EB", color: "#2F2B4A", textDecoration: "none" }}
              >
                로그인
              </Link>
            )
          )}
        </div>
      </div>
    </header>
  );
}
