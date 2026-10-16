import { NextRequest, NextResponse } from "next/server";

import { backendApiUrl, isRecord, parseJson } from "@/lib/auth/backend";
import { getSessionAccessToken } from "@/lib/auth/session";
import { SESSION_COOKIE_NAME } from "@/lib/auth/session-utils";
import { buildTemplateProxyTarget, type ProxyMethod } from "@/lib/templates/proxy-utils";

export const runtime = "nodejs";

type RouteContext = { params: Promise<{ segments?: string[] }> };

const GENERIC_ERROR = "The templates service is temporarily unavailable.";

function friendlyStatus(status: number): number {
  if ([400, 401, 403, 404, 409, 413, 422, 502, 503].includes(status)) return status;
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

async function handle(request: NextRequest, context: RouteContext, method: ProxyMethod) {
  const token = await getSessionAccessToken();
  if (!token) return unauthenticated();

  const { segments = [] } = await context.params;
  const target = buildTemplateProxyTarget(method, segments, request.nextUrl.searchParams);
  if (!target) {
    return NextResponse.json({ error: "Unsupported templates request." }, { status: 400 });
  }

  const url = backendApiUrl(target.backendPath);
  url.search = target.query.toString();

  let body: BodyInit | undefined;
  const headers: Record<string, string> = { Accept: "application/json", Authorization: `Bearer ${token}` };
  if (target.method === "POST") {
    const contentType = request.headers.get("content-type") ?? "";
    if (contentType.startsWith("multipart/form-data")) {
      body = Buffer.from(await request.arrayBuffer());
      headers["Content-Type"] = contentType;
    } else {
      const raw = await request.text();
      if (raw) {
      try { JSON.parse(raw); } catch { return NextResponse.json({ error: "Invalid JSON request." }, { status: 400 }); }
      body = raw;
      headers["Content-Type"] = "application/json";
      }
    }
  }

  let upstream: Response;
  try {
    upstream = await fetch(url, {
      method: target.method,
      headers,
      ...(body ? { body } : {}),
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
    return NextResponse.json({ error: "The templates service returned an invalid response." }, { status: 502 });
  }
  return NextResponse.json(payload, { status: upstream.status });
}

export function GET(request: NextRequest, context: RouteContext) {
  return handle(request, context, "GET");
}
export function POST(request: NextRequest, context: RouteContext) {
  return handle(request, context, "POST");
}
