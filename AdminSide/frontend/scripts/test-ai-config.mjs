import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, describe, it, beforeEach } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";
import ts from "typescript";

const root = fileURLToPath(new URL("..", import.meta.url));
const outDir = mkdtempSync(join(tmpdir(), "omniflow-ai-"));

const source = readFileSync(join(root, "src/components/ai/use-ai-config.ts"), "utf8")
  .replace(/import \{.*\} from "react";/, "")
  .replace(/import \{.*\} from "@\/lib\/ai\/browser";/, `
    const fetchAiConfig = async () => ({ provider: "platform", model: "gpt-4o", has_api_key: false });
    const updateAiConfig = async (update) => ({ provider: update.provider, model: update.model, has_api_key: !!update.api_key });
  `);
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
writeFileSync(join(outDir, "use-ai-config.mjs"), outputText);

const { useAiConfigHook } = await import(pathToFileURL(join(outDir, "use-ai-config.mjs")).href);
after(() => rmSync(outDir, { recursive: true, force: true }));

describe("AI Configuration Form State", () => {
  let states, setStates, stateIndex;
  
  function mockUseState(initialValue) {
    const idx = stateIndex++;
    if (states.length <= idx) {
      states[idx] = initialValue;
      setStates[idx] = (val) => { states[idx] = val; };
    }
    return [states[idx], setStates[idx]];
  }

  function mockUseEffect(effectFn) {
    // Just run it synchronously for the test
    effectFn();
  }

  beforeEach(() => {
    states = [];
    setStates = [];
  });

  function renderHook() {
    stateIndex = 0;
    return useAiConfigHook(mockUseState, mockUseEffect);
  }

  it("Platform-managed provider is selected by default", () => {
    const hook = renderHook();
    assert.equal(hook.provider, "platform");
  });

  it("Selecting OpenAI displays the appropriate configuration form (state change)", () => {
    let hook = renderHook();
    hook.setProvider("openai");
    
    hook = renderHook();
    assert.equal(hook.provider, "openai");
  });

  it("Required-field validation prevents saving empty API key", async () => {
    let hook = renderHook();
    hook.setProvider("openai");
    hook = renderHook();
    
    assert.equal(hook.isFormValid, false);
    
    await hook.handleSave(); // should do nothing
    hook = renderHook();
    assert.equal(hook.isSavedLocal, false);

    hook.setApiKey("sk-1234567890");
    hook = renderHook();
    assert.equal(hook.isFormValid, true);
    
    await hook.handleSave();
    hook = renderHook();
    assert.equal(hook.isSavedLocal, true);
  });

  it("Show/hide API key control toggles state", () => {
    let hook = renderHook();
    assert.equal(hook.showKey, false);
    
    hook.setShowKey(!hook.showKey);
    hook = renderHook();
    assert.equal(hook.showKey, true);
  });

  it("Cancel resets unsaved form changes", async () => {
    let hook = renderHook();
    
    hook.setApiKey("sk-1234567890");
    hook = renderHook();
    assert.equal(hook.hasUnsavedChanges, true);
    assert.equal(hook.apiKey, "sk-1234567890");
    
    // Save it
    await hook.handleSave();
    hook = renderHook();
    assert.equal(hook.hasUnsavedChanges, false);
    
    // Modify again
    hook.setApiKey("sk-new");
    hook.setModel("gpt-4-turbo");
    hook = renderHook();
    assert.equal(hook.hasUnsavedChanges, true);
    
    // Cancel
    hook.handleCancel();
    hook = renderHook();
    
    assert.equal(hook.hasUnsavedChanges, false);
    assert.equal(hook.apiKey, "••••••••••••••••"); // reverted
    assert.equal(hook.model, "gpt-4o"); // reverted
    assert.equal(hook.isSavedLocal, false);
  });

  it("Saving does not claim server persistence (isSavedLocal is true)", async () => {
    let hook = renderHook();
    hook.setApiKey("sk-validkey");
    hook = renderHook();
    await hook.handleSave();
    
    hook = renderHook();
    assert.equal(hook.isSavedLocal, true);
  });
});
