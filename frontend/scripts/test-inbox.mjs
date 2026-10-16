import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, describe, it } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";
import ts from "typescript";

const root = fileURLToPath(new URL("..", import.meta.url));
const outDir = mkdtempSync(join(tmpdir(), "omniflow-inbox-"));
const source = readFileSync(join(root, "src/lib/inbox/proxy-utils.ts"), "utf8");
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
writeFileSync(join(outDir, "proxy-utils.mjs"), outputText);
const { buildInboxProxyTarget, canSendWhatsAppReply, definitiveMessageSendFailure } = await import(
  pathToFileURL(join(outDir, "proxy-utils.mjs")).href
);
after(() => rmSync(outDir, { recursive: true, force: true }));

const conversationId = "123e4567-e89b-42d3-a456-426614174000";
const uuid = "123e4567-e89b-42d3-a456-426614174001";

describe("Inbox proxy allowlist", () => {
  it("forwards only supported conversation filters and pagination", () => {
    const target = buildInboxProxyTarget(
      "GET",
      ["conversations"],
      new URLSearchParams(`page=2&page_size=25&status=open&unread=true&search=sample`),
    );
    assert.equal(target.backendPath, "/conversations");
    assert.equal(target.query.get("page"), "2");
    assert.equal(target.query.get("status"), "open");
    assert.equal(target.query.get("search"), "sample");
    assert.equal(buildInboxProxyTarget("GET", ["conversations"], new URLSearchParams("url=https://bad.example")), null);
    assert.equal(buildInboxProxyTarget("GET", ["admin"], new URLSearchParams()), null);
  });

  it("validates text and template message contracts", () => {
    const accepted = buildInboxProxyTarget(
      "POST",
      ["conversations", conversationId, "messages"],
      new URLSearchParams(),
      { type: "text", text: "Synthetic test reply" },
    );
    assert.equal(accepted.backendPath, `/conversations/${conversationId}/messages`);
    assert.deepEqual(accepted.body, { type: "text", text: "Synthetic test reply" });
    const template = buildInboxProxyTarget("POST", ["conversations", conversationId, "messages"], new URLSearchParams(), {
      type: "template", template_name: "sample", language: "en_US", components: [],
    });
    assert.equal(template.backendPath, `/conversations/${conversationId}/messages`);
    assert.equal(buildInboxProxyTarget("POST", ["conversations", conversationId, "messages"], new URLSearchParams(), { type: "template", template_name: "sample" }), null);
    assert.equal(buildInboxProxyTarget("POST", ["conversations", conversationId, "messages"], new URLSearchParams(), { type: "text", text: "   " }), null);
    assert.equal(buildInboxProxyTarget("POST", ["conversations", conversationId, "messages"], new URLSearchParams(), { type: "text", text: "x".repeat(4097) }), null);
  });

  it("allows only enumerated authenticated resources and safe IDs", () => {
    assert.equal(buildInboxProxyTarget("GET", ["channels", uuid], new URLSearchParams()).kind, "channel");
    assert.equal(buildInboxProxyTarget("GET", ["contacts", uuid], new URLSearchParams()).kind, "contact");
    assert.equal(buildInboxProxyTarget("POST", ["conversations", "not-a-uuid", "read"], new URLSearchParams()), null);
    assert.equal(buildInboxProxyTarget("DELETE", ["conversations", conversationId, "messages"], new URLSearchParams()), null);
    assert.equal(buildInboxProxyTarget("POST", ["conversations", conversationId, "assign"], new URLSearchParams(), { assigned_user_id: uuid }).backendPath, `/conversations/${conversationId}/assign`);
    assert.equal(buildInboxProxyTarget("POST", ["conversations", conversationId, "status"], new URLSearchParams(), { status: "closed" }).backendPath, `/conversations/${conversationId}/status`);
    const templates = buildInboxProxyTarget(
      "GET",
      ["channels", uuid, "templates"],
      new URLSearchParams("page=1&page_size=100"),
    );
    assert.equal(templates.kind, "templates");
    assert.equal(templates.backendPath, `/channels/${uuid}/templates`);
    assert.equal(buildInboxProxyTarget("GET", ["channels", uuid, "templates"], new URLSearchParams("page=1")), null);
  });
});

describe("send readiness", () => {
  const conversation = { channel: { channel_type: "whatsapp" } };
  const webChat = { channel: { channel_type: "web_chat" } };

  it("requires a ready channel and an unblocked contact", () => {
    assert.match(canSendWhatsAppReply(conversation, null, null), /Checking channel/);
    assert.match(canSendWhatsAppReply(conversation, { can_send: false }, { is_blocked: false }), /not connected/);
    assert.match(canSendWhatsAppReply(conversation, { can_send: true }, { is_blocked: true }), /blocked/);
    assert.equal(canSendWhatsAppReply(conversation, { can_send: true }, { is_blocked: false }), null);
    // Instagram/Facebook are not sendable yet.
    assert.match(canSendWhatsAppReply({ channel: { channel_type: "instagram" } }, null, null), /WhatsApp and Web Chat/);
  });

  it("allows replying to a connected Web Chat conversation", () => {
    assert.match(canSendWhatsAppReply(webChat, { can_send: false }, { is_blocked: false }), /not connected/);
    assert.match(canSendWhatsAppReply(webChat, { can_send: true }, { is_blocked: true }), /blocked/);
    assert.equal(canSendWhatsAppReply(webChat, { can_send: true }, { is_blocked: false }), null);
  });

  it("identifies definitive WhatsApp rejections without marking transient send failures as certain", () => {
    const messageRoute = ["conversations", conversationId, "messages"];
    assert.equal(
      definitiveMessageSendFailure("POST", messageRoute, 502, "WhatsApp rejected the message: Authentication Error"),
      "WhatsApp authentication failed. Reconnect the channel in Channels with a valid access token.",
    );
    assert.equal(
      definitiveMessageSendFailure("POST", messageRoute, 502, "WhatsApp rejected the message: Outside the 24h window"),
      "WhatsApp rejected the message: Outside the 24h window",
    );
    assert.equal(definitiveMessageSendFailure("POST", messageRoute, 502, "Could not reach WhatsApp."), null);
    assert.equal(definitiveMessageSendFailure("POST", messageRoute, 503, "WhatsApp rejected the message: Authentication Error"), null);
  });
});
