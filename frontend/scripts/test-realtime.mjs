/**
 * Tests for src/lib/realtime/inbox.ts using Node's built-in test runner.
 * The real TypeScript sources are transpiled with the project's own
 * TypeScript compiler, so no extra test dependencies are needed.
 *
 *   npm run test:realtime
 */
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, beforeEach, describe, it, mock } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";
import ts from "typescript";

const root = fileURLToPath(new URL("..", import.meta.url));
const outDir = mkdtempSync(join(tmpdir(), "omniflow-realtime-"));

for (const [source, target] of [
  ["src/lib/api/client.ts", "client.mjs"],
  ["src/lib/realtime/inbox.ts", "inbox.mjs"],
]) {
  const { outputText } = ts.transpileModule(readFileSync(join(root, source), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  });
  writeFileSync(join(outDir, target), outputText.replace("@/lib/api/client", "./client.mjs"));
}

const { createInboxRealtime, parseRealtimeEvent } = await import(
  pathToFileURL(join(outDir, "inbox.mjs")).href
);
after(() => rmSync(outDir, { recursive: true, force: true }));

const statusEvent = (status = "delivered", overrides = {}) => ({
  event: "message.status_changed",
  event_id: "e-1",
  tenant_id: "t-1",
  conversation_id: "c-1",
  message_id: "m-1",
  timestamp: "2026-01-01T00:00:00+00:00",
  data: {
    status,
    sent_at: "2026-01-01T00:00:00+00:00",
    delivered_at: status === "delivered" ? "2026-01-01T00:01:00+00:00" : null,
    read_at: null,
    failed_at: null,
    error_code: null,
    error_message: null,
  },
  ...overrides,
});

const createdEvent = {
  event: "message.created",
  event_id: "e-2",
  tenant_id: "t-1",
  conversation_id: "c-1",
  message_id: "m-2",
  timestamp: "2026-01-01T00:00:00+00:00",
  data: { direction: "inbound", type: "text", text: "Hi", created_at: null, contact: { id: "x", name: null, phone_number: null } },
};

const conversationEvent = (dataOverrides = {}, overrides = {}) => ({
  event: "conversation.updated",
  event_id: "e-3",
  tenant_id: "t-1",
  conversation_id: "c-1",
  timestamp: "2026-01-01T00:00:00+00:00",
  data: {
    status: "open",
    unread_count: 3,
    last_message_at: "2026-01-01T00:05:00+00:00",
    last_message_id: "m-9",
    last_message_direction: "inbound",
    last_message_type: "text",
    last_message_preview: "Is my order ready?",
    ...dataOverrides,
  },
  ...overrides,
});

describe("parseRealtimeEvent: conversation.updated", () => {
  it("accepts valid events, including an empty conversation", () => {
    const parsed = parseRealtimeEvent(JSON.stringify(conversationEvent()));
    assert.equal(parsed?.event, "conversation.updated");
    assert.equal(parsed.data.unread_count, 3);
    assert.equal(parsed.data.last_message_preview, "Is my order ready?");

    const empty = conversationEvent({
      unread_count: 0, last_message_at: null, last_message_id: null,
      last_message_direction: null, last_message_type: null, last_message_preview: null,
    });
    assert.equal(parseRealtimeEvent(empty)?.event, "conversation.updated");
  });

  it("rejects malformed payloads", () => {
    const invalid = [
      conversationEvent({ unread_count: -1 }),
      conversationEvent({ unread_count: "3" }),
      conversationEvent({ unread_count: 1.5 }),
      conversationEvent({ status: "archived" }),
      conversationEvent({ last_message_preview: 42 }),
      conversationEvent({ last_message_direction: "sideways" }),
      conversationEvent({}, { conversation_id: undefined }),
      conversationEvent({}, { data: "nope" }),
    ];
    for (const payload of invalid) assert.equal(parseRealtimeEvent(JSON.stringify(payload)), null);
  });

  it("rejects unsupported event types", () => {
    for (const type of ["conversation.assigned", "conversation.read", "contact.updated"]) {
      assert.equal(parseRealtimeEvent(conversationEvent({}, { event: type })), null, type);
    }
  });
});

