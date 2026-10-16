import { NextRequest, NextResponse } from "next/server";

import { backendApiUrl, isRecord, parseJson } from "@/lib/auth/backend";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  const body: unknown = await request.json().catch(() => null);
  if (
    !isRecord(body) ||
    typeof body.token !== "string" ||
    typeof body.password !== "string" ||
    typeof body.confirm_password !== "string"
  ) {
    return NextResponse.json({ error: "Enter your new password and confirm it." }, { status: 400 });
  }
  if (body.password.length < 8 || body.password.length > 128) {
    return NextResponse.json({ error: "Password must be between 8 and 128 characters." }, { status: 400 });
  }
  if (body.password !== body.confirm_password) {
    return NextResponse.json({ error: "Passwords do not match." }, { status: 400 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(backendApiUrl("/auth/reset-password"), {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ token: body.token, password: body.password }),
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
  } catch {
    return NextResponse.json(
      { error: "Could not reset your password right now. Please try again." },
      { status: 503 },
    );
  }
  if (!upstream.ok) {
    const payload: unknown = await parseJson(upstream);
    const detail = isRecord(payload) && typeof payload.detail === "string"
      ? payload.detail
      : "Could not reset your password. The reset link may be expired.";
    return NextResponse.json({ error: detail }, { status: upstream.status >= 500 ? 503 : upstream.status });
  }
  return NextResponse.json({ success: true });
}
