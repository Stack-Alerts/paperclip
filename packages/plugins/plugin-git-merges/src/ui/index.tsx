import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  useHostContext,
  useHostNavigation,
  usePluginAction,
  usePluginData,
  usePluginToast,
  type PluginDataResult,
  type PluginPageProps,
  type PluginSettingsPageProps,
  type PluginSidebarProps,
} from "@paperclipai/plugin-sdk/ui";
import {
  ACTION_KEYS,
  DATA_KEYS,
  DEFAULT_CONFIG,
  PAGE_ROUTE,
  PLUGIN_ID,
  type ApprovalRequest,
  type BlockedChain,
  type ChainNode,
  type GitMergesConfig,
  type MergeBlock,
  type MergeCheck,
  type MergeQueueSnapshot,
  type MergeStatus,
  type ScanRecord,
} from "../constants.js";
import { diffBlocks } from "../parser.js";

// ---------------------------------------------------------------------------
// Style helpers (inline so the plugin UI bundle has no host CSS coupling)
// ---------------------------------------------------------------------------

const cardStyle: CSSProperties = {
  border: "1px solid var(--border)",
  borderRadius: "12px",
  padding: "14px",
  background: "color-mix(in srgb, var(--card, transparent) 80%, transparent)",
  display: "grid",
  gap: "10px",
};

const subtleCardStyle: CSSProperties = {
  border: "1px solid color-mix(in srgb, var(--border) 75%, transparent)",
  borderRadius: "10px",
  padding: "12px",
  display: "grid",
  gap: "8px",
};

const rowStyle: CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  alignItems: "center",
  gap: "8px",
};

const sectionHeaderStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: "8px",
};

const buttonStyle: CSSProperties = {
  appearance: "none",
  border: "1px solid var(--border)",
  borderRadius: "999px",
  background: "transparent",
  color: "inherit",
  padding: "6px 12px",
  fontSize: "12px",
  cursor: "pointer",
};

const primaryButtonStyle: CSSProperties = {
  ...buttonStyle,
  background: "var(--foreground)",
  color: "var(--background)",
  borderColor: "var(--foreground)",
};

const destructiveButtonStyle: CSSProperties = {
  ...buttonStyle,
  background: "color-mix(in srgb, #dc2626 18%, transparent)",
  borderColor: "color-mix(in srgb, #dc2626 60%, var(--border))",
  color: "#fca5a5",
};

const disabledButtonStyle: CSSProperties = {
  ...buttonStyle,
  opacity: 0.55,
  cursor: "not-allowed",
};

const inputStyle: CSSProperties = {
  width: "100%",
  border: "1px solid var(--border)",
  borderRadius: "8px",
  padding: "8px 10px",
  background: "transparent",
  color: "inherit",
  fontSize: "12px",
  fontFamily: "inherit",
};

const outputStyle: CSSProperties = {
  margin: 0,
  padding: "12px",
  borderRadius: "8px",
  border: "1px solid var(--border)",
  background:
    "color-mix(in srgb, var(--muted, #888) 12%, transparent)",
  overflow: "auto",
  fontSize: "11px",
  lineHeight: 1.45,
  fontFamily:
    "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
  whiteSpace: "pre",
  minHeight: "320px",
  maxHeight: "60vh",
};

const stderrBlockStyle: CSSProperties = {
  margin: 0,
  padding: "10px 12px",
  borderRadius: "8px",
  border: "1px solid color-mix(in srgb, #dc2626 45%, var(--border))",
  background: "color-mix(in srgb, #dc2626 12%, transparent)",
  color: "#fecaca",
  overflow: "auto",
  fontSize: "11px",
  lineHeight: 1.45,
  fontFamily:
    "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
  whiteSpace: "pre-wrap",
  maxHeight: "180px",
};

const mutedTextStyle: CSSProperties = {
  fontSize: "12px",
  opacity: 0.72,
  lineHeight: 1.45,
};

const pillStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: "6px",
  padding: "2px 10px",
  borderRadius: "999px",
  border: "1px solid var(--border)",
  fontSize: "11px",
  background: "color-mix(in srgb, var(--muted, #888) 16%, transparent)",
};

const pillOkStyle: CSSProperties = {
  ...pillStyle,
  borderColor: "color-mix(in srgb, #16a34a 60%, var(--border))",
  background: "color-mix(in srgb, #16a34a 14%, transparent)",
  color: "#86efac",
};

const pillWarnStyle: CSSProperties = {
  ...pillStyle,
  borderColor: "color-mix(in srgb, #d97706 60%, var(--border))",
  background: "color-mix(in srgb, #d97706 14%, transparent)",
  color: "#fcd34d",
};

const pillErrStyle: CSSProperties = {
  ...pillStyle,
  borderColor: "color-mix(in srgb, #dc2626 60%, var(--border))",
  background: "color-mix(in srgb, #dc2626 14%, transparent)",
  color: "#fca5a5",
};

/**
 * BTCAAAAA-39051: stuck pill — distinct from the failing-CI pill so
 * operators can tell "CI is red and we're waiting on it" apart from
 * "this PR has been in queue for >24h with no progress at all".
 */
const stuckPillStyle: CSSProperties = {
  ...pillStyle,
  borderColor: "color-mix(in srgb, #d97706 70%, var(--border))",
  background: "color-mix(in srgb, #d97706 18%, transparent)",
  color: "#fcd34d",
  fontWeight: 600,
};

const codeInlineStyle: CSSProperties = {
  fontFamily:
    "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
  fontSize: "11px",
  padding: "1px 4px",
  borderRadius: "4px",
  border: "1px solid var(--border)",
  background: "color-mix(in srgb, var(--muted, #888) 14%, transparent)",
};

// Inline link style — same color as surrounding text but underlined and
// cursor:pointer so the user can tell at a glance that the identifier
// is clickable. Hover deepens the color. Used for the issue identifier
// and the GitHub PR link inside MergeBlockCard.
const inlineLinkStyle: CSSProperties = {
  color: "inherit",
  textDecoration: "underline",
  textDecorationStyle: "dotted",
  textUnderlineOffset: "3px",
  textDecorationThickness: "1px",
  cursor: "pointer",
  fontWeight: 500,
};

// "Visited" pill — shown next to the issue/PR link after the user has
// clicked it since the last scan. Persisted in localStorage so the
// marker survives page reloads but resets automatically when a new
// scan's `startedAt` arrives (because the storage key changes).
const visitedPillStyle: CSSProperties = {
  fontSize: "10px",
  padding: "1px 7px",
  borderRadius: "999px",
  border: "1px solid color-mix(in srgb, #16a34a 60%, var(--border))",
  background: "color-mix(in srgb, #16a34a 14%, transparent)",
  color: "#86efac",
  display: "inline-flex",
  alignItems: "center",
  gap: "4px",
  cursor: "help",
  whiteSpace: "nowrap",
};

// localStorage key used to persist which blocks the user has clicked
// into since a given scan started. The full value is a JSON object
// keyed by scan `startedAt` ISO string; values are arrays of diffKey.
const VISITED_STORAGE_KEY = "paperclip.git-merges.visited-blocks";

/**
 * BTCAAAAA-39051: hard-coded default stuck threshold (in hours). Mirrors
 * DEFAULT_CONFIG.stuckThresholdHours in the worker; the tooltip on the
 * STUCK pill in the card shows this value. Operators tune it from the
 * settings page.
 */
const STUCK_THRESHOLD_HOURS = 24;

type VisitedMap = Record<string, string[]>;

function readVisitedMap(): VisitedMap {
  if (typeof localStorage === "undefined") return {};
  try {
    const raw = localStorage.getItem(VISITED_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return {};
    const out: VisitedMap = {};
    for (const [k, v] of Object.entries(parsed)) {
      if (typeof k !== "string") continue;
      if (Array.isArray(v) && v.every((x) => typeof x === "string")) {
        out[k] = v.slice();
      }
    }
    return out;
  } catch {
    return {};
  }
}

function writeVisitedMap(map: VisitedMap): void {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.setItem(VISITED_STORAGE_KEY, JSON.stringify(map));
  } catch {
    // localStorage may be full or unavailable (private mode, etc.) —
    // silently ignore so the marker becomes a no-op rather than
    // breaking the rest of the UI.
  }
}

/**
 * Returns a `Set` of diffKeys the user has clicked into during the
 * current scan, plus a `markVisited(diffKey)` callback that persists
 * the click. The set resets automatically when the host reports a
 * fresh `latestStartedAt`, because the storage key is the scan
 * timestamp itself.
 */
function useVisitedBlocks(currentScanStartedAt: string | null): {
  visited: Set<string>;
  markVisited: (diffKey: string) => void;
  clearVisited: () => void;
} {
  const [visited, setVisited] = useState<Set<string>>(() => {
    if (!currentScanStartedAt) return new Set();
    const map = readVisitedMap();
    return new Set(map[currentScanStartedAt] ?? []);
  });

  // When the scan changes (or first arrives), reload the set from
  // localStorage for the new key. This handles both the "no snapshot
  // yet → snapshot arrives" and "scan A → scan B" transitions.
  useEffect(() => {
    if (!currentScanStartedAt) {
      setVisited(new Set());
      return;
    }
    const map = readVisitedMap();
    setVisited(new Set(map[currentScanStartedAt] ?? []));
  }, [currentScanStartedAt]);

  const markVisited = useCallback(
    (diffKey: string) => {
      if (!currentScanStartedAt) return;
      setVisited((prev) => {
        if (prev.has(diffKey)) return prev;
        const next = new Set(prev);
        next.add(diffKey);
        const map = readVisitedMap();
        const arr = map[currentScanStartedAt] ?? [];
        if (!arr.includes(diffKey)) {
          map[currentScanStartedAt] = [...arr, diffKey];
          // Prune anything older than the current scan so the storage
          // doesn't grow unboundedly across many scans.
          for (const k of Object.keys(map)) {
            if (k !== currentScanStartedAt) delete map[k];
          }
          writeVisitedMap(map);
        }
        return next;
      });
    },
    [currentScanStartedAt],
  );

  const clearVisited = useCallback(() => {
    if (!currentScanStartedAt) return;
    const map = readVisitedMap();
    delete map[currentScanStartedAt];
    writeVisitedMap(map);
    setVisited(new Set());
  }, [currentScanStartedAt]);

  return { visited, markVisited, clearVisited };
}

const fieldLabelStyle: CSSProperties = {
  display: "grid",
  gap: "6px",
  flex: "1 1 200px",
  minWidth: "200px",
};

const progressBarTrackStyle: CSSProperties = {
  position: "relative",
  height: "6px",
  borderRadius: "999px",
  background: "color-mix(in srgb, var(--muted, #888) 22%, transparent)",
  overflow: "hidden",
};

const progressBarFillStyle: CSSProperties = {
  position: "absolute",
  inset: 0,
  width: "40%",
  background:
    "linear-gradient(90deg, transparent 0%, color-mix(in srgb, var(--foreground) 80%, transparent) 50%, transparent 100%)",
  animation: "paperclip-git-merges-indeterminate 1.2s linear infinite",
};

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function coerceConfig(value: unknown): GitMergesConfig {
  const base: GitMergesConfig = { ...DEFAULT_CONFIG };
  if (!value || typeof value !== "object") return base;
  const v = value as Record<string, unknown>;
  if (typeof v.pythonPath === "string") base.pythonPath = v.pythonPath;
  if (typeof v.repoPath === "string") base.repoPath = v.repoPath;
  if (typeof v.scriptPath === "string") base.scriptPath = v.scriptPath;
  if (typeof v.autoRefreshEnabled === "boolean")
    base.autoRefreshEnabled = v.autoRefreshEnabled;
  if (typeof v.autoRefreshIntervalSeconds === "number" && Number.isFinite(v.autoRefreshIntervalSeconds))
    base.autoRefreshIntervalSeconds = v.autoRefreshIntervalSeconds;
  if (typeof v.timeBlockEnabled === "boolean")
    base.timeBlockEnabled = v.timeBlockEnabled;
  if (typeof v.timeBlockStartHour === "number" && Number.isFinite(v.timeBlockStartHour))
    base.timeBlockStartHour = v.timeBlockStartHour;
  if (typeof v.timeBlockEndHour === "number" && Number.isFinite(v.timeBlockEndHour))
    base.timeBlockEndHour = v.timeBlockEndHour;
  if (typeof v.showJson === "boolean") base.showJson = v.showJson;
  if (typeof v.maxOutputChars === "number" && Number.isFinite(v.maxOutputChars))
    base.maxOutputChars = v.maxOutputChars;
  if (typeof v.scanTimeoutSeconds === "number" && Number.isFinite(v.scanTimeoutSeconds))
    base.scanTimeoutSeconds = v.scanTimeoutSeconds;
  return base;
}

