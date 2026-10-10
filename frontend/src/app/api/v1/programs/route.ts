import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export async function GET(req: NextRequest) {
  const search = req.nextUrl.search;
  try {
    const res = await fetch(`${BACKEND}/api/v1/programs${search}`);
    const data = await res.text();
    return new NextResponse(data, {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ detail: msg }, { status: 502 });
  }
}
