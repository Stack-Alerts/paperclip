/**
 * Parser for the human-readable table emitted by
 * `scripts/merge_queue_status.py --quiet`.
 *
 * The script's output is line-oriented and uses Unicode glyphs + box
 * drawing for structure. We split on the obvious boundaries (the `  ─...─`
 * block separators and the `  ═...═` outer dividers) and run regexes
 * over each block. The parser is intentionally permissive — unknown lines
 * or shapes fall back to "unknown" rather than throwing, so a future
 * tweak to the script's format doesn't break the dashboard outright.
 */
import type {
  ApprovalRequest,
  BlockedChain,
  ChainNode,
  MergeBlock,
  MergeCheck,
  MergeStatus,
  MergeTotals,
} from "./constants.js";

const BLOCK_SEPARATOR = /^ {0,4}─{20,}\s*$/;
const OUTER_DIVIDER = /^ {0,4}═{20,}\s*$/;
const HEADER_LINE = /^  MERGE QUEUE STATUS\s+(.+?)\s*$/;
const SUMMARY_LINE = /In-review:\s*(\d+)\s+Open PRs:\s*(\d+)\s+Queued CI runs:\s*(\d+)\s+In-progress CI:\s*(\d+)/;
const TOTALS_LINE = /^  TOTALS\s+(.+)$/;
const BLOCK_HEADER = /^  #(\d+)\s+([0-9a-f-]{36})\s+\(in_review for (.+?)\)\s*$/;
const TITLE_LINE = /^ {6}(.+?)\s*$/;
const FIX_SHA_LINE = /^ {6}Fix-SHA\s+(.+?)\s*$/;
const PR_LINE = /^ {6}PR #\s+(None|\d+)\s+(\S+)?\s*(.*)$/;
const CI_LINE = /^ {6}CI\s+(\S+)\s+(.+?)\s*$/;
const CHECK_LINE = /^ {8}(✓|✗|⏳|\?|MISSING|PENDING|FAIL)\s+(\S.*?)(?:\s+\[(\w+)\])?\s*$/;

const PROGRESS_RE = /([0-9]+)\/([0-9]+)/;

function trimTrailing(value: string): string {
  // The script truncates titles to 72 chars with `…`. Trim trailing
  // whitespace but leave the ellipsis intact so the UI can render it
  // exactly as the script did.
  return value.replace(/\s+$/u, "");
}

function parseCheck(raw: string, name: string, detail: string | null): MergeCheck {
  const lower = raw.toLowerCase();
  if (lower === "passed" || raw === "✓") {
    return { state: "passed", name, detail };
  }
  if (lower === "failed" || lower === "missing" || raw === "✗" || raw === "MISSING") {
    return { state: lower === "failed" || raw === "✗" ? "failed" : "missing", name, detail };
  }
  if (lower === "pending" || raw === "⏳" || raw === "PENDING") {
    return { state: "pending", name, detail };
  }
  return { state: "unknown", name, detail };
}

function parseStatusLine(label: string): {
  status: MergeStatus;
  passed: number | null;
  total: number | null;
} {
  let status: MergeStatus = "unknown";
  let passed: number | null = null;
  let total: number | null = null;

  const progress = label.match(PROGRESS_RE);
  if (progress && progress[1] && progress[2]) {
    passed = Number.parseInt(progress[1], 10);
    total = Number.parseInt(progress[2], 10);
  }

  const upper = label.toUpperCase();
  if (upper.includes("ALL GREEN") || upper.includes("READY TO MERGE")) {
    status = "ready";
  } else if (upper.includes("FAILING")) {
    status = "failing";
  } else if (upper.includes("WAITING") || upper.includes("PENDING")) {
    status = "waiting";
  } else if (upper.includes("NO PR / SHA") || upper.includes("NO PR") || upper.includes("NO SHA")) {
    status = "no-pr";
  }
  return { status, passed, total };
}

function isInsideBlock(lines: string[], idx: number): boolean {
  // A block begins at a `  #N` line and ends at the next `──...───` line.
  for (let i = idx - 1; i >= 0; i -= 1) {
    const line = lines[i];
    if (!line) continue;
    if (BLOCK_HEADER.test(line)) return true;
    if (OUTER_DIVIDER.test(line) || BLOCK_SEPARATOR.test(line)) return false;
  }
  return false;
}

