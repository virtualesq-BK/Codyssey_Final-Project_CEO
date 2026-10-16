import { NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

/** 상세분석 작업 진행 상황·결과 */
export async function GET(_req: Request, { params }: { params: { id: string } }) {
  try {
    const res = await fetch(`${BACKEND}/api/v1/analyze/jobs/${encodeURIComponent(params.id)}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
    return new NextResponse(await res.text(), { status: res.status, headers: { "Content-Type": "application/json" } });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ detail: msg }, { status: 502 });
  }
}
