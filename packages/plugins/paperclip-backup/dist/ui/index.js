import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useHostContext, useHostLocation, useHostNavigation, usePluginAction, usePluginData, } from "@paperclipai/plugin-sdk/ui";
import { useEffect, useState } from "react";
function formatBytes(bytes) {
    if (bytes <= 0)
        return "0 B";
    const units = ["B", "KiB", "MiB", "GiB", "TiB"];
    let v = bytes;
    let i = 0;
    while (v >= 1024 && i < units.length - 1) {
        v /= 1024;
        i++;
    }
    return `${v.toFixed(v >= 100 ? 0 : 1)} ${units[i]}`;
}
function formatDate(iso) {
    if (!iso)
        return "—";
    try {
        const d = new Date(iso);
        if (Number.isNaN(d.getTime()))
            return iso;
        return d.toISOString().replace("T", " ").replace(/\..+/, " UTC");
    }
    catch {
        return iso;
    }
}
function StatusDot({ ok }) {
    const color = ok ? "var(--success, #16a34a)" : "var(--destructive, #dc2626)";
    return (_jsx("span", { "aria-hidden": "true", style: {
            display: "inline-block",
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: color,
            marginRight: 6,
            verticalAlign: "middle",
        } }));
}
function ActionButton(props) {
    const variant = props.variant ?? "primary";
    // Use hardcoded dark colors instead of `var(--primary)` /
    // `var(--primary-foreground)` etc. The host's theme variables
    // resolve to near-white in dark mode (--primary → oklch(0.985 0 0)),
    // which would render the "primary" buttons as bright white blocks
    // against the dark page. Hardcoding keeps the buttons visually
    // consistent regardless of theme.
    //   primary → dark blue (#1e40af, Tailwind blue-800)
    //   danger  → dark red  (#b91c1c, Tailwind red-700)
    //   default → dark slate (#374151, Tailwind slate-700)
    // All variants get light text (#f8fafc) for contrast on the dark fill.
    const isPrimary = variant === "primary";
    const isDanger = variant === "danger";
    const baseStyle = {
        padding: "8px 14px",
        borderRadius: 6,
        fontWeight: 500,
        fontSize: 13,
        cursor: props.busy || props.disabled ? "not-allowed" : "pointer",
        opacity: props.busy || props.disabled ? 0.6 : 1,
        border: "1px solid transparent",
        background: isPrimary
            ? "#1e40af"
            : isDanger
                ? "#b91c1c"
                : "#374151",
        color: "#f8fafc",
        borderColor: isDanger ? "#991b1b" : "transparent",
    };
    const elapsed = props.busy && props.elapsedMs != null
        ? ` (${Math.floor(props.elapsedMs / 1000)}s)`
        : "";
    return (_jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 4 }, children: [_jsx("button", { type: "button", onClick: props.onClick, disabled: props.busy || props.disabled, style: baseStyle, children: props.busy ? `Working…${elapsed}` : props.label }), props.hint ? (_jsx("span", { style: { fontSize: 11, color: "var(--muted-foreground, #6b7280)" }, children: props.hint })) : null] }));
}
/**
 * Extract a human-readable error message from anything thrown by the
 * bridge. The plugin bridge throws `PluginBridgeError` (a plain object with
 * `{ code, message, details }`); an `Error`; or sometimes a string.
 */
