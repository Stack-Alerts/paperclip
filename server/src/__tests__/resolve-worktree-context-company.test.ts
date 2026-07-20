import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { resolveWorktreeContextCompanyId } from "../worktree-config.js";

describe("resolveWorktreeContextCompanyId", () => {
  let tmpDir: string;
  let savedEnv: NodeJS.ProcessEnv;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "paperclip-context-"));
    savedEnv = { ...process.env };
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
    process.env = savedEnv;
  });

  it("returns null when PAPERCLIP_CONTEXT is unset", () => {
    delete process.env.PAPERCLIP_CONTEXT;
    expect(resolveWorktreeContextCompanyId()).toBeNull();
  });

  it("returns null when the context file does not exist", () => {
    process.env.PAPERCLIP_CONTEXT = path.join(tmpDir, "missing.json");
    expect(resolveWorktreeContextCompanyId()).toBeNull();
  });

  it("returns null when the context file is malformed JSON", () => {
    const p = path.join(tmpDir, "broken.json");
    fs.writeFileSync(p, "{not valid json", "utf8");
    process.env.PAPERCLIP_CONTEXT = p;
    expect(resolveWorktreeContextCompanyId()).toBeNull();
  });

  it("returns null when currentProfile is missing", () => {
    const p = path.join(tmpDir, "no-profile.json");
    fs.writeFileSync(p, JSON.stringify({ profiles: { default: { companyId: "abc" } } }), "utf8");
    process.env.PAPERCLIP_CONTEXT = p;
    expect(resolveWorktreeContextCompanyId()).toBeNull();
  });

  it("returns null when the active profile is missing", () => {
    const p = path.join(tmpDir, "no-active-profile.json");
    fs.writeFileSync(
      p,
      JSON.stringify({ currentProfile: "staging", profiles: { default: { companyId: "abc" } } }),
      "utf8",
    );
    process.env.PAPERCLIP_CONTEXT = p;
    expect(resolveWorktreeContextCompanyId()).toBeNull();
  });

  it("returns null when companyId is empty in the active profile", () => {
    const p = path.join(tmpDir, "empty-company.json");
    fs.writeFileSync(
      p,
      JSON.stringify({ currentProfile: "default", profiles: { default: { companyId: "" } } }),
      "utf8",
    );
    process.env.PAPERCLIP_CONTEXT = p;
    expect(resolveWorktreeContextCompanyId()).toBeNull();
  });

  it("returns the companyId from the active profile", () => {
    const p = path.join(tmpDir, "ok.json");
    fs.writeFileSync(
      p,
      JSON.stringify({
        version: 2,
        currentProfile: "default",
        profiles: { default: { companyId: "73419cf3-bd37-4a7c-8782-311ccb47fced" } },
      }),
      "utf8",
    );
    process.env.PAPERCLIP_CONTEXT = p;
    expect(resolveWorktreeContextCompanyId()).toBe(
      "73419cf3-bd37-4a7c-8782-311ccb47fced",
    );
  });

  it("respects the explicit env argument", () => {
    const p = path.join(tmpDir, "ok.json");
    fs.writeFileSync(
      p,
      JSON.stringify({
        currentProfile: "default",
        profiles: { default: { companyId: "company-from-file" } },
      }),
      "utf8",
    );
    const env: NodeJS.ProcessEnv = {
      ...process.env,
      PAPERCLIP_CONTEXT: p,
    };
    expect(resolveWorktreeContextCompanyId(env)).toBe("company-from-file");
  });
});
