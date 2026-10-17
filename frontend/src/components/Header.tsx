"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

interface HeaderProps {
  activeNav?: string;
}

export default function Header({ activeNav }: HeaderProps) {
  const router = useRouter();
  const { user, loading, logout } = useAuth();
  // 좁은 화면(lg 미만)에선 메뉴를 햄버거 버튼 아래 펼침 목록으로 접는다
  const [menuOpen, setMenuOpen] = useState(false);
  const pathname = usePathname();
  useEffect(() => setMenuOpen(false), [pathname]);

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
      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 h-[60px] flex items-center gap-8 lg:grid lg:grid-cols-[1fr_auto_1fr]">
        {/* 넓은 화면: 로고 | 메뉴(정가운데) | 로그인 — 양옆 칸 너비를 같게 둬서 메뉴가 화면 중앙에 온다 */}
        <Link href="/" aria-label="나도사장 홈" className="flex items-center shrink-0 no-underline lg:justify-self-start" style={{ textDecoration: "none" }}>
          {/* 가로형 로고 (assets/logo.png를 한 줄로 이어 붙인 사본) */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/brand/logo-horizontal.png" alt="나도사장" className="h-[28px] w-auto block" />
        </Link>

        <nav className="hidden lg:flex gap-1 text-sm">
          {navItems.map((item) => (
            <Link
              key={item.key}
              href={item.href}
              className="no-underline font-medium px-3 py-1.5 rounded-xl transition-colors whitespace-nowrap"
              style={{
                color: activeNav === item.key ? "#0F3DB0" : "#53647A",
                fontWeight: activeNav === item.key ? 700 : 500,
                background: activeNav === item.key ? "#EAF0FD" : "transparent",
                textDecoration: "none",
              }}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2 ml-auto lg:ml-0 lg:justify-self-end">
          {!loading && (
            user ? (
              <>
                <span className="hidden sm:inline text-sm font-medium" style={{ color: "#53647A" }}>
                  {user.displayName ?? user.email?.split("@")[0]}
                </span>
                <button
                  onClick={handleLogout}
                  className="text-xs px-3 py-1.5 rounded-xl font-medium transition-colors hover:bg-surface whitespace-nowrap"
                  style={{ border: "1px solid #D7E0ED", color: "#53647A", background: "#fff", cursor: "pointer" }}
                >
                  로그아웃
                </button>
              </>
            ) : (
              <Link
                href="/login"
                className="text-xs px-3 py-1.5 rounded-xl font-semibold no-underline bg-white"
                style={{ border: "1px solid #D7E0ED", color: "#071B45", textDecoration: "none" }}
              >
                로그인
              </Link>
            )
          )}
          <button
            type="button"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label={menuOpen ? "메뉴 닫기" : "메뉴 열기"}
            aria-expanded={menuOpen}
            aria-controls="mobile-nav"
            className="lg:hidden w-10 h-10 -mr-2 inline-flex items-center justify-center rounded-xl"
            style={{ background: "none", border: "none", cursor: "pointer", color: "#071B45" }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              {menuOpen ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
            </svg>
          </button>
        </div>
      </div>

      {menuOpen && (
        <nav id="mobile-nav" className="lg:hidden border-t border-border bg-white px-4 py-2 flex flex-col">
          {navItems.map((item) => (
            <Link
              key={item.key}
              href={item.href}
              onClick={() => setMenuOpen(false)}
              className="no-underline px-3 py-3 rounded-xl text-sm"
              style={{
                color: activeNav === item.key ? "#0F3DB0" : "#071B45",
                fontWeight: activeNav === item.key ? 700 : 500,
                background: activeNav === item.key ? "#EAF0FD" : "transparent",
                textDecoration: "none",
              }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}
