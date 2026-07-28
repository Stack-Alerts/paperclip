import { execFile } from "node:child_process";
import { promisify } from "node:util";
import {
  CLOSURE_GATE_FIX_SHA_LINE_REGEX,
  CLOSURE_GATE_FIX_REPO_LINE_REGEX,
  CLOSURE_GATE_VERIFY_CACHE_TTL_MS,
  type ClosureGateFixShaMode,
} from "@paperclipai/shared";
import { unprocessable } from "../errors.js";

const execFileAsync = promisify(execFile);

/**
 * Closure-gate service.
 *
 * When a company has `closure_gate_fix_sha = "enforce"`, an agent PATCH that
 * sets an issue to `status: "done"` must include three contract elements in
 * the closure comment (or in a fallback comment when both are scanned):
 *
 *   1. `Fix-SHA: <40-hex-sha>` — the commit the agent is closing on.
 *   2. `Fix-Target: <branch>` (optional, defaults to `main`) — the ref
 *      `git ls-remote` should consult to confirm the SHA is reachable.
 *   3. `Fix-Repo: <url>` (optional) — overrides the `executionWorkspaces`
 *      `repoUrl` for the verification `git ls-remote` call. Use this when
 *      the issue inherits a workspace whose repo is not where the fix
 *      landed (e.g. Paperclip-side rollout decisions on a different fork).
 *      If `Fix-Repo:` is present but malformed or unreachable, the gate
 *      returns the same 422 it would for an unreachable SHA on the
 *      default repo (surfaced as a `git_error`).
 *
 * SHA verification prefers the LOCAL git object database (`git rev-parse
 * --verify <sha>^{commit}` + `git cat-file -t <sha>`) when a local repo
 * path is resolvable via `resolveLocalRepoCwd`. A real SHA held on a
 * working branch passes this check even before it lands on the canonical
 * remote ref, eliminating false-positive "fabricated SHA" flags. A truly
 * fabricated SHA fails this check locally with rc=128. When no local
 * repo path is available, the gate falls back to the canonical-ref
 * `git ls-remote` check (the previous behavior).
 *
 * If any required element is missing in `enforce` mode the gate rejects
 * the closure with HTTP 422. In `advisory` mode the same checks run but
 * the gate logs a warning and allows the closure. In `off` mode the gate
 * is a no-op.
 */

export const CLOSURE_GATE_DEFAULT_TARGET = "main";
export const CLOSURE_GATE_LS_REMOTE_TIMEOUT_MS = 10_000;

/**
 * Substring patterns that indicate git's "object does not exist" error.
 * When `git rev-parse --verify` or `git cat-file -t` is asked about a
 * fabricated SHA, git exits rc=128 and prints one of these on stderr.
 */
const GIT_OBJECT_NOT_FOUND_PATTERNS = [
  /Not a valid object/i,
  /bad object/i,
  /unknown revision or path/i,
  /couldn't find/i,
  /not our ref/i,
  /invalid object/i,
];

/**
 * CTO Fix-SHA override marker.
 *
 * When a closure comment contains a `CTO-Override: skip-verify` line, the
 * closure-gate skips the `git ls-remote` Fix-SHA reachability check and
 * allows the closure per CTO authority. This unblocks the Paperclip-side
 * override cycle (board authorizes closure on a SHA that is not yet merged
 * to the canonical remote) without forcing the SHA to be pushed to the
 * canonical branch prematurely.
 *
 * The marker is intentionally strict (must match exactly) so it cannot be
 * accidentally triggered by an agent that happens to mention the phrase in
 * a regular comment.
 */
export const CLOSURE_GATE_CTO_OVERRIDE_SKIP_REGEX = /CTO-Override:\s*skip-verify/i;

export type ClosureGateFixSha = {
  sha: string;
  target: string;
};

export type ClosureGateActorLike = {
  actorType: "agent" | "user";
  agentId?: string | null;
};

export type ClosureGateRejectReason =
  | "actor_not_agent"
  | "missing_fix_sha"
  | "unreachable_sha"
  | "git_error";

export type ClosureGateLogger = {
  warn: (payload: Record<string, unknown>, message: string) => void;
};

