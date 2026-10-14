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
  const path = `/flows${segments.length > 0 ? "/" + segments.join("/") : ""}`;
  const url = backendApiUrl(path);
  url.search = request.nextUrl.searchParams.toString();

  const incomingType = request.headers.get("content-type") ?? "";
  const isMultipart = incomingType.startsWith("multipart/form-data");

  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
  let body: BodyInit | undefined;
  if (method === "POST" || method === "PATCH") {
    if (isMultipart) {
      // Forward the raw multipart payload untouched (file uploads).
      body = Buffer.from(await request.arrayBuffer());
      headers["Content-Type"] = incomingType;
    } else {
      const json = await request.json().catch(() => undefined);
      if (json !== undefined) {
        body = JSON.stringify(json);
        headers["Content-Type"] = "application/json";
      }
    }
  }

  let upstream: Response;
  try {
    upstream = await fetch(url, { method, headers, body, cache: "no-store", signal: request.signal });
  } catch {
    return NextResponse.json({ error: "Service temporarily unavailable" }, { status: 503 });
  }

  if (!upstream.ok) {
    const payload = await parseJson(upstream);
    const detail = isRecord(payload) && typeof payload.detail === "string" ? payload.detail : "Error";
    return NextResponse.json({ error: detail }, { status: upstream.status });
  }
  if (upstream.status === 204) return new NextResponse(null, { status: 204 });

  // Binary assets (images / video / documents) are streamed straight through.
  const upstreamType = upstream.headers.get("content-type") ?? "";
  if (!upstreamType.includes("application/json")) {
    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type": upstreamType || "application/octet-stream",
        "Cache-Control": upstream.headers.get("cache-control") ?? "private, max-age=3600",
      },
    });
  }

  const payload = await parseJson(upstream);
  return NextResponse.json(payload, { status: 200 });
}

export function GET(request: NextRequest, context: RouteContext) { return handle(request, context, "GET"); }
export function POST(request: NextRequest, context: RouteContext) { return handle(request, context, "POST"); }
export function PATCH(request: NextRequest, context: RouteContext) { return handle(request, context, "PATCH"); }
export function DELETE(request: NextRequest, context: RouteContext) { return handle(request, context, "DELETE"); }
