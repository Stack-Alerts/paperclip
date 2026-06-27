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
}

export function parseMergeQueueOutput(stdout: string): ParseResult {
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
