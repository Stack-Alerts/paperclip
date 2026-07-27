// src/ui/index.tsx — paperclip-backup plugin UI
//
// Exports the 4 named components referenced by src/manifest.ts:
//   - BackupSidebarNav      → sidebar nav entry
//   - BackupDashboardWidget → at-a-glance status widget
//   - BackupManagerPage     → main backup manager page (with cleanup tab)
//   - BackupSettingsPage    → settings page
//
// The cleanup tab is the GDrive cleanup panel: a comprehensive view
// of every backup leaf on gdrive, with per-leaf "golden" flags, bulk
// mark/unmark, and a safe multi-tier cleanup-stale action. All
// destructive operations go through a preview-then-confirm flow with
// explicit safety flags required for any production scope.

import {
  useHostContext,
  useHostLocation,
  useHostNavigation,
  usePluginAction,
  usePluginData,
  type PluginDataResult,
} from "@paperclipai/plugin-sdk/ui";
import { useEffect, useMemo, useState } from "react";

// ---------------------------------------------------------------------------
// Shared formatters + helpers
// ---------------------------------------------------------------------------

function formatBytes(bytes: number): string {
  if (!bytes || bytes <= 0) return "0 B";
  const units = ["B", "KiB", "MiB", "GiB", "TiB"];
  let v = bytes;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v.toFixed(v >= 100 ? 0 : 1)} ${units[i]}`;
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return String(iso);
    return d.toISOString().replace("T", " ").replace(/\..+/, " UTC");
  } catch {
    return String(iso);
  }
}

function StatusDot({ ok }: { ok: boolean }) {
  const color = ok ? "var(--success, #16a34a)" : "var(--destructive, #dc2626)";
  return (
    <span
      aria-hidden="true"
      style={{
        display: "inline-block",
        width: 10,
        height: 10,
        borderRadius: "50%",
        background: color,
        marginRight: 6,
        verticalAlign: "middle",
      }}
    />
  );
}

function ActionButton(props: {
  label: string;
  busy?: boolean;
  onClick: () => void;
  variant?: "primary" | "danger" | "default";
  hint?: string;
  elapsedMs?: number;
  disabled?: boolean;
}) {
  const variant = props.variant ?? "primary";
  const isPrimary = variant === "primary";
  const isDanger = variant === "danger";
  const baseStyle: React.CSSProperties = {
    padding: "8px 14px",
    borderRadius: 6,
    fontWeight: 500,
    fontSize: 13,
    cursor: props.busy || props.disabled ? "not-allowed" : "pointer",
    opacity: props.busy || props.disabled ? 0.6 : 1,
    border: "1px solid transparent",
    background: isPrimary ? "#1e40af" : isDanger ? "#b91c1c" : "#374151",
    color: "#f8fafc",
    borderColor: isDanger ? "#991b1b" : "transparent",
  };
  const elapsed =
    props.busy && props.elapsedMs != null
      ? ` (${Math.floor(props.elapsedMs / 1000)}s)`
      : "";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <button
        type="button"
        onClick={props.onClick}
        disabled={props.busy || props.disabled}
        style={baseStyle}
      >
        {props.busy ? `Working…${elapsed}` : props.label}
      </button>
      {props.hint ? (
        <span style={{ fontSize: 11, color: "var(--muted-foreground, #6b7280)" }}>
          {props.hint}
        </span>
      ) : null}
    </div>
  );
}

function useElapsedMs(running: boolean | string | null): number {
  const [start, setStart] = useState<number | null>(null);
  const [now, setNow] = useState(0);
  useEffect(() => {
    if (running) {
      const s = Date.now();
      setStart(s);
      const t = setInterval(() => setNow(Date.now() - s), 250);
      return () => {
        clearInterval(t);
        setStart(null);
      };
    }
    return undefined;
  }, [running]);
  return start != null ? now : 0;
}

function errorMessage(err: unknown): string {
  if (err == null) return "Unknown error";
  if (typeof err === "string") return err;
  if (err instanceof Error) return err.message;
  if (typeof err === "object") {
    const obj = err as { message?: string; details?: unknown; code?: string };
    if (typeof obj.message === "string" && obj.message.length > 0) {
      const detail = obj.details;
      if (detail && typeof detail === "object") {
        const detailMsg = (detail as { message?: string }).message;
        if (
          typeof detailMsg === "string" &&
          detailMsg.length > 0 &&
          detailMsg !== obj.message
        ) {
          return `${obj.message} — ${detailMsg}`;
        }
      }
      return obj.message;
    }
    if (typeof obj.code === "string") return obj.code;
    try {
      return JSON.stringify(err);
    } catch {
      return String(err);
    }
  }
  return String(err);
}

function ResultBanner({
  result,
  onDismiss,
}: {
  result: {
    ok: boolean;
    message?: string;
    keep?: number;
    remotePath?: string;
    destDir?: string;
    totalBytesBefore?: number;
    totalBytesAfter?: number;
    prunedCount?: number;
    stdout?: string;
    stderr?: string;
  } | null;
  onDismiss: () => void;
}) {
  if (!result) return null;
  const isOk = result.ok;
  return (
    <div
      role="status"
      style={{
        padding: 12,
        borderRadius: 6,
        border: `1px solid ${isOk ? "var(--success, #16a34a)" : "var(--destructive, #dc2626)"}`,
        background: isOk
          ? "color-mix(in oklab, var(--success) 8%, var(--card))"
          : "color-mix(in oklab, var(--destructive) 8%, var(--card))",
        color: isOk ? "var(--success, #16a34a)" : "var(--destructive, #dc2626)",
        display: "grid",
        gap: 6,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 8,
        }}
      >
        <strong style={{ fontSize: 13 }}>{result.message ?? (isOk ? "Success" : "Failed")}</strong>
        <button
          type="button"
          onClick={onDismiss}
          style={{
            background: "transparent",
            border: "none",
            color: "inherit",
            cursor: "pointer",
            fontSize: 16,
            lineHeight: 1,
          }}
          aria-label="Dismiss"
        >
          ×
        </button>
      </div>
      {result.keep != null ? (
        <div style={{ fontSize: 12 }}>keep = {result.keep}</div>
      ) : null}
      {result.remotePath ? (
        <div style={{ fontSize: 12, fontFamily: "ui-monospace, monospace" }}>
          {result.remotePath} → {result.destDir ?? "(default)"}
        </div>
      ) : null}
      {result.totalBytesBefore != null && result.totalBytesAfter != null ? (
        <div style={{ fontSize: 12 }}>
          {formatBytes(result.totalBytesBefore)} → {formatBytes(result.totalBytesAfter)} (
          {result.prunedCount ?? 0} pruned)
        </div>
      ) : null}
      {result.stdout ? (
        <details>
          <summary style={{ fontSize: 12, cursor: "pointer" }}>stdout</summary>
          <pre
            style={{
              fontSize: 11,
              maxHeight: 160,
              overflow: "auto",
              background: "var(--muted, #f3f4f6)",
              padding: 8,
              borderRadius: 4,
              marginTop: 4,
            }}
          >
            {result.stdout}
          </pre>
        </details>
      ) : null}
      {result.stderr ? (
        <details>
          <summary style={{ fontSize: 12, cursor: "pointer" }}>stderr</summary>
          <pre
            style={{
              fontSize: 11,
              maxHeight: 160,
              overflow: "auto",
              background: "var(--muted, #f3f4f6)",
              padding: 8,
              borderRadius: 4,
              marginTop: 4,
            }}
          >
            {result.stderr}
          </pre>
        </details>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sidebar nav
// ---------------------------------------------------------------------------

export function BackupSidebarNav({ context }: { context: { companyPrefix?: string | null } }) {
  const host = useHostContext();
  const hostNavigation = useHostNavigation();
  const hostLocation = useHostLocation();
  const companyPrefix = context.companyPrefix ?? host.companyPrefix;
  const href = companyPrefix ? `/${companyPrefix}/backups` : "/backups";
  const isActive =
    hostLocation.pathname === href || hostLocation.pathname.startsWith(`${href}/`);
  return (
    <a
      {...hostNavigation.linkProps(href)}
      className={
        "flex items-center gap-2.5 px-3 py-2 pointer-coarse:py-1.5 text-[13px] font-medium transition-colors " +
        (isActive
          ? "bg-accent text-foreground"
          : "text-foreground/80 hover:bg-accent/50 hover:text-foreground")
      }
      style={{ textDecoration: "none" }}
    >
      <svg
        viewBox="0 0 24 24"
        className="shrink-0 h-4 w-4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <ellipse cx="12" cy="5" rx="9" ry="3" fill="currentColor" fillOpacity="0.18" />
        <path d="M3 5v14a9 3 0 0 0 18 0V5" />
        <path
          d="M3 12a9 3 0 0 0 18 0"
          fill="currentColor"
          fillOpacity="0.18"
        />
      </svg>
      <span className="flex-1 truncate">Backups</span>
    </a>
  );
}

// ---------------------------------------------------------------------------
// Dashboard widget
// ---------------------------------------------------------------------------

type BackupStatus = {
  backupRunning?: { pid: number; startedAt: string; recovery?: boolean; isForced?: boolean } | null;
  backupLastRun?: { ok: boolean; message: string; at: string } | null;
  local?: { count: number; totalBytes: number; newest: { mtime: string } | null };
  offsite?: { count: number; newest: { mtime: string } | null };
  missingCompanyId?: boolean;
};

export function BackupDashboardWidget({
  context,
}: {
  context: { companyId?: string | null };
}) {
  const host = useHostContext();
  const companyId = context.companyId ?? host.companyId ?? null;
  const runBackup = usePluginAction("run-backup");
  const [refreshTick, setRefreshTick] = useState(0);
  const [result, setResult] = useState<{
    ok: boolean;
    message: string;
    async?: boolean;
    pid?: number;
    exitCode?: number | null;
    durationMs?: number;
    stdout?: string;
    stderr?: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const elapsedMs = useElapsedMs(busy);
  const statusResult = usePluginData("status", { companyId, _tick: refreshTick }) as
    | PluginDataResult<BackupStatus>
    | undefined;
  const status = statusResult?.data;
  const error = statusResult?.error ? String(statusResult.error) : null;
  const running = status?.backupRunning ?? null;
  const runningElapsedMs = running
    ? Date.now() - new Date(running.startedAt).getTime()
    : 0;
  const isBusy = busy || running != null;
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setRefreshTick((n) => n + 1), 30_000);
    return () => clearInterval(t);
  }, [running?.pid, running?.startedAt]);

  const triggerBackup = async () => {
    if (busy || running) return;
    setBusy(true);
    setResult(null);
    try {
      const r = (await runBackup({ companyId })) as {
        alreadyRunning?: boolean;
        async?: boolean;
        pid?: number;
        ok?: boolean;
        message?: string;
        exitCode?: number | null;
        durationMs?: number;
        stdout?: string;
        stderr?: string;
      };
      if (r.alreadyRunning) {
        setResult({ ok: false, message: r.message ?? "Backup already running" });
      } else if (r.async || r.pid) {
        setResult({ ok: true, message: r.message ?? `Backup started (pid=${r.pid})` });
      } else {
        setResult({
          ok: r.ok === true,
          exitCode: r.exitCode ?? null,
          message:
            r.message ?? (r.ok === true ? "Backup pushed to offsite" : "Backup script failed"),
          durationMs: r.durationMs,
          stdout: r.stdout,
          stderr: r.stderr,
        });
      }
    } catch (err) {
      setResult({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(false);
      setRefreshTick((n) => n + 1);
    }
  };

  const newest = status?.offsite?.newest ?? null;
  const isOk = !error;
  let subtitle = error
    ? error
    : status?.missingCompanyId
    ? "No active company."
    : "Backup service health is good.";
  if (running) {
    const started = new Date(running.startedAt).toLocaleString();
    const mins = Math.floor(runningElapsedMs / 60_000);
    subtitle = `Backup in progress (pid=${running.pid}, started ${started}, ${mins}m elapsed)`;
  } else if (status?.backupLastRun) {
    const last = status.backupLastRun;
    const okLabel = last.ok ? "ok" : "failed";
    subtitle = `Last backup: ${okLabel} — ${last.message}`;
  }
  return (
    <section aria-label="Backup status" style={{ display: "grid", gap: 12 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>
            <StatusDot ok={isOk && !running} />
            Backup status
          </h3>
          <div style={{ fontSize: 12, color: "var(--muted-foreground, #6b7280)" }}>{subtitle}</div>
        </div>
        <ActionButton
          label={running ? "Backup running…" : "Run backup now"}
          busy={isBusy}
          onClick={triggerBackup}
          elapsedMs={running ? runningElapsedMs : elapsedMs}
          disabled={running != null}
        />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div
          style={{
            padding: 12,
            border: "1px solid var(--border, #e5e7eb)",
            borderRadius: 6,
          }}
        >
          <div style={{ fontSize: 12, color: "var(--muted-foreground, #6b7280)" }}>
            Local DB dumps
          </div>
          <div style={{ fontSize: 22, fontWeight: 600 }}>{status?.local?.count ?? "—"}</div>
          <div style={{ fontSize: 12, color: "var(--muted-foreground, #6b7280)" }}>
            {status?.local ? formatBytes(status.local.totalBytes) : "—"} total
          </div>
        </div>
        <div
          style={{
            padding: 12,
            border: "1px solid var(--border, #e5e7eb)",
            borderRadius: 6,
          }}
        >
          <div style={{ fontSize: 12, color: "var(--muted-foreground, #6b7280)" }}>
            Offsite backups (GDrive)
          </div>
          <div style={{ fontSize: 22, fontWeight: 600 }}>{status?.offsite?.count ?? "—"}</div>
          <div style={{ fontSize: 12, color: "var(--muted-foreground, #6b7280)" }}>
            {newest ? `Newest: ${formatDate(newest.mtime)}` : "—"}
          </div>
        </div>
      </div>
      <ResultBanner result={result} onDismiss={() => setResult(null)} />
    </section>
  );
}

// ---------------------------------------------------------------------------
// Cleanup panel types
// ---------------------------------------------------------------------------

type CleanupLeaf = {
  path: string;
  modified?: string;
  sizeBytes: number;
  coreBytes?: number;
  changesBytes?: number;
  fileCount?: number;
  kind?: "perCompany" | "hourly" | "daily";
  golden: boolean;
  goldenSetBy?: string | null;
  goldenSetAt?: string | null;
  goldenReason?: string | null;
  worktree: boolean;
};

type CleanupTierSummary = {
  kind: "perCompany" | "hourly" | "daily";
  remote: string;
  prefix: string;
  count: number;
  totalBytes: number;
  goldenCount: number;
  goldenBytes: number;
  leaves: CleanupLeaf[];
};

type CleanupListing = {
  roots: CleanupTierSummary[];
  totals: {
    count: number;
    totalBytes: number;
    goldenCount: number;
    goldenBytes: number;
  };
  cleanupPath: string;
  testPrefix: string;
};

type CleanupPreview = {
  scope: "perCompany" | "hourly" | "daily" | "testOnly" | "all";
  thresholdDays: number;
  dryRun: boolean;
  wouldDelete: Array<{
    path: string;
    modified?: string;
    sizeBytes: number;
    kind?: "perCompany" | "hourly" | "daily";
  }>;
  wouldDeleteCount: number;
  wouldDeleteBytes: number;
  goldenSkippedCount: number;
  ageKeptCount: number;
  scopeErrors: string[];
};

type Listing = {
  missingCompanyId?: boolean;
  local: { count: number; totalBytes: number; dumps: Array<{ filename: string; mtime: string; sizeBytes: number }> };
  offsite: { count: number; backups: Array<{ path: string; modified?: string; sizeBytes: number }> };
  offsiteRetention?: { keep: number; candidates: number };
  config?: { offsiteKeep: number; rcloneRemote: string; gdriveTierRoot?: string };
  loading?: boolean;
  loadingFresh?: boolean;
  listingAt?: number;
  requestedCompanyId?: string;
};

type LocationsData = {
  items: Array<{ id: string; path: string; note?: string }>;
};

type RecoverySnapshots = {
  snapshots: Array<{
    id: string;
    path: string;
    timestamp: string | null;
    bytes: number;
    apparentBytes?: number;
    deltaBytes?: number;
  }>;
  runningSnapshots?: Array<{ pid: number; cmd: string; startedAt: string }>;
  totalApparentBytes?: number;
  totalDeltaBytes?: number;
  dir: string;
  count: number;
};

type TierUploadProgress = {
  tier: "daily" | "hourly" | null;
  pid: number | null;
  startedAt: number | null;
  finishedAt: number | null;
  lines: string[];
  exitCode: number | null;
};

type TierStatus = {
  enabled: boolean;
  tierRoot: string;
  keep: { daily: number; hourly: number };
  counts: { daily: number; hourly: number };
  lastUpload: { daily: string | null; hourly: string | null };
  errors: { daily: string | null; hourly: string | null };
  daily: Array<{ id: string; path: string }>;
  hourly: Array<{ id: string; path: string }>;
};

// ---------------------------------------------------------------------------
// CleanupPanel — the new GDrive cleanup tab
// ---------------------------------------------------------------------------

function CleanupPanel({
  companyId,
  listing,
  listingError,
  onRefresh,
}: {
  companyId: string | null;
  listing: CleanupListing | null;
  listingError: string | null;
  onRefresh: () => void;
}) {
  const markGolden = usePluginAction("mark-golden");
  const cleanupStale = usePluginAction("cleanup-stale");
  const setThreshold = usePluginAction("set-golden-cleanup-threshold");
  const [scope, setScope] = useState<"perCompany" | "hourly" | "daily" | "testOnly" | "all">(
    "hourly",
  );
  const [thresholdDays, setThresholdDays] = useState(14);
  const [busy, setBusy] = useState(false);
  const [previewTick, setPreviewTick] = useState(0);
  const previewResult = usePluginData("gdrive-cleanup-preview", {
    scope,
    thresholdDays,
    allowActiveBtcCompany: true, // preview-only, no actual deletion
    _tick: previewTick,
  }) as PluginDataResult<CleanupPreview> | undefined;
  const preview = previewResult?.data;
  const previewError = previewResult?.error ? String(previewResult.error) : null;
  const [result, setResult] = useState<{
    ok: boolean;
    message: string;
    deleted?: number;
    goldenSkipped?: number;
    ageKept?: number;
    dryRun?: boolean;
    scope?: string;
    thresholdDays?: number;
    deletedPaths?: string[];
    skippedPaths?: string[];
    errors?: string[];
  } | null>(null);

  // Auto-refresh preview when scope or threshold changes.
  useEffect(() => {
    setPreviewTick((n) => n + 1);
  }, [scope, thresholdDays]);

  const totalLeaves = listing?.totals.count ?? 0;
  const totalGolden = listing?.totals.goldenCount ?? 0;
  const totalBytes = listing?.totals.totalBytes ?? 0;
  const goldenBytes = listing?.totals.goldenBytes ?? 0;

  const isProductionScope =
    scope === "perCompany" || scope === "hourly" || scope === "daily" || scope === "all";

  const doMarkGolden = async (leaf: CleanupLeaf, golden: boolean, reason?: string) => {
    setBusy(true);
    setResult(null);
    try {
      const r = (await markGolden({
        leaf: leaf.path,
        golden,
        setBy: "ui",
        reason: golden ? reason ?? "manually marked golden" : null,
      })) as { ok: boolean; message: string; golden: boolean };
      setResult({
        ok: r.ok === true,
        message: r.message ?? (golden ? "Marked golden" : "Unmarked"),
      });
      onRefresh();
      setPreviewTick((n) => n + 1);
    } catch (err) {
      setResult({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  };

  const doPreviewCleanup = () => {
    setPreviewTick((n) => n + 1);
  };

  const doCleanup = async (confirm: boolean, allowActiveBtcCompany: boolean) => {
    if (!preview) return;
    if (preview.wouldDeleteCount === 0) {
      setResult({
        ok: true,
        message: "Nothing to clean up — preview is empty.",
        dryRun: false,
        scope,
        thresholdDays,
      });
      return;
    }
    if (isProductionScope && !confirm) {
      setResult({
        ok: false,
        message: `Refusing: production scope "${scope}" requires explicit confirmation.`,
        scope,
        thresholdDays,
      });
      return;
    }
    if ((scope === "perCompany" || scope === "all") && !allowActiveBtcCompany) {
      setResult({
        ok: false,
        message: `Refusing: per-company scope requires allowActiveBtcCompany flag.`,
        scope,
        thresholdDays,
      });
      return;
    }
    setBusy(true);
    setResult(null);
    try {
      const r = (await cleanupStale({
        scope,
        thresholdDays,
        dryRun: false,
        confirmDelete: true,
        allowActiveBtcCompany,
      })) as {
        ok: boolean;
        dryRun: boolean;
        thresholdDays: number;
        scope: string;
        deleted: number;
        goldenSkipped: number;
        ageKept: number;
        deletedPaths: string[];
        skippedPaths?: string[];
        errors: string[];
      };
      setResult({
        ok: r.ok === true,
        message: r.ok
          ? `Cleaned up ${r.deleted} leaves, skipped ${r.goldenSkipped} golden, kept ${r.ageKept} (age threshold).`
          : `Cleanup failed: ${(r.errors ?? []).join("; ")}`,
        deleted: r.deleted,
        goldenSkipped: r.goldenSkipped,
        ageKept: r.ageKept,
        dryRun: r.dryRun,
        scope: r.scope,
        thresholdDays: r.thresholdDays,
        deletedPaths: r.deletedPaths,
        skippedPaths: r.skippedPaths ?? [],
        errors: r.errors,
      });
      onRefresh();
      setPreviewTick((n) => n + 1);
    } catch (err) {
      setResult({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  };

  const doSetThreshold = async (days: number) => {
    setBusy(true);
    try {
      await setThreshold({ days });
      setResult({ ok: true, message: `Set cleanup threshold to ${days} days.` });
    } catch (err) {
      setResult({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section style={{ display: "grid", gap: 16 }}>
      <div
        style={{
          padding: 16,
          border: "1px solid var(--border, #e5e7eb)",
          borderRadius: 8,
          background: "var(--card, #fafafa)",
        }}
      >
        <h3 style={{ marginTop: 0, fontSize: 16 }}>GDrive cleanup overview</h3>
        <p style={{ marginTop: 0, fontSize: 12, color: "var(--muted-foreground, #6b7280)" }}>
          Walks every backup leaf on gdrive under{" "}
          <code style={{ fontFamily: "ui-monospace, monospace" }}>{listing?.cleanupPath ?? "—"}</code>
          . Flag a leaf as "golden" to protect it from automated cleanup. The{" "}
          <code style={{ fontFamily: "ui-monospace, monospace" }}>{listing?.testPrefix ?? "—"}</code> subtree
          is reserved for the cleanup-panel integration test and is the only safe scope to use without
          explicit confirmation.
        </p>
        {listingError ? (
          <div
            role="alert"
            style={{
              padding: 12,
              border: "1px solid var(--destructive, #dc2626)",
              borderRadius: 6,
              color: "var(--destructive)",
              fontSize: 12,
            }}
          >
            Failed to load cleanup listing: {listingError}
          </div>
        ) : null}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 8,
            marginTop: 8,
          }}
        >
          <div
            style={{
              padding: 12,
              border: "1px solid var(--border, #e5e7eb)",
              borderRadius: 6,
            }}
          >
            <div style={{ fontSize: 11, color: "var(--muted-foreground, #6b7280)" }}>Total leaves</div>
            <div style={{ fontSize: 20, fontWeight: 600 }}>{totalLeaves}</div>
          </div>
          <div
            style={{
              padding: 12,
              border: "1px solid var(--border, #e5e7eb)",
              borderRadius: 6,
            }}
          >
            <div style={{ fontSize: 11, color: "var(--muted-foreground, #6b7280)" }}>Total bytes</div>
            <div style={{ fontSize: 20, fontWeight: 600 }}>{formatBytes(totalBytes)}</div>
          </div>
          <div
            style={{
              padding: 12,
              border: "1px solid var(--border, #e5e7eb)",
              borderRadius: 6,
            }}
          >
            <div
              style={{ fontSize: 11, color: "hsl(45, 80%, 40%)", fontWeight: 600 }}
              title="Leaves protected by a .golden.json sidecar"
            >
              ★ Golden
            </div>
            <div style={{ fontSize: 20, fontWeight: 600 }}>{totalGolden}</div>
            <div style={{ fontSize: 11, color: "var(--muted-foreground, #6b7280)" }}>
              {formatBytes(goldenBytes)}
            </div>
          </div>
          <div
            style={{
              padding: 12,
              border: "1px solid var(--border, #e5e7eb)",
              borderRadius: 6,
            }}
          >
            <div style={{ fontSize: 11, color: "var(--muted-foreground, #6b7280)" }}>
              Cleanup-eligible (older than threshold)
            </div>
            <div style={{ fontSize: 20, fontWeight: 600 }}>{preview?.wouldDeleteCount ?? "—"}</div>
            <div style={{ fontSize: 11, color: "var(--muted-foreground, #6b7280)" }}>
              {preview ? formatBytes(preview.wouldDeleteBytes) : "—"}
            </div>
          </div>
        </div>
      </div>

      <div
        style={{
          padding: 16,
          border: "1px solid var(--border, #e5e7eb)",
          borderRadius: 8,
        }}
      >
        <h3 style={{ marginTop: 0, fontSize: 16 }}>Cleanup stale backups</h3>
        <p style={{ marginTop: 0, fontSize: 12, color: "var(--muted-foreground, #6b7280)" }}>
          Delete leaves older than the threshold that are NOT flagged as golden. The golden sidecar
          (a tiny <code>.golden.json</code> next to each leaf) is the only thing that protects a leaf
          from this action.
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "end" }}>
          <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
            Scope
            <select
              value={scope}
              onChange={(e) => setScope(e.target.value as typeof scope)}
              style={{
                padding: "4px 8px",
                border: "1px solid var(--border, #e5e7eb)",
                borderRadius: 4,
                fontSize: 12,
                minWidth: 180,
                color: "var(--foreground, #e5e7eb)",
                background: "var(--card, #1f2937)",
              }}
            >
              <option value="testOnly">testOnly (safe — only test prefix)</option>
              <option value="hourly">hourly (global hourly tier)</option>
              <option value="daily">daily (global daily tier)</option>
              <option value="perCompany">perCompany (active BTC company)</option>
              <option value="all">all (everything except per-company is allowed)</option>
            </select>
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
            Threshold (days)
            <input
              type="number"
              min={1}
              max={365}
              value={thresholdDays}
              onChange={(e) => setThresholdDays(Math.max(1, Math.min(365, Number(e.target.value) || 14)))}
              style={{
                padding: "4px 8px",
                border: "1px solid var(--border, #e5e7eb)",
                borderRadius: 4,
                width: 100,
                color: "var(--foreground, #e5e7eb)",
                background: "var(--card, #1f2937)",
              }}
            />
          </label>
          <ActionButton
            label="Refresh preview"
            busy={false}
            onClick={doPreviewCleanup}
            variant="default"
            hint={`Scans gdrive and computes what cleanup would delete (always safe — no deletes).`}
          />
        </div>
        {previewError ? (
          <div
            role="alert"
            style={{
              marginTop: 8,
              padding: 8,
              border: "1px solid var(--destructive, #dc2626)",
              borderRadius: 4,
              fontSize: 12,
              color: "var(--destructive)",
            }}
          >
            Preview failed: {previewError}
          </div>
        ) : null}
        {preview && preview.scopeErrors.length > 0 ? (
          <div
            role="alert"
            style={{
              marginTop: 8,
              padding: 8,
              border: "1px solid var(--destructive, #dc2626)",
              borderRadius: 4,
              fontSize: 12,
              color: "var(--destructive)",
            }}
          >
            Scope errors: {preview.scopeErrors.join("; ")}
          </div>
        ) : null}
        {preview ? (
          <div
            style={{
              marginTop: 12,
              padding: 12,
              border: "1px solid var(--border, #e5e7eb)",
              borderRadius: 6,
              background: "var(--muted, #f9fafb)",
            }}
          >
            <div style={{ fontSize: 12, marginBottom: 8 }}>
              <strong>Would delete:</strong> {preview.wouldDeleteCount} leaves (
              {formatBytes(preview.wouldDeleteBytes)}) · <strong>Golden-skipped:</strong>{" "}
              {preview.goldenSkippedCount} · <strong>Age-kept:</strong> {preview.ageKeptCount}
            </div>
            {preview.wouldDeleteCount > 0 ? (
              <div
                style={{
                  maxHeight: 200,
                  overflow: "auto",
                  fontFamily: "ui-monospace, monospace",
                  fontSize: 11,
                  padding: 8,
                  background: "var(--card, #fff)",
                  border: "1px solid var(--border, #e5e7eb)",
                  borderRadius: 4,
                }}
              >
                {preview.wouldDelete
                  .slice(0, 200)
                  .map((l) => `${l.path}  (${formatDate(l.modified)}, ${formatBytes(l.sizeBytes)})`)
                  .join("\n")}
                {preview.wouldDelete.length > 200 ? `\n… ${preview.wouldDelete.length - 200} more` : ""}
              </div>
            ) : (
              <div
                style={{
                  fontSize: 12,
                  color: "var(--muted-foreground, #6b7280)",
                }}
              >
                Nothing to delete.
              </div>
            )}
            <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
              {scope === "testOnly" ? (
                <ActionButton
                  label={`Delete ${preview.wouldDeleteCount} (testOnly scope)`}
                  busy={busy}
                  onClick={() => doCleanup(true, true)}
                  variant="danger"
                  hint="testOnly scope requires no extra flags — only touches the test prefix."
                  disabled={preview.wouldDeleteCount === 0}
                />
              ) : scope === "hourly" || scope === "daily" ? (
                <ActionButton
                  label={`Delete ${preview.wouldDeleteCount} (scope=${scope})`}
                  busy={busy}
                  onClick={() => doCleanup(true, true)}
                  variant="danger"
                  hint={`Production scope. Will confirm in browser. confirmDelete:true is sent.`}
                  disabled={preview.wouldDeleteCount === 0}
                />
              ) : (
                <ActionButton
                  label={`Delete ${preview.wouldDeleteCount} (scope=${scope})`}
                  busy={busy}
                  onClick={() => doCleanup(true, true)}
                  variant="danger"
                  hint="Production scope. Will confirm in browser. confirmDelete:true and allowActiveBtcCompany:true are sent."
                  disabled={preview.wouldDeleteCount === 0}
                />
              )}
            </div>
            {scope === "testOnly" && preview.wouldDeleteCount > 0 ? (
              <ConfirmInline
                message={`Permanently delete ${preview.wouldDeleteCount} leaves from the test prefix? Real gdrive data is not touched (testOnly scope only).`}
                confirmLabel="Yes, delete from test prefix"
                onConfirm={() => doCleanup(true, true)}
                busy={busy}
              />
            ) : null}
            {(scope === "hourly" || scope === "daily") && preview.wouldDeleteCount > 0 ? (
              <ConfirmInline
                message={`PRODUCTION: this will permanently delete ${preview.wouldDeleteCount} leaves from the gdrive "${scope}" tier. Golden leaves are protected. Continue?`}
                confirmLabel="Yes, delete from production tier"
                onConfirm={() => doCleanup(true, true)}
                busy={busy}
              />
            ) : null}
            {(scope === "perCompany" || scope === "all") && preview.wouldDeleteCount > 0 ? (
              <ConfirmInline
                message={`PRODUCTION + ACTIVE BTC COMPANY: this will permanently delete ${preview.wouldDeleteCount} leaves from the active per-company prefix. Golden leaves are protected. Type DELETE in the box to confirm.`}
                confirmLabel="Yes, delete from active BTC company prefix"
                requireText="DELETE"
                onConfirm={() => doCleanup(true, true)}
                busy={busy}
              />
            ) : null}
          </div>
        ) : null}
        <div style={{ marginTop: 12 }}>
          <details>
            <summary style={{ fontSize: 12, cursor: "pointer" }}>
              Persist threshold as plugin default
            </summary>
            <div
              style={{
                marginTop: 8,
                display: "flex",
                gap: 8,
                alignItems: "end",
              }}
            >
              <input
                type="number"
                min={1}
                max={365}
                defaultValue={thresholdDays}
                id="cleanup-threshold-input"
                style={{
                  padding: "4px 8px",
                  border: "1px solid var(--border, #e5e7eb)",
                  borderRadius: 4,
                  width: 100,
                }}
              />
              <button
                type="button"
                onClick={() => {
                  const inp = document.getElementById("cleanup-threshold-input") as
                    | HTMLInputElement
                    | null;
                  const v = inp ? parseInt(inp.value, 10) : NaN;
                  if (Number.isFinite(v) && v >= 1) doSetThreshold(v);
                }}
                style={{
                  padding: "6px 12px",
                  background: "#374151",
                  color: "#f8fafc",
                  border: "1px solid transparent",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontSize: 12,
                }}
              >
                Save
              </button>
            </div>
          </details>
        </div>
      </div>

      <div
        style={{
          padding: 16,
          border: "1px solid var(--border, #e5e7eb)",
          borderRadius: 8,
        }}
      >
        <h3 style={{ marginTop: 0, fontSize: 16 }}>Backup leaves by tier</h3>
        <p style={{ marginTop: 0, fontSize: 12, color: "var(--muted-foreground, #6b7280)" }}>
          Every leaf on gdrive. Click "★ Mark golden" to write a protective sidecar; click again to
          remove it. Golden leaves are skipped by cleanup-stale no matter what.
        </p>
        {listing?.roots.map((root) => (
          <TierBlock
            key={root.prefix}
            root={root}
            onMarkGolden={doMarkGolden}
            busy={busy}
            companyId={companyId}
          />
        ))}
      </div>

      <ResultBanner
        result={
          result
            ? {
                ok: result.ok,
                message: result.message,
              }
            : null
        }
        onDismiss={() => setResult(null)}
      />
    </section>
  );
}

function TierBlock({
  root,
  onMarkGolden,
  busy,
  companyId,
}: {
  root: CleanupTierSummary;
  onMarkGolden: (leaf: CleanupLeaf, golden: boolean, reason?: string) => void;
  busy: boolean;
  companyId: string | null;
}) {
  const [filter, setFilter] = useState<"all" | "golden" | "nongolden" | "stale">("all");
  const [sortBy, setSortBy] = useState<"newest" | "oldest" | "size">("newest");
  const visibleLeaves = useMemo(() => {
    let lvs = root.leaves.slice();
    if (filter === "golden") lvs = lvs.filter((l) => l.golden);
    if (filter === "nongolden") lvs = lvs.filter((l) => !l.golden);
    if (filter === "stale") {
      const cutoff = Date.now() - 14 * 86_400_000;
      lvs = lvs.filter((l) => l.modified && Date.parse(l.modified) < cutoff);
    }
    lvs.sort((a, b) => {
      if (sortBy === "size") return (b.sizeBytes ?? 0) - (a.sizeBytes ?? 0);
      const am = a.modified ?? a.path;
      const bm = b.modified ?? b.path;
      if (sortBy === "newest") return am < bm ? 1 : am > bm ? -1 : 0;
      return am < bm ? -1 : am > bm ? 1 : 0;
    });
    return lvs;
  }, [root.leaves, filter, sortBy]);

  const tierLabel = (() => {
    if (root.kind === "hourly") return "Hourly tier";
    if (root.kind === "daily") return "Daily tier";
    if (root.prefix.includes("Paperclip-Backups/test-cleanup-panel")) return "Test prefix (cleanup-panel tests)";
    return "Per-company tier";
  })();
  const isTestPrefix = root.prefix.includes("Paperclip-Backups/test-cleanup-panel");

  return (
    <div
      style={{
        marginTop: 12,
        padding: 12,
        border: "1px solid var(--border, #e5e7eb)",
        borderRadius: 6,
        background: isTestPrefix ? "color-mix(in oklab, hsl(190, 35%, 25%) 60%, var(--card))" : "var(--card, #fafafa)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <div>
          <strong style={{ fontSize: 13 }}>{tierLabel}</strong>
          <span
            style={{
              marginLeft: 8,
              fontFamily: "ui-monospace, monospace",
              fontSize: 11,
              color: "var(--muted-foreground, #6b7280)",
            }}
          >
            {root.prefix}
          </span>
        </div>
        <div style={{ fontSize: 11, color: "var(--muted-foreground, #6b7280)" }}>
          {root.count} leaves · {formatBytes(root.totalBytes)} · {root.goldenCount} golden (
          {formatBytes(root.goldenBytes)})
        </div>
      </div>
      <div
        style={{
          display: "flex",
          gap: 8,
          alignItems: "center",
          marginTop: 6,
          fontSize: 11,
          color: "var(--muted-foreground, #6b7280)",
        }}
      >
        Filter:
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value as typeof filter)}
          style={{ fontSize: 11, padding: "2px 4px", border: "1px solid var(--border, #e5e7eb)", borderRadius: 3, color: "var(--foreground, #e5e7eb)", background: "var(--card, #1f2937)" }}
        >
          <option value="all">all</option>
          <option value="golden">★ golden only</option>
          <option value="nongolden">non-golden only</option>
          <option value="stale">stale (&gt;14d, default threshold)</option>
        </select>
        Sort:
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
          style={{ fontSize: 11, padding: "2px 4px", border: "1px solid var(--border, #e5e7eb)", borderRadius: 3, color: "var(--foreground, #e5e7eb)", background: "var(--card, #1f2937)" }}
        >
          <option value="newest">newest first</option>
          <option value="oldest">oldest first</option>
          <option value="size">largest first</option>
        </select>
      </div>
      <div
        style={{
          marginTop: 6,
          maxHeight: 360,
          overflow: "auto",
          border: "1px solid var(--border, #e5e7eb)",
          borderRadius: 4,
        }}
      >
        {visibleLeaves.length === 0 ? (
          <div
            style={{
              padding: 8,
              fontSize: 12,
              color: "var(--muted-foreground, #6b7280)",
            }}
          >
            (no leaves match this filter)
          </div>
        ) : (
          visibleLeaves.map((leaf) => (
            <div
              key={leaf.path}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "6px 10px",
                borderBottom: "1px solid var(--border, #e5e7eb)",
                background: leaf.golden
                  ? "color-mix(in oklab, hsl(45, 80%, 60%) 12%, var(--card, #fff))"
                  : undefined,
              }}
            >
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  color: leaf.golden ? "hsl(45, 80%, 35%)" : "var(--muted-foreground, #6b7280)",
                  width: 18,
                  textAlign: "center",
                }}
                title={leaf.golden ? "golden" : "not golden"}
              >
                {leaf.golden ? "★" : "·"}
              </span>
              <span
                style={{
                  flex: 1,
                  fontFamily: "ui-monospace, monospace",
                  fontSize: 11,
                  wordBreak: "break-all",
                }}
              >
                {leaf.path}
                <span
                  style={{
                    color: "var(--muted-foreground, #6b7280)",
                    marginLeft: 6,
                  }}
                >
                  · {formatDate(leaf.modified)} ·{" "}
                  {leaf.coreBytes ? (
                    <span>
                      core <strong>{formatBytes(leaf.coreBytes)}</strong>
                      {leaf.changesBytes ? (
                        <>
                          {" "}
                          <span style={{ color: "hsl(35, 80%, 40%)" }}>
                            (changes <strong>{formatBytes(leaf.changesBytes)}</strong>)
                          </span>
                        </>
                      ) : null}
                    </span>
                  ) : (
                    <span>{formatBytes(leaf.sizeBytes)}</span>
                  )}
                </span>
                {leaf.golden && leaf.goldenSetBy ? (
                  <span
                    style={{
                      color: "hsl(45, 80%, 35%)",
                      marginLeft: 6,
                      fontSize: 10,
                    }}
                  >
                    (set by {leaf.goldenSetBy}
                    {leaf.goldenSetAt ? ` on ${formatDate(leaf.goldenSetAt)}` : ""}
                    {leaf.goldenReason ? ` — ${leaf.goldenReason}` : ""})
                  </span>
                ) : null}
              </span>
              {leaf.golden ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onMarkGolden(leaf, false)}
                  style={{
                    padding: "2px 8px",
                    fontSize: 11,
                    border: "1px solid var(--border, #e5e7eb)",
                    borderRadius: 3,
                    background: "var(--muted, #f3f4f6)",
                    cursor: busy ? "not-allowed" : "pointer",
                  }}
                >
                  Unmark golden
                </button>
              ) : (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onMarkGolden(leaf, true)}
                  style={{
                    padding: "2px 8px",
                    fontSize: 11,
                    border: "1px solid transparent",
                    borderRadius: 3,
                    background: "hsl(45, 80%, 40%)",
                    color: "#f8fafc",
                    cursor: busy ? "not-allowed" : "pointer",
                  }}
                >
                  ★ Mark golden
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function ConfirmInline({
  message,
  confirmLabel,
  onConfirm,
  busy,
  requireText,
}: {
  message: string;
  confirmLabel: string;
  onConfirm: () => void;
  busy: boolean;
  requireText?: string;
}) {
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const canConfirm = !requireText || typed === requireText;
  if (!open) {
    return (
      <div style={{ marginTop: 8 }}>
        <button
          type="button"
          onClick={() => setOpen(true)}
          style={{
            padding: "4px 10px",
            fontSize: 11,
            border: "1px solid var(--destructive, #dc2626)",
            color: "var(--destructive, #dc2626)",
            background: "transparent",
            borderRadius: 4,
            cursor: "pointer",
          }}
        >
          {confirmLabel}…
        </button>
      </div>
    );
  }
  return (
    <div
      style={{
        marginTop: 8,
        padding: 10,
        border: "1px solid var(--destructive, #dc2626)",
        borderRadius: 6,
        background: "color-mix(in oklab, var(--destructive) 4%, var(--card))",
        fontSize: 12,
      }}
    >
      <div style={{ marginBottom: 6 }}>{message}</div>
      {requireText ? (
        <div style={{ marginBottom: 6 }}>
          Type <code>{requireText}</code> to confirm:{" "}
          <input
            type="text"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            style={{
              padding: "2px 6px",
              border: "1px solid var(--destructive, #dc2626)",
              borderRadius: 3,
              fontFamily: "ui-monospace, monospace",
              fontSize: 11,
              width: 120,
            }}
          />
        </div>
      ) : null}
      <div style={{ display: "flex", gap: 8 }}>
        <button
          type="button"
          onClick={onConfirm}
          disabled={!canConfirm || busy}
          style={{
            padding: "4px 12px",
            fontSize: 12,
            background: "var(--destructive, #b91c1c)",
            color: "#f8fafc",
            border: "1px solid transparent",
            borderRadius: 4,
            cursor: canConfirm && !busy ? "pointer" : "not-allowed",
            opacity: canConfirm && !busy ? 1 : 0.5,
          }}
        >
          {confirmLabel}
        </button>
        <button
          type="button"
          onClick={() => {
            setOpen(false);
            setTyped("");
          }}
          style={{
            padding: "4px 12px",
            fontSize: 12,
            background: "var(--muted, #f3f4f6)",
            border: "1px solid var(--border, #e5e7eb)",
            borderRadius: 4,
            cursor: "pointer",
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Manager page (with cleanup tab)
// ---------------------------------------------------------------------------

export function BackupManagerPage({
  context,
}: {
  context: { companyId?: string | null };
}) {
  const host = useHostContext();
  const companyId = context.companyId ?? host.companyId ?? null;
  const [tab, setTab] = useState<"manager" | "cleanup" | "recovery">("manager");
  const [refreshTick, setRefreshTick] = useState(0);
  const runBackup = usePluginAction("run-backup");
  const pruneLocal = usePluginAction("prune-local");
  const pruneOffsite = usePluginAction("prune-offsite");
  const restoreOffsite = usePluginAction("restore-offsite");
  const restoreLocal = usePluginAction("restore-local");
  const forceBackup = usePluginAction("force-backup");
  const forceRestore = usePluginAction("force-restore");
  const deleteRecoverySnapshots = usePluginAction("delete-recovery-snapshots");
  const uploadDailyBackup = usePluginAction("upload-daily-backup");
  const uploadHourlyBackup = usePluginAction("upload-hourly-backup");
  const setTierKeep = usePluginAction("set-tier-keep");
  const recoverySnapshotsResult = usePluginData("recovery-snapshots", { _tick: refreshTick }) as
    | PluginDataResult<RecoverySnapshots>
    | undefined;
  const recoverySnapshots = recoverySnapshotsResult?.data;
  const recoverySnapshotsError = recoverySnapshotsResult?.error
    ? String(recoverySnapshotsResult.error)
    : null;
  const tierStatusResult = usePluginData("gdrive-tier-status", { _tick: refreshTick }) as
    | PluginDataResult<TierStatus>
    | undefined;
  const tierStatus = tierStatusResult?.data;
  const tierProgressResult = usePluginData("tier-upload-progress", { _tick: refreshTick }) as
    | PluginDataResult<TierUploadProgress>
    | undefined;
  const tierProgress = tierProgressResult?.data;
  const statusResult = usePluginData("status", { companyId }) as
    | PluginDataResult<{ backupRunning?: { pid: number; startedAt: string; recovery?: boolean; isForced?: boolean } | null }>
    | undefined;
  const status = statusResult?.data;
  const listingResult = usePluginData("listing", { companyId, _tick: refreshTick }) as
    | PluginDataResult<Listing>
    | undefined;
  const listing = listingResult?.data;
  const error = listingResult?.error ? String(listingResult.error) : null;
  const locationsResult = usePluginData("locations", {}) as PluginDataResult<LocationsData> | undefined;
  const locationsData = locationsResult?.data;
  const cleanupListingResult = usePluginData("gdrive-cleanup-listing", {
    companyId,
    _tick: refreshTick,
  }) as PluginDataResult<CleanupListing> | undefined;
  const cleanupListing = cleanupListingResult?.data;
  const cleanupListingError = cleanupListingResult?.error
    ? String(cleanupListingResult.error)
    : null;

  const procRunning =
    recoverySnapshots && Array.isArray(recoverySnapshots.runningSnapshots)
      ? recoverySnapshots.runningSnapshots.find((r) => /recovery\.sh/.test(r.cmd || "")) || null
      : null;
  const stateRunning = status && status.backupRunning ? status.backupRunning : null;
  const stateRecovery = stateRunning && stateRunning.recovery === true;
  const stateForced = stateRunning && stateRunning.isForced === true;
  const forceRunning: {
    pid: number;
    startedAt: string;
    cmd?: string;
    stage?: string;
    progress?: { percent: number | null; totalBytes?: number; uploadBytes?: number; rclonePid?: number } | null;
    isForced: boolean;
  } | null = procRunning
    ? {
        pid: procRunning.pid,
        startedAt: procRunning.startedAt,
        cmd: procRunning.cmd,
        isForced: !!(stateForced || /--force/.test(procRunning.cmd || "")),
      }
    : stateRecovery && stateForced && stateRunning
    ? {
        pid: stateRunning.pid,
        startedAt: stateRunning.startedAt,
        isForced: true,
      }
    : null;

  const [busy, setBusy] = useState<string | null>(null);
  const [result, setResult] = useState<{
    ok: boolean;
    message: string;
    durationMs?: number;
    stdout?: string;
    stderr?: string;
    keep?: number;
    remotePath?: string;
    destDir?: string;
    totalBytesBefore?: number;
    totalBytesAfter?: number;
    prunedCount?: number;
    exitCode?: number | null;
  } | null>(null);
  const [restorePath, setRestorePath] = useState("");
  const [restoreDest, setRestoreDest] = useState("/tmp/paperclip-restore");
  const [restoreFile, setRestoreFile] = useState("");
  const [keep, setKeep] = useState(10);
  const [offsiteKeep, setOffsiteKeep] = useState<number | null>(null);
  const elapsedMs = useElapsedMs(busy != null);

  const runningNow = status?.backupRunning ?? null;
  useEffect(() => {
    if (busy !== "backup" && !runningNow) return;
    const t = setInterval(() => setRefreshTick((n) => n + 1), 30_000);
    return () => clearInterval(t);
  }, [busy, runningNow?.pid, runningNow?.startedAt]);

  useEffect(() => {
    if (!listing || !("loading" in listing) || !listing.loading) return;
    const t = setInterval(() => setRefreshTick((n) => n + 1), 4_000);
    return () => clearInterval(t);
  }, [listing && "loading" in listing ? (listing as { loading: boolean }).loading : false]);

  const triggerBackup = async () => {
    if (busy) return;
    setBusy("backup");
    setResult(null);
    try {
      const r = (await runBackup({ companyId })) as {
        alreadyRunning?: boolean;
        async?: boolean;
        pid?: number;
        ok?: boolean;
        message?: string;
        exitCode?: number | null;
        durationMs?: number;
        stdout?: string;
        stderr?: string;
      };
      if (r.alreadyRunning) {
        setResult({ ok: false, message: r.message ?? "Backup already running" });
      } else if (r.async || r.pid) {
        setResult({
          ok: true,
          message: r.message ?? `Backup started in background (pid=${r.pid})`,
        });
      } else {
        setResult({
          ok: r.ok === true,
          exitCode: r.exitCode ?? null,
          message: r.ok === true ? "Backup pushed" : "Backup script failed",
          durationMs: r.durationMs,
          stdout: r.stdout,
          stderr: r.stderr,
        });
      }
    } catch (err) {
      setResult({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(null);
      setRefreshTick((n) => n + 1);
    }
  };

  const triggerPrune = async () => {
    if (busy) return;
    setBusy("prune");
    setResult(null);
    try {
      const r = (await pruneLocal({ keep })) as {
        ok: boolean;
        keep?: number;
        message?: string;
        durationMs?: number;
        stdout?: string;
        stderr?: string;
        totalBytesBefore?: number;
        totalBytesAfter?: number;
        prunedCount?: number;
      };
      setResult({
        ok: r.ok === true,
        message: r.ok === true ? `Pruned, kept ${r.keep ?? keep}` : "Prune failed",
        durationMs: r.durationMs,
        stdout: r.stdout,
        stderr: r.stderr,
        keep: r.keep ?? keep,
        totalBytesBefore: r.totalBytesBefore,
        totalBytesAfter: r.totalBytesAfter,
        prunedCount: r.prunedCount,
      });
    } catch (err) {
      setResult({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(null);
      setRefreshTick((n) => n + 1);
    }
  };

  const triggerRestoreOffsite = async () => {
    if (busy) return;
    setBusy("restore-off");
    setResult(null);
    try {
      const r = (await restoreOffsite({
        companyId,
        path: restorePath || "latest",
        destDir: restoreDest,
      })) as {
        ok: boolean;
        message?: string;
        exitCode?: number | null;
        durationMs?: number;
        stdout?: string;
        stderr?: string;
        remotePath?: string;
        destDir?: string;
      };
      const usedPath = (r.remotePath ?? restorePath) || "latest";
      setResult({
        ok: r.ok === true,
        message: r.ok === true ? `Restored from ${usedPath}` : "Restore failed",
        durationMs: r.durationMs,
        stdout: r.stdout,
        stderr: r.stderr,
        remotePath: usedPath,
        destDir: r.destDir ?? restoreDest,
      });
    } catch (err) {
      setResult({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(null);
    }
  };

  const triggerPruneOffsite = async () => {
    if (busy) return;
    const effectiveKeep =
      offsiteKeep ??
      listing?.offsiteRetention?.keep ??
      listing?.config?.offsiteKeep ??
      30;
    setBusy("prune-off");
    setResult(null);
    try {
      const r = (await pruneOffsite({ companyId, keep: effectiveKeep })) as {
        alreadyRunning?: boolean;
        elapsedMs?: number;
        async?: boolean;
        startedAt?: string;
        message?: string;
        keep?: number;
        ok?: boolean;
        offsitePruned?: number;
        offsiteKept?: number;
        exitCode?: number | null;
        durationMs?: number;
        stdout?: string;
        stderr?: string;
        totalBytesBefore?: number;
        totalBytesAfter?: number;
        deletedPaths?: string[];
      };
      if (r.alreadyRunning) {
        const elapsed =
          typeof r.elapsedMs === "number" ? ` (already running for ${Math.round(r.elapsedMs / 1000)}s)` : "";
        setResult({
          ok: false,
          message: r.message ?? `Offsite prune already running${elapsed}. Pass force:true to override.`,
        });
        return;
      }
      if (r.async === true || r.startedAt) {
        setResult({
          ok: true,
          message: r.message ?? `Prune started in background (keep=${effectiveKeep}).`,
          keep: r.keep ?? effectiveKeep,
        });
        return;
      }
      const pruned = r.offsitePruned ?? 0;
      const kept = r.offsiteKept ?? 0;
      setResult({
        ok: r.ok === true,
        message: r.ok === true
          ? pruned === 0
            ? `Nothing to prune — already at or below keep=${effectiveKeep}.`
            : `Pruned ${pruned} offsite backups (kept newest ${kept}).`
          : r.message ?? "Prune failed",
        durationMs: r.durationMs,
        stdout: r.stdout,
        stderr: r.stderr,
        keep: r.keep ?? effectiveKeep,
        totalBytesBefore: r.totalBytesBefore,
        totalBytesAfter: r.totalBytesAfter,
        prunedCount: pruned,
      });
    } catch (err) {
      setResult({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(null);
      setRefreshTick((n) => n + 1);
    }
  };

  const triggerRestoreLocal = async () => {
    if (busy || !restoreFile) return;
    setBusy("restore-loc");
    setResult(null);
    try {
      const r = (await restoreLocal({ filename: restoreFile, destDir: restoreDest })) as {
        ok: boolean;
        message?: string;
        exitCode?: number | null;
        durationMs?: number;
        stdout?: string;
        stderr?: string;
        destDir?: string;
      };
      setResult({
        ok: r.ok === true,
        message: r.ok === true ? `Copied ${restoreFile}` : "Restore failed",
        durationMs: r.durationMs,
        stdout: r.stdout,
        stderr: r.stderr,
        destDir: r.destDir ?? restoreDest,
      });
    } catch (err) {
      setResult({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(null);
    }
  };

  return (
    <article style={{ display: "grid", gap: 16, padding: 16 }}>
      <header>
        <h2 style={{ margin: 0, fontSize: 20 }}>Backup Manager</h2>
        <p style={{ marginTop: 4, color: "var(--muted-foreground, #6b7280)", fontSize: 13 }}>
          Offsite push (rclone → GDrive) and local DB-dump retention. The{" "}
          <strong>Cleanup (GDrive)</strong> tab is a comprehensive view of every backup leaf
          on gdrive with golden-flag protection and bulk stale cleanup.
        </p>
      </header>

      <nav
        role="tablist"
        style={{
          display: "flex",
          gap: 4,
          borderBottom: "1px solid var(--border, #e5e7eb)",
        }}
      >
        <TabButton active={tab === "manager"} onClick={() => setTab("manager")}>
          Backup manager
        </TabButton>
        <TabButton active={tab === "cleanup"} onClick={() => setTab("cleanup")}>
          Cleanup (GDrive)
        </TabButton>
        <TabButton active={tab === "recovery"} onClick={() => setTab("recovery")}>
          Force backup &amp; recovery
        </TabButton>
      </nav>

      {tab === "manager" ? (
        <>
          <section
            style={{
              padding: 16,
              border: "1px solid var(--border, #e5e7eb)",
              borderRadius: 8,
              background: "color-mix(in oklab, var(--muted) 4%, var(--card))",
            }}
          >
            <h3 style={{ marginTop: 0, fontSize: 16 }}>Backup locations</h3>
            <p
              style={{
                marginTop: 0,
                marginBottom: 8,
                color: "var(--muted-foreground, #6b7280)",
                fontSize: 12,
              }}
            >
              Every path the operator needs to know about.
            </p>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: 12,
                fontFamily: "ui-monospace, monospace",
              }}
            >
              <thead>
                <tr
                  style={{
                    textAlign: "left",
                    color: "var(--muted-foreground, #6b7280)",
                  }}
                >
                  <th style={{ padding: "4px 6px", width: 180 }}>What</th>
                  <th style={{ padding: "4px 6px" }}>Path / Where</th>
                  <th style={{ padding: "4px 6px", width: 200 }}>Note</th>
                </tr>
              </thead>
              <tbody>
                {(locationsData?.items ?? []).map((it) => (
                  <tr
                    key={it.id}
                    style={{ borderTop: "1px solid var(--border, #e5e7eb)" }}
                  >
                    <td style={{ padding: "4px 6px", color: "var(--muted-foreground, #6b7280)" }}>
                      {it.id}
                    </td>
                    <td style={{ padding: "4px 6px", wordBreak: "break-all" }}>{it.path}</td>
                    <td style={{ padding: "4px 6px", color: "var(--muted-foreground, #6b7280)" }}>
                      {it.note || ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {error ? (
            <div
              role="alert"
              style={{
                padding: 12,
                border: "1px solid var(--destructive, #dc2626)",
                borderRadius: 6,
                background: "color-mix(in oklab, var(--destructive) 8%, var(--card))",
                color: "var(--destructive)",
              }}
            >
              Failed to load: {error}
            </div>
          ) : listing?.missingCompanyId ? (
            <div
              role="alert"
              style={{
                padding: 12,
                border: "1px solid var(--border, #e5e7eb)",
                borderRadius: 6,
                background: "color-mix(in oklab, var(--muted) 30%, var(--card))",
                color: "var(--muted-foreground, #6b7280)",
              }}
            >
              No active company. Open this page from a company context.
            </div>
          ) : null}

          <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div
              style={{
                padding: 16,
                border: "1px solid var(--border, #e5e7eb)",
                borderRadius: 8,
              }}
            >
              <header
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 8,
                }}
              >
                <h3 style={{ margin: 0, fontSize: 16 }}>Local DB dumps</h3>
                <span style={{ fontSize: 12, color: "var(--muted-foreground, #6b7280)" }}>
                  {listing?.local.count ?? "—"} files / {listing ? formatBytes(listing.local.totalBytes) : "—"}
                </span>
              </header>
              <div style={{ maxHeight: 240, overflow: "auto", fontSize: 12 }}>
                {listing?.local.dumps.length ? (
                  <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr
                        style={{
                          textAlign: "left",
                          color: "var(--muted-foreground, #6b7280)",
                        }}
                      >
                        <th style={{ padding: "4px 6px" }}>File</th>
                        <th style={{ padding: "4px 6px" }}>Modified</th>
                        <th style={{ padding: "4px 6px", textAlign: "right" }}>Size</th>
                      </tr>
                    </thead>
                    <tbody>
                      {listing.local.dumps.map((d) => (
                        <tr
                          key={d.filename}
                          style={{
                            borderTop: "1px solid var(--border, #e5e7eb)",
                            background: restoreFile === d.filename ? "var(--accent, #f3f4f6)" : undefined,
                            cursor: "pointer",
                          }}
                          onClick={() => setRestoreFile(d.filename)}
                        >
                          <td
                            style={{
                              padding: "4px 6px",
                              fontFamily: "ui-monospace, monospace",
                            }}
                          >
                            {d.filename}
                          </td>
                          <td style={{ padding: "4px 6px" }}>{formatDate(d.mtime)}</td>
                          <td style={{ padding: "4px 6px", textAlign: "right" }}>
                            {formatBytes(d.sizeBytes)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div style={{ color: "var(--muted-foreground, #6b7280)" }}>
                    No local DB dumps found.
                  </div>
                )}
              </div>
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  alignItems: "end",
                  marginTop: 12,
                  flexWrap: "wrap",
                }}
              >
                <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
                  Keep
                  <input
                    type="number"
                    min={1}
                    max={365}
                    value={keep}
                    onChange={(e) => setKeep(Math.max(1, Number(e.target.value) || 10))}
                    style={{
                      padding: "4px 8px",
                      border: "1px solid var(--border, #e5e7eb)",
                      borderRadius: 4,
                      width: 80,
                    }}
                  />
                </label>
                <ActionButton
                  label="Prune local dumps"
                  busy={busy === "prune"}
                  onClick={triggerPrune}
                  variant="danger"
                  hint={`Keep newest ${keep} file(s)`}
                  elapsedMs={elapsedMs}
                />
                <ActionButton
                  label="Restore local file"
                  busy={busy === "restore-loc"}
                  onClick={triggerRestoreLocal}
                  hint={restoreFile ? `Copy ${restoreFile}` : "Select a file in the table first"}
                  disabled={!restoreFile}
                  elapsedMs={elapsedMs}
                />
              </div>
            </div>
            <div
              style={{
                padding: 16,
                border: "1px solid var(--border, #e5e7eb)",
                borderRadius: 8,
              }}
            >
              <header
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 8,
                }}
              >
                <h3 style={{ margin: 0, fontSize: 16 }}>Offsite backups (GDrive)</h3>
                <span style={{ fontSize: 12, color: "var(--muted-foreground, #6b7280)" }}>
                  {listing?.offsite.count ?? "—"} entries · keep newest{" "}
                  {listing?.offsiteRetention?.keep ?? listing?.config?.offsiteKeep ?? 30}
                </span>
              </header>
              <div style={{ maxHeight: 240, overflow: "auto", fontSize: 12 }}>
                {listing?.offsite.backups.length ? (
                  <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr
                        style={{
                          textAlign: "left",
                          color: "var(--muted-foreground, #6b7280)",
                        }}
                      >
                        <th style={{ padding: "4px 6px" }}>Path</th>
                        <th style={{ padding: "4px 6px" }}>Modified</th>
                        <th style={{ padding: "4px 6px", textAlign: "right" }}>Size</th>
                      </tr>
                    </thead>
                    <tbody>
                      {listing.offsite.backups.map((b) => (
                        <tr
                          key={b.path}
                          style={{
                            borderTop: "1px solid var(--border, #e5e7eb)",
                            background: restorePath === b.path ? "var(--accent, #f3f4f6)" : undefined,
                            cursor: "pointer",
                          }}
                          onClick={() => setRestorePath(b.path)}
                        >
                          <td
                            style={{
                              padding: "4px 6px",
                              fontFamily: "ui-monospace, monospace",
                            }}
                          >
                            {b.path.split("/").slice(-2).join("/")}
                          </td>
                          <td style={{ padding: "4px 6px" }}>{formatDate(b.modified)}</td>
                          <td style={{ padding: "4px 6px", textAlign: "right" }}>
                            {b.sizeBytes ? formatBytes(b.sizeBytes) : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : listing?.loading ? (
                  <div
                    style={{
                      color: "var(--muted-foreground, #6b7280)",
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                    }}
                  >
                    <span
                      style={{
                        display: "inline-block",
                        width: 10,
                        height: 10,
                        borderRadius: "50%",
                        border: "2px solid var(--muted-foreground, #6b7280)",
                        borderTopColor: "transparent",
                        animation: "spin 1s linear infinite",
                      }}
                    />
                    Scanning…
                  </div>
                ) : (
                  <div style={{ color: "var(--muted-foreground, #6b7280)" }}>
                    No offsite backups listed.
                  </div>
                )}
              </div>
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  alignItems: "end",
                  marginTop: 12,
                  flexWrap: "wrap",
                }}
              >
                <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
                  Keep newest
                  <input
                    type="number"
                    min={0}
                    max={10000}
                    value={offsiteKeep ?? listing?.offsiteRetention?.keep ?? listing?.config?.offsiteKeep ?? 30}
                    onChange={(e) =>
                      setOffsiteKeep(Math.max(0, Math.min(10000, Number(e.target.value) || 0)))
                    }
                    style={{
                      padding: "4px 8px",
                      border: "1px solid var(--border, #e5e7eb)",
                      borderRadius: 4,
                      width: 90,
                    }}
                  />
                </label>
                <ActionButton
                  label="Prune offsite (GDrive)"
                  busy={busy === "prune-off"}
                  onClick={triggerPruneOffsite}
                  variant="danger"
                  hint="Deletes oldest GDrive folders beyond the keep count"
                  elapsedMs={elapsedMs}
                />
                <span style={{ fontSize: 11, color: "var(--muted-foreground, #6b7280)" }}>
                  {(listing?.offsiteRetention?.candidates ?? 0) > 0
                    ? `${listing?.offsiteRetention?.candidates} candidate(s) to delete`
                    : "No candidates to delete"}
                </span>
              </div>
            </div>
          </section>

          <section
            style={{
              padding: 16,
              border: "1px solid var(--border, #e5e7eb)",
              borderRadius: 8,
            }}
          >
            <h3 style={{ marginTop: 0, fontSize: 16 }}>Run backup &amp; restore</h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <ActionButton
                  label={runningNow ? "Backup running…" : "Run backup now"}
                  busy={busy === "backup" || runningNow != null}
                  onClick={triggerBackup}
                  hint={runningNow
                    ? `Backup in background (pid=${runningNow.pid}); will refresh when done`
                    : "Pushes latest DB + instance data to GDrive"}
                  elapsedMs={runningNow ? Date.now() - new Date(runningNow.startedAt).getTime() : elapsedMs}
                  disabled={runningNow != null}
                />
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
                  Backup path (empty = latest)
                  <input
                    type="text"
                    placeholder="latest"
                    value={restorePath}
                    onChange={(e) => setRestorePath(e.target.value)}
                    style={{
                      padding: "4px 8px",
                      border: "1px solid var(--border, #e5e7eb)",
                      borderRadius: 4,
                      fontFamily: "ui-monospace, monospace",
                      fontSize: 12,
                    }}
                  />
                </label>
                <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
                  Restore destination
                  <input
                    type="text"
                    value={restoreDest}
                    onChange={(e) => setRestoreDest(e.target.value)}
                    style={{
                      padding: "4px 8px",
                      border: "1px solid var(--border, #e5e7eb)",
                      borderRadius: 4,
                      fontFamily: "ui-monospace, monospace",
                      fontSize: 12,
                    }}
                  />
                </label>
                <ActionButton
                  label="Restore from offsite"
                  busy={busy === "restore-off"}
                  onClick={triggerRestoreOffsite}
                  variant="danger"
                  hint="Downloads + extracts the chosen backup"
                  elapsedMs={elapsedMs}
                />
              </div>
            </div>
          </section>
        </>
      ) : null}

      {tab === "cleanup" ? (
        <CleanupPanel
          companyId={companyId}
          listing={cleanupListing ?? null}
          listingError={cleanupListingError}
          onRefresh={() => setRefreshTick((n) => n + 1)}
        />
      ) : null}

      {tab === "recovery" ? (
        <ForceRecoverySection tierProgress={tierProgress}
        
          forceBackup={forceBackup}
          forceRestore={forceRestore}
          deleteRecoverySnapshots={deleteRecoverySnapshots}
          uploadDailyBackup={uploadDailyBackup}
          uploadHourlyBackup={uploadHourlyBackup}
          setTierKeep={setTierKeep}
          recoverySnapshots={recoverySnapshots ?? null}
          recoverySnapshotsError={recoverySnapshotsError}
          tierStatus={tierStatus ?? null}
          refreshRecoverySnapshots={() => setRefreshTick((n) => n + 1)}
          forceRunning={forceRunning}
        />
      ) : null}

      {tab === "manager" ? <ResultBanner result={result} onDismiss={() => setResult(null)} /> : null}
    </article>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      style={{
        padding: "8px 14px",
        fontSize: 13,
        fontWeight: active ? 600 : 500,
        color: active ? "var(--foreground)" : "var(--muted-foreground, #6b7280)",
        background: "transparent",
        border: "none",
        borderBottom: active ? "2px solid var(--primary, #2563eb)" : "2px solid transparent",
        cursor: "pointer",
        marginBottom: -1,
      }}
    >
      {children}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Force recovery section (extracted to keep the manager page readable)
// ---------------------------------------------------------------------------

function ForceRecoverySection({
  forceBackup,
  forceRestore,
  deleteRecoverySnapshots,
  uploadDailyBackup,
  uploadHourlyBackup,
  setTierKeep,
  recoverySnapshots,
  recoverySnapshotsError,
  tierStatus,
  refreshRecoverySnapshots,
  forceRunning,
  tierProgress,
}: {
  forceBackup: ReturnType<typeof usePluginAction>;
  forceRestore: ReturnType<typeof usePluginAction>;
  deleteRecoverySnapshots: ReturnType<typeof usePluginAction>;
  uploadDailyBackup: ReturnType<typeof usePluginAction>;
  uploadHourlyBackup: ReturnType<typeof usePluginAction>;
  setTierKeep: ReturnType<typeof usePluginAction>;
  recoverySnapshots: RecoverySnapshots | null;
  recoverySnapshotsError: string | null;
  tierStatus: TierStatus | null;
  refreshRecoverySnapshots: () => void;
  tierProgress?: TierUploadProgress | null;
  forceRunning: {
    pid: number;
    startedAt: string;
    cmd?: string;
    stage?: string;
    stageDetail?: string;
    progress?: { percent: number | null; totalBytes?: number; uploadBytes?: number; rclonePid?: number } | null;
    isForced: boolean;
    children?: Array<{ pid: number; startedAt: string }>;
  } | null;
}) {
  function formatTimestamp(iso: string | null | undefined): string {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return String(iso);
      const pad = (n: number) => (n < 10 ? "0" + n : "" + n);
      const Y = d.getFullYear();
      const M = pad(d.getMonth() + 1);
      const D = pad(d.getDate());
      const h = pad(d.getHours());
      const m = pad(d.getMinutes());
      const s = pad(d.getSeconds());
      const tzMatch = (d.toString().match(/\(([^)]+)\)$/) || [])[1] || "";
      const tz = tzMatch || "local";
      return `${Y}-${M}-${D} ${h}:${m}:${s} ${tz}`;
    } catch {
      return String(iso);
    }
  }

  const [open, setOpen] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [last, setLast] = useState<{ ok: boolean; message: string } | null>(null);
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [showStubs, setShowStubs] = useState(false);

  const snaps = recoverySnapshots && Array.isArray(recoverySnapshots.snapshots) ? recoverySnapshots.snapshots : [];
  const visibleSnaps = showStubs
    ? snaps
    : snaps.filter((s) => (s.apparentBytes ?? 0) >= 1024 || (s.bytes ?? 0) >= 1024);
  const stubCount = snaps.length - visibleSnaps.length;
  const snapCount = visibleSnaps.length;
  const totalApparentBytes =
    recoverySnapshots && typeof recoverySnapshots.totalApparentBytes === "number"
      ? recoverySnapshots.totalApparentBytes
      : snaps.reduce((a, s) => a + (s.apparentBytes ?? 0), 0);
  const totalDeltaBytes =
    recoverySnapshots && typeof recoverySnapshots.totalDeltaBytes === "number"
      ? recoverySnapshots.totalDeltaBytes
      : snaps.reduce((a, s) => a + (s.deltaBytes ?? s.bytes ?? 0), 0);
  const savingsBytes = Math.max(0, totalApparentBytes - totalDeltaBytes);
  const savingsPct = totalApparentBytes > 0 ? Math.round((savingsBytes / totalApparentBytes) * 100) : 0;
  const allSelected = snapCount > 0 && visibleSnaps.every((s) => !!selected[s.id]);
  const someSelected = visibleSnaps.some((s) => !!selected[s.id]);
  const selectedIds = visibleSnaps.filter((s) => !!selected[s.id]).map((s) => s.id);

  const toggleOne = (id: string) => {
    setSelected((prev) => {
      const next = { ...prev };
      if (next[id]) delete next[id];
      else next[id] = true;
      return next;
    });
  };
  const toggleAll = () => {
    if (allSelected) setSelected({});
    else {
      const next: Record<string, boolean> = {};
      snaps.forEach((s) => {
        next[s.id] = true;
      });
      setSelected(next);
    }
  };

  const doForceBackup = async () => {
    setBusy("force-backup");
    setLast(null);
    try {
      const r = (await forceBackup({})) as { message?: string; pid?: number };
      setLast({ ok: true, message: r?.message ?? `Force backup started (pid=${r?.pid})` });
    } catch (err) {
      setLast({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(null);
    }
  };

  const doForceRestore = async (id: string) => {
    setBusy(`force-restore-${id}`);
    setLast(null);
    try {
      const r = (await forceRestore({ subcommand: "restore", id })) as { ok?: boolean; message?: string; exitCode?: number };
      setLast({ ok: !!(r && r.ok), message: r?.message ?? `exit ${r?.exitCode}` });
    } catch (err) {
      setLast({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(null);
    }
  };

  const doDelete = async (ids: string[], opName: string) => {
    if (!ids || ids.length === 0) return;
    if (typeof window !== "undefined" && typeof window.confirm === "function") {
      const ok = window.confirm(
        `Delete ${ids.length} recovery snapshot${ids.length === 1 ? "" : "s"}?\n\n${ids.join(
          "\n",
        )}\n\nThis permanently removes the hardlink snapshot directories from disk. The latest 2 snapshots are protected and will be skipped.`,
      );
      if (!ok) return;
    }
    setBusy(opName);
    setLast(null);
    try {
      const r = (await deleteRecoverySnapshots({ ids })) as {
        deleted?: string[];
        skipped?: string[];
        errors?: string[];
        ok?: boolean;
        message?: string;
      };
      const deletedCount = Array.isArray(r?.deleted) ? r.deleted.length : 0;
      const skippedCount = Array.isArray(r?.skipped) ? r.skipped.length : 0;
      const errCount = Array.isArray(r?.errors) ? r.errors.length : 0;
      const skippedMsg = skippedCount > 0 ? ` (${skippedCount} skipped — newest 2 protected)` : "";
      setLast({
        ok: !!(r && r.ok !== false && errCount === 0),
        message: (r?.message ?? `Deleted ${deletedCount}`) + skippedMsg,
      });
      setSelected({});
      refreshRecoverySnapshots();
    } catch (err) {
      setLast({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(null);
    }
  };
  const doDeleteOne = (id: string) => doDelete([id], `force-delete-${id}`);
  const doDeleteSelected = () => doDelete(selectedIds.slice(), "force-delete-batch");

  function Tier({
    name,
    items,
    keep,
    count,
    last,
    error,
    onUpload,
    onChangeKeep,
    busyKey,
    busy,
    progress,
  }: {
    name: string;
    items: Array<{ id: string }>;
    keep: number;
    count: number;
    last: string | null | undefined;
    error: string | null | undefined;
    onUpload: () => void;
    onChangeKeep: (v: number) => void;
    busyKey: string;
    busy: string | null;
    progress: TierUploadProgress | undefined | null;
  }) {
    const idInput = `keep-input-${name}`;
    return (
      <div
        style={{
          padding: 12,
          border: "1px solid var(--border, #e5e7eb)",
          borderRadius: 6,
          background: "var(--card, #fafafa)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            marginBottom: 6,
          }}
        >
          <div>
            <strong
              style={{
                fontSize: 13,
                textTransform: "uppercase",
                letterSpacing: 0.5,
                color: name === "daily" ? "hsl(140, 60%, 35%)" : "hsl(35, 80%, 40%)",
              }}
            >
              {name} tier
            </strong>
            <span
              style={{
                marginLeft: 8,
                fontFamily: "ui-monospace, monospace",
                fontSize: 12,
              }}
            >
              count <strong>{count}</strong> / <strong>{keep}</strong>
            </span>
          </div>
          <ActionButton
            label={busy === busyKey ? "Uploading…" : `Upload latest to ${name}`}
            busy={busy === busyKey}
            onClick={onUpload}
          />
        </div>
        {progress && (progress.tier === name) && progress.lines.length > 0 ? (
          <div
            data-testid={`tier-progress-${name}`}
            style={{
              marginTop: 8,
              padding: "6px 8px",
              borderRadius: 4,
              background: "color-mix(in oklab, var(--muted) 15%, transparent)",
              fontFamily: "ui-monospace, monospace",
              fontSize: 11,
              color: "var(--muted-foreground, #6b7280)",
              maxHeight: 90,
              overflow: "auto",
            }}
          >
            {progress.lines.map((line, i) => (
              <div key={i} style={{ whiteSpace: "pre-wrap" }}>{line}</div>
            ))}
          </div>
        ) : null}
        {last ? (
          <div
            style={{
              fontSize: 11,
              fontFamily: "ui-monospace, monospace",
              color: "var(--muted-foreground, #6b7280)",
              marginBottom: 6,
            }}
          >
            most recent: {last}
          </div>
        ) : null}
        {items && items.length ? (
          <div
            style={{
              fontSize: 11,
              fontFamily: "ui-monospace, monospace",
              maxHeight: 70,
              overflow: "auto",
              padding: 4,
              background: "var(--muted, #f9fafb)",
              border: "1px solid var(--border, #e5e7eb)",
              borderRadius: 4,
              marginBottom: 6,
            }}
          >
            {items
              .slice()
              .sort((a, b) => (a.id < b.id ? 1 : a.id > b.id ? -1 : 0))
              .map((item) => (
                <div key={item.id} style={{ padding: "1px 0" }}>
                  {item.id}
                </div>
              ))}
          </div>
        ) : null}
        {error ? (
          <div
            style={{
              fontSize: 11,
              color: "var(--destructive, #b91c1c)",
              marginBottom: 6,
            }}
          >
            {error}
          </div>
        ) : null}
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
          <span>Retention (keep):</span>
          <input
            type="number"
            min={1}
            max={365}
            defaultValue={keep}
            id={idInput}
            style={{
              width: 60,
              padding: "2px 6px",
              border: "1px solid var(--border, #e5e7eb)",
              borderRadius: 4,
              color: "var(--foreground, #e5e7eb)",
              background: "var(--card, #1f2937)",
            }}
          />
          <button
            type="button"
            onClick={() => {
              const inp =
                typeof document !== "undefined"
                  ? (document.getElementById(idInput) as HTMLInputElement | null)
                  : null;
              const v = inp && inp.value ? parseInt(inp.value, 10) : NaN;
              onChangeKeep(v);
            }}
            style={{
              marginLeft: 4,
              padding: "2px 8px",
              fontSize: 11,
              border: "1px solid transparent",
              borderRadius: 4,
              background: "#1e40af",
              color: "#f8fafc",
              cursor: "pointer",
            }}
          >
            Save
          </button>
        </div>
      </div>
    );
  }

  function TierPanel({ progress }: { progress: TierUploadProgress | undefined | null }) {
    function doUpload(kind: "daily" | "hourly", action: ReturnType<typeof usePluginAction>) {
      setBusy(`upload-${kind}`);
      setLast({ ok: true, message: `uploading latest snapshot to ${kind} tier…` });
      (action({}) as Promise<{ message?: string; pid?: number }>)
        .then((r) => {
          setLast({
            ok: true,
            message: r?.message ?? `${kind} upload dispatched (pid=${r?.pid})`,
          });
        })
        .catch((err) => {
          setLast({ ok: false, message: errorMessage(err) });
        })
        .finally(() => {
          setBusy(null);
          setTimeout(refreshRecoverySnapshots, 2000);
        });
    }
    function doChangeKeep(tier: "daily" | "hourly", keepValue: number) {
      if (!Number.isFinite(keepValue) || keepValue < 1) {
        setLast({ ok: false, message: "keep must be a positive integer" });
        return;
      }
      setBusy(`set-keep-${tier}`);
      (setTierKeep({ tier, keep: keepValue }) as Promise<{ ok?: boolean; message?: string }>)
        .then((r) => {
          setLast({
            ok: !!(r && r.ok),
            message: r?.message ?? `Set ${tier} keep=${keepValue}`,
          });
        })
        .catch((err) => {
          setLast({ ok: false, message: errorMessage(err) });
        })
        .finally(() => {
          setBusy(null);
          setTimeout(refreshRecoverySnapshots, 1500);
        });
    }
    return (
      <div
        style={{
          marginTop: 8,
          padding: 10,
          border: "1px solid var(--border, #e5e7eb)",
          borderRadius: 6,
          background: "color-mix(in oklab, hsl(50, 60%, 95%) 30%, var(--card, #fff))",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 8,
          }}
        >
          <strong style={{ fontSize: 13 }}>GDrive tiered backup</strong>
          <span
            style={{
              fontSize: 11,
              color: "var(--muted-foreground, #6b7280)",
              fontFamily: "ui-monospace, monospace",
            }}
          >
            {tierStatus && tierStatus.enabled === false
              ? "disabled"
              : `root: ${tierStatus?.tierRoot ?? "Paperclip-Backups"}`}
          </span>
        </div>
        {tierStatus && tierStatus.enabled === false ? (
          <div style={{ fontSize: 12, color: "var(--muted-foreground, #6b7280)" }}>
            Tiered backup is disabled in plugin config.
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <Tier progress={progress}
              name="daily"
              items={tierStatus?.daily ?? []}
              keep={tierStatus?.keep?.daily ?? 3}
              count={tierStatus?.counts?.daily ?? 0}
              last={tierStatus?.lastUpload?.daily}
              error={tierStatus?.errors?.daily}
              onUpload={() => doUpload("daily", uploadDailyBackup)}
              onChangeKeep={(v) => doChangeKeep("daily", v)}
              busyKey="upload-daily"
              busy={busy}
            />
            <Tier progress={progress}
              name="hourly"
              items={tierStatus?.hourly ?? []}
              keep={tierStatus?.keep?.hourly ?? 2}
              count={tierStatus?.counts?.hourly ?? 0}
              last={tierStatus?.lastUpload?.hourly}
              error={tierStatus?.errors?.hourly}
              onUpload={() => doUpload("hourly", uploadHourlyBackup)}
              onChangeKeep={(v) => doChangeKeep("hourly", v)}
              busyKey="upload-hourly"
              busy={busy}
            />
          </div>
        )}
      </div>
    );
  }

  return (
    <section
      style={{
        marginTop: 16,
        padding: 16,
        border: "1px solid var(--border, #e5e7eb)",
        borderRadius: 8,
        background: "var(--card, #fafafa)",
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 8,
        }}
      >
        <h3 style={{ margin: 0, fontSize: 16 }}>Force backup &amp; recovery</h3>
        <div style={{ display: "flex", gap: 8 }}>
          <ActionButton
            label={
              busy === "force-backup"
                ? "Starting…"
                : forceRunning
                ? "Snapshot running…"
                : "Take recovery snapshot now"
            }
            busy={busy === "force-backup" || !!forceRunning}
            onClick={doForceBackup}
            hint="calls recovery.sh snapshot --no-upload (local hardlink-incremental; no GDrive upload)"
          />
          <ActionButton
            label={open ? "Hide recovery points" : "Pick recovery point"}
            onClick={() => setOpen(!open)}
          />
        </div>
      </header>
      <TierPanel progress={tierProgress} />
      {forceRunning ? (
        <div
          style={{
            marginTop: 8,
            marginBottom: 8,
            padding: 10,
            background: "color-mix(in oklab, var(--primary) 8%, var(--card))",
            border: "1px solid color-mix(in oklab, var(--primary) 20%, var(--border))",
            borderRadius: 6,
          }}
        >
          {(() => {
            const stage = forceRunning.stage || "running";
            const stageLabel =
              stage === "uploading"
                ? "Uploading snapshot to Google Drive"
                : stage === "packing"
                ? "Packing worktree (tar+gzip)"
                : stage === "pruning"
                ? "Pruning old snapshots"
                : stage === "snapshotting"
                ? "Creating incremental snapshot (rsync --link-dest)"
                : stage === "snapshot"
                ? "Creating snapshot"
                : stage === "running"
                ? "Snapshot running"
                : stage;
            const progress = forceRunning.progress;
            return (
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: 12,
                  }}
                >
                  <div>
                    <strong style={{ fontSize: 13 }}>{stageLabel}</strong>
                    <div
                      style={{
                        color: "var(--muted-foreground, #6b7280)",
                        fontSize: 11,
                        fontFamily: "ui-monospace, monospace",
                        marginTop: 2,
                      }}
                    >
                      pid {String(forceRunning.pid)} · started {formatTimestamp(forceRunning.startedAt)}
                      {forceRunning.stageDetail ? ` · ${String(forceRunning.stageDetail)}` : ""}
                    </div>
                  </div>
                  {progress && progress.percent !== null && progress.percent !== undefined ? (
                    <span
                      style={{
                        fontFamily: "ui-monospace, monospace",
                        fontSize: 13,
                        fontWeight: 600,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {progress.percent.toFixed(1)}%
                    </span>
                  ) : null}
                </div>
                {progress && progress.percent !== null && progress.percent !== undefined ? (
                  <div
                    style={{
                      height: 8,
                      background: "var(--muted, #f3f4f6)",
                      borderRadius: 4,
                      overflow: "hidden",
                      border: "1px solid var(--border, #e5e7eb)",
                    }}
                  >
                    <div
                      style={{
                        width: `${progress.percent}%`,
                        height: "100%",
                        background:
                          "linear-gradient(90deg, var(--primary, #2563eb) 0%, color-mix(in oklab, var(--primary, #2563eb) 70%, white) 100%)",
                        transition: "width 0.6s ease",
                      }}
                    />
                  </div>
                ) : null}
                {progress && progress.totalBytes ? (
                  <div
                    style={{
                      color: "var(--muted-foreground, #6b7280)",
                      fontSize: 11,
                      fontFamily: "ui-monospace, monospace",
                    }}
                  >
                    {((progress.uploadBytes ?? 0) / (1024 * 1024)).toFixed(1)} MiB /{" "}
                    {(progress.totalBytes / (1024 * 1024)).toFixed(0)} MiB · rclone pid{" "}
                    {String(progress.rclonePid)}
                    {(() => {
                      const child =
                        forceRunning.children && progress.rclonePid
                          ? forceRunning.children.find((c) => c.pid === progress.rclonePid)
                          : null;
                      if (!child || !child.startedAt) return "";
                      const elapsedMs = Date.now() - new Date(child.startedAt).getTime();
                      if (elapsedMs <= 0 || (progress.uploadBytes ?? 0) <= 0) return "";
                      const rate = (progress.uploadBytes ?? 0) / (elapsedMs / 1000);
                      const remaining = Math.max(0, progress.totalBytes - (progress.uploadBytes ?? 0));
                      if (rate <= 0) return "";
                      const etaSec = remaining / rate;
                      const etaLabel = etaSec >= 60 ? `${Math.round(etaSec / 60)} min` : `${Math.round(etaSec)} sec`;
                      return ` · ${(rate / (1024 * 1024)).toFixed(2)} MB/s · ETA ${etaLabel}`;
                    })()}
                  </div>
                ) : null}
                <div style={{ fontSize: 11, color: "var(--muted-foreground, #6b7280)" }}>
                  incremental rsync — typically finishes in seconds (only changed bytes are written; rest are hardlinks)
                </div>
              </div>
            );
          })()}
        </div>
      ) : null}
      <div style={{ marginTop: 4, marginBottom: 8, fontSize: 12, color: "var(--muted-foreground, #6b7280)" }}>
        Recovery snapshots: {snapCount} · logical {Math.round(totalApparentBytes / (1024 * 1024))} MiB if all
        restored · actual on-disk {Math.round(totalDeltaBytes / (1024 * 1024))} MiB (hardlink-deduped; saved{" "}
        {savingsPct}% / {Math.round(savingsBytes / (1024 * 1024))} MiB)
      </div>
      {last ? (
        <div
          style={{
            marginTop: 8,
            padding: 8,
            fontFamily: "ui-monospace, monospace",
            fontSize: 12,
            color: last.ok ? "var(--muted-foreground, #6b7280)" : "var(--destructive, #dc2626)",
            background: "var(--muted, #f3f4f6)",
            borderRadius: 4,
          }}
        >
          {last.message}
        </div>
      ) : null}
      {open ? (
        <div style={{ marginTop: 12 }}>
          {recoverySnapshotsError ? (
            <div style={{ color: "var(--destructive, #dc2626)", fontSize: 12, marginBottom: 8 }}>
              Could not list snapshots: {recoverySnapshotsError}
            </div>
          ) : null}
          {stubCount > 0 ? (
            <div
              style={{
                fontSize: 12,
                color: "var(--muted-foreground, #6b7280)",
                marginBottom: 8,
              }}
            >
              {stubCount} empty {stubCount === 1 ? "stub" : "stubs"} hidden — only {visibleSnaps.length} real{" "}
              {visibleSnaps.length === 1 ? "backup" : "backups"} on disk{" "}
              <button
                type="button"
                onClick={() => setShowStubs(!showStubs)}
                style={{
                  padding: "2px 8px",
                  fontSize: 11,
                  border: "1px solid transparent",
                  borderRadius: 4,
                  background: "var(--muted, #374151)",
                  cursor: "pointer",
                  color: "#f8fafc",
                }}
              >
                {showStubs ? "Hide stubs" : `Show ${stubCount} stub${stubCount === 1 ? "" : "s"}`}
              </button>
            </div>
          ) : null}
          {visibleSnaps.length === 0 && stubCount === 0 ? (
            <div style={{ color: "var(--muted-foreground, #6b7280)", fontSize: 12 }}>
              No snapshots available.
            </div>
          ) : null}
          {visibleSnaps.length > 0 ? (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "4px 10px",
                background: "var(--muted, #f3f4f6)",
                borderTop: "1px solid var(--border, #e5e7eb)",
                borderLeft: "1px solid var(--border, #e5e7eb)",
                borderRight: "1px solid var(--border, #e5e7eb)",
                fontSize: 12,
              }}
            >
              <input
                type="checkbox"
                checked={allSelected}
                onChange={toggleAll}
                aria-label="Select all snapshots"
              />
              <span style={{ flex: 1 }}>
                {allSelected
                  ? `All ${visibleSnaps.length} selected`
                  : someSelected
                  ? `${selectedIds.length} selected`
                  : "Select all"}
              </span>
              {someSelected ? (
                <ActionButton
                  label={`Delete selected (${selectedIds.length})`}
                  busy={busy === "force-delete-batch"}
                  variant="danger"
                  onClick={doDeleteSelected}
                />
              ) : null}
            </div>
          ) : null}
          <div
            style={{ border: "1px solid var(--border, #e5e7eb)", borderRadius: 4 }}
          >
            {(() => {
              const total = visibleSnaps.length;
              function ageColor(idx: number) {
                if (total <= 1) return "hsl(120, 60%, 35%)";
                const ratio = idx / (total - 1);
                const hue = 120 - 120 * ratio;
                return `hsl(${hue.toFixed(0)}, 55%, 38%)`;
              }
              return visibleSnaps.map((s, idx) => {
                const isProtected = idx < 2;
                const isMaster = idx === 0;
                const tsColor = ageColor(idx);
                return (
                  <div
                    key={s.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      padding: "6px 10px",
                      borderBottom: "1px solid var(--border, #e5e7eb)",
                      background: selected[s.id]
                        ? "var(--accent, #f3f4f6)"
                        : isMaster
                        ? "color-mix(in oklab, hsl(120, 55%, 60%) 8%, var(--card, #fff))"
                        : undefined,
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={!!selected[s.id]}
                      disabled={isProtected}
                      onChange={() => toggleOne(s.id)}
                      aria-label={`Select ${s.id}`}
                    />
                    <div
                      style={{
                        flex: 1,
                        fontFamily: "ui-monospace, monospace",
                        fontSize: 12,
                      }}
                    >
                      <strong>
                        {s.id}
                        {isMaster ? " · ● MASTER" : ""}
                        {isProtected && !isMaster ? " · protected" : ""}
                      </strong>
                      <div
                        style={{
                          color: tsColor,
                          fontSize: 11,
                          fontWeight: isMaster ? 600 : 400,
                        }}
                      >
                        {s.apparentBytes
                          ? `${Math.round(s.apparentBytes / (1024 * 1024))} MB${
                              s.deltaBytes !== undefined && s.deltaBytes !== null && s.apparentBytes
                                ? ` (new +${
                                    s.deltaBytes >= 1024 * 1024
                                      ? Math.round(s.deltaBytes / (1024 * 1024)) + " MB"
                                      : Math.max(1, Math.round(s.deltaBytes / 1024)) + " KB"
                                  })`
                                : ""
                            }`
                          : "—"}{" "}
                        · {formatTimestamp(s.timestamp)}
                      </div>
                    </div>
                    <ActionButton
                      label={busy === `force-restore-${s.id}` ? "Restoring…" : "Restore"}
                      busy={busy === `force-restore-${s.id}`}
                      onClick={() => doForceRestore(s.id)}
                      variant="danger"
                    />
                    {isProtected ? (
                      <span style={{ fontSize: 11, color: "var(--muted-foreground, #6b7280)" }}> </span>
                    ) : (
                      <ActionButton
                        label={busy === `force-delete-${s.id}` ? "Deleting…" : "Delete"}
                        busy={busy === `force-delete-${s.id}`}
                        variant="danger"
                        onClick={() => doDeleteOne(s.id)}
                      />
                    )}
                  </div>
                );
              });
            })()}
          </div>
          <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
            <ActionButton label="Refresh" onClick={refreshRecoverySnapshots} />
          </div>
        </div>
      ) : null}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Settings page
// ---------------------------------------------------------------------------

export function BackupSettingsPage({
  context,
}: {
  context: { companyId?: string | null };
}) {
  const host = useHostContext();
  const companyId = context.companyId ?? host.companyId ?? null;
  const saveConfig = usePluginAction("save-config");
  const [busy, setBusy] = useState<string | null>(null);
  const [config, setConfig] = useState<Record<string, unknown> | null>(null);
  const [saved, setSaved] = useState<{ ok: boolean; message: string } | null>(null);
  const listingConfigResult = usePluginData("config") as
    | PluginDataResult<Record<string, unknown>>
    | undefined;
  const listingConfig = listingConfigResult?.data;
  const error = listingConfigResult?.error ? String(listingConfigResult.error) : null;
  useEffect(() => {
    if (listingConfig && !config) setConfig(listingConfig);
  }, [listingConfig, config]);
  const update = (k: string, v: unknown) => {
    if (!config) return;
    setConfig({ ...config, [k]: v });
  };
  const save = async () => {
    if (!config || busy) return;
    setBusy("save");
    setSaved(null);
    try {
      const r = (await saveConfig({ ...config, companyId })) as { message?: string; config?: Record<string, unknown> };
      setSaved({ ok: true, message: r.message ?? "Saved" });
      if (r.config) setConfig(r.config);
    } catch (err) {
      setSaved({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(null);
    }
  };
  if (error) {
    return (
      <div style={{ padding: 16, color: "var(--destructive, #dc2626)" }}>
        Failed to load settings: {error}
      </div>
    );
  }
  if (!config) return <div style={{ padding: 16 }}>Loading…</div>;
  return (
    <article style={{ display: "grid", gap: 16, padding: 16 }}>
      <h2 style={{ margin: 0, fontSize: 20 }}>Backup settings</h2>
      <p style={{ color: "var(--muted-foreground, #6b7280)", fontSize: 13 }}>
        Paths to the existing backup / restore / prune scripts.
      </p>
      <div
        style={{
          display: "grid",
          gap: 12,
          padding: 16,
          border: "1px solid var(--border, #e5e7eb)",
          borderRadius: 8,
        }}
      >
        <Field
          label="Paperclip home"
          value={String(config.paperclipHome ?? "")}
          onChange={(v) => update("paperclipHome", v)}
        />
        <Field
          label="Backups subdir (under paperclipHome)"
          value={String(config.backupsSubdir ?? "")}
          onChange={(v) => update("backupsSubdir", v)}
        />
        <Field
          label="backup-to-drive.sh"
          value={String(config.backupScript ?? "")}
          onChange={(v) => update("backupScript", v)}
        />
        <Field
          label="restore-from-drive.sh"
          value={String(config.restoreScript ?? "")}
          onChange={(v) => update("restoreScript", v)}
        />
        <Field
          label="prune-local-dumps.sh"
          value={String(config.pruneScript ?? "")}
          onChange={(v) => update("pruneScript", v)}
        />
        <Field
          label="rclone config"
          value={String(config.rcloneConfig ?? "")}
          onChange={(v) => update("rcloneConfig", v)}
        />
        <Field
          label="rclone remote"
          value={String(config.rcloneRemote ?? "")}
          onChange={(v) => update("rcloneRemote", v)}
        />
        <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
          Default keep (newest N local dumps)
          <input
            type="number"
            min={1}
            max={365}
            value={Number(config.defaultKeep ?? 10)}
            onChange={(e) => update("defaultKeep", Math.max(1, Math.min(365, Number(e.target.value) || 10)))}
            style={{
              padding: "4px 8px",
              border: "1px solid var(--border, #e5e7eb)",
              borderRadius: 4,
              width: 100,
            }}
          />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
          Offsite keep (newest N GDrive folders; 0 = never auto-prune)
          <input
            type="number"
            min={0}
            max={10000}
            value={Number(config.offsiteKeep ?? 30)}
            onChange={(e) => update("offsiteKeep", Math.max(0, Math.min(10000, Number(e.target.value) || 0)))}
            style={{
              padding: "4px 8px",
              border: "1px solid var(--border, #e5e7eb)",
              borderRadius: 4,
              width: 100,
            }}
          />
        </label>
        <Field
          label="Offsite auto-prune schedule"
          value={String(config.offsiteSchedule ?? "")}
          onChange={(v) => update("offsiteSchedule", v)}
        />
      </div>
      <div>
        <ActionButton label="Save settings" busy={busy === "save"} onClick={save} />
      </div>
      {saved ? (
        <div
          style={{
            marginTop: 8,
            fontSize: 13,
            color: saved.ok ? "var(--success, #16a34a)" : "var(--destructive, #dc2626)",
          }}
        >
          {saved.message}
        </div>
      ) : null}
    </article>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
      {label}
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          padding: "4px 8px",
          border: "1px solid var(--border, #e5e7eb)",
          borderRadius: 4,
          fontFamily: "ui-monospace, monospace",
          fontSize: 12,
        }}
      />
    </label>
  );
}
