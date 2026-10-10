"use client";

import Link from "next/link";

interface HeaderProps {
  activeNav?: string;
}

export default function Header({ activeNav }: HeaderProps) {
  const navItems = [
    { label: "AI 진단", href: "/", key: "analyze" },
  ];

  return (
    <header className="bg-white border-b border-border">
      <div className="max-w-[1200px] mx-auto px-6 min-h-16 flex items-center gap-8 flex-wrap">
        <Link
          href="/"
          className="font-bold text-xl text-text no-underline"
          style={{ textDecoration: "none" }}
        >
          나도사장
        </Link>
        <nav className="flex gap-6 flex-wrap flex-1 text-sm">
          {navItems.map((item) => (
            <Link
              key={item.key}
              href={item.href}
              className="no-underline font-medium"
              style={{
                color: activeNav === item.key ? "#1B1D21" : "#4A505B",
                fontWeight: activeNav === item.key ? 700 : 500,
                borderBottom: activeNav === item.key ? "2px solid #1B1D21" : "none",
                paddingBottom: activeNav === item.key ? "4px" : "0",
                textDecoration: "none",
              }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
