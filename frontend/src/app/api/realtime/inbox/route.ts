import WebSocket from "ws";
import { NextResponse } from "next/server";

import { backendApiUrl } from "@/lib/auth/backend";
import { getSessionAccessToken } from "@/lib/auth/session";
import { SESSION_COOKIE_NAME } from "@/lib/auth/session-utils";

export const runtime = "nodejs";

const encoder = new TextEncoder();
const KEEPALIVE_MS = 20_000;
const ALLOWED_EVENTS = new Set([
  "ready", "message.created", "message.status_changed", "conversation.updated",
]);

function authenticationFailure() {
  const response = new NextResponse('event: auth_error\ndata: {"code":4401}\n\n', {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      "X-Content-Type-Options": "nosniff",
    },
  });
  response.cookies.set(SESSION_COOKIE_NAME, "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
  return response;
}

function eventFrame(raw: string) {
  let id = "";
  try {
    const event: unknown = JSON.parse(raw);
    if (
      event && typeof event === "object" && "event" in event &&
      typeof event.event === "string" && ALLOWED_EVENTS.has(event.event) &&
      "event_id" in event && typeof event.event_id === "string"
    ) {
      id = event.event_id.replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 100);
    } else {
      return null;
    }
  } catch {
    return null;
  }
  return `${id ? `id: ${id}\n` : ""}data: ${raw}\n\n`;
}

export async function GET(request: Request) {
  const token = await getSessionAccessToken();
  if (!token || token.length > 8192) return authenticationFailure();

  const upstreamUrl = backendApiUrl("/ws/inbox");
  if (upstreamUrl.protocol === "https:") upstreamUrl.protocol = "wss:";
  else if (upstreamUrl.protocol === "http:") upstreamUrl.protocol = "ws:";
  else return Response.json({ error: "Realtime is unavailable." }, { status: 503 });

  let cleanup = () => {};
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      let ended = false;
      let socket: WebSocket | undefined;
      const heartbeat = setInterval(() => {
        if (!ended) {
          try { controller.enqueue(encoder.encode(": keepalive\n\n")); } catch { finish(); }
        }
      }, KEEPALIVE_MS);

      const finish = (authCode?: number) => {
        if (ended) return;
        ended = true;
        clearInterval(heartbeat);
        if (authCode !== undefined) {
          const payload = `event: auth_error\ndata: ${JSON.stringify({ code: authCode })}\n\n`;
          try { controller.enqueue(encoder.encode(payload)); } catch { /* Stream already closed. */ }
        }
        try { controller.close(); } catch { /* Client already cancelled. */ }
      };

      const abort = () => {
        finish();
        try {
          socket?.close(1000);
        } catch {
          socket?.terminate();
        }
      };
      cleanup = abort;
      request.signal.addEventListener("abort", abort, { once: true });

      try {
        socket = new WebSocket(upstreamUrl, {
          handshakeTimeout: 10_000,
          maxPayload: 1_048_576,
        });
        socket.once("open", () => {
          if (!ended) socket?.send(JSON.stringify({ type: "auth", token }));
        });
        socket.on("message", (data, isBinary) => {
          if (ended || isBinary) return;
          const raw = data.toString();
          const frame = eventFrame(raw);
          if (frame) {
            try { controller.enqueue(encoder.encode(frame)); } catch { abort(); }
          }
        });
        socket.once("close", (code) => {
          if (code === 4401 || code === 4403) finish(code);
          else finish();
        });
        socket.once("error", abort);
      } catch {
        finish();
      }
    },
    cancel() {
      cleanup();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
