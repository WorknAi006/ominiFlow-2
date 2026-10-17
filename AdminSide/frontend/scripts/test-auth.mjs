import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, describe, it } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";
import ts from "typescript";

const root = fileURLToPath(new URL("..", import.meta.url));
const outDir = mkdtempSync(join(tmpdir(), "omniflow-auth-"));

for (const [source, target] of [
  ["src/lib/auth/session-utils.ts", "session-utils.mjs"],
  ["src/lib/auth/validation.ts", "validation.mjs"],
]) {
  const { outputText } = ts.transpileModule(readFileSync(join(root, source), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  });
  writeFileSync(join(outDir, target), outputText);
}

const session = await import(pathToFileURL(join(outDir, "session-utils.mjs")).href);
const validation = await import(pathToFileURL(join(outDir, "validation.mjs")).href);
after(() => rmSync(outDir, { recursive: true, force: true }));

function fakeToken(claims) {
  const encode = (value) => Buffer.from(JSON.stringify(value)).toString("base64url");
  return `${encode({ alg: "none" })}.${encode(claims)}.synthetic-signature`;
}

describe("browser session protections", () => {
  it("sets a host-only, HttpOnly, same-site cookie with the requested lifetime", () => {
    assert.deepEqual(session.sessionCookieOptions(true, 600), {
      httpOnly: true,
      secure: true,
      sameSite: "lax",
      path: "/",
      maxAge: 600,
    });
    assert.equal(session.sessionCookieOptions(false, 60).secure, false);
  });

  it("uses a valid token expiry and rejects malformed or expired tokens", () => {
    const token = fakeToken({ sub: "synthetic-user", exp: 1_700_000_600 });
    assert.equal(session.tokenMaxAgeSeconds(token, 1_700_000_000), 600);
    assert.equal(session.tokenMaxAgeSeconds(token, 1_700_000_601), null);
    assert.equal(session.tokenMaxAgeSeconds("not-a-token", 1_700_000_000), null);
  });

  it("allows only local internal post-login destinations", () => {
    assert.equal(session.safeInternalPath("/inbox"), "/inbox");
    assert.equal(session.safeInternalPath("//attacker.example"), "/dashboard");
    assert.equal(session.safeInternalPath("https://attacker.example"), "/dashboard");
    assert.equal(session.safeInternalPath("/\\attacker.example"), "/dashboard");
  });
});

describe("authentication form validation", () => {
  it("requires valid login fields", () => {
    assert.match(validation.validateLogin("", ""), /required|enter/i);
    assert.match(validation.validateLogin("not-an-email", "password"), /email/i);
    assert.equal(validation.validateLogin("agent@example.test", "synthetic-password"), null);
  });

  it("validates registration against backend field constraints", () => {
    const values = {
      email: "owner@example.test",
      password: "synthetic-password",
      confirmPassword: "synthetic-password",
      firstName: "Sample",
      lastName: "User",
      tenantName: "Sample Workspace",
    };
    assert.equal(validation.validateRegistration(values), null);
    assert.match(validation.validateRegistration({ ...values, confirmPassword: "different-password" }), /match/i);
    assert.match(validation.validateRegistration({ ...values, tenantName: "x" }), /workspace/i);
  });
});