export type ClosureGateAssertInput = {
  companyMode: ClosureGateFixShaMode;
  actor: ClosureGateActorLike;
  commentBody: string | null | undefined;
  fallbackCommentBody?: string | null;
  resolveRepoUrl: () => Promise<string | null> | string | null;
  /**
   * Optional resolver for a local git repo working directory. When this
   * returns a usable path, the gate verifies the Fix-SHA against the LOCAL
   * object database (`git rev-parse --verify` + `git cat-file -t`) instead
   * of the canonical-ref `git ls-remote` check. This eliminates false
   * positives on SHAs that exist on the working branch but have not yet
   * been pushed to the canonical remote ref.
   */
  resolveLocalRepoCwd?: () => Promise<string | null> | string | null;
  /**
   * Optional approval lookup, evaluated when the closure comment body
   * contains the `CTO-Override: skip-verify` marker. When this returns
   * `true`, the override marker bypasses SHA verification entirely
   * (board Option B path). When absent or `false`, the override marker
   * is treated as advisory only and verification still runs.
   */
  hasApprovedBoardOverride?: () => Promise<boolean> | boolean;
  defaultTarget?: string;
  clock?: () => number;
  fetchImpl?: (repoUrl: string, target: string) => Promise<Set<string>>;
  logger?: ClosureGateLogger;
};

export type ClosureGateOutcome =
  | { allowed: true; mode: ClosureGateFixShaMode; fixSha: ClosureGateFixSha; verified: "fresh" | "cache" | "local"; verificationFailed?: false }
  | { allowed: true; mode: ClosureGateFixShaMode; fixSha: ClosureGateFixSha; verified: null; verificationFailed: true }
  | { allowed: true; mode: ClosureGateFixShaMode; fixSha: ClosureGateFixSha; verified: null; verificationFailed: false; override: "cto_fix_sha_skip_verify" }
  | { allowed: true; mode: ClosureGateFixShaMode; fixSha: null; verified: null; verificationFailed?: boolean }
  | { allowed: false; mode: ClosureGateFixShaMode; reason: ClosureGateRejectReason; message: string };

export function extractFixSha(body: string | null | undefined): ClosureGateFixSha | null {
  if (!body) return null;
  const match = CLOSURE_GATE_FIX_SHA_LINE_REGEX.exec(body);
  if (!match) return null;
  const sha = match[1]?.toLowerCase();
  if (!sha) return null;
  const rawTarget = match[2]?.trim();
  const target = rawTarget && rawTarget.length > 0 ? rawTarget : CLOSURE_GATE_DEFAULT_TARGET;
  return { sha, target };
}

/**
 * Extracts a `Fix-Repo: <url>` override from a closure comment, if present.
 *
 * When the closing agent's issue inherits an `executionWorkspaces` repo that
 * is *not* the repo where the fix actually landed (e.g. Paperclip-side
 * rollout decisions on a different fork), the closure comment can declare
 * the correct `git ls-remote` target via a `Fix-Repo:` line. This is the
 * per-closure companion to `executionWorkspaces.repoUrl`, not a replacement
 * for it: absent the line, the gate falls back to the workspace's
 * configured repo URL.
 */
export function extractFixRepo(body: string | null | undefined): string | null {
  if (!body) return null;
  const match = CLOSURE_GATE_FIX_REPO_LINE_REGEX.exec(body);
  if (!match) return null;
  const url = match[1]?.trim();
  return url && url.length > 0 ? url : null;
}

export function createClosureGateCache(ttlMs: number = CLOSURE_GATE_VERIFY_CACHE_TTL_MS) {
  const entries = new Map<string, { value: Set<string>; expiresAt: number }>();

  function key(repoUrl: string, target: string) {
    return `${repoUrl}::${target}`;
  }

  function get(repoUrl: string, target: string, now: number): Set<string> | undefined {
    const entry = entries.get(key(repoUrl, target));
    if (!entry) return undefined;
    if (entry.expiresAt <= now) {
      entries.delete(key(repoUrl, target));
      return undefined;
    }
    return entry.value;
  }

  function set(repoUrl: string, target: string, value: Set<string>, now: number) {
    entries.set(key(repoUrl, target), { value, expiresAt: now + ttlMs });
  }

  function clear() {
    entries.clear();
  }

  return { get, set, clear, _size: () => entries.size };
}

