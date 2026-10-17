import { NextRequest, NextResponse } from "next/server";

import { backendApiUrl, isRecord, parseJson } from "@/lib/auth/backend";
import { getSessionAccessToken } from "@/lib/auth/session";
import { SESSION_COOKIE_NAME } from "@/lib/auth/session-utils";

export const runtime = "nodejs";

const GENERIC_ERROR = "The AI Configuration service is temporarily unavailable.";

function friendlyStatus(status: number): number {
  if ([400, 401, 403, 404, 409, 422, 502, 503].includes(status)) return status;
  return 503;
}

function clearSession(response: NextResponse) {
  response.cookies.set(SESSION_COOKIE_NAME, "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
  return response;
}

function unauthenticated() {
  return clearSession(NextResponse.json({ error: "Sign in to continue." }, { status: 401 }));
}

async function handle(request: NextRequest, method: "GET" | "PUT" | "POST") {
  const token = await getSessionAccessToken();
  if (!token) return unauthenticated();

  let body: unknown;
  if (method === "PUT") {
    body = await request.json().catch(() => undefined);
    if (!isRecord(body)) {
      return NextResponse.json({ error: "Invalid request body." }, { status: 400 });
    }
  }

  // If POST, we hit /ai-config/validate
  const urlPath = method === "POST" ? "/ai-config/validate" : "/ai-config";
  const url = backendApiUrl(urlPath);

  let upstream: Response;
  try {
    upstream = await fetch(url, {
      method,
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
      cache: "no-store",
      signal: request.signal,
    });
  } catch {
    return NextResponse.json({ error: GENERIC_ERROR }, { status: 503 });
  }

  if (!upstream.ok) {
    const payload = await parseJson(upstream);
    const detail = isRecord(payload) && typeof payload.detail === "string" ? payload.detail : null;
    const status = friendlyStatus(upstream.status);
    const error = status === 401 ? "Your session has expired. Sign in again." : detail ?? GENERIC_ERROR;
    const response = NextResponse.json({ error }, { status });
    return upstream.status === 401 ? clearSession(response) : response;
  }

  const payload = await parseJson(upstream);
  if (payload === null || typeof payload !== "object") {
    return NextResponse.json({ error: "The AI Configuration service returned an invalid response." }, { status: 502 });
  }
  return NextResponse.json(payload, { status: 200 });
}

export function GET(request: NextRequest) {
  return handle(request, "GET");
}
export function PUT(request: NextRequest) {
  return handle(request, "PUT");
}
export function POST(request: NextRequest) {
  return handle(request, "POST");
}