function formatDuration(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) return "?";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return `${minutes}m ${rest}s`;
}

function formatRelative(iso: string | null): string {
  if (!iso) return "never";
  const then = new Date(iso).getTime();
  const now = Date.now();
  const diff = now - then;
  if (diff < 0) return "in the future";
  if (diff < 1000) return "just now";
  if (diff < 60_000) return `${Math.floor(diff / 1000)}s ago`;
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return new Date(iso).toLocaleString();
}

function formatLocalHour(hour: number): string {
  const value = ((hour % 24) + 24) % 24;
  const suffix = value >= 12 ? "pm" : "am";
  const twelve = value % 12 === 0 ? 12 : value % 12;
  return `${twelve}${suffix}`;
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function isInsideTimeBlock(now: Date, startHour: number, endHour: number): boolean {
  if (startHour === endHour) return false;
  const hour = now.getHours();
  if (startHour < endHour) {
    return hour >= startHour && hour < endHour;
  }
  return hour >= startHour || hour < endHour;
}

function useNow(intervalMs: number): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), intervalMs);
    return () => window.clearInterval(id);
  }, [intervalMs]);
  return now;
}

function StatusPill({
  running,
  lastExitCode,
}: {
  running: boolean;
  lastExitCode: number | null;
}) {
  if (running) return <span style={pillWarnStyle}>scanning…</span>;
  if (lastExitCode === null)
    return <span style={pillStyle}>no scans yet</span>;
  if (lastExitCode === 0) return <span style={pillOkStyle}>last run OK</span>;
  return (
    <span style={pillErrStyle}>last run failed (exit {lastExitCode})</span>
  );
}

function HistoryRow({ scan }: { scan: ScanRecord }) {
  const finishedAt = scan.finishedAt ?? scan.startedAt;
  const duration = formatDuration(
    new Date(finishedAt).getTime() - new Date(scan.startedAt).getTime(),
  );
  const status =
    scan.exitCode === 0 ? (
      <span style={pillOkStyle}>ok</span>
    ) : scan.exitCode === null ? (
      <span style={pillWarnStyle}>no exit</span>
    ) : (
      <span style={pillErrStyle}>exit {scan.exitCode}</span>
    );
  return (
    <div
      style={{
        ...rowStyle,
        justifyContent: "space-between",
        border: "1px solid var(--border)",
        borderRadius: "8px",
        padding: "8px 10px",
        fontSize: "12px",
        background: "color-mix(in srgb, var(--card, transparent) 50%, transparent)",
      }}
    >
      <div style={{ display: "grid", gap: "2px" }}>
        <span>{formatTimestamp(scan.startedAt)}</span>
        <span style={{ ...mutedTextStyle, fontSize: "11px" }}>
          duration {duration} ·{" "}
          {scan.stdout.length} chars stdout
          {scan.stderr ? ` · ${scan.stderr.length} chars stderr` : ""}
        </span>
      </div>
      {status}
    </div>
  );
}

function TimeBlockChip({
  label,
  active = false,
  onClick,
}: {
  label: string;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      style={active ? primaryButtonStyle : buttonStyle}
      onClick={onClick}
    >
      {label}
    </button>
  );
}

function PluginMetaFooter({ pluginId }: { pluginId: string }) {
  return (
    <footer style={{ ...mutedTextStyle, paddingTop: "8px" }}>
      plugin <code style={codeInlineStyle}>{pluginId}</code>
    </footer>
  );
}

// ---------------------------------------------------------------------------
// Copy-to-clipboard button (uses navigator.clipboard.writeText).
// Falls back to a textarea+execCommand approach when the async clipboard
// API is unavailable (e.g. insecure context, older browsers).
// ---------------------------------------------------------------------------

async function copyTextToClipboard(value: string): Promise<boolean> {
  if (
    typeof navigator !== "undefined" &&
    navigator.clipboard &&
    typeof navigator.clipboard.writeText === "function"
  ) {
    try {
      await navigator.clipboard.writeText(value);
      return true;
    } catch {
      // fall through
    }
  }
  try {
    const textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    textarea.style.pointerEvents = "none";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(textarea);
    return ok;
  } catch {
    return false;
  }
}

/**
 * Refresh button with a self-healing "refreshing" state.
 *
 * Why this exists: the host's `usePluginData` returns a `loading` flag that
 * becomes true at the start of every fetch and false on success/error. If
 * the fetch hangs (server timeout, dropped connection, bridge stuck), the
 * flag can stay true indefinitely — the button stays "Refreshing…" forever.
 *
 * To guarantee the button can always recover, we keep our own
 * `refreshing` state with a hard 8-second timeout. We also trust the host's
 * `loading` flag when it resolves correctly.
 */
function RefreshButton({
  snapshotQuery,
}: {
  snapshotQuery: PluginDataResult<unknown>;
}) {
  const [refreshing, setRefreshing] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // If the host says loading went false, drop our local flag too.
  useEffect(() => {
    if (!snapshotQuery.loading && refreshing) {
      setRefreshing(false);
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    }
  }, [snapshotQuery.loading, refreshing]);

  // Cleanup on unmount.
  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    },
    [],
  );

  async function handleClick() {
    if (refreshing || snapshotQuery.loading) return;
    setRefreshing(true);
    // Hard timeout — if the refresh takes longer than 8s, reset the
    // button so the user isn't stuck looking at "Refreshing…".
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setRefreshing(false);
      timerRef.current = null;
    }, 8_000);
    try {
      await snapshotQuery.refresh();
    } catch {
      // Errors are surfaced via the host's toast; just reset the local flag.
      setRefreshing(false);
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    }
  }

  const showRefreshing = refreshing || snapshotQuery.loading;
  return (
    <button
      type="button"
      style={buttonStyle}
      onClick={handleClick}
      disabled={showRefreshing}
    >
      {showRefreshing ? "Refreshing…" : "Refresh"}
    </button>
  );
}

/**
 * "Run scan now" button with the same self-healing pattern as
 * RefreshButton. The host's usePluginAction returns a function that
 * resolves a promise — but the promise can hang indefinitely if the
 * bridge stalls. We add a hard 10-second timeout (scans are slow
 * but the *action dispatch* should be near-instant; the scan runs
 * in the background) so the button can always recover.
 *
 * We also disable the button while `running` is true (driven by the
 * snapshot's status.running) so the user doesn't double-fire the
 * action while a scan is in flight.
 */
function RunScanButton({
  runScanAction,
  running,
  onSuccess,
  onError,
}: {
  runScanAction: (params: { force: boolean }) => Promise<unknown>;
  running: boolean;
  onSuccess: () => void;
  onError: (err: unknown) => void;
}) {
  const [submitting, setSubmitting] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    },
    [],
  );

  async function handleClick() {
    if (submitting || running) return;
    setSubmitting(true);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setSubmitting(false);
      timerRef.current = null;
    }, 10_000);
    try {
      await runScanAction({ force: true });
      onSuccess();
    } catch (err) {
      onError(err);
    } finally {
      setSubmitting(false);
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    }
  }

  const showBusy = submitting || running;
  return (
    <button
      type="button"
      style={showBusy ? disabledButtonStyle : primaryButtonStyle}
      disabled={showBusy}
      onClick={handleClick}
    >
      {showBusy ? "Scanning…" : "Run scan now"}
    </button>
  );
}

function CopyButton({
  value,
  label = "Copy",
  className,
}: {
  value: string;
  label?: string;
  className?: CSSProperties;
}) {
  const [copied, setCopied] = useState(false);
  const handleCopy = useCallback(async () => {
    const ok = await copyTextToClipboard(value);
    if (ok) {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    }
  }, [value]);
  return (
    <button
      type="button"
      style={{ ...buttonStyle, ...(className ?? {}), ...(copied ? pillOkStyle : {}) }}
      onClick={handleCopy}
      disabled={!value}
      title={value ? `Copy ${label.toLowerCase()} to clipboard` : `Nothing to ${label.toLowerCase()}`}
    >
      {copied ? "✓ Copied" : label}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Presets sidebar entry — registered as a `sidebar` slot so it appears
// under the "Presets" section the host already renders in the left navbar.
// (See SlotOrder behaviour: presetsSidebar slot is rendered in the Work
// group; we use the standard sidebar slot type with order:110 to sit just
// below the existing agent-config-presets `presetsNavLink` at order:50.)
// ---------------------------------------------------------------------------

export function GitMergesPresetsSidebar(_props: PluginSidebarProps) {
  const hostNavigation = useHostNavigation();
  return (
    <a
      {...hostNavigation.linkProps(`/${PAGE_ROUTE}`)}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "10px",
        padding: "8px 10px",
        borderRadius: "8px",
        fontSize: "13px",
        fontWeight: 500,
        color: "inherit",
        textDecoration: "none",
      }}
    >
      <GitMergeIcon />
      <span className="truncate">Git Merges</span>
    </a>
  );
}

function GitMergeIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="6" cy="18" r="3" />
      <circle cx="6" cy="6" r="3" />
      <circle cx="18" cy="18" r="3" />
      <path d="M6 9v3a3 3 0 0 0 3 3h6a3 3 0 0 1 3 3v0" />
      <path d="M18 9a3 3 0 0 0-3-3H9" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Main page — the dashboard panel
// ---------------------------------------------------------------------------