export class ClosureGateGitError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ClosureGateGitError";
  }
}

export async function fetchReachableShasFromRemote(
  repoUrl: string,
  target: string,
  timeoutMs: number = CLOSURE_GATE_LS_REMOTE_TIMEOUT_MS,
): Promise<Set<string>> {
  try {
    const { stdout } = await execFileAsync(
      "git",
      ["ls-remote", "--quiet", repoUrl, target],
      { timeout: timeoutMs, maxBuffer: 4 * 1024 * 1024 },
    );
    return parseLsRemoteOutput(stdout);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    throw new ClosureGateGitError(message);
  }
}

export function parseLsRemoteOutput(stdout: string): Set<string> {
  const shas = new Set<string>();
  for (const line of stdout.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const parts = trimmed.split(/\s+/);
    const sha = parts[0];
    if (sha && /^[0-9a-f]{40}$/.test(sha)) {
      shas.add(sha.toLowerCase());
    }
  }
  return shas;
}

/**
 * Verify a Fix-SHA against the LOCAL git object database.
 *
 * This is the primary Fix-SHA verification path used by the closure-gate
 * when the closing agent's execution workspace exposes a local repo path.
 * It distinguishes "real SHA held locally" from "fabricated SHA" — the
 * remote-ref check conflates the two because pushing to canonical is
 * decoupled from authoring the commit.
 *
 * A SHA is considered real when both:
 *   - `git -C <cwd> rev-parse --verify <sha>^{commit}` exits 0 (the SHA
 *     peels to an existing commit object; `^{commit}` also resolves tag
 *     SHAs to the tagged commit).
 *   - `git -C <cwd> cat-file -t <sha>` exits 0 (the raw SHA resolves to
 *     a known object type — commit, tag, blob, etc.).
 *
 * Both checks are required so that a SHA pointing at a non-commit object
 * (a fabricated blob/tree) cannot pass by accident.
 *
 * A fabricated SHA causes git to exit rc=128 and print one of the
 * patterns in `GIT_OBJECT_NOT_FOUND_PATTERNS` on stderr; that case is
 * classified as `unreachable_sha`. Any other git failure (e.g. the cwd
 * is not a git repo, permission denied) is `git_error`.
 */
export async function verifyFixShaLocal(args: {
  cwd: string;
  sha: string;
  execImpl?: typeof execFileAsync;
  timeoutMs?: number;
}): Promise<
  | { ok: true; source: "local" }
  | { ok: false; reason: "unreachable_sha" | "git_error"; message: string }
> {
  const { cwd, sha } = args;
  const exec = args.execImpl ?? execFileAsync;
  const timeoutMs = args.timeoutMs ?? CLOSURE_GATE_LS_REMOTE_TIMEOUT_MS;

  try {
    await exec(
      "git",
      ["-C", cwd, "rev-parse", "--verify", `${sha}^{commit}`],
      { timeout: timeoutMs, maxBuffer: 1024 * 1024 },
    );
    await exec(
      "git",
      ["-C", cwd, "cat-file", "-t", sha],
      { timeout: timeoutMs, maxBuffer: 1024 * 1024 },
    );
    return { ok: true, source: "local" };
  } catch (err) {
    const code = typeof err === "object" && err && "code" in err
      ? (err as { code?: unknown }).code
      : null;
    const stderr = typeof err === "object" && err && "stderr" in err
      ? String((err as { stderr?: unknown }).stderr ?? "")
      : "";
    const exitCode = typeof code === "number" ? code : null;

    const notFound =
      exitCode === 128 ||
      GIT_OBJECT_NOT_FOUND_PATTERNS.some((p) => p.test(stderr));
    if (notFound) {
      return {
        ok: false,
        reason: "unreachable_sha",
        message: `Fix-SHA ${sha} is not present in the local object database at ${cwd}`,
      };
    }
    const detail = err instanceof Error ? err.message : String(err);
    return {
      ok: false,
      reason: "git_error",
      message: `git local verification failed for Fix-SHA ${sha} at ${cwd}: ${detail}`,
    };
  }
}