export interface ParseResult {
  blocks: MergeBlock[];
  totals: MergeTotals;
  /** Blocked-issue dependency chains (from the script's --json output). */
  blockedChains?: BlockedChain[];
  /** Pending board-approval requests (from the script's --json output). */
  approvalRequests?: ApprovalRequest[];
  /** Snapshot-level counters from the script. */
  blockedCount?: number;
  chainCount?: number;
  approvalCount?: number;
}

export function parseMergeQueueOutput(stdout: string): ParseResult {
  // First try to parse the whole stdout as JSON (the script's --json path
  // emits a single JSON document with no table). This unlocks the blocked-
  // chain + approval data that only the --json output carries.
  const jsonResult = tryParseJsonOutput(stdout);
  if (jsonResult) {
    return jsonResult;
  }

  const lines = stdout.split(/\r?\n/);
  const blocks: MergeBlock[] = [];
  const totals: MergeTotals = {
    inReview: 0,
    openPrs: 0,
    queuedRuns: 0,
    inProgressRuns: 0,
    ready: 0,
    waiting: 0,
    failing: 0,
    noPrOrSha: 0,
  };

  let headerTimestamp: string | null = null;
  let current: Partial<MergeBlock> | null = null;

  for (let i = 0; i < lines.length; i += 1) {
    const rawLine = lines[i] ?? "";
    const line = rawLine;

    // ─── header / footer lines ───────────────────────────────────────────
    const header = line.match(HEADER_LINE);
    if (header && header[1]) {
      headerTimestamp = header[1];
      continue;
    }
    const summary = line.match(SUMMARY_LINE);
    if (summary) {
      totals.inReview = Number.parseInt(summary[1] ?? "0", 10);
      totals.openPrs = Number.parseInt(summary[2] ?? "0", 10);
      totals.queuedRuns = Number.parseInt(summary[3] ?? "0", 10);
      totals.inProgressRuns = Number.parseInt(summary[4] ?? "0", 10);
      continue;
    }
    const totalsLine = line.match(TOTALS_LINE);
    if (totalsLine && totalsLine[1]) {
      // TOTALS  3 ready  4 waiting on CI  2 CI failing  1 no PR / SHA issue
      const ready = totalsLine[1].match(/(\d+)\s+ready/);
      const waiting = totalsLine[1].match(/(\d+)\s+waiting on CI/);
      const failing = totalsLine[1].match(/(\d+)\s+CI failing/);
      const noPr = totalsLine[1].match(/(\d+)\s+no PR/i);
      if (ready && ready[1]) totals.ready = Number.parseInt(ready[1], 10);
      if (waiting && waiting[1]) totals.waiting = Number.parseInt(waiting[1], 10);
      if (failing && failing[1]) totals.failing = Number.parseInt(failing[1], 10);
      if (noPr && noPr[1]) totals.noPrOrSha = Number.parseInt(noPr[1], 10);
      continue;
    }
    if (OUTER_DIVIDER.test(line) || BLOCK_SEPARATOR.test(line)) {
      // Close the current block on a separator.
      if (current && current.index !== undefined && current.issueUuid !== undefined) {
        blocks.push(finaliseBlock(current));
      }
      current = null;
      continue;
    }

    // ─── block content lines ────────────────────────────────────────────
    const blockHeader = line.match(BLOCK_HEADER);
    if (blockHeader && blockHeader[1] && blockHeader[2] && blockHeader[3]) {
      // Close any previous block (defensive — separators usually do this).
      if (current && current.index !== undefined && current.issueUuid !== undefined) {
        blocks.push(finaliseBlock(current));
      }
      const index = Number.parseInt(blockHeader[1], 10);
      const issueUuid = blockHeader[2];
      current = {
        index,
        issueUuid,
        inReviewFor: blockHeader[3],
        title: "",
        fixSha: null,
        fixShaMissing: false,
        prNumber: null,
        prMergeable: null,
        prTitle: null,
        status: "unknown",
        statusLabel: "",
        progressPassed: null,
        progressTotal: null,
        checks: [],
        diffKey: issueUuid,
      };
      continue;
    }

    if (!current) continue;

    const title = line.match(TITLE_LINE);
    if (title && title[1] && current.title === "") {
      current.title = trimTrailing(title[1]);
      continue;
    }

    const fixSha = line.match(FIX_SHA_LINE);
    if (fixSha && fixSha[1]) {
      const value = fixSha[1];
      if (value.startsWith("NOT FOUND")) {
        current.fixShaMissing = true;
        current.fixSha = null;
        current.status = "no-sha";
        current.statusLabel = value.replace(/^NOT FOUND\s*[—-]?\s*/u, "").trim() || "no fix-SHA";
      } else {
        current.fixSha = value.replace(/…$/u, "").trim();
      }
      continue;
    }

    const prLine = line.match(PR_LINE);
    if (prLine && prLine[1]) {
      const prToken = prLine[1];
      const mergeableToken = prLine[2] ?? "";
      const prTitle = trimTrailing(prLine[3] ?? "");
      if (prToken === "None") {
        current.prNumber = null;
        current.prMergeable = null;
        current.prTitle = prTitle;
        current.status = "no-pr";
        current.statusLabel = prTitle;
      } else {
        const num = Number.parseInt(prToken, 10);
        if (Number.isFinite(num)) {
          current.prNumber = num;
          current.prMergeable = mergeableToken === "" || mergeableToken === "None" ? null : mergeableToken;
          current.prTitle = prTitle;
        }
      }
      continue;
    }

    const ciLine = line.match(CI_LINE);
    if (ciLine && ciLine[1] && ciLine[2]) {
      const symbol = ciLine[1];
      const label = ciLine[2];
      const parsed = parseStatusLine(label);
      current.status = parsed.status;
      current.statusLabel = trimTrailing(label);
      current.progressPassed = parsed.passed;
      current.progressTotal = parsed.total;
      // Use the symbol for the status if it has a glyph.
      if (symbol === "✗") {
        current.status = "failing";
      } else if (symbol === "?") {
        current.status = "unknown";
      }
      continue;
    }

    const checkLine = line.match(CHECK_LINE);
    if (checkLine && checkLine[1] && checkLine[2]) {
      const raw = checkLine[1];
      const rest = checkLine[2];
      // Pull the leading name out of `rest`. Detail (in `[...]`) has been
      // captured separately by the regex group 3 when present.
      const detail = checkLine[3] ?? null;
      const checkName = rest.trim();
      current.checks?.push(parseCheck(raw, checkName, detail));
      continue;
    }

    // If we got here inside a block and the line is the trailing separator
    // we already closed the block above. Other unmatched lines inside a block
    // are ignored on purpose — the script's table has some whitespace-only
    // lines we don't want to treat as content.
    void isInsideBlock;
  }

  // Final flush.
  if (current && current.index !== undefined && current.issueUuid !== undefined) {
    blocks.push(finaliseBlock(current));
  }

  return { blocks, totals };
}

