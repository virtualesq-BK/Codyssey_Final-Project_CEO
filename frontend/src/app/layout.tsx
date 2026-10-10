import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "나도사장",
  description: "AI 기반 창업 사업성 진단 서비스",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