export async function verifyFixShaOnRemote(args: {
  repoUrl: string;
  target: string;
  sha: string;
  cache?: ReturnType<typeof createClosureGateCache>;
  clock?: () => number;
  fetchImpl?: (repoUrl: string, target: string) => Promise<Set<string>>;
}): Promise<
  | { ok: true; source: "fresh" | "cache" }
  | { ok: false; reason: "unreachable_sha" | "git_error"; message: string }
> {
  const { repoUrl, target, sha } = args;
  const clock = args.clock ?? Date.now;
  const fetchImpl = args.fetchImpl ?? ((u, t) => fetchReachableShasFromRemote(u, t));
  const cache = args.cache;

  if (cache) {
    const cached = cache.get(repoUrl, target, clock());
    if (cached) {
      return cached.has(sha.toLowerCase())
        ? { ok: true, source: "cache" }
        : {
            ok: false,
            reason: "unreachable_sha",
            message: `Fix-SHA ${sha} is not reachable on ${repoUrl}@${target}`,
          };
    }
  }

  let reachable: Set<string>;
  try {
    reachable = await fetchImpl(repoUrl, target);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      ok: false,
      reason: "git_error",
      message: `git ls-remote failed for ${repoUrl}@${target}: ${message}`,
    };
  }
  if (cache) cache.set(repoUrl, target, reachable, clock());
  return reachable.has(sha.toLowerCase())
    ? { ok: true, source: "fresh" }
    : {
        ok: false,
        reason: "unreachable_sha",
        message: `Fix-SHA ${sha} is not reachable on ${repoUrl}@${target}`,
      };
}

