/**
 * Stable identifiers, defaults, and shared constants for the Git Merges plugin.
 */

export const PLUGIN_ID = "paperclip.git-merges";
export const PLUGIN_VERSION = "0.1.0";
export const PAGE_ROUTE = "git-merges";

export const SLOT_IDS = {
  page: "git-merges-page",
  presetsSidebar: "git-merges-presets-sidebar",
  settingsPage: "git-merges-settings-page",
} as const;

export const EXPORT_NAMES = {
  page: "GitMergesPage",
  presetsSidebar: "GitMergesPresetsSidebar",
  settingsPage: "GitMergesSettingsPage",
} as const;

export const DATA_KEYS = {
  config: "git-merges-config",
  snapshot: "git-merges-snapshot",
  status: "git-merges-status",
  issueMap: "git-merges-issue-map",
} as const;

export const ACTION_KEYS = {
  runScan: "run-scan",
  clearOutput: "clear-output",
  saveConfig: "save-config",
} as const;

export const STREAM_CHANNELS = {
  output: "output",
} as const;

export const DEFAULT_CONFIG = {
  // The python interpreter. Defaults to the BTC repo venv if present,
  // otherwise falls back to system `python3`.
  pythonPath:
    "/home/sirrus/projects/BTC-Trade-Engine-PaperClip/venv/bin/python3",
  // Working directory for the script (where it picks up .env).
  // We default to a dedicated worktree that tracks
  // origin/fix/BTCAAAAA-38557-merge-ready-watcher because that branch
  // actually contains scripts/merge_queue_status.py — the script was
  // reverted from the local main branch this morning.
  repoPath: "/home/sirrus/btc-test-worktrees/fix-38557",
  // Path to the script relative to repoPath.
  scriptPath: "scripts/merge_queue_status.py",
  // Auto-refresh master toggle.
  autoRefreshEnabled: true,
  // Interval in seconds. 300 = every 5 min.
  autoRefreshIntervalSeconds: 300,
  // Time block. Script only runs inside this window (inclusive on both ends).
  timeBlockEnabled: true,
  timeBlockStartHour: 8,
  timeBlockEndHour: 16,
  // Show the JSON output alongside the table.
  showJson: false,
  // Cap on how many characters to keep per scan in the output buffer.
  // The script's --json output (with chains + approvals) is typically
  // ~1–2 MB on a busy company; the 200 KB default was tuned for the
  // human-readable table. Raise the default so the full JSON survives.
  maxOutputChars: 5_000_000,
  // Soft timeout for a single scan.
  scanTimeoutSeconds: 120,
} as const;

export type GitMergesConfig = {
  pythonPath: string;
  repoPath: string;
  scriptPath: string;
  autoRefreshEnabled: boolean;
  autoRefreshIntervalSeconds: number;
  timeBlockEnabled: boolean;
  timeBlockStartHour: number;
  timeBlockEndHour: number;
  showJson: boolean;
  maxOutputChars: number;
  scanTimeoutSeconds: number;
};

export type ScanRecord = {
  /** ISO timestamp the scan started. */
  startedAt: string;
  /** ISO timestamp the scan finished. */
  finishedAt: string | null;
  /** Exit code from the python process, or null if still running. */
  exitCode: number | null;
  /** Captured stdout (already stripped of ANSI for display). */
  stdout: string;
  /** Captured stderr. */
  stderr: string;
  /** True if the scan was skipped (e.g. outside the time block). */
  skipped?: boolean;
  /** Reason string if skipped. */
  skipReason?: string;
  /** Parsed structured blocks for this scan. Absent for skipped scans. */
  blocks?: MergeBlock[];
  /** Totals parsed from the script summary + TOTALS line. */
  totals?: MergeTotals;
  /** Blocked-issue dependency chains (from the script's JSON output). */
  blockedChains?: BlockedChain[];
  /** Pending board-approval requests (from the script's JSON output). */
  approvalRequests?: ApprovalRequest[];
  /** Snapshot-level counters from the script. */
  blockedCount?: number;
  chainCount?: number;
  approvalCount?: number;
};

export type ScanStatus = {
  /** True if a scan is currently running. */
  running: boolean;
  /** ISO timestamp of the most recent completed scan. */
  lastRunAt: string | null;
  /** ISO timestamp of the most recent attempted scan (incl. skipped). */
  lastAttemptAt: string | null;
  /** Last exit code. */
  lastExitCode: number | null;
  /** Whether the most recent scan was skipped. */
  lastSkipped: boolean;
};