function finaliseBlock(partial: Partial<MergeBlock>): MergeBlock {
  const checks = (partial.checks ?? []) as MergeCheck[];
  return {
    index: partial.index ?? 0,
    issueUuid: partial.issueUuid ?? "",
    issueIdentifier: partial.issueIdentifier ?? null,
    title: partial.title ?? "",
    inReviewFor: partial.inReviewFor ?? "",
    fixSha: partial.fixSha ?? null,
    fixShaMissing: partial.fixShaMissing ?? false,
    prNumber: partial.prNumber ?? null,
    prMergeable: partial.prMergeable ?? null,
    prTitle: partial.prTitle ?? null,
    status: partial.status ?? "unknown",
    statusLabel: partial.statusLabel ?? "",
    progressPassed: partial.progressPassed ?? null,
    progressTotal: partial.progressTotal ?? null,
    checks,
    diffKey: partial.diffKey ?? partial.issueUuid ?? "",
  };
}

export interface BlockDiff {
  /** Issue UUID (stable across scans). */
  diffKey: string;
  /** What changed since the previous scan. */
  changes: BlockChange[];
  /** "added" / "removed" / "changed" / "unchanged". */
  kind: "added" | "removed" | "changed" | "unchanged";
}

export type BlockChange =
  | "status"
  | "pr-number"
  | "fix-sha"
  | "progress"
  | "checks"
  | "title";

