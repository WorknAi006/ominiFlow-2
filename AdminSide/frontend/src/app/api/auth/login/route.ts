import { NextRequest, NextResponse } from "next/server";

import { backendApiUrl, isRecord, parseJson } from "@/lib/auth/backend";
import { sessionCookieOptions, tokenMaxAgeSeconds, SESSION_COOKIE_NAME } from "@/lib/auth/session-utils";
import { validateLogin } from "@/lib/auth/validation";

export async function POST(request: NextRequest) {
  const body: unknown = await request.json().catch(() => null);
  if (!isRecord(body) || typeof body.email !== "string" || typeof body.password !== "string") {
    return NextResponse.json({ error: "Enter your email and password." }, { status: 400 });
  }

  const validationError = validateLogin(body.email, body.password);
  if (validationError) return NextResponse.json({ error: validationError }, { status: 400 });

  let upstream: Response;
  try {
    upstream = await fetch(backendApiUrl("/auth/login"), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ email: body.email, password: body.password }),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { error: "Sign in is temporarily unavailable. Please try again." },
      { status: 503 },
    );
  }

  const payload: unknown = await parseJson(upstream);
  if (!upstream.ok) {
    const fallback = upstream.status === 401
      ? "Invalid email or password."
      : upstream.status === 422
        ? "Check your email and password, then try again."
        : "Unable to sign in right now. Please try again.";
    return NextResponse.json(
      { error: fallback },
      { status: upstream.status >= 400 && upstream.status < 500 ? upstream.status : 503 },
    );
  }

  if (!isRecord(payload) || typeof payload.access_token !== "string" || payload.token_type !== "bearer") {
    return NextResponse.json({ error: "The sign-in response was invalid." }, { status: 502 });
  }

  const maxAge = tokenMaxAgeSeconds(payload.access_token);
  if (maxAge === null) {
    return NextResponse.json({ error: "The sign-in response was invalid." }, { status: 502 });
  }

  const response = NextResponse.json({ success: true });
  response.cookies.set(
    SESSION_COOKIE_NAME,
    payload.access_token,
    sessionCookieOptions(process.env.NODE_ENV === "production", maxAge),
  );
  return response;
}