export function GitMergesPage(_props: PluginPageProps) {
  const toast = usePluginToast();
  const hostContext = useHostContext();
  const snapshotQuery = usePluginData<MergeQueueSnapshot>(DATA_KEYS.snapshot);
  const runScanAction = usePluginAction(ACTION_KEYS.runScan);
  const clearAction = usePluginAction(ACTION_KEYS.clearOutput);
  const saveAction = usePluginAction(ACTION_KEYS.saveConfig);

  // Snapshot polling: while a scan is running, refresh the snapshot every
  // 1.5 s so the UI sees incremental output from the worker's partial-state
  // writer. When the scan completes we drop back to a 30 s heartbeat. The
  // host's stream bridge is not enabled in this Paperclip release, so we
  // can't rely on SSE — polling is the universal fallback.
  //
  // We depend on the *stable* refresh function and the running flag, not
  // the entire `snapshotQuery` object. The host's usePluginData returns a
  // fresh object reference every render, so depending on the whole object
  // would tear down and re-create this interval on every render.
  const snapshotRefresh = snapshotQuery.refresh;
  const runningNow = Boolean(snapshotQuery.data?.status?.running);
  useEffect(() => {
    const id = window.setInterval(() => {
      void snapshotRefresh();
    }, runningNow ? 1500 : 30_000);
    return () => window.clearInterval(id);
  }, [snapshotRefresh, runningNow]);

  const snapshot = snapshotQuery.data;
  const config = snapshot?.config ?? { ...DEFAULT_CONFIG };
  const status = snapshot?.status;
  const latest = snapshot?.latest ?? null;
  const history = snapshot?.history ?? [];

  // Local copies of the controls so the inputs feel responsive even before the
  // worker confirms the save.
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState<boolean>(
    config.autoRefreshEnabled,
  );
  const [intervalMinutes, setIntervalMinutes] = useState<number>(
    Math.max(1, Math.round(config.autoRefreshIntervalSeconds / 60)),
  );
  const [timeBlockEnabled, setTimeBlockEnabled] = useState<boolean>(
    config.timeBlockEnabled,
  );
  const [startHour, setStartHour] = useState<number>(config.timeBlockStartHour);
  const [endHour, setEndHour] = useState<number>(config.timeBlockEndHour);
  const [draftDirty, setDraftDirty] = useState(false);

  useEffect(() => {
    if (!snapshot) return;
    setAutoRefreshEnabled(snapshot.config.autoRefreshEnabled);
    setIntervalMinutes(
      Math.max(1, Math.round(snapshot.config.autoRefreshIntervalSeconds / 60)),
    );
    setTimeBlockEnabled(snapshot.config.timeBlockEnabled);
    setStartHour(snapshot.config.timeBlockStartHour);
    setEndHour(snapshot.config.timeBlockEndHour);
    setDraftDirty(false);
  }, [snapshot]);

  const draftConfig: GitMergesConfig = useMemo(
    () => ({
      ...config,
      autoRefreshEnabled,
      autoRefreshIntervalSeconds: Math.max(1, intervalMinutes) * 60,
      timeBlockEnabled,
      timeBlockStartHour: startHour,
      timeBlockEndHour: endHour,
    }),
    [config, autoRefreshEnabled, intervalMinutes, timeBlockEnabled, startHour, endHour],
  );

  const running = Boolean(status?.running);
  const effectiveStdout = latest?.stdout ?? "";
  const effectiveStderr = latest?.stderr ?? "";

  // Track which blocks the user has clicked into since the current scan
  // started. The set persists in localStorage and auto-resets when a
  // new scan arrives (because the storage key is the scan timestamp).
  const { visited, markVisited } = useVisitedBlocks(
    snapshot?.latestStartedAt ?? null,
  );

  // Build a delta lookup table by diffKey, shared by the Blocks and Diff
  // views so each card can show elapsed time + per-block check-count delta.
  const deltaByKey = useMemo(() => {
    const map = new Map<string, BlockDelta>();
    if (!snapshot) return map;
    const currentStartedAt = snapshot.latestStartedAt;
    const previousStartedAt = snapshot.previousStartedAt;
    const previousBlocks = snapshot.previousBlocks ?? [];
    const currentBlocks = snapshot.blocks;
    const previousByKey = new Map(previousBlocks.map((b) => [b.diffKey, b]));
    for (const cur of currentBlocks) {
      const prev = previousByKey.get(cur.diffKey) ?? null;
      map.set(
        cur.diffKey,
        computeBlockDelta(cur, prev, currentStartedAt, previousStartedAt),
      );
    }
    for (const prev of previousBlocks) {
      if (!map.has(prev.diffKey)) {
        map.set(
          prev.diffKey,
          computeBlockDelta(null, prev, currentStartedAt, previousStartedAt),
        );
      }
    }
    return map;
  }, [snapshot]);

  async function handleClear() {
    try {
      await clearAction({});
      await snapshotQuery.refresh();
      toast({ title: "Output cleared", tone: "info" });
    } catch (err) {
      toast({
        title: "Could not clear output",
        body: getErrorMessage(err),
        tone: "error",
      });
    }
  }

  async function handleSaveDraft() {
    try {
      await saveAction(draftConfig as unknown as Record<string, unknown>);
      setDraftDirty(false);
      toast({ title: "Git Merges settings saved", tone: "success" });
    } catch (err) {
      toast({
        title: "Could not save settings",
        body: getErrorMessage(err),
        tone: "error",
      });
    }
  }

  function handleRefresh() {
    void snapshotQuery.refresh();
  }

  // Next scheduled run: based on lastAttemptAt + interval (if auto-refresh
  // is enabled and we're inside the time block, otherwise show "paused").
  const lastAttemptMs = status?.lastAttemptAt
    ? new Date(status.lastAttemptAt).getTime()
    : 0;
  const nextRunMs = useMemo(() => {
    if (!draftConfig.autoRefreshEnabled) return null;
    const intervalMs = draftConfig.autoRefreshIntervalSeconds * 1000;
    if (!lastAttemptMs) return Date.now();
    return lastAttemptMs + intervalMs;
  }, [draftConfig.autoRefreshEnabled, draftConfig.autoRefreshIntervalSeconds, lastAttemptMs]);
  const nextRunText = useMemo(() => {
    if (!draftConfig.autoRefreshEnabled) return "Auto-refresh is off";
    if (!nextRunMs) return "—";
    return formatRelative(new Date(nextRunMs).toISOString());
  }, [draftConfig.autoRefreshEnabled, nextRunMs]);

  const now = useNow(15_000);
  const insideTimeBlock = useMemo(() => {
    if (!draftConfig.timeBlockEnabled) return true;
    return isInsideTimeBlock(
      now,
      draftConfig.timeBlockStartHour,
      draftConfig.timeBlockEndHour,
    );
  }, [now, draftConfig.timeBlockEnabled, draftConfig.timeBlockStartHour, draftConfig.timeBlockEndHour]);

  return (
    <div style={{ display: "grid", gap: "16px" }}>
      <style>{indeterminateKeyframes}</style>
      <header style={{ display: "grid", gap: "6px" }}>
        <h1 style={{ fontSize: "20px", margin: 0, fontWeight: 600 }}>
          Git Merges
        </h1>
        <p style={mutedTextStyle}>
          Runs BTC-Trade-Engine-PaperClip's{" "}
          <code style={codeInlineStyle}>scripts/merge_queue_status.py</code> on a
          schedule. The script's full stdout/stderr is shown below and refreshed
          automatically inside your configured time block.
        </p>
      </header>

      <section style={cardStyle} aria-label="Status">
        <div style={sectionHeaderStyle}>
          <strong style={{ fontSize: "14px" }}>Status</strong>
          <StatusPill
            running={running}
            lastExitCode={status?.lastExitCode ?? null}
          />
        </div>
        {running ? (
          <div style={progressBarTrackStyle} aria-label="Scanning">
            <div style={progressBarFillStyle} />
          </div>
        ) : null}
        <div style={rowStyle}>
          <span style={mutedTextStyle}>
            Last scan: {formatRelative(status?.lastRunAt ?? null)}
          </span>
          <span style={mutedTextStyle}>
            Last attempt: {formatRelative(status?.lastAttemptAt ?? null)}
          </span>
          <span style={mutedTextStyle}>Next scheduled: {nextRunText}</span>
        </div>
        <div style={rowStyle}>
          {draftConfig.autoRefreshEnabled ? (
            <span style={pillOkStyle}>auto-refresh ON</span>
          ) : (
            <span style={pillWarnStyle}>auto-refresh OFF</span>
          )}
          {draftConfig.timeBlockEnabled ? (
            insideTimeBlock ? (
              <span style={pillOkStyle}>
                inside time block {formatLocalHour(draftConfig.timeBlockStartHour)}–
                {formatLocalHour(draftConfig.timeBlockEndHour)}
              </span>
            ) : (
              <span style={pillWarnStyle}>
                outside time block {formatLocalHour(draftConfig.timeBlockStartHour)}–
                {formatLocalHour(draftConfig.timeBlockEndHour)}
              </span>
            )
          ) : (
            <span style={pillStyle}>time block disabled</span>
          )}
          {status?.lastSkipped ? (
            <span style={pillWarnStyle}>last attempt skipped</span>
          ) : null}
        </div>
      </section>

      <section style={cardStyle} aria-label="Controls">
        <div style={sectionHeaderStyle}>
          <strong style={{ fontSize: "14px" }}>Controls</strong>
        </div>
        <div style={rowStyle}>
          <RunScanButton
            runScanAction={runScanAction}
            running={running}
            onSuccess={() => {
              toast({ title: "Git Merges scan started", tone: "info" });
              void snapshotQuery.refresh();
            }}
            onError={(err) =>
              toast({
                title: "Could not start scan",
                body: getErrorMessage(err),
                tone: "error",
              })
            }
          />
          <button
            type="button"
            style={destructiveButtonStyle}
            onClick={handleClear}
            disabled={!latest}
          >
            Clear output
          </button>
          <button
            type="button"
            style={draftDirty ? primaryButtonStyle : disabledButtonStyle}
            disabled={!draftDirty}
            onClick={handleSaveDraft}
          >
            {draftDirty ? "Save changes" : "Saved"}
          </button>
          <RefreshButton snapshotQuery={snapshotQuery} />
        </div>
      </section>

      <section style={cardStyle} aria-label="Auto-refresh settings">
        <div style={sectionHeaderStyle}>
          <strong style={{ fontSize: "14px" }}>Auto-refresh</strong>
        </div>
        <div style={rowStyle}>
          <label
            style={{
              ...rowStyle,
              fontSize: "12px",
              gap: "6px",
              cursor: "pointer",
            }}
          >
            <input
              type="checkbox"
              checked={autoRefreshEnabled}
              onChange={(event) => {
                setAutoRefreshEnabled(event.target.checked);
                setDraftDirty(true);
              }}
            />
            <span>Enable auto-refresh</span>
          </label>
        </div>
        <label style={fieldLabelStyle}>
          <span style={mutedTextStyle}>
            Run script every <strong>{intervalMinutes}</strong> minute
            {intervalMinutes === 1 ? "" : "s"}
          </span>
          <input
            type="range"
            min={1}
            max={60}
            step={1}
            value={intervalMinutes}
            onChange={(event) => {
              setIntervalMinutes(Number(event.target.value));
              setDraftDirty(true);
            }}
            style={{ width: "100%" }}
          />
          <div style={rowStyle}>
            {[1, 2, 5, 10, 15, 30, 60].map((m) => (
              <button
                key={m}
                type="button"
                style={intervalMinutes === m ? primaryButtonStyle : buttonStyle}
                onClick={() => {
                  setIntervalMinutes(m);
                  setDraftDirty(true);
                }}
              >
                {m}m
              </button>
            ))}
          </div>
        </label>
      </section>

      <section style={cardStyle} aria-label="Time block settings">
        <div style={sectionHeaderStyle}>
          <strong style={{ fontSize: "14px" }}>Time block</strong>
          <span style={mutedTextStyle}>
            Auto-refresh only runs inside this window (local time).
          </span>
        </div>
        <div style={rowStyle}>
          <label
            style={{
              ...rowStyle,
              fontSize: "12px",
              gap: "6px",
              cursor: "pointer",
            }}
          >
            <input
              type="checkbox"
              checked={timeBlockEnabled}
              onChange={(event) => {
                setTimeBlockEnabled(event.target.checked);
                setDraftDirty(true);
              }}
            />
            <span>Limit auto-refresh to a time block</span>
          </label>
        </div>
        <div style={rowStyle}>
          <label style={fieldLabelStyle}>
            <span style={mutedTextStyle}>Start hour</span>
            <select
              value={startHour}
              onChange={(event) => {
                setStartHour(Number(event.target.value));
                setDraftDirty(true);
              }}
              style={inputStyle}
            >
              {Array.from({ length: 24 }).map((_, h) => (
                <option key={`start-${h}`} value={h}>
                  {formatLocalHour(h)} ({String(h).padStart(2, "0")}:00)
                </option>
              ))}
            </select>
          </label>
          <label style={fieldLabelStyle}>
            <span style={mutedTextStyle}>End hour</span>
            <select
              value={endHour}
              onChange={(event) => {
                setEndHour(Number(event.target.value));
                setDraftDirty(true);
              }}
              style={inputStyle}
            >
              {Array.from({ length: 24 }).map((_, h) => (
                <option key={`end-${h}`} value={h}>
                  {formatLocalHour(h)} ({String(h).padStart(2, ":00")
                  .slice(0, 5)}:00)
                </option>
              ))}
            </select>
          </label>
        </div>
        <div style={rowStyle}>
          <TimeBlockChip
            label="8am – 4pm"
            onClick={() => {
              setTimeBlockEnabled(true);
              setStartHour(8);
              setEndHour(16);
              setDraftDirty(true);
            }}
          />
          <TimeBlockChip
            label="9am – 6pm"
            onClick={() => {
              setTimeBlockEnabled(true);
              setStartHour(9);
              setEndHour(18);
              setDraftDirty(true);
            }}
          />
          <TimeBlockChip
            label="24/7 (no block)"
            onClick={() => {
              setTimeBlockEnabled(false);
              setDraftDirty(true);
            }}
          />
          <TimeBlockChip
            label="5min · 8am–4pm"
            active={
              autoRefreshEnabled === true &&
              intervalMinutes === 5 &&
              timeBlockEnabled === true &&
              startHour === 8 &&
              endHour === 16
            }
            onClick={() => {
              setAutoRefreshEnabled(true);
              setIntervalMinutes(5);
              setTimeBlockEnabled(true);
              setStartHour(8);
              setEndHour(16);
              setDraftDirty(true);
            }}
          />
        </div>
      </section>

      <section style={cardStyle} aria-label="Merge queue">
        <div style={sectionHeaderStyle}>
          <strong style={{ fontSize: "14px" }}>Merge queue</strong>
          <span style={mutedTextStyle}>
            {snapshot
              ? `${snapshot.blocks.length} PR${snapshot.blocks.length === 1 ? "" : "s"} · ${snapshot.totals.ready} ready · ${snapshot.totals.waiting} waiting · ${snapshot.totals.failing} failing · ${snapshot.totals.noPrOrSha} no PR / SHA`
              : "no data yet"}
          </span>
        </div>
        <NowProcessingPanel />
        <QueueTabs
          blocks={snapshot?.blocks ?? []}
          previousBlocks={snapshot?.previousBlocks ?? null}
          deltaByKey={deltaByKey}
          visited={visited}
          onVisit={markVisited}
          totals={snapshot?.totals ?? null}
          stdout={effectiveStdout}
          stderr={effectiveStderr}
          companyPrefix={hostContext.companyPrefix}
          blockedChains={snapshot?.blockedChains ?? []}
          approvalRequests={snapshot?.approvalRequests ?? []}
          approvalChainLookup={snapshot?.approvalChainLookup ?? {}}
          blockedCount={snapshot?.blockedCount ?? 0}
          chainCount={snapshot?.chainCount ?? 0}
          approvalCount={snapshot?.approvalCount ?? 0}
        />
      </section>

      <section style={cardStyle} aria-label="History">
        <div style={sectionHeaderStyle}>
          <strong style={{ fontSize: "14px" }}>Recent scans</strong>
          <span style={mutedTextStyle}>
            Showing the {history.length} most recent completed scan
            {history.length === 1 ? "" : "s"}.
          </span>
        </div>
        {history.length === 0 ? (
          <div style={mutedTextStyle}>No scans yet.</div>
        ) : (
          <div style={{ display: "grid", gap: "6px" }}>
            {history.map((scan, idx) => (
              <HistoryRow key={`${scan.startedAt}-${idx}`} scan={scan} />
            ))}
          </div>
        )}
      </section>

      <PluginMetaFooter pluginId={PLUGIN_ID} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Queue tabs — Blocks / Diff / Blocked Chain / Awaiting Approval / Raw
// ---------------------------------------------------------------------------

type QueueTab = "blocks" | "diff" | "chains" | "approvals" | "raw";

const tabBarStyle: CSSProperties = {
  display: "flex",
  gap: "4px",
  borderBottom: "1px solid var(--border)",
  marginBottom: "10px",
  flexWrap: "wrap",
};

const tabButtonStyle = (active: boolean): CSSProperties => ({
  appearance: "none",
  border: "1px solid var(--border)",
  borderBottom: active ? "1px solid transparent" : "1px solid var(--border)",
  background: active ? "var(--card, transparent)" : "transparent",
  color: "inherit",
  padding: "6px 12px",
  fontSize: "12px",
  fontWeight: active ? 600 : 400,
  borderRadius: "8px 8px 0 0",
  marginBottom: active ? "-1px" : 0,
  cursor: "pointer",
});

/**
 * BTCAAAAA-39051: stuck-filter toggle button style. The active state
 * uses the same amber palette as the STUCK pill so the visual
 * language stays consistent (orange = "needs attention").
 */
const stuckFilterButtonStyle = (active: boolean): CSSProperties => ({
  appearance: "none",
  border: "1px solid color-mix(in srgb, #d97706 50%, var(--border))",
  background: active
    ? "color-mix(in srgb, #d97706 22%, transparent)"
    : "transparent",
  color: active ? "#fcd34d" : "var(--muted, #888)",
  padding: "4px 10px",
  fontSize: "12px",
  fontWeight: active ? 600 : 400,
  borderRadius: "999px",
  cursor: "pointer",
});

/**
 * BTCAAAAA-39051: small panel above the queue showing the merge-
 * dispatch routine's currently-in-progress execution issues. Polls
 * the `git-merges-running` data channel every 2s while visible.
 * Empty state shows the time-since-last-dispatch (when known).
 */
function NowProcessingPanel() {
  const runningQuery = usePluginData<{
    jobs: Array<{
      issueUuid: string;
      issueIdentifier: string | null;
      linkedIssueTitle: string | null;
      startedAt: string;
      elapsedSeconds: number;
      hasAgent: boolean;
    }>;
    lastDispatchAt: string | null;
  }>(DATA_KEYS.running, { jobs: [], lastDispatchAt: null });

  // Poll every 2s while mounted. Cheap — the worker caches the result.
  useEffect(() => {
    const id = setInterval(() => runningQuery.refresh(), 2000);
    return () => clearInterval(id);
  }, [runningQuery]);

  const data = runningQuery.data;
  const jobs = data?.jobs ?? [];
  const lastDispatchAt = data?.lastDispatchAt ?? null;

  // Empty state: no active dispatches right now.
  if (jobs.length === 0) {
    return (
      <div
        style={{
          ...mutedTextStyle,
          padding: "6px 10px",
          fontSize: "12px",
          border: "1px dashed var(--border)",
          borderRadius: "6px",
          marginBottom: "10px",
        }}
        title="No active dispatch jobs right now. The Phase 4a routine picks up in_review issues every 5 minutes."
      >
        {lastDispatchAt
          ? `⚙ No active dispatches — last run ${formatRelativeTime(lastDispatchAt)}`
          : "⚙ No active dispatches"}
      </div>
    );
  }

  return (
    <div
      style={{
        padding: "8px 10px",
        border: "1px solid color-mix(in srgb, #2563eb 50%, var(--border))",
        borderRadius: "6px",
        background: "color-mix(in srgb, #2563eb 8%, transparent)",
        marginBottom: "10px",
        display: "grid",
        gap: "4px",
      }}
      title="Active merge-dispatch jobs. Updated every 2s."
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "6px",
          fontSize: "12px",
          fontWeight: 600,
          color: "#93c5fd",
        }}
      >
        <span
          style={{
            display: "inline-block",
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            background: "#3b82f6",
            animation: "pulse 1.4s ease-in-out infinite",
          }}
        />
        Now processing ({jobs.length})
      </div>
      {jobs.map((job) => (
        <div
          key={job.issueUuid}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            fontSize: "12px",
            paddingLeft: "14px",
            color: "var(--text)",
          }}
        >
          <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis" }}>
            {job.issueIdentifier ?? job.issueUuid.slice(0, 8) + "…"}
            {job.linkedIssueTitle ? ` — ${job.linkedIssueTitle}` : ""}
          </span>
          <span style={mutedTextStyle}>
            {job.hasAgent ? "agent working" : "queued"} ·{" "}
            {formatElapsedSeconds(job.elapsedSeconds)}
          </span>
        </div>
      ))}
    </div>
  );
}

