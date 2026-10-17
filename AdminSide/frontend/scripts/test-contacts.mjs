import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, describe, it } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";
import ts from "typescript";

const root = fileURLToPath(new URL("..", import.meta.url));
const outDir = mkdtempSync(join(tmpdir(), "omniflow-contacts-"));
const source = readFileSync(join(root, "src/lib/contacts/proxy-utils.ts"), "utf8");
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
writeFileSync(join(outDir, "proxy-utils.mjs"), outputText);
const { buildContactProxyTarget } = await import(pathToFileURL(join(outDir, "proxy-utils.mjs")).href);
after(() => rmSync(outDir, { recursive: true, force: true }));

const id = "123e4567-e89b-42d3-a456-426614174000";
const params = (q = "") => new URLSearchParams(q);

describe("Contacts proxy allowlist", () => {
  it("forwards list filters and pagination, rejecting unknown params", () => {
    const target = buildContactProxyTarget("GET", [], params("page=3&page_size=25&search=alice&phone=15550001"));
    assert.equal(target.backendPath, "/contacts");
    assert.equal(target.query.get("page"), "3");
    assert.equal(target.query.get("search"), "alice");
    assert.equal(target.query.get("phone"), "15550001");
    assert.equal(buildContactProxyTarget("GET", [], params("evil=1")), null);
    assert.equal(buildContactProxyTarget("GET", [], params("page_size=101")), null);
    assert.equal(buildContactProxyTarget("GET", [], params("page=0")), null);
  });

  it("requires a phone or email when creating", () => {
    const ok = buildContactProxyTarget("POST", [], params(), { first_name: " Al ", email: " al@x.io " });
    assert.equal(ok.backendPath, "/contacts");
    assert.equal(ok.body.first_name, "Al");
    assert.equal(ok.body.email, "al@x.io");
    assert.equal(buildContactProxyTarget("POST", [], params(), { first_name: "No Identity" }), null);
    assert.equal(buildContactProxyTarget("POST", [], params(), {}), null);
    assert.equal(buildContactProxyTarget("POST", [], params(), { phone_number: "15550001", is_blocked: true }), null);
  });

  it("validates update bodies including null-clears and block toggle", () => {
    assert.equal(buildContactProxyTarget("PATCH", [id], params(), { is_blocked: true }).body.is_blocked, true);
    assert.equal(buildContactProxyTarget("PATCH", [id], params(), { email: null }).body.email, null);
    assert.equal(buildContactProxyTarget("PATCH", [id], params(), { display_name: " Bob " }).body.display_name, "Bob");
    assert.equal(buildContactProxyTarget("PATCH", [id], params(), {}), null);
    assert.equal(buildContactProxyTarget("PATCH", [id], params(), { phone_number: null }), null);
    assert.equal(buildContactProxyTarget("PATCH", [id], params(), { tenant_id: "x" }), null);
  });

  it("resolves a contact's conversations through the tenant-scoped filter", () => {
    const target = buildContactProxyTarget("GET", [id, "conversations"], params("page=1&page_size=20"));
    assert.equal(target.backendPath, "/conversations");
    assert.equal(target.query.get("contact_id"), id);
    assert.equal(buildContactProxyTarget("GET", [id, "conversations"], params("status=open")), null);
    assert.equal(buildContactProxyTarget("GET", ["not-a-uuid"], params()), null);
    assert.equal(buildContactProxyTarget("DELETE", [id], params()), null);
  });
});
