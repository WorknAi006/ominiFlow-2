import { NextRequest, NextResponse } from "next/server";

import { backendApiUrl, isRecord, parseJson } from "@/lib/auth/backend";
import { sessionCookieOptions, tokenMaxAgeSeconds, SESSION_COOKIE_NAME } from "@/lib/auth/session-utils";

// Accept a team invitation. The invitation token is the credential; on
// success the backend returns an access token, which we store in the
// HttpOnly session cookie exactly like sign-in. The raw token is only ever
// forwarded server-side and never logged.
export async function POST(request: NextRequest) {
  const body: unknown = await request.json().catch(() => null);
  if (!isRecord(body) || typeof body.token !== "string" || typeof body.password !== "string") {
    return NextResponse.json({ error: "Enter and confirm a password to accept your invitation." }, { status: 400 });
  }

  const payloadOut: Record<string, unknown> = { token: body.token, password: body.password };
  if (typeof body.first_name === "string" && body.first_name.trim()) payloadOut.first_name = body.first_name.trim();
  if (typeof body.last_name === "string" && body.last_name.trim()) payloadOut.last_name = body.last_name.trim();

  let upstream: Response;
  try {
    upstream = await fetch(backendApiUrl("/users/invitations/accept"), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payloadOut),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ error: "Accepting invitations is temporarily unavailable. Please try again." }, { status: 503 });
  }

  const payload: unknown = await parseJson(upstream);
  if (!upstream.ok) {
    const detail = isRecord(payload) && typeof payload.detail === "string" ? payload.detail : null;
    const fallback = upstream.status === 400
      ? "This invitation is invalid, expired or already used."
      : upstream.status === 401
        ? "That password does not match your existing account."
        : upstream.status === 409
          ? "This invitation could not be completed. You may already be a member."
          : "Unable to accept this invitation right now. Please try again.";
    const status = upstream.status >= 400 && upstream.status < 500 ? upstream.status : 503;
    return NextResponse.json({ error: detail ?? fallback }, { status });
  }

  if (!isRecord(payload) || typeof payload.access_token !== "string" || payload.token_type !== "bearer") {
    return NextResponse.json({ error: "The invitation response was invalid." }, { status: 502 });
  }

  const maxAge = tokenMaxAgeSeconds(payload.access_token);
  if (maxAge === null) {
    return NextResponse.json({ error: "The invitation response was invalid." }, { status: 502 });
  }

  const response = NextResponse.json({ success: true });
  response.cookies.set(
    SESSION_COOKIE_NAME,
    payload.access_token,
    sessionCookieOptions(process.env.NODE_ENV === "production", maxAge),
  );
  return response;
}
