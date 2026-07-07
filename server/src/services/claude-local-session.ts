import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

/**
 * Mirrors Claude Code's project-dir encoding used at
 * packages/adapters/claude-local/src/server/execute.ts (the `poisonedJsonlPath`
 * computation) and at the Claude CLI itself. Non-alphanumeric characters in the
 * cwd become `-`; existing hyphens pass through. Keeping the encoding here lets
 * server-side preflight and sweeper code compute the same path the adapter (and
 * the CLI) would, without taking a dependency on the adapter package.
 */
export function encodeClaudeProjectDirSegment(cwd: string): string {
  return cwd.replace(/[^a-zA-Z0-9-]/g, "-");
}

export function resolveSharedClaudeConfigDir(
  env: NodeJS.ProcessEnv = process.env,
): string {
  const fromEnv = typeof env.CLAUDE_CONFIG_DIR === "string" && env.CLAUDE_CONFIG_DIR.trim().length > 0
    ? env.CLAUDE_CONFIG_DIR.trim()
    : null;
  return fromEnv ? path.resolve(fromEnv) : path.join(os.homedir(), ".claude");
}

export function claudeLocalSessionFilePath(input: {
  configDir?: string;
  cwd: string;
  sessionId: string;
}): string {
  const configDir = input.configDir ?? resolveSharedClaudeConfigDir();
  const encoded = encodeClaudeProjectDirSegment(input.cwd);
  return path.join(configDir, "projects", encoded, `${input.sessionId}.jsonl`);
}

/**
 * Returns true when the on-disk session file is absent. Symlink-aware stat:
 * follows links (matches `claude_local`'s own lookup). A "missing" file is
 * treated as such whether the cause is a deleted file, a dangling symlink, or
 * a permission error — the caller treats all three identically.
 */
export async function isClaudeLocalSessionFileMissing(input: {
  configDir?: string;
  cwd: string;
  sessionId: string;
}): Promise<boolean> {
  const sessionPath = claudeLocalSessionFilePath(input);
  try {
    const stats = await fs.stat(sessionPath);
    if (!stats.isFile() && !stats.isSymbolicLink()) return true;
    return false;
  } catch (err: unknown) {
    const code = (err as { code?: string } | null)?.code;
    if (code === "ENOENT" || code === "ENOTDIR" || code === "ELOOP") return true;
    // Permission errors etc. — treat as "cannot verify", not as missing.
    return false;
  }
}