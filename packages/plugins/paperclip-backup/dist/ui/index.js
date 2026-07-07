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
    const baseStyle = {
        padding: "8px 14px",
        borderRadius: 6,
        fontWeight: 500,
        fontSize: 13,
        cursor: props.busy || props.disabled ? "not-allowed" : "pointer",
        opacity: props.busy || props.disabled ? 0.6 : 1,
        border: "1px solid var(--border, #e5e7eb)",
        background: variant === "primary" ? "var(--primary, #2563eb)" : "var(--card, #fff)",
        color: variant === "primary" ? "var(--primary-foreground, #fff)" : "var(--destructive, #dc2626)",
        borderColor: variant === "danger" ? "var(--destructive, #dc2626)" : "var(--border, #e5e7eb)",
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
                : "text-foreground/80 hover:bg-accent/50 hover:text-foreground"), style: { textDecoration: "none" }, children: [_jsx("span", { "aria-hidden": true, className: "shrink-0 text-base leading-none", children: "\uD83D\uDCBE" }), _jsx("span", { className: "flex-1 truncate", children: "Backups" })] }));
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
    const [refreshTick, setRefreshTick] = useState(0);
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
    return (_jsxs("article", { style: { display: "grid", gap: 16, padding: 16 }, children: [_jsxs("header", { children: [_jsx("h2", { style: { margin: 0, fontSize: 20 }, children: "Backup Manager" }), _jsx("p", { style: { marginTop: 4, color: "var(--muted-foreground, #6b7280)", fontSize: 13 }, children: "Offsite push (rclone \u2192 GDrive) and local DB-dump retention." })] }), error ? (_jsxs("div", { role: "alert", style: {
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
                                                } })] }), _jsx(ActionButton, { label: "Restore from offsite", busy: busy === "restore-off", onClick: triggerRestoreOffsite, variant: "danger", hint: "Downloads + extracts the chosen backup", elapsedMs: elapsedMs })] })] })] }), _jsx(ResultBanner, { result: result, onDismiss: () => setResult(null) })] }));
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