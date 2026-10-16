import { NextResponse } from "next/server";

import { backendApiUrl } from "@/lib/auth/backend";
import { getSessionAccessToken } from "@/lib/auth/session";
import { SESSION_COOKIE_NAME } from "@/lib/auth/session-utils";

export const runtime = "nodejs";

export async function POST() {
  const token = await getSessionAccessToken();
  let serverSessionRevoked = !token;
  if (token) {
    try {
      const upstream = await fetch(backendApiUrl("/auth/logout"), {
        method: "POST",
        headers: {
          Accept: "application/json",
          Authorization: `Bearer ${token}`,
        },
        cache: "no-store",
        signal: AbortSignal.timeout(5000),
      });
      serverSessionRevoked = upstream.ok;
    } catch {
      serverSessionRevoked = false;
    }
  }

  const response = NextResponse.json({ success: true, server_session_revoked: serverSessionRevoked });
  response.cookies.set(SESSION_COOKIE_NAME, "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
  return response;
}
