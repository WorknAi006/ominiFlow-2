/** Tests the realtime parser and cookie-backed event stream using Node's test runner. */
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, describe, it } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";
import ts from "typescript";

const root = fileURLToPath(new URL("..", import.meta.url));
const outDir = mkdtempSync(join(tmpdir(), "omniflow-realtime-"));
const { outputText } = ts.transpileModule(
  readFileSync(join(root, "src/lib/realtime/inbox.ts"), "utf8"),
  { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } },
);
writeFileSync(join(outDir, "inbox.mjs"), outputText);
const { createInboxEventStream, parseRealtimeEvent } = await import(
  pathToFileURL(join(outDir, "inbox.mjs")).href
);
after(() => rmSync(outDir, { recursive: true, force: true }));

const statusEvent = (status = "delivered", eventId = "event-status") => ({
  event: "message.status_changed",
  event_id: eventId,
  tenant_id: "tenant-1",
  conversation_id: "conversation-1",
  message_id: "message-1",
  timestamp: "2026-01-01T00:00:00Z",
  data: {
    status, sent_at: null, delivered_at: null, read_at: null,
    failed_at: null, error_code: null, error_message: null,
  },
});

const conversationEvent = (unread = 2, eventId = "event-conversation") => ({
  event: "conversation.updated",
  event_id: eventId,
  tenant_id: "tenant-1",
  conversation_id: "conversation-1",
  timestamp: "2026-01-01T00:00:00Z",
  data: {
    status: "open", unread_count: unread, last_message_at: null,
    last_message_id: null, last_message_direction: null, last_message_type: null,
    last_message_preview: null,
  },
});

class FakeEventSource {
  static instances = [];
  constructor(url) {
    this.url = url;
    this.closed = false;
    this.listeners = new Map();
    FakeEventSource.instances.push(this);
  }
  addEventListener(name, handler) { this.listeners.set(name, handler); }
  open() { this.onopen?.(); }
  receive(payload) { this.onmessage?.({ data: typeof payload === "string" ? payload : JSON.stringify(payload) }); }
  authError(code) { this.listeners.get("auth_error")?.({ data: JSON.stringify({ code }) }); }
  close() { this.closed = true; }
}

describe("parseRealtimeEvent", () => {
  it("accepts supported conversation, status, message, and ready events", () => {
    assert.equal(parseRealtimeEvent({ event: "ready" }).event, "ready");
    assert.equal(parseRealtimeEvent(conversationEvent())?.event, "conversation.updated");
    assert.equal(parseRealtimeEvent(statusEvent("read"))?.event, "message.status_changed");
    assert.equal(parseRealtimeEvent({
      event: "message.created", conversation_id: "conversation-1", message_id: "message-2",
      data: { direction: "inbound", type: "text", text: "synthetic message", created_at: null, contact: { id: "contact-1", name: null, phone_number: null } },
    })?.event, "message.created");
  });

  it("rejects malformed, unsupported, and invalid unread events", () => {
    assert.equal(parseRealtimeEvent("not-json"), null);
    assert.equal(parseRealtimeEvent({ event: "unrecognized" }), null);
    assert.equal(parseRealtimeEvent(conversationEvent(-1)), null);
  });
});

describe("InboxEventStreamClient cookie-backed bridge", () => {
  it("connects only to the same-origin bridge, deduplicates, and unsubscribes", () => {
    FakeEventSource.instances = [];
    const received = [];
    const states = [];
    const client = createInboxEventStream({
      onStateChange: (state) => states.push(state),
      eventSourceFactory: (url) => new FakeEventSource(url),
    });
    const unsubscribe = client.onEvent((event) => received.push(event));
    client.connect();

    const source = FakeEventSource.instances[0];
    assert.equal(source.url, "/api/realtime/inbox");
    source.open();
    source.receive(conversationEvent());
    source.receive(conversationEvent());
    source.receive(statusEvent("read"));
    assert.equal(received.length, 2);
    assert.deepEqual(states, ["connecting", "connected"]);

    unsubscribe();
    source.receive(conversationEvent(9, "event-next"));
    assert.equal(received.length, 2);
    client.disconnect();
    assert.equal(source.closed, true);
    assert.equal(client.state, "disconnected");
  });

  it("stops on an upstream authentication failure", () => {
    FakeEventSource.instances = [];
    const failures = [];
    const client = createInboxEventStream({
      onAuthError: (code) => failures.push(code),
      eventSourceFactory: (url) => new FakeEventSource(url),
    });
    client.connect();
    const source = FakeEventSource.instances[0];
    source.authError(4401);
    assert.deepEqual(failures, [4401]);
    assert.equal(source.closed, true);
    assert.equal(client.state, "disconnected");
    client.disconnect();
  });
});