function formatElapsedSeconds(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

function formatRelativeTime(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 0) return "just now";
  return `${formatElapsedSeconds(Math.round(ms / 1000))} ago`;
}

function QueueTabs({
  blocks,
  previousBlocks,
  deltaByKey,
  visited,
  onVisit,
  totals: _totals,
  stdout,
  stderr,
  companyPrefix,
  blockedChains,
  approvalRequests,
  approvalChainLookup,
  blockedCount,
  chainCount,
  approvalCount,
}: {
  blocks: MergeBlock[];
  previousBlocks: MergeBlock[] | null;
  deltaByKey: Map<string, BlockDelta>;
  visited: Set<string>;
  onVisit: (diffKey: string) => void;
  totals: MergeQueueSnapshot["totals"] | null;
  stdout: string;
  stderr: string;
  companyPrefix: string | null;
  blockedChains: BlockedChain[];
  approvalRequests: ApprovalRequest[];
  approvalChainLookup: Record<string, { chainId: string; node: ChainNode }>;
  blockedCount: number;
  chainCount: number;
  approvalCount: number;
}) {
  const [tab, setTab] = useState<QueueTab>("blocks");
  // BTCAAAAA-39051: stuck-only filter. Default ON so operators see
  // the actionable set first; can be turned off to see all in-review.
  const [stuckOnly, setStuckOnly] = useState<boolean>(true);
  const hasPrevious = previousBlocks !== null && previousBlocks.length > 0;
  const stuckCount = blocks.filter((b) => b.isStuck).length;
  const visibleBlocks = stuckOnly ? blocks.filter((b) => b.isStuck) : blocks;

  return (
    <div>
      <div style={tabBarStyle} role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "blocks"}
          style={tabButtonStyle(tab === "blocks")}
          onClick={() => setTab("blocks")}
        >
          Blocks ({stuckOnly ? `${stuckCount}/${blocks.length}` : blocks.length})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "diff"}
          style={tabButtonStyle(tab === "diff")}
          onClick={() => setTab("diff")}
          disabled={!hasPrevious}
          title={hasPrevious ? "Compare to the previous scan" : "Run a second scan to see the diff"}
        >
          Diff vs last {hasPrevious ? `(${previousBlocks?.length ?? 0})` : ""}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "chains"}
          style={tabButtonStyle(tab === "chains")}
          onClick={() => setTab("chains")}
          disabled={blockedChains.length === 0}
          title={
            blockedChains.length > 0
              ? `${chainCount} chains across ${blockedCount} blocked issues`
              : "No blocked chains"
          }
        >
          Blocked Chain ({chainCount})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "approvals"}
          style={tabButtonStyle(tab === "approvals")}
          onClick={() => setTab("approvals")}
          disabled={approvalRequests.length === 0}
          title={
            approvalRequests.length > 0
              ? `${approvalCount} pending board-approval requests`
              : "No pending approvals"
          }
        >
          Awaiting Approval ({approvalCount})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "raw"}
          style={tabButtonStyle(tab === "raw")}
          onClick={() => setTab("raw")}
        >
          Raw
        </button>
      </div>
      {tab === "blocks" ? (
        <div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 0",
              flexWrap: "wrap",
            }}
          >
            <button
              type="button"
              onClick={() => setStuckOnly((v) => !v)}
              style={stuckFilterButtonStyle(stuckOnly)}
              title={
                stuckOnly
                  ? `Showing ${stuckCount} stuck of ${blocks.length} in-review. Click to show all.`
                  : `Showing all ${blocks.length} in-review. Click to filter to stuck only (>= ${STUCK_THRESHOLD_HOURS}h, no progress).`
              }
            >
              {stuckOnly ? "⚠ Stuck only" : "Show all"} ({stuckOnly ? stuckCount : blocks.length})
            </button>
            {stuckOnly && blocks.length > stuckCount ? (
              <span style={mutedTextStyle}>
                {blocks.length - stuckCount} non-stuck hidden — click "Show all" to view
              </span>
            ) : null}
          </div>
          <BlocksView
            blocks={visibleBlocks}
            deltaByKey={deltaByKey}
            visited={visited}
            onVisit={onVisit}
            companyPrefix={companyPrefix}
          />
        </div>
      ) : tab === "diff" ? (
        <DiffView
          current={blocks}
          previous={previousBlocks ?? []}
          deltaByKey={deltaByKey}
          visited={visited}
          onVisit={onVisit}
          companyPrefix={companyPrefix}
        />
      ) : tab === "chains" ? (
        <BlockedChainsView
          chains={blockedChains}
          visited={visited}
          onVisit={onVisit}
          companyPrefix={companyPrefix}
        />
      ) : tab === "approvals" ? (
        <AwaitingApprovalView
          approvals={approvalRequests}
          approvalChainLookup={approvalChainLookup}
          visited={visited}
          onVisit={onVisit}
          companyPrefix={companyPrefix}
        />
      ) : (
        <RawView stdout={stdout} stderr={stderr} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Blocks view — one card per in-review issue with status, progress, links.
// ---------------------------------------------------------------------------

const blockCardStyle: CSSProperties = {
  border: "1px solid var(--border)",
  borderRadius: "10px",
  padding: "10px 12px",
  display: "grid",
  gap: "8px",
  background:
    "color-mix(in srgb, var(--card, transparent) 50%, transparent)",
};

const blockHeaderStyle: CSSProperties = {
  display: "flex",
  alignItems: "flex-start",
  justifyContent: "space-between",
  gap: "10px",
};

const blockTitleStyle: CSSProperties = {
  fontSize: "13px",
  fontWeight: 600,
  margin: 0,
  lineHeight: 1.35,
};

const blockMetaStyle: CSSProperties = {
  fontSize: "11px",
  opacity: 0.7,
  display: "flex",
  gap: "10px",
  flexWrap: "wrap",
  alignItems: "center",
};

const progressTrackStyle: CSSProperties = {
  position: "relative",
  display: "flex",
  width: "100%",
  height: "8px",
  borderRadius: "999px",
  overflow: "hidden",
  background:
    "color-mix(in srgb, var(--muted, #888) 22%, transparent)",
  border: "1px solid color-mix(in srgb, var(--border) 80%, transparent)",
};

const checkListStyle: CSSProperties = {
  display: "grid",
  gap: "2px",
  fontSize: "11px",
};

function MergeStatusPill({ status }: { status: MergeStatus }) {
  if (status === "ready") return <span style={pillOkStyle}>ready to merge</span>;
  if (status === "waiting") return <span style={pillWarnStyle}>waiting on CI</span>;
  if (status === "failing") return <span style={pillErrStyle}>CI failing</span>;
  if (status === "no-pr") return <span style={pillWarnStyle}>no PR found</span>;
  if (status === "no-sha") return <span style={pillWarnStyle}>no Fix-SHA</span>;
  return <span style={pillStyle}>unknown</span>;
}

/**
 * BTCAAAAA-39051: ETA pill — shows the estimated time-to-merge based on
 * historical closure durations bucketed by status. Green for fast (<15 min),
 * yellow for medium (15 min - 2 h), red for slow (>2 h), grey for unknown.
 */
function EtaPill({
  bucket,
  minutes,
}: {
  bucket: MergeBlock["etaBucket"];
  minutes: number | null;
}) {
  const styleByBucket = {
    fast: pillOkStyle,
    medium: pillWarnStyle,
    slow: pillErrStyle,
    unknown: pillStyle,
  } as const;
  const labelByBucket = {
    fast: "ETA ~quick",
    medium: "ETA ~medium",
    slow: "ETA ~slow",
    unknown: "ETA unknown",
  } as const;
  const style = styleByBucket[bucket];
  const label =
    minutes != null && bucket !== "unknown"
      ? `ETA ~${formatEtaMinutes(minutes)}`
      : labelByBucket[bucket];
  return (
    <span
      style={style}
      title={
        minutes != null
          ? `Median duration for this status bucket (last ${"~20"} closures): ${formatEtaMinutes(minutes)}`
          : "ETA unknown — insufficient history for this status bucket"
      }
    >
      {label}
    </span>
  );
}

function formatEtaMinutes(minutes: number): string {
  if (minutes < 1) return "<1 min";
  if (minutes < 60) return `${Math.round(minutes)} min`;
  if (minutes < 60 * 24) return `${(minutes / 60).toFixed(1)} h`;
  return `${(minutes / (60 * 24)).toFixed(1)} d`;
}

function ProgressBar({
  passed,
  total,
}: {
  passed: number | null;
  total: number | null;
}) {
  if (passed === null || total === null || total <= 0) {
    return (
      <span style={{ ...mutedTextStyle, fontSize: "11px" }}>
        no progress info
      </span>
    );
  }
  const safePassed = Math.min(passed, total);
  const passedPct = (safePassed / total) * 100;
  const failed = total - safePassed;
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        width: "100%",
      }}
    >
      <div style={progressTrackStyle} aria-hidden>
        <div
          style={{
            width: `${passedPct}%`,
            height: "100%",
            background: "var(--foreground)",
          }}
        />
        {failed > 0 ? (
          <div
            style={{
              position: "absolute",
              inset: 0,
              width: "100%",
              display: "flex",
              pointerEvents: "none",
            }}
          >
            <div style={{ width: `${passedPct}%` }} />
            <div
              style={{
                flex: 1,
                background:
                  "repeating-linear-gradient(45deg, transparent 0 4px, color-mix(in srgb, #dc2626 22%, transparent) 4px 8px)",
              }}
            />
          </div>
        ) : null}
      </div>
      <span
        style={{
          ...mutedTextStyle,
          fontSize: "11px",
          whiteSpace: "nowrap",
        }}
      >
        {safePassed}/{total} checks
      </span>
    </div>
  );
}