/**
 * Compute a per-block diff between the current snapshot and the previous
 * snapshot. Used by the UI to flag what changed since the last scan.
 */
export function diffBlocks(
  previous: MergeBlock[] | null,
  current: MergeBlock[],
): BlockDiff[] {
  if (!previous) {
    return current.map((block) => ({
      diffKey: block.diffKey,
      changes: [],
      kind: "added",
    }));
  }
  const previousByKey = new Map<string, MergeBlock>();
  for (const block of previous) {
    previousByKey.set(block.diffKey, block);
  }
  const currentByKey = new Map<string, MergeBlock>();
  for (const block of current) {
    currentByKey.set(block.diffKey, block);
  }
  const result: BlockDiff[] = [];
  for (const block of current) {
    const prior = previousByKey.get(block.diffKey);
    if (!prior) {
      result.push({ diffKey: block.diffKey, changes: [], kind: "added" });
      continue;
    }
    const changes: BlockChange[] = [];
    if (prior.status !== block.status) changes.push("status");
    if (prior.prNumber !== block.prNumber) changes.push("pr-number");
    if (prior.fixSha !== block.fixSha || prior.fixShaMissing !== block.fixShaMissing) {
      changes.push("fix-sha");
    }
    if (
      prior.progressPassed !== block.progressPassed ||
      prior.progressTotal !== block.progressTotal
    ) {
      changes.push("progress");
    }
    if (JSON.stringify(prior.checks) !== JSON.stringify(block.checks)) {
      changes.push("checks");
    }
    if (prior.title !== block.title) changes.push("title");
    result.push({
      diffKey: block.diffKey,
      changes,
      kind: changes.length > 0 ? "changed" : "unchanged",
    });
  }
  for (const block of previous) {
    if (!currentByKey.has(block.diffKey)) {
      result.push({ diffKey: block.diffKey, changes: [], kind: "removed" });
    }
  }
  return result;
}

// ---------------------------------------------------------------------------
// JSON output parser
// ---------------------------------------------------------------------------

/**
 * Try to parse the script's `--json` output. The script writes a single
 * JSON document with `queue` (the in-review list, same shape as the table
 * parser's output) plus blocked-chain data + approval requests.
 *
 * Returns `null` when the stdout doesn't look like a JSON document (e.g.
 * the table output from `--quiet`). Caller falls back to the table parser.
 */
