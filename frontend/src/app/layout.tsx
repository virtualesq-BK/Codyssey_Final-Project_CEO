import type { Metadata } from "next";
import "./globals.css";
import DiagnosisWatcher from "@/components/DiagnosisWatcher";
import { AuthProvider } from "@/contexts/AuthContext";

export const metadata: Metadata = {
  title: "나도사장",
  description: "AI 기반 창업 사업성 진단 서비스",
  // favicon.ico · icon.svg · apple-icon.png는 app 폴더 파일로 자동 연결된다
  manifest: undefined,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>
        <AuthProvider>
          {children}
          <DiagnosisWatcher />
        </AuthProvider>
      </body>
    </html>
  );
}
