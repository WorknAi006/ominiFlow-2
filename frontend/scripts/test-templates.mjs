import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, describe, it } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";
import ts from "typescript";

const root = fileURLToPath(new URL("..", import.meta.url));
const outDir = mkdtempSync(join(tmpdir(), "omniflow-templates-"));
const source = readFileSync(join(root, "src/lib/templates/proxy-utils.ts"), "utf8");
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
writeFileSync(join(outDir, "proxy-utils.mjs"), outputText);
const { buildTemplateProxyTarget } = await import(pathToFileURL(join(outDir, "proxy-utils.mjs")).href);
after(() => rmSync(outDir, { recursive: true, force: true }));

const id = "123e4567-e89b-42d3-a456-426614174000";
const channelId = "123e4567-e89b-42d3-a456-4266141740ab";
const params = (q = "") => new URLSearchParams(q);

describe("Templates proxy allowlist", () => {
  it("forwards tenant-wide list filters and rejects unknown/invalid ones", () => {
    const target = buildTemplateProxyTarget("GET", [], params(`page=2&page_size=25&channel_id=${channelId}&status=approved&category=utility&language=en_US&search=order`));
    assert.equal(target.backendPath, "/templates");
    assert.equal(target.query.get("channel_id"), channelId);
    assert.equal(target.query.get("status"), "approved");
    assert.equal(target.query.get("category"), "utility");
    assert.equal(target.query.get("language"), "en_US");
    assert.equal(buildTemplateProxyTarget("GET", [], params("evil=1")), null);
    assert.equal(buildTemplateProxyTarget("GET", [], params("channel_id=not-a-uuid")), null);
    assert.equal(buildTemplateProxyTarget("GET", [], params("status=bad!status")), null);
    assert.equal(buildTemplateProxyTarget("GET", [], params("language=english-us")), null);
    assert.equal(buildTemplateProxyTarget("GET", [], params("page_size=101")), null);
  });

  it("accepts include_inactive only as a boolean", () => {
    assert.equal(buildTemplateProxyTarget("GET", [], params("include_inactive=true")).query.get("include_inactive"), "true");
    assert.equal(buildTemplateProxyTarget("GET", [], params("include_inactive=maybe")), null);
  });

  it("allows the shared template library and scoped admin actions", () => {
    assert.equal(buildTemplateProxyTarget("GET", ["platform-template-library"], params()).backendPath, "/platform-template-library");
    assert.equal(buildTemplateProxyTarget("GET", ["platform-template-library", "admin-status"], params()).backendPath, "/platform-template-library/admin-status");
    assert.equal(buildTemplateProxyTarget("POST", ["platform-template-library"], params()).backendPath, "/platform-template-library");
    assert.equal(buildTemplateProxyTarget("POST", ["platform-template-library", id, "submit"], params()).backendPath, `/platform-template-library/${id}/submit`);
    assert.equal(buildTemplateProxyTarget("POST", ["platform-template-library", id, "activate"], params()).backendPath, `/platform-template-library/${id}/activate`);
    assert.equal(buildTemplateProxyTarget("POST", ["platform-template-library", id, "deactivate"], params()).backendPath, `/platform-template-library/${id}/deactivate`);
    assert.equal(buildTemplateProxyTarget("POST", ["platform-template-library", "not-a-uuid", "submit"], params()), null);
    assert.equal(buildTemplateProxyTarget("DELETE", ["platform-template-library", id, "submit"], params()), null);
  });

  it("maps template details by id", () => {
    assert.equal(buildTemplateProxyTarget("GET", [id], params()).backendPath, `/templates/${id}`);
    assert.equal(buildTemplateProxyTarget("GET", ["not-a-uuid"], params()), null);
    assert.equal(buildTemplateProxyTarget("GET", [id], params("x=1")), null);
  });

  it("allows scoped template submissions and channel media uploads only", () => {
    assert.equal(buildTemplateProxyTarget("POST", ["submit"], params()).backendPath, "/templates/submit");
    assert.equal(buildTemplateProxyTarget("POST", ["channels", channelId, "media-upload"], params()).backendPath, `/templates/channels/${channelId}/media-upload`);
    assert.equal(buildTemplateProxyTarget("POST", ["channels", "not-a-uuid", "media-upload"], params()), null);
    assert.equal(buildTemplateProxyTarget("GET", ["submit"], params()), null);
    assert.equal(buildTemplateProxyTarget("POST", ["channels", channelId, "media-upload"], params("unexpected=1")), null);
  });

  it("reuses the existing channel sync endpoint", () => {
    const target = buildTemplateProxyTarget("POST", ["sync", channelId], params());
    assert.equal(target.backendPath, `/channels/${channelId}/templates/sync`);
    assert.equal(buildTemplateProxyTarget("POST", ["sync", "not-a-uuid"], params()), null);
    assert.equal(buildTemplateProxyTarget("POST", ["sync"], params()), null);
    assert.equal(buildTemplateProxyTarget("DELETE", ["sync", channelId], params()), null);
  });
});
