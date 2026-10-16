import { NextRequest, NextResponse } from "next/server";

import { backendApiUrl, isRecord, parseJson } from "@/lib/auth/backend";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  const body: unknown = await request.json().catch(() => null);
  if (!isRecord(body) || typeof body.email !== "string" || body.email.length > 320) {
    return NextResponse.json({ error: "Enter a valid email address." }, { status: 400 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(backendApiUrl("/auth/password-reset-requests"), {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ email: body.email }),
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
  } catch {
    return NextResponse.json(
      { error: "Could not submit your request right now. Please try again." },
      { status: 503 },
    );
  }

  const payload: unknown = await parseJson(upstream);
  if (!upstream.ok) {
    const detail = isRecord(payload) && typeof payload.detail === "string"
      ? payload.detail
      : "Could not submit your request right now. Please try again.";
    return NextResponse.json({ error: detail }, { status: upstream.status >= 500 ? 503 : upstream.status });
  }
  return NextResponse.json(
    { message: "If an active account matches that email, a platform administrator will review the reset request." },
    { status: 202 },
  );
}