export function createClosureGate(
  options: {
    cache?: ReturnType<typeof createClosureGateCache>;
    clock?: () => number;
    fetchImpl?: (repoUrl: string, target: string) => Promise<Set<string>>;
    /**
     * Optional override for the local git object database verification.
     * Defaults to `verifyFixShaLocal`. Tests inject a mock here so they
     * can simulate fabricated / real SHAs without spawning `git`.
     */
    localVerifyImpl?: (args: { cwd: string; sha: string }) => Promise<
      | { ok: true; source: "local" }
      | { ok: false; reason: "unreachable_sha" | "git_error"; message: string }
    >;
    logger?: ClosureGateLogger;
    defaultTarget?: string;
  } = {},
) {
  const cache = options.cache ?? createClosureGateCache();
  const clock = options.clock ?? Date.now;
  const fetchImpl = options.fetchImpl;
  const localVerifyImpl = options.localVerifyImpl ?? verifyFixShaLocal;
  const logger = options.logger;
  const defaultTarget = options.defaultTarget ?? CLOSURE_GATE_DEFAULT_TARGET;

  async function assertAllowed(input: ClosureGateAssertInput): Promise<ClosureGateOutcome> {
    const mode = input.companyMode;

    if (mode === "off") {
      return { allowed: true, mode, fixSha: null, verified: null, verificationFailed: false };
    }

    if (input.actor.actorType !== "agent") {
      return { allowed: true, mode, fixSha: null, verified: null, verificationFailed: false };
    }

    const combinedBody = [input.commentBody, input.fallbackCommentBody]
      .filter((b): b is string => typeof b === "string" && b.length > 0)
      .join("\n");
    const fixSha = extractFixSha(combinedBody);

    if (!fixSha) {
      if (mode === "advisory") {
        logger?.warn(
          { mode, reason: "missing_fix_sha" },
          "closure-gate advisory: no Fix-SHA line found in closure comment",
        );
        return { allowed: true, mode, fixSha: null, verified: null, verificationFailed: true };
      }
      return {
        allowed: false,
        mode,
        reason: "missing_fix_sha",
        message:
          "Closure-gate enforce: PATCH setting status=done by an agent requires a 'Fix-SHA: <40-hex-sha>' line in the closure comment (optionally followed by 'Fix-Target: <branch>').",
      };
    }

    if (CLOSURE_GATE_CTO_OVERRIDE_SKIP_REGEX.test(combinedBody)) {
      const hasApprovedBoardOverride = await input.hasApprovedBoardOverride?.();
      if (hasApprovedBoardOverride === true) {
        logger?.warn(
          { mode, fixSha: fixSha.sha, target: fixSha.target, override: "cto_fix_sha_skip_verify" },
          "closure-gate: CTO Fix-SHA override marker honored with linked approved board approval; skipping SHA verification",
        );
        return {
          allowed: true,
          mode,
          fixSha: { sha: fixSha.sha, target: fixSha.target },
          verified: null,
          verificationFailed: false,
          override: "cto_fix_sha_skip_verify",
        };
      }
      logger?.warn(
        { mode, fixSha: fixSha.sha, target: fixSha.target, override: "cto_fix_sha_skip_verify", hasApprovedBoardOverride: false },
        "closure-gate: CTO Fix-SHA override marker detected without linked approved board approval; continuing SHA verification",
      );
    }

    const target = fixSha.target || defaultTarget;

    // Prefer LOCAL git object database verification when a local repo cwd
    // is resolvable. A real SHA held on a working branch passes even if it
    // has not been pushed to the canonical remote ref, eliminating the
    // false-positive "fabricated SHA" signal that the previous remote-only
    // check produced. When no local cwd is available, fall back to the
    // canonical-ref `git ls-remote` check.
    const resolvedLocalCwd = await input.resolveLocalRepoCwd?.();
    if (typeof resolvedLocalCwd === "string" && resolvedLocalCwd.length > 0) {
      const localVerify = await localVerifyImpl({
        cwd: resolvedLocalCwd,
        sha: fixSha.sha,
      });
      if (localVerify.ok) {
        return {
          allowed: true,
          mode,
          fixSha: { sha: fixSha.sha, target },
          verified: "local",
          verificationFailed: false,
        };
      }
      if (mode === "advisory") {
        logger?.warn(
          {
            mode,
            reason: localVerify.reason,
            fixSha: fixSha.sha,
            target,
            localCwd: resolvedLocalCwd,
            message: localVerify.message,
          },
          "closure-gate advisory: local Fix-SHA verification failed",
        );
        return {
          allowed: true,
          mode,
          fixSha: { sha: fixSha.sha, target },
          verified: null,
          verificationFailed: true,
        };
      }
      return { allowed: false, mode, reason: localVerify.reason, message: localVerify.message };
    }

    const fixRepoOverride = extractFixRepo(combinedBody);
    const resolvedRepoUrl = await input.resolveRepoUrl();
    const repoUrl = fixRepoOverride ?? resolvedRepoUrl;
    if (!repoUrl) {
      if (mode === "advisory") {
        logger?.warn(
          { mode, reason: "git_error", fixSha: fixSha.sha, target },
          "closure-gate advisory: no repo URL configured for company",
        );
        return { allowed: true, mode, fixSha: null, verified: null, verificationFailed: true };
      }
      return {
        allowed: false,
        mode,
        reason: "git_error",
        message: `Closure-gate enforce: company has no configured remote repository URL to verify Fix-SHA ${fixSha.sha}.`,
      };
    }

    const verify = await verifyFixShaOnRemote({
      repoUrl,
      target,
      sha: fixSha.sha,
      cache,
      clock,
      fetchImpl,
    });

    if (verify.ok) {
      return {
        allowed: true,
        mode,
        fixSha: { sha: fixSha.sha, target },
        verified: verify.source,
        verificationFailed: false,
      };
    }

    if (mode === "advisory") {
      logger?.warn(
        { mode, reason: verify.reason, fixSha: fixSha.sha, target, repoUrl, message: verify.message },
        "closure-gate advisory: Fix-SHA verification failed",
      );
      return {
        allowed: true,
        mode,
        fixSha: { sha: fixSha.sha, target },
        verified: null,
        verificationFailed: true,
      };
    }

    return { allowed: false, mode, reason: verify.reason, message: verify.message };
  }

  return { assertAllowed, extractFixSha, verifyFixShaOnRemote, verifyFixShaLocal: localVerifyImpl, cache };
}

export function throwIfClosureGateRejected(outcome: ClosureGateOutcome): void {
  if (outcome.allowed) return;
  throw unprocessable(outcome.message, { reason: outcome.reason, mode: outcome.mode });
}
