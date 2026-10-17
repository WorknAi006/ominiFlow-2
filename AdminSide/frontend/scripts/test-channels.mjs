import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, describe, it } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";
import ts from "typescript";

const root = fileURLToPath(new URL("..", import.meta.url));
const outDir = mkdtempSync(join(tmpdir(), "omniflow-channels-"));
const source = readFileSync(join(root, "src/lib/channels/proxy-utils.ts"), "utf8");
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
writeFileSync(join(outDir, "proxy-utils.mjs"), outputText);
const { buildChannelProxyTarget } = await import(pathToFileURL(join(outDir, "proxy-utils.mjs")).href);
after(() => rmSync(outDir, { recursive: true, force: true }));

const id = "123e4567-e89b-42d3-a456-426614174000";
const params = (q = "") => new URLSearchParams(q);

describe("Channel proxy allowlist", () => {
  it("forwards list filters and rejects unknown ones", () => {
    const target = buildChannelProxyTarget("GET", [], params("page=2&page_size=10&status=connected&channel_type=whatsapp&search=acme"));
    assert.equal(target.backendPath, "/channels");
    assert.equal(target.query.get("page"), "2");
    assert.equal(target.query.get("status"), "connected");
    assert.equal(target.query.get("channel_type"), "whatsapp");
    assert.equal(buildChannelProxyTarget("GET", [], params("status=bogus")), null);
    assert.equal(buildChannelProxyTarget("GET", [], params("channel_type=telegram")), null);
    assert.equal(buildChannelProxyTarget("GET", [], params("evil=1")), null);
    assert.equal(buildChannelProxyTarget("GET", [], params("page_size=101")), null);
  });

  it("validates create bodies", () => {
    const ok = buildChannelProxyTarget("POST", [], params(), { channel_type: "whatsapp", name: "  Support  " });
    assert.equal(ok.backendPath, "/channels");
    assert.equal(ok.body.name, "Support");
    assert.equal(buildChannelProxyTarget("POST", [], params(), { channel_type: "whatsapp", name: "x" }), null);
    assert.equal(buildChannelProxyTarget("POST", [], params(), { channel_type: "telegram", name: "Nope" }), null);
    assert.equal(buildChannelProxyTarget("POST", [], params(), { channel_type: "whatsapp", name: "ok", status: "connected" }), null);
    assert.equal(buildChannelProxyTarget("POST", [], params(), { channel_type: "whatsapp", name: "ok", external_account_id: "has space" }), null);
  });

  it("validates the WhatsApp connect body and never allows extra fields", () => {
    const ok = buildChannelProxyTarget("POST", [id, "whatsapp", "connect"], params(), {
      phone_number_id: "100000000000001",
      waba_id: "200000000000001",
      access_token: "a-secret-token",
    });
    assert.equal(ok.backendPath, `/channels/${id}/whatsapp/connect`);
    assert.deepEqual(Object.keys(ok.body).sort(), ["access_token", "phone_number_id", "waba_id"]);
    assert.equal(buildChannelProxyTarget("POST", [id, "whatsapp", "connect"], params(), { phone_number_id: "abc", waba_id: "200000000000001", access_token: "t" }), null);
    assert.equal(buildChannelProxyTarget("POST", [id, "whatsapp", "connect"], params(), { phone_number_id: "1", waba_id: "2", access_token: "t", code: "x" }), null);
    assert.equal(buildChannelProxyTarget("POST", [id, "whatsapp", "connect"], params(), { phone_number_id: "1", waba_id: "2", access_token: "" }), null);
  });

  it("allows test, disconnect, delete, templates and sync on a valid id only", () => {
    assert.equal(buildChannelProxyTarget("POST", [id, "whatsapp", "test"], params()).backendPath, `/channels/${id}/whatsapp/test`);
    assert.equal(buildChannelProxyTarget("POST", [id, "disconnect"], params()).backendPath, `/channels/${id}/disconnect`);
    assert.equal(buildChannelProxyTarget("DELETE", [id], params()).expectsNoContent, true);
    assert.equal(buildChannelProxyTarget("GET", [id, "templates"], params("include_inactive=true&status=APPROVED")).backendPath, `/channels/${id}/templates`);
    assert.equal(buildChannelProxyTarget("POST", [id, "templates", "sync"], params()).backendPath, `/channels/${id}/templates/sync`);
    assert.equal(buildChannelProxyTarget("GET", ["not-a-uuid"], params()), null);
    assert.equal(buildChannelProxyTarget("POST", [id, "whatsapp", "test"], params("x=1")), null);
    assert.equal(buildChannelProxyTarget("DELETE", [id, "whatsapp", "connect"], params()), null);
  });

  it("validates PATCH update bodies", () => {
    assert.equal(buildChannelProxyTarget("PATCH", [id], params(), { name: "Renamed" }).body.name, "Renamed");
    assert.equal(buildChannelProxyTarget("PATCH", [id], params(), { is_active: false }).body.is_active, false);
    assert.equal(buildChannelProxyTarget("PATCH", [id], params(), {}), null);
    assert.equal(buildChannelProxyTarget("PATCH", [id], params(), { status: "connected" }), null);
  });
});
