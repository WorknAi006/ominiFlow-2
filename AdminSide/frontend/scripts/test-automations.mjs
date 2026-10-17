import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, describe, it } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";
import ts from "typescript";

const root = fileURLToPath(new URL("..", import.meta.url));
const out = mkdtempSync(join(tmpdir(), "omniflow-automations-"));
const source = readFileSync(join(root, "src/lib/automations/proxy-utils.ts"), "utf8");
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
writeFileSync(join(out, "proxy.mjs"), js);
const { buildAutomationTarget } = await import(pathToFileURL(join(out, "proxy.mjs")).href);
after(() => rmSync(out, { recursive: true, force: true }));

const automationId = "a4f48072-9c16-4ea0-b690-2ee865eb03a1";
const executionId = "b5f48072-9c16-4ea0-b690-2ee865eb03a2";

describe("automation API proxy allowlist", () => {
  it("allows tenant-scoped CRUD and safe query parameters", () => {
    assert.equal(buildAutomationTarget("GET", [], new URLSearchParams("page=2&page_size=25&status=draft"))?.backendPath, "/automations");
    assert.equal(buildAutomationTarget("POST", [], new URLSearchParams())?.backendPath, "/automations");
    assert.equal(buildAutomationTarget("GET", [automationId], new URLSearchParams())?.backendPath, `/automations/${automationId}`);
    assert.equal(buildAutomationTarget("PUT", [automationId, "flow"], new URLSearchParams())?.method, "PUT");
    assert.equal(buildAutomationTarget("DELETE", [automationId], new URLSearchParams())?.method, "DELETE");
    assert.equal(buildAutomationTarget("GET", ["worker-health"], new URLSearchParams())?.backendPath, "/automations/worker-health");
    assert.equal(buildAutomationTarget("GET", [automationId, "metrics"], new URLSearchParams())?.backendPath, `/automations/${automationId}/metrics`);
  });
  it("allows validation, lifecycle, simulation and tenant-bound execution logs", () => {
    for (const action of ["validate", "activate", "pause", "simulate"]) assert.ok(buildAutomationTarget("POST", [automationId, action], new URLSearchParams()));
    assert.equal(buildAutomationTarget("GET", [automationId, "executions", executionId, "logs"], new URLSearchParams())?.backendPath, `/automations/${automationId}/executions/${executionId}/logs`);
  });
  it("rejects unsupported methods, malformed ids, paths, and query injection", () => {
    assert.equal(buildAutomationTarget("POST", [automationId, "flow"], new URLSearchParams()), null);
    assert.equal(buildAutomationTarget("GET", ["../users"], new URLSearchParams()), null);
    assert.equal(buildAutomationTarget("GET", [automationId], new URLSearchParams("include_secrets=true")), null);
    assert.equal(buildAutomationTarget("GET", [], new URLSearchParams("status=anything")), null);
  });
});