export type MergeQueueSnapshot = {
  config: GitMergesConfig;
  status: ScanStatus;
  /** Last completed scan. */
  latest: ScanRecord | null;
  /** Up to N most recent completed scans (newest first). */
  history: ScanRecord[];
  /**
   * Parsed structured blocks from the latest scan, in script-table order.
   * Each block corresponds to one in-review issue / PR. The UI renders
   * these as cards with status, progress bar, and links.
   */
  blocks: MergeBlock[];
  /**
   * The parsed blocks from the previous completed scan (the one immediately
   * before `latest`). The UI uses this to compute the diff-vs-last view.
   * `null` when there is no prior scan or when the previous scan was cleared.
   */
  previousBlocks: MergeBlock[] | null;
  /**
   * `startedAt` of the previous scan — used to compute per-block elapsed
   * time between the two scans. `null` when there's no previous scan.
   */
  previousStartedAt: string | null;
  /** Snapshot-level counters derived from the latest scan. */
  totals: MergeTotals;
  /** Wall-clock time the latest scan started. */
  latestStartedAt: string | null;
  /** Wall-clock time the latest scan finished. */
  latestFinishedAt: string | null;
  /**
   * Blocked-issue dependency chains. Built from the Paperclip DB's
   * `issue_relations` table (graph edges) combined with REST API metadata
   * (node labels). Each chain is a connected component in the
   * directed `blocks` graph.
   */
  blockedChains: BlockedChain[];
  /**
   * Pending board-approval requests (`request_confirmation` interactions
   * with status='pending'). Sorted by unblocks_count DESC then created_at
   * DESC, so the most impactful approval floats to the top.
   */
  approvalRequests: ApprovalRequest[];
  /** Quick lookup table uuid → chain_node for approval cross-references. */
  approvalChainLookup: Record<string, { chainId: string; node: ChainNode }>;
  /** Snapshot-level counters for the new tabs. */
  blockedCount: number;
  chainCount: number;
  approvalCount: number;
};

/**
 * Status of a single in-review issue / PR as parsed from the script's
 * human-readable table.
 */
export type MergeStatus =
  | "ready"
  | "waiting"
  | "failing"
  | "no-pr"
  | "no-sha"
  | "unknown";

/**
 * Parsed structured representation of one row in the merge queue.
 * Matches the format produced by `scripts/merge_queue_status.py --quiet`.
 */
export type MergeBlock = {
  /** 1-based position in the merge queue. */
  index: number;
  /** Paperclip issue UUID (from the script's #N line). */
  issueUuid: string;
  /**
   * Paperclip issue identifier (e.g. `BTCAAAAA-38557`). Resolved via the
   * Paperclip REST API after parsing the raw output; falls back to the
   * UUID prefix when the lookup fails or the API key isn't available.
   */
  issueIdentifier: string | null;
  /** Issue title. */
  title: string;
  /** "in review for Xm" relative age string from the script. */
  inReviewFor: string;
  /** Full fix-SHA if recorded on the issue's closure comment. */
  fixSha: string | null;
  /** `true` when the fix-SHA line was `NOT FOUND`. */
  fixShaMissing: boolean;
  /** Pull request number if the fix-SHA matched an open PR. */
  prNumber: number | null;
  /** GitHub mergeable state: `clean` / `dirty` / `blocked` / `null` (unknown / not found). */
  prMergeable: string | null;
  /** PR title (truncated to ~48 chars by the script). */
  prTitle: string | null;
  /** High-level CI bucket. */
  status: MergeStatus;
  /** Human-readable status string from the script. */
  statusLabel: string;
  /** Passed / total counts parsed from the status line, when present. */
  progressPassed: number | null;
  progressTotal: number | null;
  /** Per-required-check list (order preserved). */
  checks: MergeCheck[];
  /** Stamp for compare diffs. Stable across runs for the same issue UUID. */
  diffKey: string;
};

export type MergeCheck = {
  /** Lowercase script status: passed / failed / pending / missing / unknown. */
  state: "passed" | "failed" | "pending" | "missing" | "unknown";
  /** Check name (e.g. "pytest + coverage gate"). */
  name: string;
  /** Optional detail from the script (e.g. "[queued]" / "[in_progress]"). */
  detail: string | null;
};

export type MergeTotals = {
  inReview: number;
  openPrs: number;
  queuedRuns: number;
  inProgressRuns: number;
  ready: number;
  waiting: number;
  failing: number;
  noPrOrSha: number;
};

// ---------------------------------------------------------------------------
// Blocked-chain + awaiting-approval types (added for the new tabs)
// ---------------------------------------------------------------------------

export type ChainNode = {
  uuid: string;
  identifier: string | null;
  title: string;
  status: string;
  priority: string | null;
  labels: string[];
  /**
   * Distance from the nearest leaf in this chain. 0 = leaf (nothing blocks
   * it; resolving this node unblocks its downstream). Higher = deeper in
   * the dependency tree.
   */
  depth: number;
  isLeaf: boolean;
  isRoot: boolean;
  /** Direct blockers (uuids) inside the same chain. */
  blockedBy: string[];
  /** Direct downstream issues (uuids) inside the same chain. */
  blocks: string[];
  /** Total transitive downstream issues this node unblocks if resolved. */
  downstreamCount: number;
};

export type BlockedChain = {
  id: string;
  /** Chain heads: issues that are blocked by others but themselves block nothing in this chain. */
  rootIds: string[];
  /** Actionable leaves: issues that nothing in this chain blocks (resolving them unblocks downstream). */
  leafIds: string[];
  nodeCount: number;
  nodes: Record<string, ChainNode>;
};

export type ApprovalRequest = {
  issueId: string;
  issueIdentifier: string | null;
  issueTitle: string;
  issueStatus: string;
  issuePriority: string | null;
  interactionId: string;
  kind: string;
  title: string;
  body: string;
  createdAt: string | null;
  createdBy: string | null;
  idempotencyKey: string | null;
  /**
   * Chain this issue belongs to (when the issue is part of a dependency
   * chain). null if the issue stands alone.
   */
  chainId: string | null;
  /** The matching chain node, if any. */
  chainNode: ChainNode | null;
  /**
   * How many issues would unblock if this approval is granted. 0 when
   * the issue isn't part of a chain or the chain has no downstream issues.
   */
  unblocksCount: number;
};
