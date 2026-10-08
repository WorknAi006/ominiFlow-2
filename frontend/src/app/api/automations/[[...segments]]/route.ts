import { NextRequest, NextResponse } from "next/server";
import { backendApiUrl, isRecord, parseJson } from "@/lib/auth/backend";
import { getSessionAccessToken } from "@/lib/auth/session";
import { SESSION_COOKIE_NAME } from "@/lib/auth/session-utils";
import { buildAutomationTarget, type AutomationMethod } from "@/lib/automations/proxy-utils";

export const runtime = "nodejs";
type Context = { params: Promise<{ segments?: string[] }> };
const FAIL = "The automations service is temporarily unavailable.";

async function handle(request: NextRequest, context: Context, method: AutomationMethod) {
  const token = await getSessionAccessToken();
  if (!token) return clear(NextResponse.json({ error: "Sign in to continue." }, { status: 401 }));
  const { segments = [] } = await context.params;
  const target = buildAutomationTarget(method, segments, request.nextUrl.searchParams);
  if (!target) return NextResponse.json({ error: "Unsupported automation request." }, { status: 400 });
  let body: string | undefined;
  if (!["GET", "DELETE"].includes(method)) {
    const raw = await request.text();
    if (raw.length > 1_000_000) return NextResponse.json({ error: "Request body is too large." }, { status: 413 });
    try { JSON.parse(raw); } catch { return NextResponse.json({ error: "Invalid JSON request." }, { status: 400 }); }
    body = raw;
  }
  const url = backendApiUrl(target.backendPath);
  url.search = target.query.toString();
  let upstream: Response;
  try { upstream = await fetch(url, { method, headers: { Accept: "application/json", Authorization: `Bearer ${token}`, ...(body ? { "Content-Type": "application/json" } : {}) }, body, cache: "no-store", signal: request.signal }); }
  catch { return NextResponse.json({ error: FAIL }, { status: 503 }); }
  if (upstream.status === 204) return new NextResponse(null, { status: 204 });
  if (!upstream.ok) {
    const payload = await parseJson(upstream);
    const status = [400, 401, 403, 404, 409, 413, 422, 502, 503].includes(upstream.status) ? upstream.status : 503;
    const detail = isRecord(payload) && typeof payload.detail === "string" ? payload.detail : FAIL;
    const response = NextResponse.json({ error: upstream.status === 401 ? "Your session has expired. Sign in again." : detail }, { status });
    return upstream.status === 401 ? clear(response) : response;
  }
  const payload = await parseJson(upstream);
  return payload === null ? NextResponse.json({ error: "Invalid service response." }, { status: 502 }) : NextResponse.json(payload, { status: upstream.status });
}
function clear(response: NextResponse) {
  response.cookies.set(SESSION_COOKIE_NAME, "", { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/", maxAge: 0 });
  return response;
}
export const GET = (r: NextRequest, c: Context) => handle(r, c, "GET");
export const POST = (r: NextRequest, c: Context) => handle(r, c, "POST");
export const PATCH = (r: NextRequest, c: Context) => handle(r, c, "PATCH");
export const PUT = (r: NextRequest, c: Context) => handle(r, c, "PUT");
export const DELETE = (r: NextRequest, c: Context) => handle(r, c, "DELETE");
