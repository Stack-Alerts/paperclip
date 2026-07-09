import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  claudeLocalSessionFilePath,
  encodeClaudeProjectDirSegment,
  isClaudeLocalSessionFileMissing,
  resolveSharedClaudeConfigDir,
} from "../services/claude-local-session.ts";

let tempRoot: string | null = null;
let originalClaudeConfigDir: string | undefined;

beforeEach(async () => {
  tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), "paperclip-claude-session-"));
  originalClaudeConfigDir = process.env.CLAUDE_CONFIG_DIR;
  process.env.CLAUDE_CONFIG_DIR = tempRoot;
});

afterEach(async () => {
  if (originalClaudeConfigDir === undefined) {
    delete process.env.CLAUDE_CONFIG_DIR;
  } else {
    process.env.CLAUDE_CONFIG_DIR = originalClaudeConfigDir;
  }
  if (tempRoot) {
    await fs.rm(tempRoot, { recursive: true, force: true });
    tempRoot = null;
  }
});

describe("encodeClaudeProjectDirSegment", () => {
  it("replaces non-alphanumeric chars with hyphens and preserves existing hyphens", () => {
    expect(encodeClaudeProjectDirSegment("/home/user/my project!")).toBe(
      "-home-user-my-project-",
    );
    expect(encodeClaudeProjectDirSegment("/var/log/app.log")).toBe(
      "-var-log-app-log",
    );
  });

  it("passes through alphanumerics and hyphens untouched, encodes underscores", () => {
    // Claude's own encoding replaces anything outside [a-zA-Z0-9-]; underscores
    // are not in that set. Document the contract instead of asserting
    // "untouched" — the adapter matches Claude's exact behavior.
    expect(encodeClaudeProjectDirSegment("/home/user/app-name-1")).toBe(
      "-home-user-app-name-1",
    );
    expect(encodeClaudeProjectDirSegment("/home/user/app_name_1")).toBe(
      "-home-user-app-name-1",
    );
  });
});

describe("resolveSharedClaudeConfigDir", () => {
  it("returns CLAUDE_CONFIG_DIR when set", () => {
    process.env.CLAUDE_CONFIG_DIR = "/custom/claude";
    expect(resolveSharedClaudeConfigDir()).toBe(path.resolve("/custom/claude"));
  });

  it("falls back to ~/.claude when unset", () => {
    delete process.env.CLAUDE_CONFIG_DIR;
    expect(resolveSharedClaudeConfigDir()).toBe(path.join(os.homedir(), ".claude"));
  });

  it("ignores blank CLAUDE_CONFIG_DIR", () => {
    process.env.CLAUDE_CONFIG_DIR = "   ";
    expect(resolveSharedClaudeConfigDir()).toBe(path.join(os.homedir(), ".claude"));
  });
});

describe("claudeLocalSessionFilePath", () => {
  it("builds the same path the claude_local adapter unlinks (BFG-poisoned-session case)", () => {
    const cwd = "/home/sirrus/projects/BTC-Trade-Engine-PaperClip";
    const sessionId = "97b59333-7fc0-4f0d-bd4e-d5f174e43ff2";
    const expected = path.join(
      tempRoot!,
      "projects",
      encodeClaudeProjectDirSegment(cwd),
      `${sessionId}.jsonl`,
    );
    expect(
      claudeLocalSessionFilePath({
        configDir: tempRoot!,
        cwd,
        sessionId,
      }),
    ).toBe(expected);
  });

  it("accepts an explicit configDir override", () => {
    expect(
      claudeLocalSessionFilePath({
        configDir: "/tmp/explicit",
        cwd: "/x",
        sessionId: "abc",
      }),
    ).toBe("/tmp/explicit/projects/-x/abc.jsonl");
  });
});

describe("isClaudeLocalSessionFileMissing", () => {
  const cwd = "/home/sirrus/projects/repo";
  const sessionId = "11111111-2222-3333-4444-555555555555";

  function sessionPath(): string {
    return path.join(
      tempRoot!,
      "projects",
      encodeClaudeProjectDirSegment(cwd),
      `${sessionId}.jsonl`,
    );
  }

  async function touchSessionFile(): Promise<void> {
    const target = sessionPath();
    await fs.mkdir(path.dirname(target), { recursive: true });
    await fs.writeFile(target, "{}", "utf8");
  }

  it("returns false when the session file exists on disk", async () => {
    await touchSessionFile();
    await expect(
      isClaudeLocalSessionFileMissing({ configDir: tempRoot!, cwd, sessionId }),
    ).resolves.toBe(false);
  });

  it("returns true when the session file is absent", async () => {
    await fs.mkdir(path.dirname(sessionPath()), { recursive: true });
    // Note: not creating the file.
    await expect(
      isClaudeLocalSessionFileMissing({ configDir: tempRoot!, cwd, sessionId }),
    ).resolves.toBe(true);
  });

  it("returns true when the projects dir has not been created yet (ENOENT)", async () => {
    // No mkdir at all.
    await expect(
      isClaudeLocalSessionFileMissing({ configDir: tempRoot!, cwd, sessionId }),
    ).resolves.toBe(true);
  });

  it("returns true when the path exists but is a directory (not a file)", async () => {
    await fs.mkdir(sessionPath(), { recursive: true });
    await expect(
      isClaudeLocalSessionFileMissing({ configDir: tempRoot!, cwd, sessionId }),
    ).resolves.toBe(true);
  });

  it("returns false (treated as cannot-verify) on a permission error", async () => {
    if (process.getuid && process.getuid() !== 0) {
      await touchSessionFile();
      await fs.chmod(sessionPath(), 0o000);
      try {
        await expect(
          isClaudeLocalSessionFileMissing({ configDir: tempRoot!, cwd, sessionId }),
        ).resolves.toBe(false);
      } finally {
        await fs.chmod(sessionPath(), 0o600);
      }
    } else {
      // root bypasses permissions; nothing to assert, just confirm the call resolves.
      await expect(
        isClaudeLocalSessionFileMissing({ configDir: tempRoot!, cwd, sessionId }),
      ).resolves.toBeDefined();
    }
  });
});