describe("parseRealtimeEvent", () => {
  it("accepts every supported delivery status", () => {
    for (const status of ["sent", "delivered", "read", "failed"]) {
      const parsed = parseRealtimeEvent(JSON.stringify(statusEvent(status)));
      assert.equal(parsed?.event, "message.status_changed");
      assert.equal(parsed.data.status, status);
    }
  });

  it("accepts ready and message.created", () => {
    assert.deepEqual(parseRealtimeEvent('{"event":"ready"}'), { event: "ready" });
    assert.equal(parseRealtimeEvent(JSON.stringify(createdEvent))?.event, "message.created");
  });

  it("rejects malformed or unexpected frames", () => {
    const invalid = [
      "not json",
      "null",
      "[]",
      JSON.stringify({ event: 42 }),
      JSON.stringify(statusEvent("deleted")),
      JSON.stringify(statusEvent("read", { message_id: undefined })),
      JSON.stringify(statusEvent("read", { data: "x" })),
      JSON.stringify({ ...statusEvent(), event: "conversation.updated" }),
    ];
    for (const frame of invalid) assert.equal(parseRealtimeEvent(frame), null, frame);
  });
});

class FakeSocket {
  static instances = [];
  constructor(url) {
    this.url = url;
    this.sent = [];
    this.closed = null;
    FakeSocket.instances.push(this);
  }
  send(data) { this.sent.push(JSON.parse(data)); }
  close(code) { this.closed = code; }
  receive(payload) { this.onmessage({ data: typeof payload === "string" ? payload : JSON.stringify(payload) }); }
}

describe("InboxRealtimeClient dispatch", () => {
  beforeEach(() => {
    FakeSocket.instances = [];
    mock.method(console, "log", () => {});
  });

  async function connectedClient() {
    const states = [];
    const client = createInboxRealtime({
      getToken: () => "token-abc",
      url: "ws://test/api/v1/ws/inbox",
      onStateChange: (state) => states.push(state),
      webSocketFactory: (url) => new FakeSocket(url),
    });
    client.connect();
    const socket = FakeSocket.instances[0];
    await socket.onopen();
    socket.receive({ event: "ready" });
    return { client, socket, states };
  }

  it("authenticates via first message and becomes connected", async () => {
    const { socket, states } = await connectedClient();
    assert.equal(socket.url, "ws://test/api/v1/ws/inbox");
    assert.deepEqual(socket.sent, [{ type: "auth", token: "token-abc" }]);
    assert.deepEqual(states, ["connecting", "connected"]);
  });

  it("dispatches message.status_changed only to status handlers", async () => {
    const { client, socket } = await connectedClient();
    const statuses = [];
    const created = [];
    client.onMessageStatusChanged((event) => statuses.push(event));
    client.onMessageCreated((event) => created.push(event));

    socket.receive(statusEvent("read"));
    socket.receive(createdEvent);

    assert.equal(statuses.length, 1);
    assert.equal(statuses[0].data.status, "read");
    assert.equal(statuses[0].message_id, "m-1");
    assert.equal(created.length, 1);
    assert.equal(created[0].event, "message.created");
    assert.ok(console.log.mock.calls.some((call) => call.arguments[0] === "Realtime message status changed"));
  });

  it("ignores malformed frames and supports unsubscribe", async () => {
    const { client, socket } = await connectedClient();
    const statuses = [];
    const unsubscribe = client.onMessageStatusChanged((event) => statuses.push(event));

    socket.receive("garbage");
    socket.receive(statusEvent("deleted"));
    socket.receive({ ...statusEvent(), event: "conversation.updated" });
    assert.equal(statuses.length, 0);

    socket.receive(statusEvent("sent"));
    unsubscribe();
    socket.receive(statusEvent("delivered"));
    assert.deepEqual(statuses.map((e) => e.data.status), ["sent"]);
  });

  it("dispatches conversation.updated only to conversation handlers", async () => {
    const { client, socket } = await connectedClient();
    const conversations = [];
    const statuses = [];
    const created = [];
    const unsubscribe = client.onConversationUpdated((event) => conversations.push(event));
    client.onMessageStatusChanged((event) => statuses.push(event));
    client.onMessageCreated((event) => created.push(event));

    socket.receive(conversationEvent());
    socket.receive(conversationEvent({ unread_count: -5 })); // malformed: ignored
    socket.receive(statusEvent("read"));
    socket.receive(createdEvent);

    assert.equal(conversations.length, 1);
    assert.deepEqual(conversations[0].data, conversationEvent().data);
    assert.equal(conversations[0].conversation_id, "c-1");
    assert.equal(statuses.length, 1);
    assert.equal(created.length, 1);
    assert.ok(console.log.mock.calls.some((call) => call.arguments[0] === "Realtime conversation updated"));

    unsubscribe();
    socket.receive(conversationEvent({ unread_count: 4 }));
    assert.equal(conversations.length, 1);
  });

  it("disconnect closes the socket and stops", async () => {
    const { client, socket, states } = await connectedClient();
    client.disconnect();
    assert.equal(socket.closed, 1000);
    assert.equal(client.state, "disconnected");
    assert.equal(states.at(-1), "disconnected");
  });
});
