import { NextRequest, NextResponse } from "next/server";

import { backendApiUrl, isRecord, parseJson } from "@/lib/auth/backend";
import { getSessionAccessToken } from "@/lib/auth/session";
import { SESSION_COOKIE_NAME } from "@/lib/auth/session-utils";
import { buildInboxProxyTarget } from "@/lib/inbox/proxy-utils";

export const runtime = "nodejs";

type RouteContext = { params: Promise<{ segments: string[] }> };

function upstreamFailure(status: number) {
  if (status === 401) return { status: 401, error: "Your session has expired. Sign in again." };
  if (status === 403) return { status: 403, error: "You do not have access to this inbox action." };
  if (status === 404) return { status: 404, error: "This inbox item could not be found." };
  if (status === 409) return { status: 409, error: "This conversation or channel is not ready for that action." };
  if (status === 422) return { status: 422, error: "The request could not be accepted. Check the message and try again." };
  return { status: 503, error: "The inbox service is temporarily unavailable." };
}

function unauthenticated() {
  return clearSession(NextResponse.json({ error: "Sign in to continue." }, { status: 401 }));
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

async function handle(request: NextRequest, context: RouteContext, method: "GET" | "POST") {
  const token = await getSessionAccessToken();
  if (!token) return unauthenticated();

  const { segments } = await context.params;
  let body: unknown;
  if (method === "POST" && ["messages", "assign", "status"].includes(segments.at(-1) ?? "")) {
    body = await request.json().catch(() => null);
  }
  const target = buildInboxProxyTarget(method, segments, request.nextUrl.searchParams, body);
  if (!target) return NextResponse.json({ error: "Unsupported inbox request." }, { status: 400 });

  const url = backendApiUrl(target.backendPath);
  url.search = target.query.toString();

  let upstream: Response;
  try {
    upstream = await fetch(url, {
      method,
      headers: {
        Accept: target.kind === "media" ? "*/*" : "application/json",
        Authorization: `Bearer ${token}`,
        ...(request.headers.get("Idempotency-Key")
          ? { "Idempotency-Key": request.headers.get("Idempotency-Key")! }
          : {}),
        ...(target.body ? { "Content-Type": "application/json" } : {}),
      },
      ...(target.body ? { body: JSON.stringify(target.body) } : {}),
      cache: "no-store",
      signal: request.signal,
    });
  } catch {
    return NextResponse.json(
      { error: "The inbox service is temporarily unavailable." },
      { status: 503 },
    );
  }

  if (!upstream.ok) {
    const failure = upstreamFailure(upstream.status);
    const response = NextResponse.json({ error: failure.error }, { status: failure.status });
    return upstream.status === 401 ? clearSession(response) : response;
  }

  if (target.kind === "media") {
    const headers = new Headers({
      "Content-Type": upstream.headers.get("content-type") ?? "application/octet-stream",
      "X-Content-Type-Options": "nosniff",
      "Content-Security-Policy": "default-src 'none'; sandbox",
      "Cache-Control": "private, no-store",
    });
    const length = upstream.headers.get("content-length");
    const disposition = upstream.headers.get("content-disposition");
    if (length) headers.set("Content-Length", length);
    if (disposition) headers.set("Content-Disposition", disposition);
    return new NextResponse(upstream.body, { status: 200, headers });
  }

  const payload: unknown = await parseJson(upstream);
  if (!isRecord(payload)) {
    return NextResponse.json({ error: "The inbox service returned an invalid response." }, { status: 502 });
  }
  if (target.kind === "channel") {
    const connected = payload.status === "connected" && payload.is_active === true &&
      typeof payload.external_account_id === "string" && payload.external_account_id.length > 0;
    // WhatsApp needs stored credentials to send; Web Chat is internal and
    // needs none.
    const canSend = connected && (
      payload.channel_type === "whatsapp" ? payload.has_credentials === true
        : payload.channel_type === "web_chat"
    );
    return NextResponse.json({ can_send: canSend });
  }
  if (target.kind === "contact") {
    if (typeof payload.is_blocked !== "boolean") {
      return NextResponse.json({ error: "The inbox service returned an invalid response." }, { status: 502 });
    }
    return NextResponse.json({
      id: typeof payload.id === "string" ? payload.id : null,
      name: typeof payload.name === "string" ? payload.name : null,
      phone_number: typeof payload.phone_number === "string" ? payload.phone_number : null,
      email: typeof payload.email === "string" ? payload.email : null,
      is_blocked: payload.is_blocked,
    });
  }
  if (target.kind === "channels" || target.kind === "users" || target.kind === "templates") {
    if (!Array.isArray(payload.items)) {
      return NextResponse.json({ error: "The inbox service returned an invalid response." }, { status: 502 });
    }
    const items = target.kind === "channels"
      ? payload.items.flatMap((item) => isRecord(item) && typeof item.id === "string" &&
        typeof item.name === "string" && typeof item.channel_type === "string"
        ? [{ id: item.id, name: item.name, channel_type: item.channel_type }]
        : [])
        : target.kind === "users" ? payload.items.flatMap((item) => isRecord(item) && typeof item.id === "string" &&
        typeof item.first_name === "string"
        ? [{
            id: item.id,
            first_name: item.first_name,
            last_name: typeof item.last_name === "string" ? item.last_name : null,
            role: typeof item.role === "string" ? item.role : "",
          }]
        : []) : payload.items.flatMap((item) => isRecord(item) && typeof item.id === "string" &&
          typeof item.name === "string" && typeof item.language === "string" && item.is_usable === true &&
          Array.isArray(item.components)
          ? [{ id: item.id, name: item.name, language: item.language, components: item.components }]
          : []);
    return NextResponse.json({
      items,
      total: typeof payload.total === "number" ? payload.total : items.length,
    });
  }
  if (payload === null) {
    return NextResponse.json({ error: "The inbox service returned an invalid response." }, { status: 502 });
  }
  return NextResponse.json(payload, { status: upstream.status });
}

export function GET(request: NextRequest, context: RouteContext) {
  return handle(request, context, "GET");
}

export function POST(request: NextRequest, context: RouteContext) {
  return handle(request, context, "POST");
}