function errorMessage(err) {
    if (err == null)
        return "Unknown error";
    if (typeof err === "string")
        return err;
    if (err instanceof Error)
        return err.message;
    if (typeof err === "object") {
        const obj = err;
        if (typeof obj.message === "string" && obj.message.length > 0) {
            const detail = obj.details;
            if (detail && typeof detail === "object") {
                const detailMsg = detail.message;
                if (typeof detailMsg === "string" && detailMsg.length > 0 && detailMsg !== obj.message) {
                    return `${obj.message} — ${detailMsg}`;
                }
            }
            return obj.message;
        }
        if (typeof obj.code === "string")
            return obj.code;
        try {
            return JSON.stringify(err);
        }
        catch {
            return String(err);
        }
    }
    return String(err);
}
function useElapsedMs(running) {
    const [start, setStart] = useState(null);
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
function ResultBanner({ result, onDismiss, }) {
    if (!result)
        return null;
    const isOk = result.ok;
    return (_jsxs("div", { role: "status", style: {
            padding: 12,
            borderRadius: 6,
            border: `1px solid ${isOk ? "var(--success, #16a34a)" : "var(--destructive, #dc2626)"}`,
            background: isOk
                ? "color-mix(in oklab, var(--success) 8%, var(--card))"
                : "color-mix(in oklab, var(--destructive) 8%, var(--card))",
            color: isOk ? "var(--success, #16a34a)" : "var(--destructive, #dc2626)",
            display: "grid",
            gap: 6,
        }, children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }, children: [_jsx("strong", { style: { fontSize: 13 }, children: result.message ?? (isOk ? "Success" : "Failed") }), _jsx("button", { type: "button", onClick: onDismiss, style: {
                            background: "transparent",
                            border: "none",
                            color: "inherit",
                            cursor: "pointer",
                            fontSize: 16,
                            lineHeight: 1,
                        }, "aria-label": "Dismiss", children: "\u00D7" })] }), result.keep != null ? _jsxs("div", { style: { fontSize: 12 }, children: ["keep = ", result.keep] }) : null, result.remotePath ? (_jsxs("div", { style: { fontSize: 12, fontFamily: "ui-monospace, monospace" }, children: [result.remotePath, " \u2192 ", result.destDir ?? "(default)"] })) : null, result.totalBytesBefore != null && result.totalBytesAfter != null ? (_jsxs("div", { style: { fontSize: 12 }, children: [formatBytes(result.totalBytesBefore), " \u2192 ", formatBytes(result.totalBytesAfter), " (", result.prunedCount ?? 0, " pruned)"] })) : null, result.stdout ? (_jsxs("details", { children: [_jsx("summary", { style: { fontSize: 12, cursor: "pointer" }, children: "stdout" }), _jsx("pre", { style: {
                            fontSize: 11,
                            maxHeight: 160,
                            overflow: "auto",
                            background: "var(--muted, #f3f4f6)",
                            padding: 8,
                            borderRadius: 4,
                            marginTop: 4,
                        }, children: result.stdout })] })) : null, result.stderr ? (_jsxs("details", { children: [_jsx("summary", { style: { fontSize: 12, cursor: "pointer" }, children: "stderr" }), _jsx("pre", { style: {
                            fontSize: 11,
                            maxHeight: 160,
                            overflow: "auto",
                            background: "var(--muted, #f3f4f6)",
                            padding: 8,
                            borderRadius: 4,
                            marginTop: 4,
                        }, children: result.stderr })] })) : null] }));
}
// ---------------------------------------------------------------------------
// Sidebar nav entry — links to the Backup Manager page
// ---------------------------------------------------------------------------
export function BackupSidebarNavItem({ context }) {
    const host = useHostContext();
    const hostNavigation = useHostNavigation();
    const hostLocation = useHostLocation();
    const companyPrefix = context.companyPrefix ?? host.companyPrefix;
    const href = companyPrefix ? `/${companyPrefix}/backups` : "/backups";
    const isActive = hostLocation.pathname === href || hostLocation.pathname.startsWith(`${href}/`);
    return (_jsxs("a", { ...hostNavigation.linkProps(href), className: "flex items-center gap-2.5 px-3 py-2 pointer-coarse:py-1.5 text-[13px] font-medium transition-colors " +
            (isActive
                ? "bg-accent text-foreground"
                : "text-foreground/80 hover:bg-accent/50 hover:text-foreground"), style: { textDecoration: "none" }, children: [_jsx("svg", { viewBox: "0 0 24 24", className: "shrink-0 h-4 w-4", fill: "none", stroke: "currentColor", strokeWidth: "1.6", strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": "true", children: [_jsx("ellipse", { cx: "12", cy: "5", rx: "9", ry: "3", fill: "currentColor", fillOpacity: "0.18", stroke: "currentColor" }), _jsx("path", { d: "M3 5v14a9 3 0 0 0 18 0V5" }), _jsx("path", { d: "M3 12a9 3 0 0 0 18 0", fill: "currentColor", fillOpacity: "0.18", stroke: "currentColor" })] }), _jsx("span", { className: "flex-1 truncate", children: "Backups" })] }));
}
// ---------------------------------------------------------------------------
// Dashboard widget — at-a-glance status
// ---------------------------------------------------------------------------
export function BackupDashboardWidget({ context }) {
    const host = useHostContext();
    const companyId = context.companyId ?? host.companyId ?? null;
    const runBackup = usePluginAction("run-backup");
    const [refreshTick, setRefreshTick] = useState(0);
    const [result, setResult] = useState(null);
    const [busy, setBusy] = useState(false);
    const elapsedMs = useElapsedMs(busy);
    const { data: status, error } = usePluginData("status", { companyId, _tick: refreshTick });
    // The backup script runs detached and takes ~30-40 min. Reflect that
    // in the UI: while the worker reports a live pid, the button stays
    // "Working…" and we poll for status every 30s. The action RPC itself
    // returns instantly with `pid: N`.
    const running = status?.backupRunning ?? null;
    const runningElapsedMs = running
        ? Date.now() - new Date(running.startedAt).getTime()
        : 0;
    const isBusy = busy || running != null;
    // Auto-refresh while a backup is running so we pick up completion
    // without the user clicking anything.
    useEffect(() => {
        if (!running)
            return;
        const t = setInterval(() => setRefreshTick((n) => n + 1), 30 * 1000);
        return () => clearInterval(t);
    }, [running?.pid, running?.startedAt]);
    const triggerBackup = async () => {
        if (busy || running)
            return;
        setBusy(true);
        setResult(null);
        try {
            const r = (await runBackup({ companyId }));
            if (r.alreadyRunning) {
                setResult({
                    ok: false,
                    exitCode: null,
                    message: r.message ?? "Backup already running",
                });
            }
            else if (r.async || r.pid) {
                setResult({
                    ok: true,
                    exitCode: 0,
                    message: r.message ?? `Backup started (pid=${r.pid})`,
                });
            }
            else {
                setResult({
                    ok: r.ok === true,
                    exitCode: r.exitCode ?? null,
                    message: r.message ?? (r.ok === true ? "Backup pushed to offsite" : "Backup script failed"),
                    durationMs: r.durationMs,
                    stdout: r.stdout,
                    stderr: r.stderr,
                });
            }
        }
        catch (err) {
            setResult({ ok: false, exitCode: null, message: errorMessage(err) });
        }
        finally {
            setBusy(false);
            setRefreshTick((n) => n + 1);
        }
    };
    const newest = status?.local?.newest;
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
    }
    else if (status?.backupLastRun) {
        const last = status.backupLastRun;
        const okLabel = last.ok ? "ok" : "failed";
        subtitle = `Last backup: ${okLabel} — ${last.message}`;
    }
    return (_jsxs("section", { "aria-label": "Backup status", style: { display: "grid", gap: 12 }, children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center" }, children: [_jsxs("div", { children: [_jsxs("h3", { style: { margin: 0, fontSize: 14, fontWeight: 600 }, children: [_jsx(StatusDot, { ok: isOk && !running }), "Backup status"] }), _jsx("div", { style: { fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: subtitle })] }), _jsx(ActionButton, { label: running ? "Backup running…" : "Run backup now", busy: isBusy, onClick: triggerBackup, elapsedMs: running ? runningElapsedMs : elapsedMs, disabled: running != null })] }), _jsxs("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }, children: [_jsxs("div", { style: { padding: 12, border: "1px solid var(--border, #e5e7eb)", borderRadius: 6 }, children: [_jsx("div", { style: { fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: "Local DB dumps" }), _jsx("div", { style: { fontSize: 22, fontWeight: 600 }, children: status?.local?.count ?? "—" }), _jsxs("div", { style: { fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: [status?.local ? formatBytes(status.local.totalBytes) : "—", " total"] })] }), _jsxs("div", { style: { padding: 12, border: "1px solid var(--border, #e5e7eb)", borderRadius: 6 }, children: [_jsx("div", { style: { fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: "Offsite backups (GDrive)" }), _jsx("div", { style: { fontSize: 22, fontWeight: 600 }, children: status?.offsite?.count ?? "—" }), _jsx("div", { style: { fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: newest ? `Newest: ${formatDate(newest.mtime)}` : "—" })] })] }), _jsx(ResultBanner, { result: result, onDismiss: () => setResult(null) })] }));
}
// ---------------------------------------------------------------------------
// Main Backup Manager page
// ---------------------------------------------------------------------------
export function BackupManagerPage({ context }) {
    const host = useHostContext();
    const companyId = context.companyId ?? host.companyId ?? null;
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
    const [refreshTick, setRefreshTick] = useState(0);
    // _tick: refreshTick ensures the picker re-fetches when the user clicks
    // "Refresh" (see refreshRecoverySnapshots below). Without it, the React
    // hook keeps returning the cached result and a newly-created snapshot
    // wouldn't appear until the next SDK-side refetch.
    const recoverySnapshotsResult = usePluginData("recovery-snapshots", { _tick: refreshTick });
    const recoverySnapshots = recoverySnapshotsResult && recoverySnapshotsResult.data;
    const recoverySnapshotsError = recoverySnapshotsResult && recoverySnapshotsResult.error;
    const tierStatusResult = usePluginData("gdrive-tier-status", { _tick: refreshTick });
    const tierStatus = tierStatusResult && tierStatusResult.data;
    const { data: statusData } = usePluginData("status", { companyId });
    // Prefer /proc-detected running recovery script (works for orphans and any
    // script the worker spawned). Fall back to in-state backupRunning if /proc
    // finds nothing. ONLY consider recovery.sh here, not backup-to-drive.sh
    // — that belongs to the Backup status widget above.
    const procRunning = recoverySnapshots && Array.isArray(recoverySnapshots.runningSnapshots)
        ? recoverySnapshots.runningSnapshots.find(function (r) { return /recovery\.sh/.test(r.cmd || ""); }) || null
        : null;
    const stateRunning = statusData && statusData.backupRunning ? statusData.backupRunning : null;
    const stateRecovery = stateRunning && stateRunning.recovery === true;
    const stateForced = stateRunning && stateRunning.isForced === true;
    const forceRunning = procRunning
        ? { pid: procRunning.pid, startedAt: procRunning.startedAt, cmd: procRunning.cmd, stage: procRunning.stage, stageDetail: procRunning.stageDetail, progress: procRunning.progress, isForced: stateForced || /--force/.test(procRunning.cmd || "") }
        : (stateRecovery && stateForced ? stateRunning : null);
    const [busy, setBusy] = useState(null);
    const [result, setResult] = useState(null);
    const [restorePath, setRestorePath] = useState("");
    const [restoreDest, setRestoreDest] = useState("/tmp/paperclip-restore");
    const [restoreFile, setRestoreFile] = useState("");
    const [keep, setKeep] = useState(10);
    const [offsiteKeep, setOffsiteKeep] = useState(null);
    const elapsedMs = useElapsedMs(busy != null);
    const { data: listing, error } = usePluginData("listing", {
        companyId,
        _tick: refreshTick,
    });
    const { data: status } = usePluginData("status", { companyId });
    // Locations — every path the operator needs to know about: where
    // local DB dumps live, where recovery.sh snapshots are stored, where
    // the per-company / hourly / daily gdrive prefixes sit, and where
    // the rclone config + pass file live on disk.
    const { data: locationsData } = usePluginData("locations", {});
    // While a backup is detached-running in the background, poll every
    // 30s so the page picks up completion (and the running marker clears)
    // without the user clicking anything.
    const runningNow = status?.backupRunning ?? null;
    useEffect(() => {
        if (busy !== "backup" && !runningNow)
            return;
        const t = setInterval(() => setRefreshTick((n) => n + 1), 30 * 1000);
        return () => clearInterval(t);
    }, [busy, runningNow?.pid, runningNow?.startedAt]);
    const triggerBackup = async () => {
        if (busy)
            return;
        setBusy("backup");
        setResult(null);
        try {
            const r = (await runBackup({ companyId }));
            if (r.alreadyRunning) {
                setResult({
                    ok: false,
                    exitCode: null,
                    message: r.message ?? "Backup already running",
                });
            }
            else if (r.async || r.pid) {
                setResult({
                    ok: true,
                    exitCode: 0,
                    message: r.message ?? `Backup started in background (pid=${r.pid})`,
                });
            }
            else {
                setResult({
                    ok: r.ok === true,
                    exitCode: r.exitCode ?? null,
                    message: r.message ?? (r.ok === true ? "Backup pushed" : "Backup script failed"),
                    durationMs: r.durationMs,
                    stdout: r.stdout,
                    stderr: r.stderr,
                });
            }
        }
        catch (err) {
            setResult({ ok: false, exitCode: null, message: errorMessage(err) });
        }
        finally {
            setBusy(null);
            setRefreshTick((n) => n + 1);
        }
    };
    const triggerPrune = async () => {
        if (busy)
            return;
        setBusy("prune");
        setResult(null);
        try {
            const r = (await pruneLocal({ keep }));
            setResult({
                ok: r.ok === true,
                exitCode: r.exitCode ?? null,
                message: r.ok === true ? `Pruned, kept ${r.keep ?? keep}` : "Prune failed",
                durationMs: r.durationMs,
                stdout: r.stdout,
                stderr: r.stderr,
                keep: r.keep ?? keep,
                totalBytesBefore: r.totalBytesBefore,
                totalBytesAfter: r.totalBytesAfter,
                prunedCount: r.prunedCount,
            });
        }
        catch (err) {
            setResult({ ok: false, exitCode: null, message: errorMessage(err) });
        }
        finally {
            setBusy(null);
            setRefreshTick((n) => n + 1);
        }
    };
    const triggerRestoreOffsite = async () => {
        if (busy)
            return;
        setBusy("restore-off");
        setResult(null);
        try {
            const r = (await restoreOffsite({
                companyId,
                path: restorePath || "latest",
                destDir: restoreDest,
            }));
            const usedPath = (r.remotePath ?? restorePath) || "latest";
            setResult({
                ok: r.ok === true,
                exitCode: r.exitCode ?? null,
                message: r.ok === true ? `Restored from ${usedPath}` : "Restore failed",
                durationMs: r.durationMs,
                stdout: r.stdout,
                stderr: r.stderr,
                remotePath: usedPath,
                destDir: r.destDir ?? restoreDest,
            });
        }
        catch (err) {
            setResult({ ok: false, exitCode: null, message: errorMessage(err) });
        }
        finally {
            setBusy(null);
        }
    };
    const triggerPruneOffsite = async () => {
        if (busy)
            return;
        const keep = offsiteKeep ??
            listing?.offsiteRetention?.keep ??
            listing?.config?.offsiteKeep ??
            30;
        setBusy("prune-off");
        setResult(null);
        try {
            const r = (await pruneOffsite({ companyId, keep }));
            // The prune-offsite action runs detached (rclone rm/purge can take
            // many minutes on GDrive) so the RPC returns immediately with
            // async:true. The UI must recognize this and tell the user the
            // prune is running in the background — the real counts arrive
            // later via usePluginData("status").offsiteLastRun.
            if (r.alreadyRunning) {
                const elapsed = typeof r.elapsedMs === "number"
                    ? ` (already running for ${Math.round(r.elapsedMs / 1000)}s)`
                    : "";
                setResult({
                    ok: false,
                    exitCode: null,
                    message: r.message ?? `Offsite prune already running${elapsed}. Pass force:true to override.`,
                });
                return;
            }
            if (r.async === true || r.startedAt) {
                setResult({
                    ok: true,
                    exitCode: 0,
                    async: true,
                    message: r.message ?? `Prune started in background (keep=${keep}). Watch the offsite count decrease — this can take several minutes for GDrive.`,
                    startedAt: r.startedAt,
                    keep: r.keep ?? keep,
                    prunedCount: null,
                    deletedPaths: null,
                });
                return;
            }
            const pruned = r.offsitePruned ?? 0;
            const kept = r.offsiteKept ?? 0;
            setResult({
                ok: r.ok === true,
                exitCode: r.exitCode ?? null,
                message: r.ok === true
                    ? pruned === 0
                        ? `Nothing to prune — already at or below keep=${keep}.`
                        : `Pruned ${pruned} offsite backups (kept newest ${kept}).`
                    : r.message ?? "Prune failed",
                durationMs: r.durationMs,
                totalBytesBefore: r.totalBytesBefore,
                totalBytesAfter: r.totalBytesAfter,
                prunedCount: pruned,
                deletedPaths: r.deletedPaths,
            });
        }
        catch (err) {
            setResult({ ok: false, exitCode: null, message: errorMessage(err) });
        }
        finally {
            setBusy(null);
            setRefreshTick((n) => n + 1);
        }
    };
    const triggerRestoreLocal = async () => {
        if (busy || !restoreFile)
            return;
        setBusy("restore-loc");
        setResult(null);
        try {
            const r = (await restoreLocal({ filename: restoreFile, destDir: restoreDest }));
            setResult({
                ok: r.ok === true,
                exitCode: r.exitCode ?? null,
                message: r.ok === true ? `Copied ${restoreFile}` : "Restore failed",
                durationMs: r.durationMs,
                stdout: r.stdout,
                stderr: r.stderr,
                source: "local",
                destDir: r.destDir ?? restoreDest,
            });
        }
        catch (err) {
            setResult({ ok: false, exitCode: null, message: errorMessage(err) });
        }
        finally {
            setBusy(null);
        }
    };
    return (_jsxs("article", { style: { display: "grid", gap: 16, padding: 16 }, children: [_jsxs("header", { children: [_jsx("h2", { style: { margin: 0, fontSize: 20 }, children: "Backup Manager" }), _jsx("p", { style: { marginTop: 4, color: "var(--muted-foreground, #6b7280)", fontSize: 13 }, children: "Offsite push (rclone \u2192 GDrive) and local DB-dump retention." })] }), _jsxs("section", { style: { padding: 16, border: "1px solid var(--border, #e5e7eb)", borderRadius: 8, background: "color-mix(in oklab, var(--muted) 4%, var(--card))" }, children: [_jsx("h3", { style: { marginTop: 0, fontSize: 16 }, children: "Backup locations" }), _jsx("p", { style: { marginTop: 0, marginBottom: 8, color: "var(--muted-foreground, #6b7280)", fontSize: 12 }, children: "Every path the operator needs to know about. Locations are read from the live config and rclone environment each render." }), _jsx("table", { style: { width: "100%", borderCollapse: "collapse", fontSize: 12, fontFamily: "ui-monospace, monospace" }, children: [_jsx("thead", { children: _jsxs("tr", { style: { textAlign: "left", color: "var(--muted-foreground, #6b7280)" }, children: [_jsx("th", { style: { padding: "4px 6px", width: 180 }, children: "What" }), _jsx("th", { style: { padding: "4px 6px" }, children: "Path / Where" }), _jsx("th", { style: { padding: "4px 6px", width: 200 }, children: "Note" })] }) }), _jsx("tbody", { children: (locationsData === null || locationsData === void 0 ? [] : (locationsData.items || [])).map((it) => (_jsxs("tr", { style: { borderTop: "1px solid var(--border, #e5e7eb)" }, children: [_jsx("td", { style: { padding: "4px 6px", color: "var(--muted-foreground, #6b7280)" }, children: it.id }), _jsx("td", { style: { padding: "4px 6px", wordBreak: "break-all" }, children: it.path }), _jsx("td", { style: { padding: "4px 6px", color: "var(--muted-foreground, #6b7280)" }, children: it.note || "" })] }, it.id))) })] }) ]}) , error ? (_jsxs("div", { role: "alert", style: {
                    padding: 12,
                    border: "1px solid var(--destructive, #dc2626)",
                    borderRadius: 6,
                    background: "color-mix(in oklab, var(--destructive) 8%, var(--card))",
                    color: "var(--destructive)",
                }, children: ["Failed to load: ", error] })) : listing?.missingCompanyId ? (_jsx("div", { role: "alert", style: {
                    padding: 12,
                    border: "1px solid var(--border, #e5e7eb)",
                    borderRadius: 6,
                    background: "color-mix(in oklab, var(--muted) 30%, var(--card))",
                    color: "var(--muted-foreground, #6b7280)",
                }, children: "No active company. Open this page from a company context (e.g. /BTCAAAAA/backups)." })) : null, _jsxs("section", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }, children: [_jsxs("div", { style: { padding: 16, border: "1px solid var(--border, #e5e7eb)", borderRadius: 8 }, children: [_jsxs("header", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }, children: [_jsx("h3", { style: { margin: 0, fontSize: 16 }, children: "Local DB dumps" }), _jsxs("span", { style: { fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: [listing?.local.count ?? "—", " files / ", listing ? formatBytes(listing.local.totalBytes) : "—"] })] }), _jsx("div", { style: { maxHeight: 240, overflow: "auto", fontSize: 12 }, children: listing?.local.dumps.length ? (_jsxs("table", { style: { width: "100%", borderCollapse: "collapse" }, children: [_jsx("thead", { children: _jsxs("tr", { style: { textAlign: "left", color: "var(--muted-foreground, #6b7280)" }, children: [_jsx("th", { style: { padding: "4px 6px" }, children: "File" }), _jsx("th", { style: { padding: "4px 6px" }, children: "Modified" }), _jsx("th", { style: { padding: "4px 6px", textAlign: "right" }, children: "Size" })] }) }), _jsx("tbody", { children: listing.local.dumps.map((d) => (_jsxs("tr", { style: {
                                                    borderTop: "1px solid var(--border, #e5e7eb)",
                                                    background: restoreFile === d.filename ? "var(--accent, #f3f4f6)" : undefined,
                                                    cursor: "pointer",
                                                }, onClick: () => setRestoreFile(d.filename), children: [_jsx("td", { style: { padding: "4px 6px", fontFamily: "ui-monospace, monospace" }, children: d.filename }), _jsx("td", { style: { padding: "4px 6px" }, children: formatDate(d.mtime) }), _jsx("td", { style: { padding: "4px 6px", textAlign: "right" }, children: formatBytes(d.sizeBytes) })] }, d.filename))) })] })) : (_jsx("div", { style: { color: "var(--muted-foreground, #6b7280)" }, children: "No local DB dumps found." })) }), _jsxs("div", { style: { display: "flex", gap: 8, alignItems: "end", marginTop: 12, flexWrap: "wrap" }, children: [_jsxs("label", { style: { display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }, children: ["Keep", _jsx("input", { type: "number", min: 1, max: 365, value: keep, onChange: (e) => setKeep(Math.max(1, Number(e.target.value) || 10)), style: {
                                                    padding: "4px 8px",
                                                    border: "1px solid var(--border, #e5e7eb)",
                                                    borderRadius: 4,
                                                    width: 80,
                                                } })] }), _jsx(ActionButton, { label: "Prune local dumps", busy: busy === "prune", onClick: triggerPrune, variant: "danger", hint: `Keep newest ${keep} file(s)`, elapsedMs: elapsedMs }), _jsx(ActionButton, { label: "Restore local file", busy: busy === "restore-loc", onClick: triggerRestoreLocal, hint: restoreFile ? `Copy ${restoreFile}` : "Select a file in the table first", disabled: !restoreFile, elapsedMs: elapsedMs })] })] }), _jsxs("div", { style: { padding: 16, border: "1px solid var(--border, #e5e7eb)", borderRadius: 8 }, children: [_jsxs("header", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }, children: [_jsx("h3", { style: { margin: 0, fontSize: 16 }, children: "Offsite backups (GDrive)" }), _jsxs("span", { style: { fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: [listing?.offsite.count ?? "—", " entries \u00B7 keep newest", " ", listing?.offsiteRetention?.keep ?? listing?.config?.offsiteKeep ?? 30] })] }), _jsx("div", { style: { maxHeight: 240, overflow: "auto", fontSize: 12 }, children: listing?.offsite.backups.length ? (_jsxs("table", { style: { width: "100%", borderCollapse: "collapse" }, children: [_jsx("thead", { children: _jsxs("tr", { style: { textAlign: "left", color: "var(--muted-foreground, #6b7280)" }, children: [_jsx("th", { style: { padding: "4px 6px" }, children: "Path" }), _jsx("th", { style: { padding: "4px 6px" }, children: "Modified" }), _jsx("th", { style: { padding: "4px 6px", textAlign: "right" }, children: "Size" })] }) }), _jsx("tbody", { children: listing.offsite.backups.map((b) => (_jsxs("tr", { style: {
                                                    borderTop: "1px solid var(--border, #e5e7eb)",
                                                    background: restorePath === b.path ? "var(--accent, #f3f4f6)" : undefined,
                                                    cursor: "pointer",
                                                }, onClick: () => setRestorePath(b.path), children: [_jsx("td", { style: { padding: "4px 6px", fontFamily: "ui-monospace, monospace" }, children: b.path.split("/").slice(-2).join("/") }), _jsx("td", { style: { padding: "4px 6px" }, children: formatDate(b.modified) }), _jsx("td", { style: { padding: "4px 6px", textAlign: "right" }, children: b.sizeBytes ? formatBytes(b.sizeBytes) : "—" })] }, b.path))) })] })) : (_jsx("div", { style: { color: "var(--muted-foreground, #6b7280)" }, children: "No offsite backups listed." })) }), _jsxs("div", { style: { display: "flex", gap: 8, alignItems: "end", marginTop: 12, flexWrap: "wrap" }, children: [_jsxs("label", { style: { display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }, children: ["Keep newest", _jsx("input", { type: "number", min: 0, max: 10000, value: offsiteKeep ?? listing?.offsiteRetention?.keep ?? listing?.config?.offsiteKeep ?? 30, onChange: (e) => setOffsiteKeep(Math.max(0, Math.min(10000, Number(e.target.value) || 0))), style: {
                                                    padding: "4px 8px",
                                                    border: "1px solid var(--border, #e5e7eb)",
                                                    borderRadius: 4,
                                                    width: 90,
                                                } })] }), _jsx(ActionButton, { label: "Prune offsite (GDrive)", busy: busy === "prune-off", onClick: triggerPruneOffsite, variant: "danger", hint: `Deletes oldest GDrive folders beyond the keep count`, elapsedMs: elapsedMs }), _jsx("span", { style: { fontSize: 11, color: "var(--muted-foreground, #6b7280)" }, children: (listing?.offsiteRetention?.candidates ?? 0) > 0
                                            ? `${listing?.offsiteRetention?.candidates} candidate(s) to delete`
                                            : "No candidates to delete" })] })] })] }), _jsxs("section", { style: { padding: 16, border: "1px solid var(--border, #e5e7eb)", borderRadius: 8 }, children: [_jsx("h3", { style: { marginTop: 0, fontSize: 16 }, children: "Run backup & restore" }), _jsxs("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }, children: [_jsx("div", { style: { display: "flex", flexDirection: "column", gap: 8 }, children: _jsx(ActionButton, { label: runningNow ? "Backup running…" : "Run backup now", busy: busy === "backup" || runningNow != null, onClick: triggerBackup, hint: runningNow
                                        ? `Backup in background (pid=${runningNow.pid}); will refresh when done`
                                        : "Pushes latest DB + instance data to GDrive", elapsedMs: runningNow ? Date.now() - new Date(runningNow.startedAt).getTime() : elapsedMs, disabled: runningNow != null }) }), _jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 8 }, children: [_jsxs("label", { style: { display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }, children: ["Backup path (empty = latest)", _jsx("input", { type: "text", placeholder: "latest", value: restorePath, onChange: (e) => setRestorePath(e.target.value), style: {
                                                    padding: "4px 8px",
                                                    border: "1px solid var(--border, #e5e7eb)",
                                                    borderRadius: 4,
                                                    fontFamily: "ui-monospace, monospace",
                                                    fontSize: 12,
                                                } })] }), _jsxs("label", { style: { display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }, children: ["Restore destination", _jsx("input", { type: "text", value: restoreDest, onChange: (e) => setRestoreDest(e.target.value), style: {
                                                    padding: "4px 8px",
                                                    border: "1px solid var(--border, #e5e7eb)",
                                                    borderRadius: 4,
                                                    fontFamily: "ui-monospace, monospace",
                                                    fontSize: 12,
                                                } })] }), _jsx(ActionButton, { label: "Restore from offsite", busy: busy === "restore-off", onClick: triggerRestoreOffsite, variant: "danger", hint: "Downloads + extracts the chosen backup", elapsedMs: elapsedMs })] })] })] }), _jsx(ResultBanner, { result: result, onDismiss: () => setResult(null) }), _jsx(ForceRecoverySection, { forceBackup: forceBackup, forceRestore: forceRestore, deleteRecoverySnapshots: deleteRecoverySnapshots, uploadDailyBackup: uploadDailyBackup, uploadHourlyBackup: uploadHourlyBackup, setTierKeep: setTierKeep, recoverySnapshots: recoverySnapshots, recoverySnapshotsError: recoverySnapshotsError, tierStatus: tierStatus, refreshRecoverySnapshots: function () { setRefreshTick(function (n) { return n + 1; }); }, forceRunning: forceRunning, Button: ActionButton })] }));
}
// ---------------------------------------------------------------------------
// Settings page
// ---------------------------------------------------------------------------
export function BackupSettingsPage({ context }) {
    const host = useHostContext();
    const companyId = context.companyId ?? host.companyId ?? null;
    const saveConfig = usePluginAction("save-config");
    const [busy, setBusy] = useState(null);
    const [config, setConfig] = useState(null);
    const [saved, setSaved] = useState(null);
    const { data: listingConfig, error } = usePluginData("config");
    useEffect(() => {
        if (listingConfig && !config)
            setConfig(listingConfig);
    }, [listingConfig, config]);
    const update = (k, v) => {
        if (!config)
            return;
        setConfig({ ...config, [k]: v });
    };
    const save = async () => {
        if (!config || busy)
            return;
        setBusy("save");
        setSaved(null);
        try {
            const r = await saveConfig({ ...config, companyId });
            setSaved({ ok: true, message: r.message ?? "Saved" });
            if (r.config)
                setConfig(r.config);
        }
        catch (err) {
            setSaved({ ok: false, message: errorMessage(err) });
        }
        finally {
            setBusy(null);
        }
    };
    if (error) {
        return (_jsxs("div", { style: { padding: 16, color: "var(--destructive, #dc2626)" }, children: ["Failed to load settings: ", error] }));
    }
    if (!config)
        return _jsx("div", { style: { padding: 16 }, children: "Loading\u2026" });
    return (_jsxs("article", { style: { display: "grid", gap: 16, padding: 16 }, children: [_jsx("h2", { style: { margin: 0, fontSize: 20 }, children: "Backup settings" }), _jsx("p", { style: { color: "var(--muted-foreground, #6b7280)", fontSize: 13 }, children: "Paths to the existing backup / restore / prune scripts. Defaults match the layout used by the paperclip-backup systemd service." }), _jsxs("div", { style: {
                    display: "grid",
                    gap: 12,
                    padding: 16,
                    border: "1px solid var(--border, #e5e7eb)",
                    borderRadius: 8,
                }, children: [_jsx(Field, { label: "Paperclip home", value: config.paperclipHome, onChange: (v) => update("paperclipHome", v) }), _jsx(Field, { label: "Backups subdir (under paperclipHome)", value: config.backupsSubdir, onChange: (v) => update("backupsSubdir", v) }), _jsx(Field, { label: "backup-to-drive.sh", value: config.backupScript, onChange: (v) => update("backupScript", v) }), _jsx(Field, { label: "restore-from-drive.sh", value: config.restoreScript, onChange: (v) => update("restoreScript", v) }), _jsx(Field, { label: "prune-local-dumps.sh", value: config.pruneScript, onChange: (v) => update("pruneScript", v) }), _jsx(Field, { label: "rclone config", value: config.rcloneConfig, onChange: (v) => update("rcloneConfig", v) }), _jsx(Field, { label: "rclone remote", value: config.rcloneRemote, onChange: (v) => update("rcloneRemote", v) }), _jsxs("label", { style: { display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }, children: ["Default keep (newest N local dumps)", _jsx("input", { type: "number", min: 1, max: 365, value: config.defaultKeep, onChange: (e) => update("defaultKeep", Math.max(1, Math.min(365, Number(e.target.value) || 10))), style: {
                                    padding: "4px 8px",
                                    border: "1px solid var(--border, #e5e7eb)",
                                    borderRadius: 4,
                                    width: 100,
                                } })] }), _jsxs("label", { style: { display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }, children: ["Offsite keep (newest N GDrive folders; 0 = never auto-prune)", _jsx("input", { type: "number", min: 0, max: 10000, value: config.offsiteKeep, onChange: (e) => update("offsiteKeep", Math.max(0, Math.min(10000, Number(e.target.value) || 0))), style: {
                                    padding: "4px 8px",
                                    border: "1px solid var(--border, #e5e7eb)",
                                    borderRadius: 4,
                                    width: 100,
                                } })] }), _jsx(Field, { label: "Offsite auto-prune schedule (e.g. 'every 24h', 'every 7d'; empty = off)", value: config.offsiteSchedule, onChange: (v) => update("offsiteSchedule", v) })] }), _jsx("div", { children: _jsx(ActionButton, { label: "Save settings", busy: busy === "save", onClick: save }) }), saved ? (_jsx("div", { style: {
                    marginTop: 8,
                    fontSize: 13,
                    color: saved.ok ? "var(--success, #16a34a)" : "var(--destructive, #dc2626)",
                }, children: saved.message })) : null] }));
}
function Field(props) {
    return (_jsxs("label", { style: { display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }, children: [props.label, _jsx("input", { type: "text", value: props.value, onChange: (e) => props.onChange(e.target.value), style: {
                    padding: "4px 8px",
                    border: "1px solid var(--border, #e5e7eb)",
                    borderRadius: 4,
                    fontFamily: "ui-monospace, monospace",
                    fontSize: 12,
                } })] }));
}
//# sourceMappingURL=index.js.map
function ForceRecoverySection({ forceBackup, forceRestore, deleteRecoverySnapshots, uploadDailyBackup, uploadHourlyBackup, setTierKeep, recoverySnapshots, recoverySnapshotsError, tierStatus, refreshRecoverySnapshots, forceRunning, Button }) {
    // Format ISO timestamps (UTC) as local time so the displayed clock matches
    // the operator's wall clock. Falls back to the raw string if parsing fails.
    function formatTimestamp(iso) {
        if (!iso) return "";
        try {
            const d = new Date(iso);
            if (isNaN(d.getTime())) return iso;
            // Short, human-friendly: "2026-07-07 14:21:22 CEST"
            const pad = function (n) { return n < 10 ? "0" + n : "" + n; };
            const Y = d.getFullYear();
            const M = pad(d.getMonth() + 1);
            const D = pad(d.getDate());
            const h = pad(d.getHours());
            const m = pad(d.getMinutes());
            const s = pad(d.getSeconds());
            const tzMatch = (d.toString().match(/\(([^)]+)\)$/) || [])[1] || "";
            const tz = tzMatch || "local";
            return Y + "-" + M + "-" + D + " " + h + ":" + m + ":" + s + " " + tz;
        }
        catch {
            return iso;
        }
    }
    function Tier({ name, items, keep, count, last, error, onUpload, onChangeKeep, busyKey, busy, Button }) {
        const idInput = "keep-input-" + name;
        return _jsxs("div", { style: { padding: 12, border: "1px solid var(--border, #e5e7eb)", borderRadius: 6, background: "var(--card, #fafafa)" }, children: [
            _jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }, children: [
                _jsxs("div", { children: [
                    _jsx("strong", { style: { fontSize: 13, textTransform: "uppercase", letterSpacing: 0.5, color: name === "daily" ? "hsl(140, 60%, 35%)" : "hsl(35, 80%, 40%)" }, children: name + " tier" }),
                    _jsxs("span", { style: { marginLeft: 8, fontFamily: "ui-monospace, monospace", fontSize: 12 }, children: ["count ", _jsx("strong", { children: count }), " / ", _jsx("strong", { children: keep })] }),
                ] }),
                _jsx(Button, { label: busy === busyKey ? "Uploading\u2026" : ("Upload latest to " + name), busy: busy === busyKey, onClick: function () { onUpload(); } }),
            ] }),
            last ? _jsx("div", { style: { fontSize: 11, fontFamily: "ui-monospace, monospace", color: "var(--muted-foreground, #6b7280)", marginBottom: 6 }, children: "most recent: " + last }) : null,
            items && items.length ? _jsx("div", { style: { fontSize: 11, fontFamily: "ui-monospace, monospace", maxHeight: 70, overflow: "auto", padding: 4, background: "var(--muted, #f9fafb)", border: "1px solid var(--border, #e5e7eb)", borderRadius: 4, marginBottom: 6 }, children: items.slice().sort().reverse().map(function (id) {
                return _jsx("div", { style: { padding: "1px 0" }, children: id });
            }) }) : null,
            error ? _jsx("div", { style: { fontSize: 11, color: "var(--destructive, #b91c1c)", marginBottom: 6 }, children: error }) : null,
            _jsxs("div", { style: { display: "flex", alignItems: "center", gap: 6, fontSize: 12 }, children: [
                _jsx("span", { children: "Retention (keep):" }),
                _jsx("input", { type: "number", min: 1, max: 365, defaultValue: keep, id: idInput, style: { width: 60, padding: "2px 6px", border: "1px solid var(--border, #e5e7eb)", borderRadius: 4 } }),
                _jsx("button", { type: "button", onClick: function () {
                    var inp = typeof document !== "undefined" ? document.getElementById(idInput) : null;
                    var v = inp && inp.value ? parseInt(inp.value, 10) : NaN;
                    onChangeKeep(v);
                }, style: { marginLeft: 4, padding: "2px 8px", fontSize: 11, border: "1px solid transparent", borderRadius: 4, background: "#1e40af", color: "#f8fafc", cursor: "pointer" }, children: "Save" }),
            ] }),
        ] });
    }
    function TierPanel({ uploadDailyBackup, uploadHourlyBackup, setTierKeep, tierStatus, refreshRecoverySnapshots, setLast, busy, setBusy, Button }) {
        function doUpload(kind, action) {
            setBusy("upload-" + kind);
            setLast({ ok: true, message: "uploading latest snapshot to " + kind + " tier\u2026" });
            action({}).then(function (r) {
                setLast({ ok: true, message: r && r.message ? r.message : (kind + " upload dispatched (pid=" + (r && r.pid) + ")") });
            }).catch(function (err) {
                setLast({ ok: false, message: err && err.message ? err.message : String(err) });
            }).finally(function () {
                setBusy(null);
                setTimeout(refreshRecoverySnapshots, 2000);
            });
        }
        function doChangeKeep(tier, keepValue) {
            if (!Number.isFinite(keepValue) || keepValue < 1) {
                setLast({ ok: false, message: "keep must be a positive integer" });
                return;
            }
            setBusy("set-keep-" + tier);
            setTierKeep({ tier: tier, keep: keepValue }).then(function (r) {
                setLast({ ok: !!r && r.ok, message: r && r.message ? r.message : "Set " + tier + " keep=" + keepValue });
            }).catch(function (err) {
                setLast({ ok: false, message: err && err.message ? err.message : String(err) });
            }).finally(function () {
                setBusy(null);
                setTimeout(refreshRecoverySnapshots, 1500);
            });
        }
        return _jsxs("div", { style: { marginTop: 8, padding: 10, border: "1px solid var(--border, #e5e7eb)", borderRadius: 6, background: "color-mix(in oklab, hsl(50, 60%, 95%) 30%, var(--card, #fff))" }, children: [
            _jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }, children: [
                _jsx("strong", { style: { fontSize: 13 }, children: "GDrive tiered backup" }),
                _jsx("span", { style: { fontSize: 11, color: "var(--muted-foreground, #6b7280)", fontFamily: "ui-monospace, monospace" }, children: tierStatus && tierStatus.enabled === false ? "disabled" : ("root: " + (tierStatus && tierStatus.tierRoot ? tierStatus.tierRoot : "Paperclip-Backups")) }),
            ] }),
            tierStatus && tierStatus.enabled === false
                ? _jsx("div", { style: { fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: "Tiered backup is disabled in plugin config." })
                : _jsxs("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }, children: [
                    _jsx(Tier, { name: "daily", items: (tierStatus && tierStatus.daily) || [], keep: (tierStatus && tierStatus.keep && tierStatus.keep.daily) || 3, count: (tierStatus && tierStatus.counts && tierStatus.counts.daily) || 0, last: tierStatus && tierStatus.lastUpload && tierStatus.lastUpload.daily, error: tierStatus && tierStatus.errors && tierStatus.errors.daily, onUpload: function () { return doUpload("daily", uploadDailyBackup); }, onChangeKeep: function (v) { return doChangeKeep("daily", v); }, busyKey: "upload-daily", busy: busy, Button: Button }),
                    _jsx(Tier, { name: "hourly", items: (tierStatus && tierStatus.hourly) || [], keep: (tierStatus && tierStatus.keep && tierStatus.keep.hourly) || 2, count: (tierStatus && tierStatus.counts && tierStatus.counts.hourly) || 0, last: tierStatus && tierStatus.lastUpload && tierStatus.lastUpload.hourly, error: tierStatus && tierStatus.errors && tierStatus.errors.hourly, onUpload: function () { return doUpload("hourly", uploadHourlyBackup); }, onChangeKeep: function (v) { return doChangeKeep("hourly", v); }, busyKey: "upload-hourly", busy: busy, Button: Button }),
                ] }),
        ] });
    }
    const [open, setOpen] = useState(true);
    const [busy, setBusy] = useState(null);
    const [last, setLast] = useState(null);
    const [selected, setSelected] = useState({});
    const [showStubs, setShowStubs] = useState(false);
    const snaps = recoverySnapshots && Array.isArray(recoverySnapshots.snapshots) ? recoverySnapshots.snapshots : [];
    const visibleSnaps = showStubs ? snaps : snaps.filter(function (s) { return (s.apparentBytes || 0) >= 1024 || (s.bytes || 0) >= 1024; });
    const stubCount = snaps.length - visibleSnaps.length;
    const snapCount = visibleSnaps.length;
    const totalApparentBytes = recoverySnapshots && typeof recoverySnapshots.totalApparentBytes === "number"
        ? recoverySnapshots.totalApparentBytes
        : snaps.reduce(function (a, s) { return a + (s.apparentBytes || 0); }, 0);
    const totalDeltaBytes = recoverySnapshots && typeof recoverySnapshots.totalDeltaBytes === "number"
        ? recoverySnapshots.totalDeltaBytes
        : snaps.reduce(function (a, s) { return a + (s.deltaBytes || s.bytes || 0); }, 0);
    // Each snapshot's logical size if restored alone, summed across all = totalApparentBytes.
    // Real on-disk cost = totalDeltaBytes (cross-snapshot inode-dedup aware).
    // Savings (logical - real) shown separately.
    const savingsBytes = Math.max(0, totalApparentBytes - totalDeltaBytes);
    const savingsPct = totalApparentBytes > 0 ? Math.round((savingsBytes / totalApparentBytes) * 100) : 0;
    const allSelected = snapCount > 0 && visibleSnaps.every(function (s) { return !!selected[s.id]; });
    const someSelected = visibleSnaps.some(function (s) { return !!selected[s.id]; });
    const selectedIds = visibleSnaps.filter(function (s) { return !!selected[s.id]; }).map(function (s) { return s.id; });
    const toggleOne = function (id) {
        setSelected(function (prev) {
            const next = Object.assign({}, prev);
            if (next[id]) { delete next[id]; } else { next[id] = true; }
            return next;
        });
    };
    const toggleAll = function () {
        if (allSelected) { setSelected({}); }
        else { const next = {}; snaps.forEach(function (s) { next[s.id] = true; }); setSelected(next); }
    };
    const doForceBackup = async () => {
        setBusy("force-backup"); setLast(null);
        try {
            const r = await forceBackup({});
            setLast({ ok: true, message: r && r.message ? r.message : "Force backup started (pid=" + (r && r.pid) + ")" });
        }
        catch (err) { setLast({ ok: false, message: err && err.message ? err.message : String(err) }); }
        finally { setBusy(null); }
    };
    const doForceRestore = async (id) => {
        setBusy("force-restore-" + id); setLast(null);
        try {
            const r = await forceRestore({ subcommand: "restore", id });
            setLast({ ok: !!(r && r.ok), message: r && r.message ? r.message : ("exit " + (r && r.exitCode)) });
        }
        catch (err) { setLast({ ok: false, message: err && err.message ? err.message : String(err) }); }
        finally { setBusy(null); }
    };
    const doDelete = async (ids, opName) => {
        if (!ids || ids.length === 0) return;
        if (typeof window !== "undefined" && typeof window.confirm === "function") {
            const ok = window.confirm("Delete " + ids.length + " recovery snapshot" + (ids.length === 1 ? "" : "s") + "?\n\n" + ids.join("\n") + "\n\nThis permanently removes the hardlink snapshot directories from disk. The latest 2 snapshots are protected and will be skipped.");
            if (!ok) return;
        }
        setBusy(opName); setLast(null);
        try {
            const r = await deleteRecoverySnapshots({ ids });
            const deletedCount = r && Array.isArray(r.deleted) ? r.deleted.length : 0;
            const skippedCount = r && Array.isArray(r.skipped) ? r.skipped.length : 0;
            const errCount = r && Array.isArray(r.errors) ? r.errors.length : 0;
            const skippedMsg = skippedCount > 0 ? " (" + skippedCount + " skipped — newest 2 protected)" : "";
            setLast({ ok: !!(r && r.ok !== false && errCount === 0), message: r && r.message ? r.message + skippedMsg : ("Deleted " + deletedCount) });
            setSelected({});
            refreshRecoverySnapshots();
        }
        catch (err) { setLast({ ok: false, message: err && err.message ? err.message : String(err) }); }
        finally { setBusy(null); }
    };
    const doDeleteOne = function (id) { return doDelete([id], "force-delete-" + id); };
    const doDeleteSelected = function () { return doDelete(selectedIds.slice(), "force-delete-batch"); };
    return _jsxs("section", { style: { marginTop: 16, padding: 16, border: "1px solid var(--border, #e5e7eb)", borderRadius: 8, background: "var(--card, #fafafa)" }, children: [
        _jsxs("header", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }, children: [
            _jsx("h3", { style: { margin: 0, fontSize: 16 }, children: "Force backup & recovery" }),
            _jsxs("div", { style: { display: "flex", gap: 8 }, children: [
                _jsx(Button, { label: busy === "force-backup" ? "Starting…" : (forceRunning ? "Snapshot running…" : "Take recovery snapshot now"), busy: busy === "force-backup" || !!forceRunning, onClick: doForceBackup, hint: "calls recovery.sh snapshot --no-upload (local hardlink-incremental; no GDrive upload)" }),
                _jsx(Button, { label: open ? "Hide recovery points" : "Pick recovery point", onClick: function () { setOpen(!open); } }),
            ] }),
        ] }),
        TierPanel({ uploadDailyBackup: uploadDailyBackup, uploadHourlyBackup: uploadHourlyBackup, setTierKeep: setTierKeep, tierStatus: tierStatus, refreshRecoverySnapshots: refreshRecoverySnapshots, setLast: setLast, busy: busy, setBusy: setBusy, Button: Button }),
        forceRunning ? _jsx("div", { style: { marginTop: 8, marginBottom: 8, padding: 10, background: "color-mix(in oklab, var(--primary) 8%, var(--card))", border: "1px solid color-mix(in oklab, var(--primary) 20%, var(--border))", borderRadius: 6 }, children:
            (function () {
                const stage = forceRunning.stage || "running";
                const stageLabel = stage === "uploading" ? "Uploading snapshot to Google Drive" : stage === "packing" ? "Packing worktree (tar+gzip)" : stage === "pruning" ? "Pruning old snapshots" : stage === "snapshotting" ? "Creating incremental snapshot (rsync --link-dest)" : stage === "snapshot" ? "Creating snapshot" : stage === "running" ? "Snapshot running" : stage;
                const progress = forceRunning.progress;
                return _jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 6 }, children: [
                    _jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }, children: [
                        _jsxs("div", { children: [
                            _jsx("strong", { style: { fontSize: 13 }, children: stageLabel }),
                            _jsx("div", { style: { color: "var(--muted-foreground, #6b7280)", fontSize: 11, fontFamily: "ui-monospace, monospace", marginTop: 2 }, children: "pid " + String(forceRunning.pid) + " \u00b7 started " + formatTimestamp(forceRunning.startedAt) + (forceRunning.stageDetail ? " \u00b7 " + String(forceRunning.stageDetail) : "") }),
                        ] }),
                        progress && progress.percent !== null && progress.percent !== undefined ? _jsx("span", { style: { fontFamily: "ui-monospace, monospace", fontSize: 13, fontWeight: 600, whiteSpace: "nowrap" }, children: progress.percent.toFixed(1) + "%" }) : null,
                    ] }),
                    progress && progress.percent !== null && progress.percent !== undefined ? _jsx("div", { style: { height: 8, background: "var(--muted, #f3f4f6)", borderRadius: 4, overflow: "hidden", border: "1px solid var(--border, #e5e7eb)" }, children:
                        _jsx("div", { style: { width: progress.percent + "%", height: "100%", background: "linear-gradient(90deg, var(--primary, #2563eb) 0%, color-mix(in oklab, var(--primary, #2563eb) 70%, white) 100%)", transition: "width 0.6s ease" }, children: "" })
                    }) : null,
                    progress && progress.totalBytes ? _jsxs("div", { style: { color: "var(--muted-foreground, #6b7280)", fontSize: 11, fontFamily: "ui-monospace, monospace" }, children: [
                        (progress.uploadBytes / (1024 * 1024)).toFixed(1) + " MiB / " + (progress.totalBytes / (1024 * 1024)).toFixed(0) + " MiB \u00b7 rclone pid " + String(progress.rclonePid),
                        (function () {
                            const child = forceRunning.children && forceRunning.children.find(function (c) { return c.pid === progress.rclonePid; });
                            if (!child || !child.startedAt) return "";
                            const elapsedMs = Date.now() - new Date(child.startedAt).getTime();
                            if (elapsedMs <= 0 || progress.uploadBytes <= 0) return "";
                            const rate = progress.uploadBytes / (elapsedMs / 1000);
                            const remaining = Math.max(0, progress.totalBytes - progress.uploadBytes);
                            if (rate <= 0) return "";
                            const etaSec = remaining / rate;
                            const etaLabel = etaSec >= 60 ? Math.round(etaSec / 60) + " min" : Math.round(etaSec) + " sec";
                            return " \u00b7 " + (rate / (1024 * 1024)).toFixed(2) + " MB/s \u00b7 ETA " + etaLabel;
                        })(),
                    ] }) : null,
                    _jsx("div", { style: { fontSize: 11, color: "var(--muted-foreground, #6b7280)" }, children: "incremental rsync \u2014 typically finishes in seconds (only changed bytes are written; rest are hardlinks)" }),
                ] });
            })()
        }) : null,
        _jsxs("div", { style: { marginTop: 4, marginBottom: 8, fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: [
            "Recovery snapshots: " + snapCount + " \u00b7 logical " + Math.round(totalApparentBytes / (1024 * 1024)) + " MiB if all restored \u00b7 actual on-disk " + Math.round(totalDeltaBytes / (1024 * 1024)) + " MiB (hardlink-deduped; saved " + savingsPct + "\u202f% / " + Math.round(savingsBytes / (1024 * 1024)) + " MiB)",
        ] }),
        last ? _jsx("div", { style: { marginTop: 8, padding: 8, fontFamily: "ui-monospace, monospace", fontSize: 12, color: last.ok ? "var(--muted-foreground, #6b7280)" : "var(--destructive, #dc2626)", background: "var(--muted, #f3f4f6)", borderRadius: 4 }, children: last.message }) : null,
        open ? _jsxs("div", { style: { marginTop: 12 }, children: [
            recoverySnapshotsError ? _jsx("div", { style: { color: "var(--destructive, #dc2626)", fontSize: 12, marginBottom: 8 }, children: "Could not list snapshots: " + String(recoverySnapshotsError) }) : null,
            stubCount > 0 ? _jsx("div", { style: { fontSize: 12, color: "var(--muted-foreground, #6b7280)", marginBottom: 8 }, children: [
                stubCount + " empty " + (stubCount === 1 ? "stub" : "stubs") + " hidden \u2014 only " + visibleSnaps.length + " real " + (visibleSnaps.length === 1 ? "backup" : "backups") + " on disk ",
                _jsx("button", { type: "button", onClick: function () { setShowStubs(!showStubs); }, style: { padding: "2px 8px", fontSize: 11, border: "1px solid transparent", borderRadius: 4, background: "var(--muted, #374151)", cursor: "pointer", color: "#f8fafc" }, children: showStubs ? "Hide stubs" : "Show " + stubCount + " stub" + (stubCount === 1 ? "" : "s") }),
            ] }) : null,
            visibleSnaps.length === 0 && stubCount === 0 ? _jsx("div", { style: { color: "var(--muted-foreground, #6b7280)", fontSize: 12 }, children: "No snapshots available at /home/sirrus/paperclip-snapshots" }) : null,
            visibleSnaps.length > 0 ? _jsxs("div", { style: { display: "flex", alignItems: "center", gap: 8, padding: "4px 10px", background: "var(--muted, #f3f4f6)", borderTop: "1px solid var(--border, #e5e7eb)", borderLeft: "1px solid var(--border, #e5e7eb)", borderRight: "1px solid var(--border, #e5e7eb)", fontSize: 12 }, children: [
                _jsx("input", { type: "checkbox", checked: allSelected, onChange: toggleAll, "aria-label": "Select all snapshots" }),
                _jsxs("span", { style: { flex: 1 }, children: [
                    allSelected ? "All " + visibleSnaps.length + " selected" : (someSelected ? selectedIds.length + " selected" : "Select all"),
                ] }),
                someSelected ? _jsx(Button, { label: "Delete selected (" + selectedIds.length + ")", busy: busy === "force-delete-batch", variant: "danger", onClick: doDeleteSelected }) : null,
            ] }) : null,
            _jsx("div", { style: { border: "1px solid var(--border, #e5e7eb)", borderRadius: 4 }, children:
                (function () {
                    const total = visibleSnaps.length;
                    // Compute an HSL gradient from green (newest, idx 0) to red
                    // (oldest, idx total-1). Saturation/lightness tuned so even the
                    // extremes are readable on white backgrounds.
                    function ageColor(idx) {
                        if (total <= 1) return "hsl(120, 60%, 35%)";
                        const ratio = idx / (total - 1); // 0=newest, 1=oldest
                        const hue = 120 - 120 * ratio; // 120 (green) -> 0 (red)
                        return "hsl(" + hue.toFixed(0) + ", 55%, 38%)";
                    }
                    return visibleSnaps.map(function (s) {
                        const idx = visibleSnaps.indexOf(s);
                        const isProtected = idx < 2;
                        const isMaster = idx === 0;
                        const tsColor = ageColor(idx);
                        return _jsxs("div", { style: { display: "flex", alignItems: "center", gap: 8, padding: "6px 10px", borderBottom: "1px solid var(--border, #e5e7eb)", background: selected[s.id] ? "var(--accent, #f3f4f6)" : (isMaster ? "color-mix(in oklab, hsl(120, 55%, 60%) 8%, var(--card, #fff))" : undefined) }, children: [
                            _jsx("input", { type: "checkbox", checked: !!selected[s.id], disabled: isProtected, onChange: function () { toggleOne(s.id); }, "aria-label": "Select " + s.id }),
                            _jsxs("div", { style: { flex: 1, fontFamily: "ui-monospace, monospace", fontSize: 12 }, children: [
                                _jsxs("strong", { children: [
                                    s.id,
                                    isMaster ? " \u00b7 \u25cf MASTER" : "",
                                    isProtected && !isMaster ? " \u00b7 protected" : "",
                                    !isProtected ? "" : "",
                                ] }),
                                _jsx("div", { style: { color: tsColor, fontSize: 11, fontWeight: isMaster ? 600 : 400 }, children: [
                                    (s.apparentBytes ? Math.round(s.apparentBytes / (1024 * 1024)) + " MB" : "\u2014"),
                                    (s.deltaBytes !== undefined && s.deltaBytes !== null && s.apparentBytes ? " (new +" + (s.deltaBytes >= 1024 * 1024 ? Math.round(s.deltaBytes / (1024 * 1024)) + " MB" : Math.max(1, Math.round(s.deltaBytes / 1024)) + " KB") + ")" : ""),
                                    " \u00b7 ",
                                    formatTimestamp(s.timestamp),
                                ] }),
                            ] }),
                            _jsx(Button, { label: busy === "force-restore-" + s.id ? "Restoring\u2026" : "Restore", busy: busy === "force-restore-" + s.id, onClick: function () { doForceRestore(s.id); }, variant: "danger" }),
                            isProtected ? _jsx("span", { style: { fontSize: 11, color: "var(--muted-foreground, #6b7280)" }, children: " " }) : _jsx(Button, { label: busy === "force-delete-" + s.id ? "Deleting\u2026" : "Delete", busy: busy === "force-delete-" + s.id, variant: "danger", onClick: function () { doDeleteOne(s.id); } }),
                        ] });
                    });
                })()
            }),
            _jsx("div", { style: { marginTop: 8, display: "flex", gap: 8 }, children: _jsx(Button, { label: "Refresh", onClick: refreshRecoverySnapshots }) }),
        ] }) : null,
    ] });
}

