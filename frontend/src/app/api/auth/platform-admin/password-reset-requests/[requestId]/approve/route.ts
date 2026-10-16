import { NextRequest, NextResponse } from "next/server";

import { backendApiUrl, isRecord, parseJson } from "@/lib/auth/backend";
import { getSessionAccessToken } from "@/lib/auth/session";
import { SESSION_COOKIE_NAME } from "@/lib/auth/session-utils";

export const runtime = "nodejs";

type RouteContext = { params: Promise<{ requestId: string }> };

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

export async function POST(_request: NextRequest, context: RouteContext) {
  const token = await getSessionAccessToken();
  if (!token) return expiredSession();
  const { requestId } = await context.params;
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(requestId)) {
    return NextResponse.json({ error: "Invalid reset request." }, { status: 400 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(backendApiUrl(`/auth/password-reset-requests/${requestId}/approve`), {
      method: "POST",
      headers: { Accept: "application/json", Authorization: `Bearer ${token}` },
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
  } catch {
    return NextResponse.json({ error: "Could not approve this request. Please try again." }, { status: 503 });
  }
  if (upstream.status === 204) return new NextResponse(null, { status: 204 });
  const payload: unknown = await parseJson(upstream);
  const message = isRecord(payload) && typeof payload.detail === "string"
    ? payload.detail
    : "Could not approve this request.";
  const response = NextResponse.json({ error: message }, { status: upstream.status });
  return upstream.status === 401 ? expiredSession() : response;
}