function tryParseJsonOutput(stdout: string): ParseResult | null {
  // The worker's clampOutput() prepends "[... truncated to last N characters ...]"
  // when the stdout exceeds maxOutputChars (default 200_000). The script's
  // --json output is a single-line JSON document, so any truncation happens at
  // the front of the line — which means our JSON.parse would see the
  // truncation marker instead of `{`. Strip the marker before parsing.
  let trimmed = stdout.trim();
  const truncationPrefix = "[... truncated to last";
  const truncationEnd = "characters ...]";
  if (trimmed.startsWith(truncationPrefix)) {
    const closeIdx = trimmed.indexOf(truncationEnd);
    if (closeIdx > 0) {
      trimmed = trimmed.slice(closeIdx + truncationEnd.length).trim();
    }
  }
  if (!trimmed.startsWith("{")) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(trimmed);
  } catch {
    return null;
  }
  if (!parsed || typeof parsed !== "object") return null;
  const obj = parsed as Record<string, unknown>;
  const queueRaw = obj["queue"];
  const chainsRaw = obj["blocked_chains"];
  const approvalsRaw = obj["approval_requests"];

  // We treat this as JSON only if we recognize the shape — must have
  // either `blocked_chains`, `approval_requests`, or `queue`. Otherwise
  // fall back to the table parser.
  if (!Array.isArray(queueRaw) && !Array.isArray(chainsRaw) && !Array.isArray(approvalsRaw)) {
    return null;
  }

  const blocks: MergeBlock[] = [];
  if (Array.isArray(queueRaw)) {
    let i = 1;
    for (const item of queueRaw) {
      if (!item || typeof item !== "object") {
        i += 1;
        continue;
      }
      const it = item as Record<string, unknown>;
      const issueId = typeof it["issue_id"] === "string" ? (it["issue_id"] as string) : "";
      if (!issueId) {
        i += 1;
        continue;
      }
      const checks = Array.isArray(it["checks"])
        ? (it["checks"] as Array<Record<string, unknown>>).map((c) => ({
            state: (c["state"] as MergeCheck["state"]) ?? "unknown",
            name: (c["name"] as string) ?? "",
            detail: (c["detail"] as string | null) ?? null,
          }))
        : [];
      const statusRaw = (it["pr_mergeable"] as string | null) ?? "";
      const passed = Number.parseInt((it["passed"] as string) ?? "0", 10) || 0;
      const total = Number.parseInt((it["total"] as string) ?? "0", 10) || 0;
      blocks.push({
        index: i++,
        issueUuid: issueId,
        issueIdentifier: (it["display_key"] as string | null) ?? null,
        title: (it["title"] as string) ?? "(no title)",
        inReviewFor: "",
        fixSha: (it["fix_sha"] as string | null) ?? null,
        fixShaMissing: !it["fix_sha"],
        prNumber: typeof it["pr_number"] === "number" ? (it["pr_number"] as number) : null,
        prMergeable: statusRaw || null,
        prTitle: (it["pr_title"] as string | null) ?? null,
        status: deriveStatus(it),
        statusLabel: "",
        progressPassed: Number.isFinite(passed) ? passed : null,
        progressTotal: Number.isFinite(total) ? total : null,
        checks,
        diffKey: issueId,
      });
    }
  }

  const blockedChains: BlockedChain[] = [];
  if (Array.isArray(chainsRaw)) {
    for (const c of chainsRaw) {
      if (!c || typeof c !== "object") continue;
      const ch = c as Record<string, unknown>;
      const nodes: Record<string, ChainNode> = {};
      const nodesRaw = ch["nodes"];
      if (nodesRaw && typeof nodesRaw === "object") {
        for (const [uuid, raw] of Object.entries(nodesRaw as Record<string, unknown>)) {
          if (!raw || typeof raw !== "object") continue;
          const n = raw as Record<string, unknown>;
          nodes[uuid] = {
            uuid: (n["uuid"] as string) ?? uuid,
            identifier: (n["identifier"] as string | null) ?? null,
            title: (n["title"] as string) ?? "(no title)",
            status: (n["status"] as string) ?? "blocked",
            priority: (n["priority"] as string | null) ?? null,
            labels: Array.isArray(n["labels"]) ? (n["labels"] as string[]) : [],
            depth: typeof n["depth"] === "number" ? (n["depth"] as number) : 0,
            isLeaf: Boolean(n["is_leaf"]),
            isRoot: Boolean(n["is_root"]),
            blockedBy: Array.isArray(n["blocked_by"]) ? (n["blocked_by"] as string[]) : [],
            blocks: Array.isArray(n["blocks"]) ? (n["blocks"] as string[]) : [],
            downstreamCount: typeof n["downstream_count"] === "number" ? (n["downstream_count"] as number) : 0,
          };
        }
      }
      blockedChains.push({
        id: (ch["id"] as string) ?? "",
        rootIds: Array.isArray(ch["root_ids"]) ? (ch["root_ids"] as string[]) : [],
        leafIds: Array.isArray(ch["leaf_ids"]) ? (ch["leaf_ids"] as string[]) : [],
        nodeCount: typeof ch["node_count"] === "number" ? (ch["node_count"] as number) : 0,
        nodes,
      });
    }
  }

  const approvalRequests: ApprovalRequest[] = [];
  if (Array.isArray(approvalsRaw)) {
    for (const a of approvalsRaw) {
      if (!a || typeof a !== "object") continue;
      const ar = a as Record<string, unknown>;
      const chainNodeRaw = ar["chain_node"];
      const chainNode: ChainNode | null =
        chainNodeRaw && typeof chainNodeRaw === "object"
          ? {
              uuid: ((chainNodeRaw as Record<string, unknown>)["uuid"] as string) ?? "",
              identifier: ((chainNodeRaw as Record<string, unknown>)["identifier"] as string | null) ?? null,
              title: ((chainNodeRaw as Record<string, unknown>)["title"] as string) ?? "(no title)",
              status: ((chainNodeRaw as Record<string, unknown>)["status"] as string) ?? "blocked",
              priority: ((chainNodeRaw as Record<string, unknown>)["priority"] as string | null) ?? null,
              labels: [],
              depth: ((chainNodeRaw as Record<string, unknown>)["depth"] as number) ?? 0,
              isLeaf: Boolean((chainNodeRaw as Record<string, unknown>)["is_leaf"]),
              isRoot: Boolean((chainNodeRaw as Record<string, unknown>)["is_root"]),
              blockedBy: [],
              blocks: [],
              downstreamCount:
                typeof (chainNodeRaw as Record<string, unknown>)["downstream_count"] === "number"
                  ? ((chainNodeRaw as Record<string, unknown>)["downstream_count"] as number)
                  : 0,
            }
          : null;
      approvalRequests.push({
        issueId: (ar["issue_id"] as string) ?? "",
        issueIdentifier: (ar["issue_identifier"] as string | null) ?? null,
        issueTitle: (ar["issue_title"] as string) ?? "(no title)",
        issueStatus: (ar["issue_status"] as string) ?? "blocked",
        issuePriority: (ar["issue_priority"] as string | null) ?? null,
        interactionId: (ar["interaction_id"] as string) ?? "",
        kind: (ar["kind"] as string) ?? "request_confirmation",
        title: (ar["title"] as string) ?? "",
        body: (ar["body"] as string) ?? "",
        createdAt: (ar["created_at"] as string | null) ?? null,
        createdBy: (ar["created_by"] as string | null) ?? null,
        idempotencyKey: (ar["idempotency_key"] as string | null) ?? null,
        chainId: (ar["chain_id"] as string | null) ?? null,
        chainNode,
        unblocksCount: typeof ar["unblocks_count"] === "number" ? (ar["unblocks_count"] as number) : 0,
      });
    }
  }

  const totals: MergeTotals = {
    inReview: typeof obj["in_review_count"] === "number" ? (obj["in_review_count"] as number) : blocks.length,
    openPrs: typeof obj["open_pr_count"] === "number" ? (obj["open_pr_count"] as number) : 0,
    queuedRuns: typeof obj["queued_runs"] === "number" ? (obj["queued_runs"] as number) : 0,
    inProgressRuns: typeof obj["in_progress_runs"] === "number" ? (obj["in_progress_runs"] as number) : 0,
    ready: 0,
    waiting: 0,
    failing: 0,
    noPrOrSha: 0,
  };

  return {
    blocks,
    totals,
    blockedChains,
    approvalRequests,
    blockedCount: typeof obj["blocked_count"] === "number" ? (obj["blocked_count"] as number) : 0,
    chainCount: typeof obj["chain_count"] === "number" ? (obj["chain_count"] as number) : 0,
    approvalCount: typeof obj["approval_count"] === "number" ? (obj["approval_count"] as number) : 0,
  };
}

