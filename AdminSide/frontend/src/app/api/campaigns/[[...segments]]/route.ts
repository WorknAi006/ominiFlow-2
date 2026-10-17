import { NextRequest, NextResponse } from "next/server";
import { backendApiUrl, isRecord, parseJson } from "@/lib/auth/backend";
import { getSessionAccessToken } from "@/lib/auth/session";

export const runtime = "nodejs";

type RouteContext = { params: Promise<{ segments?: string[] }> };
type ProxyMethod = "GET" | "POST" | "PATCH" | "DELETE";

async function handle(request: NextRequest, context: RouteContext, method: ProxyMethod) {
  const token = await getSessionAccessToken();
  if (!token) return NextResponse.json({ error: "Sign in to continue." }, { status: 401 });

  const { segments = [] } = await context.params;
  const path = `/campaigns${segments.length > 0 ? "/" + segments.join("/") : ""}`;
  
  let body: unknown;
  if (method === "POST" || method === "PATCH") {
    body = await request.json().catch(() => undefined);
  }

  const url = backendApiUrl(path);
  url.search = request.nextUrl.searchParams.toString();

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
    return NextResponse.json({ error: "Service temporarily unavailable" }, { status: 503 });
  }

  if (!upstream.ok) {
    const payload = await parseJson(upstream);
    const detail = isRecord(payload) && typeof payload.detail === "string" ? payload.detail : "Error";
    return NextResponse.json({ error: detail }, { status: upstream.status });
  }

  if (upstream.status === 204) return new NextResponse(null, { status: 204 });

  const payload = await parseJson(upstream);
  return NextResponse.json(payload, { status: 200 });
}

export function GET(request: NextRequest, context: RouteContext) { return handle(request, context, "GET"); }
export function POST(request: NextRequest, context: RouteContext) { return handle(request, context, "POST"); }
export function PATCH(request: NextRequest, context: RouteContext) { return handle(request, context, "PATCH"); }
export function DELETE(request: NextRequest, context: RouteContext) { return handle(request, context, "DELETE"); }
