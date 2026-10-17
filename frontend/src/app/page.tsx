"use client";

import Header from "@/components/Header";
import Dashboard from "@/components/home/Dashboard";
import Landing from "@/components/home/Landing";
import { useAuth } from "@/contexts/AuthContext";

/** 홈: 비로그인은 랜딩, 로그인하면 내 아이디어·지원서 중심의 대시보드 */
export default function Home() {
  const { user, loading } = useAuth();
  return (
    <div className="min-h-screen" style={{ background: "#F5F7FB" }}>
      <Header />
      {/* 로그인 확인 전엔 비워 둬서 랜딩이 잠깐 비쳤다가 바뀌지 않게 한다 */}
      {loading ? null : user ? <Dashboard user={user} /> : <Landing />}
    </div>
  );
}