/**
 * Status heuristic matching the table parser's behavior. Without the
 * exact table lines we can't replicate every nuance; this picks the
 * safest bucket so the UI shows something reasonable for parsed-JSON
 * queue items.
 */
function deriveStatus(item: Record<string, unknown>): MergeStatus {
  if (!item["pr_number"]) return "no-pr";
  const passed = Number.parseInt((item["passed"] as string) ?? "0", 10) || 0;
  const total = Number.parseInt((item["total"] as string) ?? "0", 10) || 0;
  const failed = Number.parseInt((item["failed"] as string) ?? "0", 10) || 0;
  const mergeable = (item["pr_mergeable"] as string | null) ?? "";
  const ciAllGreen = total > 0 && passed === total && failed === 0;
  // `mergeable` is GitHub's `mergeable_state`. Only "clean" and "blocked"
  // count as functionally ready from the agent's POV (the latter means
  // "branch protection / required review", which is the merge-dispatch
  // routine's job, not the agent's). "dirty" / "behind" / "draft" /
  // "unstable" mean the agent still has work to do, so don't classify
  // those as ready even when CI is green.
  if (ciAllGreen) {
    if (mergeable === "" || mergeable === "clean" || mergeable === "blocked") {
      return "ready";
    }
    return "waiting";
  }
  if (failed > 0) return "failing";
  if (total > 0 && passed < total) return "waiting";
  return "unknown";
}
