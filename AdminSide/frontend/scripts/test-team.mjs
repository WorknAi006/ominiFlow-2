import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, describe, it } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";
import ts from "typescript";

const root = fileURLToPath(new URL("..", import.meta.url));
const outDir = mkdtempSync(join(tmpdir(), "omniflow-team-"));
const source = readFileSync(join(root, "src/lib/team/proxy-utils.ts"), "utf8");
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
writeFileSync(join(outDir, "proxy-utils.mjs"), outputText);
const { buildTeamProxyTarget } = await import(pathToFileURL(join(outDir, "proxy-utils.mjs")).href);
after(() => rmSync(outDir, { recursive: true, force: true }));

const id = "123e4567-e89b-42d3-a456-426614174000";
const roleId = "123e4567-e89b-42d3-a456-426614174abc";
const params = (q = "") => new URLSearchParams(q);

describe("Team proxy allowlist", () => {
  it("maps member listing with pagination/search and rejects unknown params", () => {
    const target = buildTeamProxyTarget("GET", [], params("page=2&page_size=25&search=ann"));
    assert.equal(target.backendPath, "/users");
    assert.equal(target.query.get("page"), "2");
    assert.equal(target.query.get("search"), "ann");
    assert.equal(buildTeamProxyTarget("GET", [], params("evil=1")), null);
    assert.equal(buildTeamProxyTarget("GET", [], params("page_size=101")), null);
  });

  it("maps roles and invitations, redacting the invitation token", () => {
    assert.equal(buildTeamProxyTarget("GET", ["roles"], params()).backendPath, "/roles");
    const invites = buildTeamProxyTarget("GET", ["invitations"], params());
    assert.equal(invites.backendPath, "/users/invitations");
    assert.deepEqual(invites.redact, ["invitation_token"]);
  });

  it("validates the invite body and always redacts the token", () => {
    const ok = buildTeamProxyTarget("POST", ["invite"], params(), { email: " New@Example.com ", role_id: roleId });
    assert.equal(ok.backendPath, "/users/invite");
    assert.equal(ok.body.email, "new@example.com");
    assert.deepEqual(ok.redact, ["invitation_token"]);
    assert.equal(buildTeamProxyTarget("POST", ["invite"], params(), { email: "bad", role_id: roleId }), null);
    assert.equal(buildTeamProxyTarget("POST", ["invite"], params(), { email: "a@b.co", role_id: "not-a-uuid" }), null);
    assert.equal(buildTeamProxyTarget("POST", ["invite"], params(), { email: "a@b.co", role_id: roleId, extra: 1 }), null);
  });

  it("validates member role/status updates and removals", () => {
    assert.equal(buildTeamProxyTarget("PATCH", [id], params(), { role_id: roleId }).backendPath, `/users/${id}`);
    assert.equal(buildTeamProxyTarget("PATCH", [id], params(), { status: "suspended" }).body.status, "suspended");
    assert.equal(buildTeamProxyTarget("PATCH", [id], params(), { status: "removed" }), null);
    assert.equal(buildTeamProxyTarget("PATCH", [id], params(), {}), null);
    assert.equal(buildTeamProxyTarget("DELETE", [id], params()).expectsNoContent, true);
    assert.equal(buildTeamProxyTarget("DELETE", ["invitations", id], params()).backendPath, `/users/invitations/${id}`);
    assert.equal(buildTeamProxyTarget("DELETE", ["not-a-uuid"], params()), null);
  });
});
