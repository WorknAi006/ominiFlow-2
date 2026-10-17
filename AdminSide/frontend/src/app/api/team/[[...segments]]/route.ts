import { NextRequest, NextResponse } from "next/server";

import { backendApiUrl, isRecord, parseJson } from "@/lib/auth/backend";
import { getSessionAccessToken } from "@/lib/auth/session";
import { SESSION_COOKIE_NAME } from "@/lib/auth/session-utils";
import { buildTeamProxyTarget, type ProxyMethod } from "@/lib/team/proxy-utils";

export const runtime = "nodejs";

type RouteContext = { params: Promise<{ segments?: string[] }> };

const GENERIC_ERROR = "The team service is temporarily unavailable.";

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

// Strip sensitive fields (e.g. invitation_token) from an object or an array
// of objects before the response reaches the browser.
function redact(payload: unknown, fields: string[]): unknown {
  if (Array.isArray(payload)) return payload.map((item) => redact(item, fields));
  if (isRecord(payload)) {
    const copy: Record<string, unknown> = { ...payload };
    for (const field of fields) delete copy[field];
    return copy;
  }
  return payload;
}

async function handle(request: NextRequest, context: RouteContext, method: ProxyMethod) {
  const token = await getSessionAccessToken();
  if (!token) return unauthenticated();

  const { segments = [] } = await context.params;

  let body: unknown;
  if (method === "POST" || method === "PATCH") {
    body = await request.json().catch(() => undefined);
  }

  const target = buildTeamProxyTarget(method, segments, request.nextUrl.searchParams, body);
  if (!target) {
    return NextResponse.json({ error: "Unsupported team request." }, { status: 400 });
  }

  const url = backendApiUrl(target.backendPath);
  url.search = target.query.toString();

  let upstream: Response;
  try {
    upstream = await fetch(url, {
      method: target.method,
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
        ...(target.body ? { "Content-Type": "application/json" } : {}),
      },
      ...(target.body ? { body: JSON.stringify(target.body) } : {}),
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

  if (target.expectsNoContent || upstream.status === 204) {
    return new NextResponse(null, { status: 204 });
  }

  let payload = await parseJson(upstream);
  if (payload === null || typeof payload !== "object") {
    return NextResponse.json({ error: "The team service returned an invalid response." }, { status: 502 });
  }
  if (target.redact) payload = redact(payload, target.redact);
  return NextResponse.json(payload, { status: 200 });
}

export function GET(request: NextRequest, context: RouteContext) {
  return handle(request, context, "GET");
}
export function POST(request: NextRequest, context: RouteContext) {
  return handle(request, context, "POST");
}
export function PATCH(request: NextRequest, context: RouteContext) {
  return handle(request, context, "PATCH");
}
export function DELETE(request: NextRequest, context: RouteContext) {
  return handle(request, context, "DELETE");
}