function CheckRow({ check }: { check: MergeCheck }) {
  const color =
    check.state === "passed"
      ? "#16a34a"
      : check.state === "failed" || check.state === "missing"
        ? "#dc2626"
        : check.state === "pending"
          ? "#d97706"
          : "var(--muted, #888)";
  const icon =
    check.state === "passed"
      ? "✓"
      : check.state === "failed"
        ? "✗"
        : check.state === "missing"
          ? "✗"
          : check.state === "pending"
            ? "⏳"
            : "·";
  return (
    <div style={checkListStyle}>
      <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
        <span style={{ color, fontWeight: 700, width: "14px" }}>{icon}</span>
        <span>{check.name}</span>
        {check.detail ? (
          <span style={{ ...mutedTextStyle, fontSize: "11px" }}>
            [{check.detail}]
          </span>
        ) : null}
      </span>
    </div>
  );
}

function MergeBlockCard({
  block,
  companyPrefix,
  diffBadge,
  delta,
  isVisited,
  onVisit,
}: {
  block: MergeBlock;
  companyPrefix: string | null;
  diffBadge?: ReactNode;
  delta?: BlockDelta | null;
  isVisited?: boolean;
  onVisit?: (diffKey: string) => void;
}) {
  const hostNavigation = useHostNavigation();
  const issueHref =
    companyPrefix && block.issueIdentifier
      ? `/${companyPrefix}/issues/${block.issueIdentifier}`
      : null;
  const prHref = block.prNumber
    ? `https://github.com/Stack-Alerts/BTC-Trade-Engine-PaperClip/pull/${block.prNumber}`
    : null;

  // Build link props via the host SPA router so internal Paperclip
  // navigation does not reload the document. External (GitHub) links
  // use a plain anchor with target=_blank since they leave the app.
  const issueLinkProps = issueHref
    ? hostNavigation.linkProps(issueHref)
    : null;

  // Compose click handlers so the visited marker is recorded when the
  // user actually navigates. We wrap the host-router onClick (and the
  // default action for external links) so the marker fires only on
  // intentional clicks, not on prefetch/right-click/etc.
  const handleIssueClick = (event: React.MouseEvent<HTMLAnchorElement>) => {
    onVisit?.(block.diffKey);
    issueLinkProps?.onClick(event);
  };
  const handlePrClick = () => {
    onVisit?.(block.diffKey);
  };

  return (
    <div style={blockCardStyle}>
      <div style={blockHeaderStyle}>
        <div style={{ display: "grid", gap: "2px", flex: 1 }}>
          <h4 style={blockTitleStyle}>
            <span style={{ opacity: 0.55, fontWeight: 400 }}>#{block.index}</span>{" "}
            {block.title}
          </h4>
          <div style={blockMetaStyle}>
            <span>in review {block.inReviewFor}</span>
            {issueLinkProps ? (
              <a
                {...issueLinkProps}
                onClick={handleIssueClick}
                style={inlineLinkStyle}
                title={`Open ${block.issueIdentifier} in Paperclip`}
              >
                {block.issueIdentifier}
              </a>
            ) : block.issueIdentifier ? (
              <span title="Issue identifier (no company prefix in host context)">
                {block.issueIdentifier}
              </span>
            ) : (
              <span style={{ opacity: 0.5 }}>
                {block.issueUuid.slice(0, 8)}…
              </span>
            )}
            {isVisited ? (
              <span
                style={visitedPillStyle}
                title="You opened this block's link since the last scan. Marker clears on the next scan."
              >
                ✓ checked
              </span>
            ) : null}
            {prHref ? (
              <a
                href={prHref}
                target="_blank"
                rel="noreferrer"
                onClick={handlePrClick}
                style={inlineLinkStyle}
                title={`Open PR #${block.prNumber} on GitHub`}
              >
                PR #{block.prNumber}
              </a>
            ) : block.prNumber ? (
              <span>PR #{block.prNumber}</span>
            ) : null}
            {block.prMergeable ? (
              <span style={{ opacity: 0.7 }}>({block.prMergeable})</span>
            ) : null}
            {block.fixSha ? (
              <code
                style={{
                  fontSize: "10px",
                  padding: "1px 4px",
                  border: "1px solid var(--border)",
                  borderRadius: "4px",
                  fontFamily:
                    "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                }}
                title={block.fixSha}
              >
                {block.fixSha.slice(0, 7)}
              </code>
            ) : null}
          </div>
        </div>
        <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
          {diffBadge}
          {block.isStuck ? (
            <span
              style={stuckPillStyle}
              title={`In review for ${block.inReviewFor || "a long time"} with no progress since the last scan. Threshold: ${STUCK_THRESHOLD_HOURS}h (configurable in settings).`}
            >
              ⚠ STUCK
            </span>
          ) : null}
          <EtaPill bucket={block.etaBucket} minutes={block.etaMinutes} />
          <MergeStatusPill status={block.status} />
        </div>
      </div>
      {delta ? <DeltaLine delta={delta} current={block} /> : null}
      {(block.progressPassed !== null || block.progressTotal !== null) && (
        <ProgressBar
          passed={block.progressPassed}
          total={block.progressTotal}
        />
      )}
      {block.checks.length > 0 ? (
        <div style={{ display: "grid", gap: "2px" }}>
          {block.checks.map((check, idx) => (
            <CheckRow key={`${block.issueUuid}-check-${idx}`} check={check} />
          ))}
        </div>
      ) : null}
      {block.statusLabel && block.statusLabel !== block.title ? (
        <div style={{ ...mutedTextStyle, fontSize: "11px" }}>
          {block.statusLabel}
        </div>
      ) : null}
    </div>
  );
}

function BlocksView({
  blocks,
  deltaByKey,
  visited,
  onVisit,
  companyPrefix,
}: {
  blocks: MergeBlock[];
  deltaByKey: Map<string, BlockDelta>;
  visited: Set<string>;
  onVisit: (diffKey: string) => void;
  companyPrefix: string | null;
}) {
  if (blocks.length === 0) {
    return (
      <div style={mutedTextStyle}>
        No in-review issues. Run a scan to populate the queue.
      </div>
    );
  }
  return (
    <div style={{ display: "grid", gap: "8px" }}>
      {blocks.map((block) => {
        const delta = deltaByKey.get(block.diffKey) ?? null;
        return (
          <MergeBlockCard
            key={block.issueUuid}
            block={block}
            companyPrefix={companyPrefix}
            delta={delta}
            isVisited={visited.has(block.diffKey)}
            onVisit={onVisit}
          />
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Per-block delta: elapsed time + check-count change vs the previous scan.
// Used by the Diff view and as an inline hint on the Blocks view.
// ---------------------------------------------------------------------------

type BlockDelta = {
  kind: "added" | "removed" | "changed" | "unchanged";
  /** Wall-clock ms between the previous and current scan, when both present. */
  elapsedMs: number | null;
  /** Passed checks in the previous scan (when matched). */
  prevPassed: number | null;
  prevTotal: number | null;
  prevStatus: MergeStatus | null;
  /** `true` if the block made no progress between scans (stalled). */
  stalled: boolean;
  /** Set of check names that transitioned to passed since the previous scan. */
  newlyPassed: string[];
  /** Set of check names that transitioned away from passed since the previous scan. */
  noLongerPassing: string[];
};

function computeBlockDelta(
  current: MergeBlock | null,
  previous: MergeBlock | null,
  currentStartedAt: string | null,
  previousStartedAt: string | null,
): BlockDelta {
  const base: BlockDelta = {
    kind: current && previous ? "unchanged" : current ? "added" : "removed",
    elapsedMs: null,
    prevPassed: null,
    prevTotal: null,
    prevStatus: null,
    stalled: false,
    newlyPassed: [],
    noLongerPassing: [],
  };
  if (!current || !previous) return base;
  base.kind = "unchanged";
  base.prevPassed = previous.progressPassed;
  base.prevTotal = previous.progressTotal;
  base.prevStatus = previous.status;
  if (currentStartedAt && previousStartedAt) {
    const cur = Date.parse(currentStartedAt);
    const prev = Date.parse(previousStartedAt);
    if (Number.isFinite(cur) && Number.isFinite(prev)) {
      base.elapsedMs = Math.max(0, cur - prev);
    }
  }
  // Check-count change
  const curPassed = current.progressPassed ?? 0;
  const prevPassed = previous.progressPassed ?? 0;
  if (curPassed !== prevPassed) {
    base.kind = "changed";
  }
  // Per-check name transitions
  const prevPassedNames = new Set(
    previous.checks.filter((c) => c.state === "passed").map((c) => c.name),
  );
  const curPassedNames = new Set(
    current.checks.filter((c) => c.state === "passed").map((c) => c.name),
  );
  for (const name of curPassedNames) {
    if (!prevPassedNames.has(name)) {
      base.newlyPassed.push(name);
      base.kind = "changed";
    }
  }
  for (const name of prevPassedNames) {
    if (!curPassedNames.has(name)) {
      base.noLongerPassing.push(name);
      base.kind = "changed";
    }
  }
  // Status / pr / sha changes
  if (current.status !== previous.status) base.kind = "changed";
  if (current.prNumber !== previous.prNumber) base.kind = "changed";
  if (current.fixSha !== previous.fixSha) base.kind = "changed";
  // Stalled = same checks-passed total AND same status AND no check transitions
  if (
    curPassed === prevPassed &&
    current.status === previous.status &&
    base.newlyPassed.length === 0 &&
    base.noLongerPassing.length === 0
  ) {
    base.stalled = true;
  }
  return base;
}

function formatElapsed(ms: number | null): string {
  if (ms === null) return "—";
  if (ms < 1000) return "<1s";
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}

const deltaRowStyle: CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "6px",
  alignItems: "center",
  fontSize: "11px",
};

const deltaPillBase: CSSProperties = {
  fontSize: "10px",
  padding: "1px 7px",
  borderRadius: "999px",
  border: "1px solid var(--border)",
  background: "color-mix(in srgb, var(--muted, #888) 14%, transparent)",
  whiteSpace: "nowrap",
};

const deltaPillGood: CSSProperties = {
  ...deltaPillBase,
  borderColor: "color-mix(in srgb, #16a34a 60%, var(--border))",
  background: "color-mix(in srgb, #16a34a 14%, transparent)",
  color: "#86efac",
};

const deltaPillWarn: CSSProperties = {
  ...deltaPillBase,
  borderColor: "color-mix(in srgb, #d97706 60%, var(--border))",
  background: "color-mix(in srgb, #d97706 14%, transparent)",
  color: "#fcd34d",
};

const deltaPillBad: CSSProperties = {
  ...deltaPillBase,
  borderColor: "color-mix(in srgb, #dc2626 60%, var(--border))",
  background: "color-mix(in srgb, #dc2626 14%, transparent)",
  color: "#fca5a5",
};

const deltaPillStalled: CSSProperties = {
  ...deltaPillBase,
  borderColor: "color-mix(in srgb, #f43f5e 60%, var(--border))",
  background: "color-mix(in srgb, #f43f5e 14%, transparent)",
  color: "#fda4af",
  fontWeight: 600,
};

function DeltaLine({
  delta,
  current,
}: {
  delta: BlockDelta;
  current: MergeBlock | null;
}) {
  if (delta.kind === "added") {
    return (
      <div style={deltaRowStyle}>
        <span style={deltaPillGood}>new since last scan</span>
        {delta.elapsedMs !== null ? (
          <span style={deltaPillBase}>
            first scan was {formatElapsed(delta.elapsedMs)} ago
          </span>
        ) : null}
      </div>
    );
  }
  if (delta.kind === "removed") {
    return (
      <div style={deltaRowStyle}>
        <span style={deltaPillBad}>removed</span>
      </div>
    );
  }

  const pills: ReactNode[] = [];
  pills.push(
    <span key="since" style={deltaPillBase}>
      since {formatElapsed(delta.elapsedMs)}
    </span>,
  );

  const curPassed = current?.progressPassed ?? null;
  const curTotal = current?.progressTotal ?? null;
  const prevPassed = delta.prevPassed;
  const prevTotal = delta.prevTotal;

  // Passed delta: +N means N more checks passed (good).
  if (curPassed !== null && prevPassed !== null) {
    const diff = curPassed - prevPassed;
    if (diff > 0) {
      pills.push(
        <span key="passed" style={deltaPillGood}>
          +{diff} passed
        </span>,
      );
    } else if (diff < 0) {
      pills.push(
        <span key="passed" style={deltaPillBad}>
          {diff} passed
        </span>,
      );
    }
  }
  // Waiting delta: pending checks. Negative waiting = progress (good).
  if (
    curPassed !== null &&
    curTotal !== null &&
    prevPassed !== null &&
    prevTotal !== null
  ) {
    const curWaiting = Math.max(0, curTotal - curPassed);
    const prevWaiting = Math.max(0, prevTotal - prevPassed);
    const wDiff = curWaiting - prevWaiting;
    if (wDiff !== 0) {
      const sign = wDiff > 0 ? "+" : "−";
      const abs = Math.abs(wDiff);
      const style = wDiff < 0 ? deltaPillGood : deltaPillWarn;
      pills.push(
        <span key="waiting" style={style}>
          {sign}
          {abs} waiting
        </span>,
      );
    }
  }
  // Per-check transitions (only meaningful when something flipped).
  if (delta.newlyPassed.length > 0) {
    pills.push(
      <span key="np" style={deltaPillGood}>
        {delta.newlyPassed.length} newly passed
      </span>,
    );
  }
  if (delta.noLongerPassing.length > 0) {
    pills.push(
      <span key="nlp" style={deltaPillBad}>
        {delta.noLongerPassing.length} flipped
      </span>,
    );
  }
  if (delta.stalled) {
    pills.push(
      <span key="stalled" style={deltaPillStalled}>stalled</span>,
    );
  }
  return <div style={deltaRowStyle}>{pills}</div>;
}

// ---------------------------------------------------------------------------
// Diff view — what changed since the last scan.
// ---------------------------------------------------------------------------

const diffBadgeBase: CSSProperties = {
  fontSize: "10px",
  padding: "1px 6px",
  borderRadius: "999px",
  border: "1px solid var(--border)",
  background:
    "color-mix(in srgb, var(--muted, #888) 18%, transparent)",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};

const diffKindStyle: Record<string, CSSProperties> = {
  added: {
    ...diffBadgeBase,
    borderColor: "color-mix(in srgb, #16a34a 60%, var(--border))",
    background: "color-mix(in srgb, #16a34a 14%, transparent)",
    color: "#86efac",
  },
  removed: {
    ...diffBadgeBase,
    borderColor: "color-mix(in srgb, #dc2626 60%, var(--border))",
    background: "color-mix(in srgb, #dc2626 14%, transparent)",
    color: "#fca5a5",
  },
  changed: {
    ...diffBadgeBase,
    borderColor: "color-mix(in srgb, #d97706 60%, var(--border))",
    background: "color-mix(in srgb, #d97706 14%, transparent)",
    color: "#fcd34d",
  },
  unchanged: {
    ...diffBadgeBase,
    opacity: 0.6,
  },
};

function DiffBadge({
  kind,
  changes,
}: {
  kind: "added" | "removed" | "changed" | "unchanged";
  changes: string[];
}) {
  if (kind === "unchanged") return null;
  const label =
    kind === "added"
      ? "new"
      : kind === "removed"
        ? "gone"
        : `Δ ${changes.join(", ")}`;
  return <span style={diffKindStyle[kind]}>{label}</span>;
}

function DiffView({
  current,
  previous,
  deltaByKey,
  visited,
  onVisit,
  companyPrefix,
}: {
  current: MergeBlock[];
  previous: MergeBlock[];
  deltaByKey: Map<string, BlockDelta>;
  visited: Set<string>;
  onVisit: (diffKey: string) => void;
  companyPrefix: string | null;
}) {
  if (previous.length === 0) {
    return (
      <div style={mutedTextStyle}>
        No previous scan to compare against. Run another scan to see the
        diff.
      </div>
    );
  }
  const diffs = diffBlocks(previous, current);
  const diffByKey = new Map(diffs.map((d) => [d.diffKey, d]));
  const ordered = [
    ...current.map((b) => ({ kind: "current" as const, block: b })),
    ...previous
      .filter((b) => !current.some((c) => c.diffKey === b.diffKey))
      .map((b) => ({ kind: "previous" as const, block: b })),
  ];
  return (
    <div style={{ display: "grid", gap: "8px" }}>
      <div style={{ ...mutedTextStyle, fontSize: "11px" }}>
        Comparing against {previous.length} block
        {previous.length === 1 ? "" : "s"} from the previous scan.
      </div>
      {ordered.map(({ kind, block }) => {
        const diff = diffByKey.get(block.diffKey);
        const diffKind = diff?.kind ?? "unchanged";
        const changes = diff?.changes ?? [];
        const badge = (
          <DiffBadge
            kind={kind === "previous" ? "removed" : diffKind}
            changes={changes}
          />
        );
        // For "removed" rows (block only in previous), the card body would
        // show no current values; suppress delta rendering in that case so
        // the user doesn't see confusing "+0 passed" math.
        const delta =
          kind === "previous" ? null : (deltaByKey.get(block.diffKey) ?? null);
        // Marker only on current rows — a removed block can't have been
        // visited during the current scan (it wasn't in the scan).
        const isVisited =
          kind === "current" ? visited.has(block.diffKey) : false;
        return (
          <MergeBlockCard
            key={`${kind}-${block.issueUuid}`}
            block={block}
            companyPrefix={companyPrefix}
            diffBadge={badge}
            delta={delta}
            isVisited={isVisited}
            onVisit={onVisit}
          />
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Blocked Chain view — one card per connected chain in the issue_relations
// graph, with hierarchy rendered via indentation. Leaves (issues nothing
// blocks in this chain — resolving them unblocks downstream) are surfaced
// first and highlighted with the "needs attention" rose pill.
// ---------------------------------------------------------------------------

function statusPillStyleFor(status: string): CSSProperties {
  // Color-code by status so "todo", "in_progress", "done", "cancelled"
  // are visually distinct.
  if (status === "done") {
    return {
      ...pillStyle,
      borderColor: "color-mix(in srgb, #16a34a 60%, var(--border))",
      background: "color-mix(in srgb, #16a34a 14%, transparent)",
      color: "#86efac",
    };
  }
  if (status === "cancelled") {
    return {
      ...pillStyle,
      borderColor: "color-mix(in srgb, #6b7280 60%, var(--border))",
      background: "color-mix(in srgb, #6b7280 14%, transparent)",
      color: "#9ca3af",
    };
  }
  if (status === "in_progress" || status === "in_review") {
    return {
      ...pillStyle,
      borderColor: "color-mix(in srgb, #d97706 60%, var(--border))",
      background: "color-mix(in srgb, #d97706 14%, transparent)",
      color: "#fcd34d",
    };
  }
  // default: blocked / todo / etc.
  return {
    ...pillStyle,
    borderColor: "color-mix(in srgb, #dc2626 60%, var(--border))",
    background: "color-mix(in srgb, #dc2626 14%, transparent)",
    color: "#fca5a5",
  };
}

function IssueLink({
  node,
  companyPrefix,
  visited,
  onVisit,
}: {
  node: ChainNode;
  companyPrefix: string | null;
  visited: boolean;
  onVisit: (diffKey: string) => void;
}) {
  const hostNavigation = useHostNavigation();
  const issueHref =
    companyPrefix && node.identifier
      ? `/${companyPrefix}/issues/${node.identifier}`
      : null;
  const props = issueHref ? hostNavigation.linkProps(issueHref) : null;
  const handleClick: React.MouseEventHandler<HTMLAnchorElement> = (e) => {
    onVisit(node.uuid);
    if (props) props.onClick(e);
  };
  return (
    <span style={{ display: "inline-flex", gap: "6px", alignItems: "center" }}>
      {node.identifier && props ? (
        <a
          {...props}
          target="_blank"
          rel="noreferrer"
          onClick={handleClick}
          style={inlineLinkStyle}
          title={`Open ${node.identifier} in Paperclip`}
        >
          {node.identifier}
        </a>
      ) : node.identifier ? (
        <span style={inlineLinkStyle}>{node.identifier}</span>
      ) : (
        <span style={{ ...mutedTextStyle, fontSize: "10px" }}>
          {node.uuid.slice(0, 8)}…
        </span>
      )}
      {visited ? (
        <span style={visitedPillStyle} title="You opened this since the last scan">
          ✓ checked
        </span>
      ) : null}
    </span>
  );
}

function ChainNodeRow({
  node,
  depth,
  isActionable,
  isLeaf,
  visited,
  onVisit,
  companyPrefix,
}: {
  node: ChainNode;
  depth: number;
  isActionable: boolean;
  isLeaf: boolean;
  visited: boolean;
  onVisit: (diffKey: string) => void;
  companyPrefix: string | null;
}) {
  const indent = depth * 18;
  return (
    <div
      style={{
        display: "grid",
        gap: "4px",
        paddingLeft: `${indent}px`,
        borderLeft: depth > 0 ? "1px dashed var(--border)" : "none",
        marginLeft: depth > 0 ? "8px" : "0",
        paddingTop: "6px",
        paddingBottom: "6px",
      }}
    >
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
        <IssueLink
          node={node}
          companyPrefix={companyPrefix}
          visited={visited}
          onVisit={onVisit}
        />
        <span style={statusPillStyleFor(node.status)}>{node.status}</span>
        {node.priority ? (
          <span style={pillStyle}>{node.priority}</span>
        ) : null}
        {isLeaf && isActionable ? (
          <span style={chainActionablePillStyle} title="Nothing blocks this issue in this chain — resolving it unblocks the whole chain">
            ⚡ needs attention
          </span>
        ) : isLeaf ? (
          <span style={chainLeafPillStyle}>leaf</span>
        ) : null}
      </div>
      <div style={{ ...mutedTextStyle, fontSize: "11px" }}>
        {node.title.length > 120 ? node.title.slice(0, 120) + "…" : node.title}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", alignItems: "center", fontSize: "10px" }}>
        <span style={chainMetaPillStyle}>depth {node.depth}</span>
        {node.blockedBy.length > 0 ? (
          <span style={chainMetaPillStyle}>blocked by {node.blockedBy.length}</span>
        ) : null}
        {node.blocks.length > 0 ? (
          <span style={chainMetaPillStyle}>blocks {node.blocks.length} downstream</span>
        ) : null}
        {node.downstreamCount > 0 ? (
          <span style={chainUnblocksPillStyle}>
            resolving unblocks {node.downstreamCount}
          </span>
        ) : null}
      </div>
    </div>
  );
}

const chainActionablePillStyle: CSSProperties = {
  fontSize: "10px",
  padding: "1px 8px",
  borderRadius: "999px",
  border: "1px solid color-mix(in srgb, #f43f5e 60%, var(--border))",
  background: "color-mix(in srgb, #f43f5e 14%, transparent)",
  color: "#fda4af",
  fontWeight: 600,
};

const chainLeafPillStyle: CSSProperties = {
  fontSize: "10px",
  padding: "1px 8px",
  borderRadius: "999px",
  border: "1px solid color-mix(in srgb, #6b7280 60%, var(--border))",
  background: "color-mix(in srgb, #6b7280 14%, transparent)",
  color: "#9ca3af",
};

const chainMetaPillStyle: CSSProperties = {
  fontSize: "10px",
  padding: "1px 7px",
  borderRadius: "999px",
  border: "1px solid var(--border)",
  background: "color-mix(in srgb, var(--muted, #888) 14%, transparent)",
};

const chainUnblocksPillStyle: CSSProperties = {
  fontSize: "10px",
  padding: "1px 7px",
  borderRadius: "999px",
  border: "1px solid color-mix(in srgb, #16a34a 60%, var(--border))",
  background: "color-mix(in srgb, #16a34a 14%, transparent)",
  color: "#86efac",
  fontWeight: 500,
};

const chainCardStyle: CSSProperties = {
  border: "1px solid var(--border)",
  borderRadius: "10px",
  padding: "12px",
  display: "grid",
  gap: "8px",
  background: "color-mix(in srgb, var(--card, transparent) 50%, transparent)",
};

const chainCardActionableStyle: CSSProperties = {
  ...chainCardStyle,
  borderColor: "color-mix(in srgb, #f43f5e 60%, var(--border))",
};

function BlockedChainCard({
  chain,
  visited,
  onVisit,
  companyPrefix,
}: {
  chain: BlockedChain;
  visited: Set<string>;
  onVisit: (diffKey: string) => void;
  companyPrefix: string | null;
}) {
  // Decide "actionable": chain has at least one leaf that isn't done/cancelled.
  const actionableLeaves = chain.leafIds.filter((uuid) => {
    const n = chain.nodes[uuid];
    if (!n) return false;
    return n.status !== "done" && n.status !== "cancelled";
  });
  const isActionable = actionableLeaves.length > 0;
  // Sort nodes by (depth ASC, is_leaf DESC, title) so leaves surface first.
  const sortedNodes = Object.values(chain.nodes).sort((a, b) => {
    if (a.depth !== b.depth) return a.depth - b.depth;
    if (a.isLeaf !== b.isLeaf) return a.isLeaf ? -1 : 1;
    return (a.title || "").localeCompare(b.title || "");
  });
  return (
    <div style={isActionable ? chainCardActionableStyle : chainCardStyle}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
        <strong style={{ fontSize: "13px" }}>{chain.id}</strong>
        <span style={chainMetaPillStyle}>
          {chain.nodeCount} issue{chain.nodeCount === 1 ? "" : "s"}
        </span>
        {chain.leafIds.length > 0 ? (
          <span style={chainMetaPillStyle}>
            {chain.leafIds.length} actionable leaf{chain.leafIds.length === 1 ? "" : "s"}
          </span>
        ) : null}
        {isActionable ? (
          <span style={chainActionablePillStyle}>⚡ needs attention</span>
        ) : null}
      </div>
      <div style={{ display: "grid", gap: "4px" }}>
        {sortedNodes.map((node) => (
          <ChainNodeRow
            key={node.uuid}
            node={node}
            depth={node.depth}
            isActionable={
              isActionable && node.isLeaf && actionableLeaves.includes(node.uuid)
            }
            isLeaf={node.isLeaf}
            visited={visited.has(node.uuid)}
            onVisit={onVisit}
            companyPrefix={companyPrefix}
          />
        ))}
      </div>
    </div>
  );
}

function BlockedChainsView({
  chains,
  visited,
  onVisit,
  companyPrefix,
}: {
  chains: BlockedChain[];
  visited: Set<string>;
  onVisit: (diffKey: string) => void;
  companyPrefix: string | null;
}) {
  if (chains.length === 0) {
    return (
      <div style={mutedTextStyle}>
        No blocked-issue chains. Run a scan to populate.
      </div>
    );
  }
  // Surface actionable chains first (smallest leaf count first = most
  // targeted), then by node count ascending.
  const sorted = [...chains].sort((a, b) => {
    const aLeaves = a.leafIds.filter((u) => {
      const n = a.nodes[u];
      return n && n.status !== "done" && n.status !== "cancelled";
    }).length;
    const bLeaves = b.leafIds.filter((u) => {
      const n = b.nodes[u];
      return n && n.status !== "done" && n.status !== "cancelled";
    }).length;
    if (aLeaves !== bLeaves) return aLeaves - bLeaves;
    return a.nodeCount - b.nodeCount;
  });
  return (
    <div style={{ display: "grid", gap: "8px" }}>
      <div style={{ ...mutedTextStyle, fontSize: "11px" }}>
        {chains.length} chain{chains.length === 1 ? "" : "s"} — actionable
        (smallest actionable leaf count first). Click any identifier to
        open the issue in a new tab; it is also marked ✓ checked.
      </div>
      {sorted.map((chain) => (
        <BlockedChainCard
          key={chain.id}
          chain={chain}
          visited={visited}
          onVisit={onVisit}
          companyPrefix={companyPrefix}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Awaiting Approval view — pending board-approval requests, with chain
// cross-reference so the operator can see which approvals would unblock
// downstream work.
// ---------------------------------------------------------------------------

function AwaitingApprovalView({
  approvals,
  approvalChainLookup,
  visited,
  onVisit,
  companyPrefix,
}: {
  approvals: ApprovalRequest[];
  approvalChainLookup: Record<string, { chainId: string; node: ChainNode }>;
  visited: Set<string>;
  onVisit: (diffKey: string) => void;
  companyPrefix: string | null;
}) {
  if (approvals.length === 0) {
    return (
      <div style={mutedTextStyle}>
        No pending board-approval requests. The agent will surface any
        new ones on the next scan.
      </div>
    );
  }
  return (
    <div style={{ display: "grid", gap: "8px" }}>
      <div style={{ ...mutedTextStyle, fontSize: "11px" }}>
        {approvals.length} pending request_confirmation interaction
        {approvals.length === 1 ? "" : "s"}, ordered by unblocks-count DESC
        then newest. Click an identifier to open the issue in a new tab.
      </div>
      {approvals.map((a) => (
        <ApprovalCard
          key={a.interactionId || `${a.issueId}-${a.kind}`}
          approval={a}
          chain={a.issueId ? approvalChainLookup[a.issueId] : undefined}
          visited={a.issueId ? visited.has(a.issueId) : false}
          onVisit={onVisit}
          companyPrefix={companyPrefix}
        />
      ))}
    </div>
  );
}

function ApprovalCard({
  approval,
  chain,
  visited,
  onVisit,
  companyPrefix,
}: {
  approval: ApprovalRequest;
  chain?: { chainId: string; node: ChainNode };
  visited: boolean;
  onVisit: (diffKey: string) => void;
  companyPrefix: string | null;
}) {
  const isHighImpact = approval.unblocksCount > 0;
  return (
    <div style={isHighImpact ? chainCardActionableStyle : chainCardStyle}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
        <IssueLink
          node={{
            uuid: approval.issueId,
            identifier: approval.issueIdentifier,
            title: approval.issueTitle,
            status: approval.issueStatus,
            priority: approval.issuePriority,
            labels: [],
            depth: chain?.node.depth ?? 0,
            isLeaf: chain?.node.isLeaf ?? false,
            isRoot: chain?.node.isRoot ?? false,
            blockedBy: chain?.node.blockedBy ?? [],
            blocks: chain?.node.blocks ?? [],
            downstreamCount: chain?.node.downstreamCount ?? 0,
          }}
          companyPrefix={companyPrefix}
          visited={visited}
          onVisit={onVisit}
        />
        <span style={statusPillStyleFor(approval.issueStatus)}>
          {approval.issueStatus}
        </span>
        {approval.issuePriority ? (
          <span style={pillStyle}>{approval.issuePriority}</span>
        ) : null}
        <span style={pillStyle}>request_confirmation</span>
        {chain ? (
          <span style={chainMetaPillStyle}>chain {chain.chainId}</span>
        ) : null}
        {approval.unblocksCount > 0 ? (
          <span style={chainUnblocksPillStyle}>
            ⚡ unblocks {approval.unblocksCount}
          </span>
        ) : null}
      </div>
      <div style={{ ...mutedTextStyle, fontSize: "11px" }}>
        <strong style={{ color: "inherit" }}>{approval.title || "(no request title)"}</strong>
      </div>
      {approval.body ? (
        <pre style={outputStyle}>{approval.body.slice(0, 800)}</pre>
      ) : null}
      <div style={{ ...mutedTextStyle, fontSize: "10px" }}>
        requested {approval.createdAt || "—"}
        {approval.createdBy ? ` by ${approval.createdBy.slice(0, 8)}…` : ""}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Raw view — full text + copy.
// ---------------------------------------------------------------------------

function RawView({ stdout, stderr }: { stdout: string; stderr: string }) {
  return (
    <div style={{ display: "grid", gap: "8px" }}>
      <div style={rowStyle}>
        <CopyButton value={stdout} label="Copy output" />
        {stderr ? <CopyButton value={stderr} label="Copy stderr" /> : null}
        <span style={mutedTextStyle}>
          {stdout.length} chars stdout
          {stderr ? ` · ${stderr.length} chars stderr` : ""}
        </span>
      </div>
      <pre style={outputStyle} aria-live="polite">
        {stdout || "(empty)"}
      </pre>
      {stderr ? <pre style={stderrBlockStyle}>{stderr}</pre> : null}
    </div>
  );
}

const indeterminateKeyframes = `
@keyframes paperclip-git-merges-indeterminate {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(350%); }
}
`;

// ---------------------------------------------------------------------------
// Settings page — full editor for the persisted instance config
// ---------------------------------------------------------------------------

export function GitMergesSettingsPage(_props: PluginSettingsPageProps) {
  const toast = usePluginToast();
  const snapshotQuery = usePluginData<MergeQueueSnapshot>(DATA_KEYS.snapshot);
  const saveAction = usePluginAction(ACTION_KEYS.saveConfig);
  const config = snapshotQuery.data?.config ?? { ...DEFAULT_CONFIG };

  const [pythonPath, setPythonPath] = useState(config.pythonPath);
  const [repoPath, setRepoPath] = useState(config.repoPath);
  const [scriptPath, setScriptPath] = useState(config.scriptPath);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(
    config.autoRefreshEnabled,
  );
  const [intervalSeconds, setIntervalSeconds] = useState(
    config.autoRefreshIntervalSeconds,
  );
  const [timeBlockEnabled, setTimeBlockEnabled] = useState(
    config.timeBlockEnabled,
  );
  const [startHour, setStartHour] = useState(config.timeBlockStartHour);
  const [endHour, setEndHour] = useState(config.timeBlockEndHour);
  const [showJson, setShowJson] = useState(config.showJson);
  const [maxOutputChars, setMaxOutputChars] = useState(config.maxOutputChars);
  const [scanTimeoutSeconds, setScanTimeoutSeconds] = useState(
    config.scanTimeoutSeconds,
  );
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!snapshotQuery.data) return;
    const c = snapshotQuery.data.config;
    setPythonPath(c.pythonPath);
    setRepoPath(c.repoPath);
    setScriptPath(c.scriptPath);
    setAutoRefreshEnabled(c.autoRefreshEnabled);
    setIntervalSeconds(c.autoRefreshIntervalSeconds);
    setTimeBlockEnabled(c.timeBlockEnabled);
    setStartHour(c.timeBlockStartHour);
    setEndHour(c.timeBlockEndHour);
    setShowJson(c.showJson);
    setMaxOutputChars(c.maxOutputChars);
    setScanTimeoutSeconds(c.scanTimeoutSeconds);
  }, [snapshotQuery.data]);

  const next: GitMergesConfig = {
    pythonPath: pythonPath.trim(),
    repoPath: repoPath.trim(),
    scriptPath: scriptPath.trim() || DEFAULT_CONFIG.scriptPath,
    autoRefreshEnabled,
    autoRefreshIntervalSeconds: Math.max(30, Math.min(86_400, intervalSeconds)),
    timeBlockEnabled,
    timeBlockStartHour: Math.max(0, Math.min(23, startHour)),
    timeBlockEndHour: Math.max(0, Math.min(23, endHour)),
    showJson,
    maxOutputChars: Math.max(1000, Math.min(5_000_000, maxOutputChars)),
    scanTimeoutSeconds: Math.max(10, Math.min(3600, scanTimeoutSeconds)),
    // BTCAAAAA-39051: new fields. The settings UI doesn't yet expose
    // controls for these (that lands in the follow-up commit); the
    // DEFAULT_CONFIG values are sent on save.
    stuckThresholdHours: DEFAULT_CONFIG.stuckThresholdHours,
    etaHistorySize: DEFAULT_CONFIG.etaHistorySize,
    runningRefreshIntervalSeconds: DEFAULT_CONFIG.runningRefreshIntervalSeconds,
  };

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await saveAction(next as unknown as Record<string, unknown>);
      await snapshotQuery.refresh();
      toast({ title: "Git Merges settings saved", tone: "success" });
    } catch (err) {
      toast({
        title: "Could not save settings",
        body: getErrorMessage(err),
        tone: "error",
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={onSubmit} style={{ display: "grid", gap: "18px" }}>
      <div style={{ display: "grid", gap: "8px" }}>
        <strong style={{ fontSize: "14px" }}>About</strong>
        <p style={mutedTextStyle}>
          Git Merges runs{" "}
          <code style={codeInlineStyle}>scripts/merge_queue_status.py</code>{" "}
          from the BTC-Trade-Engine-PaperClip repo and renders the output
          here. The script reads <code style={codeInlineStyle}>.env</code>{" "}
          from the repo root for Paperclip and GitHub credentials, so make
          sure those are present on the host that runs the plugin worker.
        </p>
      </div>

      <fieldset style={subtleCardStyle}>
        <legend style={{ fontSize: "12px", opacity: 0.7, padding: "0 6px" }}>
          Script location
        </legend>
        <label style={fieldLabelStyle}>
          <span style={mutedTextStyle}>Python interpreter (absolute path)</span>
          <input
            style={inputStyle}
            value={pythonPath}
            onChange={(event) => setPythonPath(event.target.value)}
            spellCheck={false}
          />
        </label>
        <label style={fieldLabelStyle}>
          <span style={mutedTextStyle}>BTC repo path (working directory)</span>
          <input
            style={inputStyle}
            value={repoPath}
            onChange={(event) => setRepoPath(event.target.value)}
            spellCheck={false}
          />
        </label>
        <label style={fieldLabelStyle}>
          <span style={mutedTextStyle}>
            Script path (relative to repo path)
          </span>
          <input
            style={inputStyle}
            value={scriptPath}
            onChange={(event) => setScriptPath(event.target.value)}
            spellCheck={false}
          />
        </label>
      </fieldset>

      <fieldset style={subtleCardStyle}>
        <legend style={{ fontSize: "12px", opacity: 0.7, padding: "0 6px" }}>
          Auto-refresh
        </legend>
        <label style={{ ...rowStyle, fontSize: "12px", gap: "6px" }}>
          <input
            type="checkbox"
            checked={autoRefreshEnabled}
            onChange={(event) => setAutoRefreshEnabled(event.target.checked)}
          />
          <span>Enable auto-refresh</span>
        </label>
        <label style={fieldLabelStyle}>
          <span style={mutedTextStyle}>Interval (seconds, 30 – 86400)</span>
          <input
            style={inputStyle}
            type="number"
            min={30}
            max={86_400}
            value={intervalSeconds}
            onChange={(event) =>
              setIntervalSeconds(Number(event.target.value) || 0)
            }
          />
        </label>
      </fieldset>

      <fieldset style={subtleCardStyle}>
        <legend style={{ fontSize: "12px", opacity: 0.7, padding: "0 6px" }}>
          Time block (local time)
        </legend>
        <label style={{ ...rowStyle, fontSize: "12px", gap: "6px" }}>
          <input
            type="checkbox"
            checked={timeBlockEnabled}
            onChange={(event) => setTimeBlockEnabled(event.target.checked)}
          />
          <span>Only auto-refresh inside the time block below</span>
        </label>
        <div style={rowStyle}>
          <label style={fieldLabelStyle}>
            <span style={mutedTextStyle}>Start hour (0–23)</span>
            <input
              style={inputStyle}
              type="number"
              min={0}
              max={23}
              value={startHour}
              onChange={(event) =>
                setStartHour(Number(event.target.value) || 0)
              }
            />
          </label>
          <label style={fieldLabelStyle}>
            <span style={mutedTextStyle}>End hour (0–23, exclusive)</span>
            <input
              style={inputStyle}
              type="number"
              min={0}
              max={23}
              value={endHour}
              onChange={(event) => setEndHour(Number(event.target.value) || 0)}
            />
          </label>
        </div>
      </fieldset>

      <fieldset style={subtleCardStyle}>
        <legend style={{ fontSize: "12px", opacity: 0.7, padding: "0 6px" }}>
          Capture
        </legend>
        <label style={{ ...rowStyle, fontSize: "12px", gap: "6px" }}>
          <input
            type="checkbox"
            checked={showJson}
            onChange={(event) => setShowJson(event.target.checked)}
          />
          <span>Pass --json to the script (machine-readable output)</span>
        </label>
        <label style={fieldLabelStyle}>
          <span style={mutedTextStyle}>
            Max output characters kept per scan (stdout)
          </span>
          <input
            style={inputStyle}
            type="number"
            min={1000}
            max={5_000_000}
            value={maxOutputChars}
            onChange={(event) =>
              setMaxOutputChars(Number(event.target.value) || 0)
            }
          />
        </label>
        <label style={fieldLabelStyle}>
          <span style={mutedTextStyle}>Per-scan soft timeout (seconds)</span>
          <input
            style={inputStyle}
            type="number"
            min={10}
            max={3600}
            value={scanTimeoutSeconds}
            onChange={(event) =>
              setScanTimeoutSeconds(Number(event.target.value) || 0)
            }
          />
        </label>
      </fieldset>

      <div style={rowStyle}>
        <button type="submit" style={primaryButtonStyle} disabled={saving}>
          {saving ? "Saving…" : "Save settings"}
        </button>
        <span style={mutedTextStyle}>
          Changes apply on the next auto-scan tick or the next "Run scan now".
        </span>
      </div>
    </form>
  );
}

// `useCallback` is part of the React hook contract surface; import it
// so it stays in our dependency graph even though the current UI doesn't
// directly use it. (Future expansion: memoised event handlers.)
const _keepUseCallbackImport = useCallback;
void _keepUseCallbackImport;

// Re-export utilities used elsewhere.
export { coerceConfig as _coerceConfigForTests };
export function cloneDefaultConfig(): GitMergesConfig {
  return { ...DEFAULT_CONFIG };
}

// TS-reserved type re-export to silence the unused-import warning for
// ReactNode on builds that strip types.
export type { ReactNode };
