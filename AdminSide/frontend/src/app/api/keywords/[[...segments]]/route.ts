import { NextResponse, type NextRequest } from "next/server";

import { backendApiUrl } from "@/lib/auth/backend";
import { getSessionAccessToken } from "@/lib/auth/session";
import { buildKeywordProxyTarget, type ProxyMethod } from "@/lib/keywords/proxy-utils";

function unauthenticated() {
  return NextResponse.json({ error: "Not authenticated." }, { status: 401 });
}

export async function GET(request: NextRequest, props: { params: Promise<{ segments?: string[] }> }) {
  return proxyRequest(request, props, "GET");
}

export async function POST(request: NextRequest, props: { params: Promise<{ segments?: string[] }> }) {
  return proxyRequest(request, props, "POST");
}

export async function PATCH(request: NextRequest, props: { params: Promise<{ segments?: string[] }> }) {
  return proxyRequest(request, props, "PATCH");
}

export async function DELETE(request: NextRequest, props: { params: Promise<{ segments?: string[] }> }) {
  return proxyRequest(request, props, "DELETE");
}

async function proxyRequest(request: NextRequest, props: { params: Promise<{ segments?: string[] }> }, method: ProxyMethod) {
  const token = await getSessionAccessToken();
  if (!token) return unauthenticated();

  const { segments = [] } = await props.params;
  const hasBody = ["POST", "PATCH"].includes(method);
  const body = hasBody ? await request.json().catch(() => undefined) : undefined;

  const target = buildKeywordProxyTarget(method, segments, body);
  if (!target) return NextResponse.json({ error: "Invalid request." }, { status: 400 });

  const url = backendApiUrl(target.backendPath);
  url.search = target.query.toString();

  try {
    const backendResponse = await fetch(url, {
      method: target.method,
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/json",
        ...(target.body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      ...(target.body !== undefined ? { body: JSON.stringify(target.body) } : {}),
      cache: "no-store",
    });

    if (backendResponse.status === 204) return new NextResponse(null, { status: 204 });

    const data = await backendResponse.text();
    return new NextResponse(data, {
      status: backendResponse.status,
      headers: { "Content-Type": backendResponse.headers.get("Content-Type") ?? "application/json" },
    });
  } catch (error) {
    console.error("Keyword proxy error:", error);
    return NextResponse.json({ error: "Backend service unavailable." }, { status: 502 });
  }
}
