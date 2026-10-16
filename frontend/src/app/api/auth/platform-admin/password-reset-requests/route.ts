import { NextResponse } from "next/server";

import { backendApiUrl, isRecord, parseJson } from "@/lib/auth/backend";
import { getSessionAccessToken } from "@/lib/auth/session";
import { SESSION_COOKIE_NAME } from "@/lib/auth/session-utils";

export const runtime = "nodejs";

function expiredSession() {
  const response = NextResponse.json({ error: "Sign in to continue." }, { status: 401 });
  response.cookies.set(SESSION_COOKIE_NAME, "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
  return response;
}

export async function GET() {
  const token = await getSessionAccessToken();
  if (!token) return expiredSession();

  let upstream: Response;
  try {
    upstream = await fetch(backendApiUrl("/auth/password-reset-requests"), {
      headers: { Accept: "application/json", Authorization: `Bearer ${token}` },
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
  } catch {
    return NextResponse.json({ error: "Could not load password reset requests." }, { status: 503 });
  }
  const payload: unknown = await parseJson(upstream);
  if (!upstream.ok) {
    const message = isRecord(payload) && typeof payload.detail === "string"
      ? payload.detail
      : "Could not load password reset requests.";
    const response = NextResponse.json({ error: message }, { status: upstream.status });
    return upstream.status === 401 ? expiredSession() : response;
  }
  return NextResponse.json(payload);
}
