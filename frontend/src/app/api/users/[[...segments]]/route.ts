import { NextRequest, NextResponse } from "next/server";

import { backendApiUrl, isRecord, parseJson } from "@/lib/auth/backend";
import { getSessionAccessToken } from "@/lib/auth/session";
import { SESSION_COOKIE_NAME } from "@/lib/auth/session-utils";

export const runtime = "nodejs";

type RouteContext = { params: Promise<{ segments?: string[] }> };

const GENERIC_ERROR = "The user service is temporarily unavailable.";

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

async function handle(request: NextRequest, context: RouteContext, method: string) {
  const token = await getSessionAccessToken();
  if (!token) return unauthenticated();

  const { segments = [] } = await context.params;

  let backendPath = `/users`;
  if (segments.length > 0) {
    backendPath += `/${segments.join("/")}`;
  }

  const url = backendApiUrl(backendPath);
  url.search = request.nextUrl.searchParams.toString();

  let upstream: Response;
  try {
    upstream = await fetch(url, {
      method: method,
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
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
  
  if (upstream.status === 204) {
    return new NextResponse(null, { status: 204 });
  }

  const payload = await parseJson(upstream);
  if (payload === null || typeof payload !== "object") {
    return NextResponse.json({ error: "The user service returned an invalid response." }, { status: 502 });
  }
  return NextResponse.json(payload, { status: 200 });
}

export function GET(request: NextRequest, context: RouteContext) {
  return handle(request, context, "GET");
}

export function DELETE(request: NextRequest, context: RouteContext) {
  return handle(request, context, "DELETE");
}
