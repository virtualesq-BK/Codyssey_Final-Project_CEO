"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// 메모는 MY아이디어 화면에서 바로 입력한다. 예전 링크(?memo= 포함)는 그쪽으로 넘긴다
export default function NewIdeaRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace(`/ideas${window.location.search}`);
  }, [router]);
  return null;
}
