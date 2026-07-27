// src/ui/index.tsx
import {
  useHostContext,
  useHostLocation,
  useHostNavigation,
  usePluginAction,
  usePluginData
} from "@paperclipai/plugin-sdk/ui";
import { useEffect, useMemo, useState } from "react";
import { Fragment, jsx, jsxs } from "react/jsx-runtime";
function formatBytes(bytes) {
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
function formatDate(iso) {
  if (!iso) return "\u2014";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return String(iso);
    return d.toISOString().replace("T", " ").replace(/\..+/, " UTC");
  } catch {
    return String(iso);
  }
}
function StatusDot({ ok }) {
  const color = ok ? "var(--success, #16a34a)" : "var(--destructive, #dc2626)";
  return /* @__PURE__ */ jsx(
    "span",
    {
      "aria-hidden": "true",
      style: {
        display: "inline-block",
        width: 10,
        height: 10,
        borderRadius: "50%",
        background: color,
        marginRight: 6,
        verticalAlign: "middle"
      }
    }
  );
}
function ActionButton(props) {
  const variant = props.variant ?? "primary";
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
    background: isPrimary ? "#1e40af" : isDanger ? "#b91c1c" : "#374151",
    color: "#f8fafc",
    borderColor: isDanger ? "#991b1b" : "transparent"
  };
  const elapsed = props.busy && props.elapsedMs != null ? ` (${Math.floor(props.elapsedMs / 1e3)}s)` : "";
  return /* @__PURE__ */ jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 4 }, children: [
    /* @__PURE__ */ jsx(
      "button",
      {
        type: "button",
        onClick: props.onClick,
        disabled: props.busy || props.disabled,
        style: baseStyle,
        children: props.busy ? `Working\u2026${elapsed}` : props.label
      }
    ),
    props.hint ? /* @__PURE__ */ jsx("span", { style: { fontSize: 11, color: "var(--muted-foreground, #6b7280)" }, children: props.hint }) : null
  ] });
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
    return void 0;
  }, [running]);
  return start != null ? now : 0;
}
function errorMessage(err) {
  if (err == null) return "Unknown error";
  if (typeof err === "string") return err;
  if (err instanceof Error) return err.message;
  if (typeof err === "object") {
    const obj = err;
    if (typeof obj.message === "string" && obj.message.length > 0) {
      const detail = obj.details;
      if (detail && typeof detail === "object") {
        const detailMsg = detail.message;
        if (typeof detailMsg === "string" && detailMsg.length > 0 && detailMsg !== obj.message) {
          return `${obj.message} \u2014 ${detailMsg}`;
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
  onDismiss
}) {
  if (!result) return null;
  const isOk = result.ok;
  return /* @__PURE__ */ jsxs(
    "div",
    {
      role: "status",
      style: {
        padding: 12,
        borderRadius: 6,
        border: `1px solid ${isOk ? "var(--success, #16a34a)" : "var(--destructive, #dc2626)"}`,
        background: isOk ? "color-mix(in oklab, var(--success) 8%, var(--card))" : "color-mix(in oklab, var(--destructive) 8%, var(--card))",
        color: isOk ? "var(--success, #16a34a)" : "var(--destructive, #dc2626)",
        display: "grid",
        gap: 6
      },
      children: [
        /* @__PURE__ */ jsxs(
          "div",
          {
            style: {
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 8
            },
            children: [
              /* @__PURE__ */ jsx("strong", { style: { fontSize: 13 }, children: result.message ?? (isOk ? "Success" : "Failed") }),
              /* @__PURE__ */ jsx(
                "button",
                {
                  type: "button",
                  onClick: onDismiss,
                  style: {
                    background: "transparent",
                    border: "none",
                    color: "inherit",
                    cursor: "pointer",
                    fontSize: 16,
                    lineHeight: 1
                  },
                  "aria-label": "Dismiss",
                  children: "\xD7"
                }
              )
            ]
          }
        ),
        result.keep != null ? /* @__PURE__ */ jsxs("div", { style: { fontSize: 12 }, children: [
          "keep = ",
          result.keep
        ] }) : null,
        result.remotePath ? /* @__PURE__ */ jsxs("div", { style: { fontSize: 12, fontFamily: "ui-monospace, monospace" }, children: [
          result.remotePath,
          " \u2192 ",
          result.destDir ?? "(default)"
        ] }) : null,
        result.totalBytesBefore != null && result.totalBytesAfter != null ? /* @__PURE__ */ jsxs("div", { style: { fontSize: 12 }, children: [
          formatBytes(result.totalBytesBefore),
          " \u2192 ",
          formatBytes(result.totalBytesAfter),
          " (",
          result.prunedCount ?? 0,
          " pruned)"
        ] }) : null,
        result.stdout ? /* @__PURE__ */ jsxs("details", { children: [
          /* @__PURE__ */ jsx("summary", { style: { fontSize: 12, cursor: "pointer" }, children: "stdout" }),
          /* @__PURE__ */ jsx(
            "pre",
            {
              style: {
                fontSize: 11,
                maxHeight: 160,
                overflow: "auto",
                background: "var(--muted, #f3f4f6)",
                padding: 8,
                borderRadius: 4,
                marginTop: 4
              },
              children: result.stdout
            }
          )
        ] }) : null,
        result.stderr ? /* @__PURE__ */ jsxs("details", { children: [
          /* @__PURE__ */ jsx("summary", { style: { fontSize: 12, cursor: "pointer" }, children: "stderr" }),
          /* @__PURE__ */ jsx(
            "pre",
            {
              style: {
                fontSize: 11,
                maxHeight: 160,
                overflow: "auto",
                background: "var(--muted, #f3f4f6)",
                padding: 8,
                borderRadius: 4,
                marginTop: 4
              },
              children: result.stderr
            }
          )
        ] }) : null
      ]
    }
  );
}
function BackupSidebarNav({ context }) {
  const host = useHostContext();
  const hostNavigation = useHostNavigation();
  const hostLocation = useHostLocation();
  const companyPrefix = context.companyPrefix ?? host.companyPrefix;
  const href = companyPrefix ? `/${companyPrefix}/backups` : "/backups";
  const isActive = hostLocation.pathname === href || hostLocation.pathname.startsWith(`${href}/`);
  return /* @__PURE__ */ jsxs(
    "a",
    {
      ...hostNavigation.linkProps(href),
      className: "flex items-center gap-2.5 px-3 py-2 pointer-coarse:py-1.5 text-[13px] font-medium transition-colors " + (isActive ? "bg-accent text-foreground" : "text-foreground/80 hover:bg-accent/50 hover:text-foreground"),
      style: { textDecoration: "none" },
      children: [
        /* @__PURE__ */ jsxs(
          "svg",
          {
            viewBox: "0 0 24 24",
            className: "shrink-0 h-4 w-4",
            fill: "none",
            stroke: "currentColor",
            strokeWidth: "1.6",
            strokeLinecap: "round",
            strokeLinejoin: "round",
            "aria-hidden": "true",
            children: [
              /* @__PURE__ */ jsx("ellipse", { cx: "12", cy: "5", rx: "9", ry: "3", fill: "currentColor", fillOpacity: "0.18" }),
              /* @__PURE__ */ jsx("path", { d: "M3 5v14a9 3 0 0 0 18 0V5" }),
              /* @__PURE__ */ jsx(
                "path",
                {
                  d: "M3 12a9 3 0 0 0 18 0",
                  fill: "currentColor",
                  fillOpacity: "0.18"
                }
              )
            ]
          }
        ),
        /* @__PURE__ */ jsx("span", { className: "flex-1 truncate", children: "Backups" })
      ]
    }
  );
}
function BackupDashboardWidget({
  context
}) {
  const host = useHostContext();
  const companyId = context.companyId ?? host.companyId ?? null;
  const runBackup = usePluginAction("run-backup");
  const [refreshTick, setRefreshTick] = useState(0);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const elapsedMs = useElapsedMs(busy);
  const statusResult = usePluginData("status", { companyId, _tick: refreshTick });
  const status = statusResult?.data;
  const error = statusResult?.error ? String(statusResult.error) : null;
  const running = status?.backupRunning ?? null;
  const runningElapsedMs = running ? Date.now() - new Date(running.startedAt).getTime() : 0;
  const isBusy = busy || running != null;
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setRefreshTick((n) => n + 1), 3e4);
    return () => clearInterval(t);
  }, [running?.pid, running?.startedAt]);
  const triggerBackup = async () => {
    if (busy || running) return;
    setBusy(true);
    setResult(null);
    try {
      const r = await runBackup({ companyId });
      if (r.alreadyRunning) {
        setResult({ ok: false, message: r.message ?? "Backup already running" });
      } else if (r.async || r.pid) {
        setResult({ ok: true, message: r.message ?? `Backup started (pid=${r.pid})` });
      } else {
        setResult({
          ok: r.ok === true,
          exitCode: r.exitCode ?? null,
          message: r.message ?? (r.ok === true ? "Backup pushed to offsite" : "Backup script failed"),
          durationMs: r.durationMs,
          stdout: r.stdout,
          stderr: r.stderr
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
  let subtitle = error ? error : status?.missingCompanyId ? "No active company." : "Backup service health is good.";
  if (running) {
    const started = new Date(running.startedAt).toLocaleString();
    const mins = Math.floor(runningElapsedMs / 6e4);
    subtitle = `Backup in progress (pid=${running.pid}, started ${started}, ${mins}m elapsed)`;
  } else if (status?.backupLastRun) {
    const last = status.backupLastRun;
    const okLabel = last.ok ? "ok" : "failed";
    subtitle = `Last backup: ${okLabel} \u2014 ${last.message}`;
  }
  return /* @__PURE__ */ jsxs("section", { "aria-label": "Backup status", style: { display: "grid", gap: 12 }, children: [
    /* @__PURE__ */ jsxs(
      "div",
      {
        style: {
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center"
        },
        children: [
          /* @__PURE__ */ jsxs("div", { children: [
            /* @__PURE__ */ jsxs("h3", { style: { margin: 0, fontSize: 14, fontWeight: 600 }, children: [
              /* @__PURE__ */ jsx(StatusDot, { ok: isOk && !running }),
              "Backup status"
            ] }),
            /* @__PURE__ */ jsx("div", { style: { fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: subtitle })
          ] }),
          /* @__PURE__ */ jsx(
            ActionButton,
            {
              label: running ? "Backup running\u2026" : "Run backup now",
              busy: isBusy,
              onClick: triggerBackup,
              elapsedMs: running ? runningElapsedMs : elapsedMs,
              disabled: running != null
            }
          )
        ]
      }
    ),
    /* @__PURE__ */ jsxs("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }, children: [
      /* @__PURE__ */ jsxs(
        "div",
        {
          style: {
            padding: 12,
            border: "1px solid var(--border, #e5e7eb)",
            borderRadius: 6
          },
          children: [
            /* @__PURE__ */ jsx("div", { style: { fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: "Local DB dumps" }),
            /* @__PURE__ */ jsx("div", { style: { fontSize: 22, fontWeight: 600 }, children: status?.local?.count ?? "\u2014" }),
            /* @__PURE__ */ jsxs("div", { style: { fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: [
              status?.local ? formatBytes(status.local.totalBytes) : "\u2014",
              " total"
            ] })
          ]
        }
      ),
      /* @__PURE__ */ jsxs(
        "div",
        {
          style: {
            padding: 12,
            border: "1px solid var(--border, #e5e7eb)",
            borderRadius: 6
          },
          children: [
            /* @__PURE__ */ jsx("div", { style: { fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: "Offsite backups (GDrive)" }),
            /* @__PURE__ */ jsx("div", { style: { fontSize: 22, fontWeight: 600 }, children: status?.offsite?.count ?? "\u2014" }),
            /* @__PURE__ */ jsx("div", { style: { fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: newest ? `Newest: ${formatDate(newest.mtime)}` : "\u2014" })
          ]
        }
      )
    ] }),
    /* @__PURE__ */ jsx(ResultBanner, { result, onDismiss: () => setResult(null) })
  ] });
}
function CleanupPanel({
  companyId,
  listing,
  listingError,
  onRefresh
}) {
  const markGolden = usePluginAction("mark-golden");
  const cleanupStale = usePluginAction("cleanup-stale");
  const setThreshold = usePluginAction("set-golden-cleanup-threshold");
  const [scope, setScope] = useState(
    "hourly"
  );
  const [thresholdDays, setThresholdDays] = useState(14);
  const [busy, setBusy] = useState(false);
  const [previewTick, setPreviewTick] = useState(0);
  const previewResult = usePluginData("gdrive-cleanup-preview", {
    scope,
    thresholdDays,
    allowActiveBtcCompany: true,
    // preview-only, no actual deletion
    _tick: previewTick
  });
  const preview = previewResult?.data;
  const previewError = previewResult?.error ? String(previewResult.error) : null;
  const [result, setResult] = useState(null);
  useEffect(() => {
    setPreviewTick((n) => n + 1);
  }, [scope, thresholdDays]);
  const totalLeaves = listing?.totals.count ?? 0;
  const totalGolden = listing?.totals.goldenCount ?? 0;
  const totalBytes = listing?.totals.totalBytes ?? 0;
  const goldenBytes = listing?.totals.goldenBytes ?? 0;
  const isProductionScope = scope === "perCompany" || scope === "hourly" || scope === "daily" || scope === "all";
  const doMarkGolden = async (leaf, golden, reason) => {
    setBusy(true);
    setResult(null);
    try {
      const r = await markGolden({
        leaf: leaf.path,
        golden,
        setBy: "ui",
        reason: golden ? reason ?? "manually marked golden" : null
      });
      setResult({
        ok: r.ok === true,
        message: r.message ?? (golden ? "Marked golden" : "Unmarked")
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
  const doCleanup = async (confirm, allowActiveBtcCompany) => {
    if (!preview) return;
    if (preview.wouldDeleteCount === 0) {
      setResult({
        ok: true,
        message: "Nothing to clean up \u2014 preview is empty.",
        dryRun: false,
        scope,
        thresholdDays
      });
      return;
    }
    if (isProductionScope && !confirm) {
      setResult({
        ok: false,
        message: `Refusing: production scope "${scope}" requires explicit confirmation.`,
        scope,
        thresholdDays
      });
      return;
    }
    if ((scope === "perCompany" || scope === "all") && !allowActiveBtcCompany) {
      setResult({
        ok: false,
        message: `Refusing: per-company scope requires allowActiveBtcCompany flag.`,
        scope,
        thresholdDays
      });
      return;
    }
    setBusy(true);
    setResult(null);
    try {
      const r = await cleanupStale({
        scope,
        thresholdDays,
        dryRun: false,
        confirmDelete: true,
        allowActiveBtcCompany
      });
      setResult({
        ok: r.ok === true,
        message: r.ok ? `Cleaned up ${r.deleted} leaves, skipped ${r.goldenSkipped} golden, kept ${r.ageKept} (age threshold).` : `Cleanup failed: ${(r.errors ?? []).join("; ")}`,
        deleted: r.deleted,
        goldenSkipped: r.goldenSkipped,
        ageKept: r.ageKept,
        dryRun: r.dryRun,
        scope: r.scope,
        thresholdDays: r.thresholdDays,
        deletedPaths: r.deletedPaths,
        skippedPaths: r.skippedPaths ?? [],
        errors: r.errors
      });
      onRefresh();
      setPreviewTick((n) => n + 1);
    } catch (err) {
      setResult({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  };
  const doSetThreshold = async (days) => {
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
  return /* @__PURE__ */ jsxs("section", { style: { display: "grid", gap: 16 }, children: [
    /* @__PURE__ */ jsxs(
      "div",
      {
        style: {
          padding: 16,
          border: "1px solid var(--border, #e5e7eb)",
          borderRadius: 8,
          background: "var(--card, #fafafa)"
        },
        children: [
          /* @__PURE__ */ jsx("h3", { style: { marginTop: 0, fontSize: 16 }, children: "GDrive cleanup overview" }),
          /* @__PURE__ */ jsxs("p", { style: { marginTop: 0, fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: [
            "Walks every backup leaf on gdrive under",
            " ",
            /* @__PURE__ */ jsx("code", { style: { fontFamily: "ui-monospace, monospace" }, children: listing?.cleanupPath ?? "\u2014" }),
            '. Flag a leaf as "golden" to protect it from automated cleanup. The',
            " ",
            /* @__PURE__ */ jsx("code", { style: { fontFamily: "ui-monospace, monospace" }, children: listing?.testPrefix ?? "\u2014" }),
            " subtree is reserved for the cleanup-panel integration test and is the only safe scope to use without explicit confirmation."
          ] }),
          listingError ? /* @__PURE__ */ jsxs(
            "div",
            {
              role: "alert",
              style: {
                padding: 12,
                border: "1px solid var(--destructive, #dc2626)",
                borderRadius: 6,
                color: "var(--destructive)",
                fontSize: 12
              },
              children: [
                "Failed to load cleanup listing: ",
                listingError
              ]
            }
          ) : null,
          /* @__PURE__ */ jsxs(
            "div",
            {
              style: {
                display: "grid",
                gridTemplateColumns: "repeat(4, 1fr)",
                gap: 8,
                marginTop: 8
              },
              children: [
                /* @__PURE__ */ jsxs(
                  "div",
                  {
                    style: {
                      padding: 12,
                      border: "1px solid var(--border, #e5e7eb)",
                      borderRadius: 6
                    },
                    children: [
                      /* @__PURE__ */ jsx("div", { style: { fontSize: 11, color: "var(--muted-foreground, #6b7280)" }, children: "Total leaves" }),
                      /* @__PURE__ */ jsx("div", { style: { fontSize: 20, fontWeight: 600 }, children: totalLeaves })
                    ]
                  }
                ),
                /* @__PURE__ */ jsxs(
                  "div",
                  {
                    style: {
                      padding: 12,
                      border: "1px solid var(--border, #e5e7eb)",
                      borderRadius: 6
                    },
                    children: [
                      /* @__PURE__ */ jsx("div", { style: { fontSize: 11, color: "var(--muted-foreground, #6b7280)" }, children: "Total bytes" }),
                      /* @__PURE__ */ jsx("div", { style: { fontSize: 20, fontWeight: 600 }, children: formatBytes(totalBytes) })
                    ]
                  }
                ),
                /* @__PURE__ */ jsxs(
                  "div",
                  {
                    style: {
                      padding: 12,
                      border: "1px solid var(--border, #e5e7eb)",
                      borderRadius: 6
                    },
                    children: [
                      /* @__PURE__ */ jsx(
                        "div",
                        {
                          style: { fontSize: 11, color: "hsl(45, 80%, 40%)", fontWeight: 600 },
                          title: "Leaves protected by a .golden.json sidecar",
                          children: "\u2605 Golden"
                        }
                      ),
                      /* @__PURE__ */ jsx("div", { style: { fontSize: 20, fontWeight: 600 }, children: totalGolden }),
                      /* @__PURE__ */ jsx("div", { style: { fontSize: 11, color: "var(--muted-foreground, #6b7280)" }, children: formatBytes(goldenBytes) })
                    ]
                  }
                ),
                /* @__PURE__ */ jsxs(
                  "div",
                  {
                    style: {
                      padding: 12,
                      border: "1px solid var(--border, #e5e7eb)",
                      borderRadius: 6
                    },
                    children: [
                      /* @__PURE__ */ jsx("div", { style: { fontSize: 11, color: "var(--muted-foreground, #6b7280)" }, children: "Cleanup-eligible (older than threshold)" }),
                      /* @__PURE__ */ jsx("div", { style: { fontSize: 20, fontWeight: 600 }, children: preview?.wouldDeleteCount ?? "\u2014" }),
                      /* @__PURE__ */ jsx("div", { style: { fontSize: 11, color: "var(--muted-foreground, #6b7280)" }, children: preview ? formatBytes(preview.wouldDeleteBytes) : "\u2014" })
                    ]
                  }
                )
              ]
            }
          )
        ]
      }
    ),
    /* @__PURE__ */ jsxs(
      "div",
      {
        style: {
          padding: 16,
          border: "1px solid var(--border, #e5e7eb)",
          borderRadius: 8
        },
        children: [
          /* @__PURE__ */ jsx("h3", { style: { marginTop: 0, fontSize: 16 }, children: "Cleanup stale backups" }),
          /* @__PURE__ */ jsxs("p", { style: { marginTop: 0, fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: [
            "Delete leaves older than the threshold that are NOT flagged as golden. The golden sidecar (a tiny ",
            /* @__PURE__ */ jsx("code", { children: ".golden.json" }),
            " next to each leaf) is the only thing that protects a leaf from this action."
          ] }),
          /* @__PURE__ */ jsxs("div", { style: { display: "flex", flexWrap: "wrap", gap: 12, alignItems: "end" }, children: [
            /* @__PURE__ */ jsxs("label", { style: { display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }, children: [
              "Scope",
              /* @__PURE__ */ jsxs(
                "select",
                {
                  value: scope,
                  onChange: (e) => setScope(e.target.value),
                  style: {
                    padding: "4px 8px",
                    border: "1px solid var(--border, #e5e7eb)",
                    borderRadius: 4,
                    fontSize: 12,
                    minWidth: 180,
                    color: "var(--foreground, #e5e7eb)",
                    background: "var(--card, #1f2937)"
                  },
                  children: [
                    /* @__PURE__ */ jsx("option", { value: "testOnly", children: "testOnly (safe \u2014 only test prefix)" }),
                    /* @__PURE__ */ jsx("option", { value: "hourly", children: "hourly (global hourly tier)" }),
                    /* @__PURE__ */ jsx("option", { value: "daily", children: "daily (global daily tier)" }),
                    /* @__PURE__ */ jsx("option", { value: "perCompany", children: "perCompany (active BTC company)" }),
                    /* @__PURE__ */ jsx("option", { value: "all", children: "all (everything except per-company is allowed)" })
                  ]
                }
              )
            ] }),
            /* @__PURE__ */ jsxs("label", { style: { display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }, children: [
              "Threshold (days)",
              /* @__PURE__ */ jsx(
                "input",
                {
                  type: "number",
                  min: 1,
                  max: 365,
                  value: thresholdDays,
                  onChange: (e) => setThresholdDays(Math.max(1, Math.min(365, Number(e.target.value) || 14))),
                  style: {
                    padding: "4px 8px",
                    border: "1px solid var(--border, #e5e7eb)",
                    borderRadius: 4,
                    width: 100,
                    color: "var(--foreground, #e5e7eb)",
                    background: "var(--card, #1f2937)"
                  }
                }
              )
            ] }),
            /* @__PURE__ */ jsx(
              ActionButton,
              {
                label: "Refresh preview",
                busy: false,
                onClick: doPreviewCleanup,
                variant: "default",
                hint: `Scans gdrive and computes what cleanup would delete (always safe \u2014 no deletes).`
              }
            )
          ] }),
          previewError ? /* @__PURE__ */ jsxs(
            "div",
            {
              role: "alert",
              style: {
                marginTop: 8,
                padding: 8,
                border: "1px solid var(--destructive, #dc2626)",
                borderRadius: 4,
                fontSize: 12,
                color: "var(--destructive)"
              },
              children: [
                "Preview failed: ",
                previewError
              ]
            }
          ) : null,
          preview && preview.scopeErrors.length > 0 ? /* @__PURE__ */ jsxs(
            "div",
            {
              role: "alert",
              style: {
                marginTop: 8,
                padding: 8,
                border: "1px solid var(--destructive, #dc2626)",
                borderRadius: 4,
                fontSize: 12,
                color: "var(--destructive)"
              },
              children: [
                "Scope errors: ",
                preview.scopeErrors.join("; ")
              ]
            }
          ) : null,
          preview ? /* @__PURE__ */ jsxs(
            "div",
            {
              style: {
                marginTop: 12,
                padding: 12,
                border: "1px solid var(--border, #e5e7eb)",
                borderRadius: 6,
                background: "var(--muted, #f9fafb)"
              },
              children: [
                /* @__PURE__ */ jsxs("div", { style: { fontSize: 12, marginBottom: 8 }, children: [
                  /* @__PURE__ */ jsx("strong", { children: "Would delete:" }),
                  " ",
                  preview.wouldDeleteCount,
                  " leaves (",
                  formatBytes(preview.wouldDeleteBytes),
                  ") \xB7 ",
                  /* @__PURE__ */ jsx("strong", { children: "Golden-skipped:" }),
                  " ",
                  preview.goldenSkippedCount,
                  " \xB7 ",
                  /* @__PURE__ */ jsx("strong", { children: "Age-kept:" }),
                  " ",
                  preview.ageKeptCount
                ] }),
                preview.wouldDeleteCount > 0 ? /* @__PURE__ */ jsxs(
                  "div",
                  {
                    style: {
                      maxHeight: 200,
                      overflow: "auto",
                      fontFamily: "ui-monospace, monospace",
                      fontSize: 11,
                      padding: 8,
                      background: "var(--card, #fff)",
                      border: "1px solid var(--border, #e5e7eb)",
                      borderRadius: 4
                    },
                    children: [
                      preview.wouldDelete.slice(0, 200).map((l) => `${l.path}  (${formatDate(l.modified)}, ${formatBytes(l.sizeBytes)})`).join("\n"),
                      preview.wouldDelete.length > 200 ? `
\u2026 ${preview.wouldDelete.length - 200} more` : ""
                    ]
                  }
                ) : /* @__PURE__ */ jsx(
                  "div",
                  {
                    style: {
                      fontSize: 12,
                      color: "var(--muted-foreground, #6b7280)"
                    },
                    children: "Nothing to delete."
                  }
                ),
                /* @__PURE__ */ jsx("div", { style: { display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }, children: scope === "testOnly" ? /* @__PURE__ */ jsx(
                  ActionButton,
                  {
                    label: `Delete ${preview.wouldDeleteCount} (testOnly scope)`,
                    busy,
                    onClick: () => doCleanup(true, true),
                    variant: "danger",
                    hint: "testOnly scope requires no extra flags \u2014 only touches the test prefix.",
                    disabled: preview.wouldDeleteCount === 0
                  }
                ) : scope === "hourly" || scope === "daily" ? /* @__PURE__ */ jsx(
                  ActionButton,
                  {
                    label: `Delete ${preview.wouldDeleteCount} (scope=${scope})`,
                    busy,
                    onClick: () => doCleanup(true, true),
                    variant: "danger",
                    hint: `Production scope. Will confirm in browser. confirmDelete:true is sent.`,
                    disabled: preview.wouldDeleteCount === 0
                  }
                ) : /* @__PURE__ */ jsx(
                  ActionButton,
                  {
                    label: `Delete ${preview.wouldDeleteCount} (scope=${scope})`,
                    busy,
                    onClick: () => doCleanup(true, true),
                    variant: "danger",
                    hint: "Production scope. Will confirm in browser. confirmDelete:true and allowActiveBtcCompany:true are sent.",
                    disabled: preview.wouldDeleteCount === 0
                  }
                ) }),
                scope === "testOnly" && preview.wouldDeleteCount > 0 ? /* @__PURE__ */ jsx(
                  ConfirmInline,
                  {
                    message: `Permanently delete ${preview.wouldDeleteCount} leaves from the test prefix? Real gdrive data is not touched (testOnly scope only).`,
                    confirmLabel: "Yes, delete from test prefix",
                    onConfirm: () => doCleanup(true, true),
                    busy
                  }
                ) : null,
                (scope === "hourly" || scope === "daily") && preview.wouldDeleteCount > 0 ? /* @__PURE__ */ jsx(
                  ConfirmInline,
                  {
                    message: `PRODUCTION: this will permanently delete ${preview.wouldDeleteCount} leaves from the gdrive "${scope}" tier. Golden leaves are protected. Continue?`,
                    confirmLabel: "Yes, delete from production tier",
                    onConfirm: () => doCleanup(true, true),
                    busy
                  }
                ) : null,
                (scope === "perCompany" || scope === "all") && preview.wouldDeleteCount > 0 ? /* @__PURE__ */ jsx(
                  ConfirmInline,
                  {
                    message: `PRODUCTION + ACTIVE BTC COMPANY: this will permanently delete ${preview.wouldDeleteCount} leaves from the active per-company prefix. Golden leaves are protected. Type DELETE in the box to confirm.`,
                    confirmLabel: "Yes, delete from active BTC company prefix",
                    requireText: "DELETE",
                    onConfirm: () => doCleanup(true, true),
                    busy
                  }
                ) : null
              ]
            }
          ) : null,
          /* @__PURE__ */ jsx("div", { style: { marginTop: 12 }, children: /* @__PURE__ */ jsxs("details", { children: [
            /* @__PURE__ */ jsx("summary", { style: { fontSize: 12, cursor: "pointer" }, children: "Persist threshold as plugin default" }),
            /* @__PURE__ */ jsxs(
              "div",
              {
                style: {
                  marginTop: 8,
                  display: "flex",
                  gap: 8,
                  alignItems: "end"
                },
                children: [
                  /* @__PURE__ */ jsx(
                    "input",
                    {
                      type: "number",
                      min: 1,
                      max: 365,
                      defaultValue: thresholdDays,
                      id: "cleanup-threshold-input",
                      style: {
                        padding: "4px 8px",
                        border: "1px solid var(--border, #e5e7eb)",
                        borderRadius: 4,
                        width: 100
                      }
                    }
                  ),
                  /* @__PURE__ */ jsx(
                    "button",
                    {
                      type: "button",
                      onClick: () => {
                        const inp = document.getElementById("cleanup-threshold-input");
                        const v = inp ? parseInt(inp.value, 10) : NaN;
                        if (Number.isFinite(v) && v >= 1) doSetThreshold(v);
                      },
                      style: {
                        padding: "6px 12px",
                        background: "#374151",
                        color: "#f8fafc",
                        border: "1px solid transparent",
                        borderRadius: 4,
                        cursor: "pointer",
                        fontSize: 12
                      },
                      children: "Save"
                    }
                  )
                ]
              }
            )
          ] }) })
        ]
      }
    ),
    /* @__PURE__ */ jsxs(
      "div",
      {
        style: {
          padding: 16,
          border: "1px solid var(--border, #e5e7eb)",
          borderRadius: 8
        },
        children: [
          /* @__PURE__ */ jsx("h3", { style: { marginTop: 0, fontSize: 16 }, children: "Backup leaves by tier" }),
          /* @__PURE__ */ jsx("p", { style: { marginTop: 0, fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: 'Every leaf on gdrive. Click "\u2605 Mark golden" to write a protective sidecar; click again to remove it. Golden leaves are skipped by cleanup-stale no matter what.' }),
          listing?.roots.map((root) => /* @__PURE__ */ jsx(
            TierBlock,
            {
              root,
              onMarkGolden: doMarkGolden,
              busy,
              companyId
            },
            root.prefix
          ))
        ]
      }
    ),
    /* @__PURE__ */ jsx(
      ResultBanner,
      {
        result: result ? {
          ok: result.ok,
          message: result.message
        } : null,
        onDismiss: () => setResult(null)
      }
    )
  ] });
}
function TierBlock({
  root,
  onMarkGolden,
  busy,
  companyId
}) {
  const [filter, setFilter] = useState("all");
  const [sortBy, setSortBy] = useState("newest");
  const visibleLeaves = useMemo(() => {
    let lvs = root.leaves.slice();
    if (filter === "golden") lvs = lvs.filter((l) => l.golden);
    if (filter === "nongolden") lvs = lvs.filter((l) => !l.golden);
    if (filter === "stale") {
      const cutoff = Date.now() - 14 * 864e5;
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
  return /* @__PURE__ */ jsxs(
    "div",
    {
      style: {
        marginTop: 12,
        padding: 12,
        border: "1px solid var(--border, #e5e7eb)",
        borderRadius: 6,
        background: isTestPrefix ? "color-mix(in oklab, hsl(190, 35%, 25%) 60%, var(--card))" : "var(--card, #fafafa)"
      },
      children: [
        /* @__PURE__ */ jsxs(
          "div",
          {
            style: {
              display: "flex",
              justifyContent: "space-between",
              alignItems: "baseline",
              flexWrap: "wrap",
              gap: 8
            },
            children: [
              /* @__PURE__ */ jsxs("div", { children: [
                /* @__PURE__ */ jsx("strong", { style: { fontSize: 13 }, children: tierLabel }),
                /* @__PURE__ */ jsx(
                  "span",
                  {
                    style: {
                      marginLeft: 8,
                      fontFamily: "ui-monospace, monospace",
                      fontSize: 11,
                      color: "var(--muted-foreground, #6b7280)"
                    },
                    children: root.prefix
                  }
                )
              ] }),
              /* @__PURE__ */ jsxs("div", { style: { fontSize: 11, color: "var(--muted-foreground, #6b7280)" }, children: [
                root.count,
                " leaves \xB7 ",
                formatBytes(root.totalBytes),
                " \xB7 ",
                root.goldenCount,
                " golden (",
                formatBytes(root.goldenBytes),
                ")"
              ] })
            ]
          }
        ),
        /* @__PURE__ */ jsxs(
          "div",
          {
            style: {
              display: "flex",
              gap: 8,
              alignItems: "center",
              marginTop: 6,
              fontSize: 11,
              color: "var(--muted-foreground, #6b7280)"
            },
            children: [
              "Filter:",
              /* @__PURE__ */ jsxs(
                "select",
                {
                  value: filter,
                  onChange: (e) => setFilter(e.target.value),
                  style: { fontSize: 11, padding: "2px 4px", border: "1px solid var(--border, #e5e7eb)", borderRadius: 3, color: "var(--foreground, #e5e7eb)", background: "var(--card, #1f2937)" },
                  children: [
                    /* @__PURE__ */ jsx("option", { value: "all", children: "all" }),
                    /* @__PURE__ */ jsx("option", { value: "golden", children: "\u2605 golden only" }),
                    /* @__PURE__ */ jsx("option", { value: "nongolden", children: "non-golden only" }),
                    /* @__PURE__ */ jsx("option", { value: "stale", children: "stale (>14d, default threshold)" })
                  ]
                }
              ),
              "Sort:",
              /* @__PURE__ */ jsxs(
                "select",
                {
                  value: sortBy,
                  onChange: (e) => setSortBy(e.target.value),
                  style: { fontSize: 11, padding: "2px 4px", border: "1px solid var(--border, #e5e7eb)", borderRadius: 3, color: "var(--foreground, #e5e7eb)", background: "var(--card, #1f2937)" },
                  children: [
                    /* @__PURE__ */ jsx("option", { value: "newest", children: "newest first" }),
                    /* @__PURE__ */ jsx("option", { value: "oldest", children: "oldest first" }),
                    /* @__PURE__ */ jsx("option", { value: "size", children: "largest first" })
                  ]
                }
              )
            ]
          }
        ),
        /* @__PURE__ */ jsx(
          "div",
          {
            style: {
              marginTop: 6,
              maxHeight: 360,
              overflow: "auto",
              border: "1px solid var(--border, #e5e7eb)",
              borderRadius: 4
            },
            children: visibleLeaves.length === 0 ? /* @__PURE__ */ jsx(
              "div",
              {
                style: {
                  padding: 8,
                  fontSize: 12,
                  color: "var(--muted-foreground, #6b7280)"
                },
                children: "(no leaves match this filter)"
              }
            ) : visibleLeaves.map((leaf) => /* @__PURE__ */ jsxs(
              "div",
              {
                style: {
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "6px 10px",
                  borderBottom: "1px solid var(--border, #e5e7eb)",
                  background: leaf.golden ? "color-mix(in oklab, hsl(45, 80%, 60%) 12%, var(--card, #fff))" : void 0
                },
                children: [
                  /* @__PURE__ */ jsx(
                    "span",
                    {
                      style: {
                        fontSize: 11,
                        fontWeight: 700,
                        color: leaf.golden ? "hsl(45, 80%, 35%)" : "var(--muted-foreground, #6b7280)",
                        width: 18,
                        textAlign: "center"
                      },
                      title: leaf.golden ? "golden" : "not golden",
                      children: leaf.golden ? "\u2605" : "\xB7"
                    }
                  ),
                  /* @__PURE__ */ jsxs(
                    "span",
                    {
                      style: {
                        flex: 1,
                        fontFamily: "ui-monospace, monospace",
                        fontSize: 11,
                        wordBreak: "break-all"
                      },
                      children: [
                        leaf.path,
                        /* @__PURE__ */ jsxs(
                          "span",
                          {
                            style: {
                              color: "var(--muted-foreground, #6b7280)",
                              marginLeft: 6
                            },
                            children: [
                              "\xB7 ",
                              formatDate(leaf.modified),
                              " \xB7",
                              " ",
                              leaf.coreBytes ? /* @__PURE__ */ jsxs("span", { children: [
                                "core ",
                                /* @__PURE__ */ jsx("strong", { children: formatBytes(leaf.coreBytes) }),
                                leaf.changesBytes ? /* @__PURE__ */ jsxs(Fragment, { children: [
                                  " ",
                                  /* @__PURE__ */ jsxs("span", { style: { color: "hsl(35, 80%, 40%)" }, children: [
                                    "(changes ",
                                    /* @__PURE__ */ jsx("strong", { children: formatBytes(leaf.changesBytes) }),
                                    ")"
                                  ] })
                                ] }) : null
                              ] }) : /* @__PURE__ */ jsx("span", { children: formatBytes(leaf.sizeBytes) })
                            ]
                          }
                        ),
                        leaf.golden && leaf.goldenSetBy ? /* @__PURE__ */ jsxs(
                          "span",
                          {
                            style: {
                              color: "hsl(45, 80%, 35%)",
                              marginLeft: 6,
                              fontSize: 10
                            },
                            children: [
                              "(set by ",
                              leaf.goldenSetBy,
                              leaf.goldenSetAt ? ` on ${formatDate(leaf.goldenSetAt)}` : "",
                              leaf.goldenReason ? ` \u2014 ${leaf.goldenReason}` : "",
                              ")"
                            ]
                          }
                        ) : null
                      ]
                    }
                  ),
                  leaf.golden ? /* @__PURE__ */ jsx(
                    "button",
                    {
                      type: "button",
                      disabled: busy,
                      onClick: () => onMarkGolden(leaf, false),
                      style: {
                        padding: "2px 8px",
                        fontSize: 11,
                        border: "1px solid var(--border, #e5e7eb)",
                        borderRadius: 3,
                        background: "var(--muted, #f3f4f6)",
                        cursor: busy ? "not-allowed" : "pointer"
                      },
                      children: "Unmark golden"
                    }
                  ) : /* @__PURE__ */ jsx(
                    "button",
                    {
                      type: "button",
                      disabled: busy,
                      onClick: () => onMarkGolden(leaf, true),
                      style: {
                        padding: "2px 8px",
                        fontSize: 11,
                        border: "1px solid transparent",
                        borderRadius: 3,
                        background: "hsl(45, 80%, 40%)",
                        color: "#f8fafc",
                        cursor: busy ? "not-allowed" : "pointer"
                      },
                      children: "\u2605 Mark golden"
                    }
                  )
                ]
              },
              leaf.path
            ))
          }
        )
      ]
    }
  );
}
function ConfirmInline({
  message,
  confirmLabel,
  onConfirm,
  busy,
  requireText
}) {
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const canConfirm = !requireText || typed === requireText;
  if (!open) {
    return /* @__PURE__ */ jsx("div", { style: { marginTop: 8 }, children: /* @__PURE__ */ jsxs(
      "button",
      {
        type: "button",
        onClick: () => setOpen(true),
        style: {
          padding: "4px 10px",
          fontSize: 11,
          border: "1px solid var(--destructive, #dc2626)",
          color: "var(--destructive, #dc2626)",
          background: "transparent",
          borderRadius: 4,
          cursor: "pointer"
        },
        children: [
          confirmLabel,
          "\u2026"
        ]
      }
    ) });
  }
  return /* @__PURE__ */ jsxs(
    "div",
    {
      style: {
        marginTop: 8,
        padding: 10,
        border: "1px solid var(--destructive, #dc2626)",
        borderRadius: 6,
        background: "color-mix(in oklab, var(--destructive) 4%, var(--card))",
        fontSize: 12
      },
      children: [
        /* @__PURE__ */ jsx("div", { style: { marginBottom: 6 }, children: message }),
        requireText ? /* @__PURE__ */ jsxs("div", { style: { marginBottom: 6 }, children: [
          "Type ",
          /* @__PURE__ */ jsx("code", { children: requireText }),
          " to confirm:",
          " ",
          /* @__PURE__ */ jsx(
            "input",
            {
              type: "text",
              value: typed,
              onChange: (e) => setTyped(e.target.value),
              style: {
                padding: "2px 6px",
                border: "1px solid var(--destructive, #dc2626)",
                borderRadius: 3,
                fontFamily: "ui-monospace, monospace",
                fontSize: 11,
                width: 120
              }
            }
          )
        ] }) : null,
        /* @__PURE__ */ jsxs("div", { style: { display: "flex", gap: 8 }, children: [
          /* @__PURE__ */ jsx(
            "button",
            {
              type: "button",
              onClick: onConfirm,
              disabled: !canConfirm || busy,
              style: {
                padding: "4px 12px",
                fontSize: 12,
                background: "var(--destructive, #b91c1c)",
                color: "#f8fafc",
                border: "1px solid transparent",
                borderRadius: 4,
                cursor: canConfirm && !busy ? "pointer" : "not-allowed",
                opacity: canConfirm && !busy ? 1 : 0.5
              },
              children: confirmLabel
            }
          ),
          /* @__PURE__ */ jsx(
            "button",
            {
              type: "button",
              onClick: () => {
                setOpen(false);
                setTyped("");
              },
              style: {
                padding: "4px 12px",
                fontSize: 12,
                background: "var(--muted, #f3f4f6)",
                border: "1px solid var(--border, #e5e7eb)",
                borderRadius: 4,
                cursor: "pointer"
              },
              children: "Cancel"
            }
          )
        ] })
      ]
    }
  );
}
function BackupManagerPage({
  context
}) {
  const host = useHostContext();
  const companyId = context.companyId ?? host.companyId ?? null;
  const [tab, setTab] = useState("manager");
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
  const recoverySnapshotsResult = usePluginData("recovery-snapshots", { _tick: refreshTick });
  const recoverySnapshots = recoverySnapshotsResult?.data;
  const recoverySnapshotsError = recoverySnapshotsResult?.error ? String(recoverySnapshotsResult.error) : null;
  const tierStatusResult = usePluginData("gdrive-tier-status", { _tick: refreshTick });
  const tierStatus = tierStatusResult?.data;
  const tierProgressResult = usePluginData("tier-upload-progress", { _tick: refreshTick });
  const tierProgress = tierProgressResult?.data;
  const statusResult = usePluginData("status", { companyId });
  const status = statusResult?.data;
  const listingResult = usePluginData("listing", { companyId, _tick: refreshTick });
  const listing = listingResult?.data;
  const error = listingResult?.error ? String(listingResult.error) : null;
  const locationsResult = usePluginData("locations", {});
  const locationsData = locationsResult?.data;
  const cleanupListingResult = usePluginData("gdrive-cleanup-listing", {
    companyId,
    _tick: refreshTick
  });
  const cleanupListing = cleanupListingResult?.data;
  const cleanupListingError = cleanupListingResult?.error ? String(cleanupListingResult.error) : null;
  const procRunning = recoverySnapshots && Array.isArray(recoverySnapshots.runningSnapshots) ? recoverySnapshots.runningSnapshots.find((r) => /recovery\.sh/.test(r.cmd || "")) || null : null;
  const stateRunning = status && status.backupRunning ? status.backupRunning : null;
  const stateRecovery = stateRunning && stateRunning.recovery === true;
  const stateForced = stateRunning && stateRunning.isForced === true;
  const forceRunning = procRunning ? {
    pid: procRunning.pid,
    startedAt: procRunning.startedAt,
    cmd: procRunning.cmd,
    isForced: !!(stateForced || /--force/.test(procRunning.cmd || ""))
  } : stateRecovery && stateForced && stateRunning ? {
    pid: stateRunning.pid,
    startedAt: stateRunning.startedAt,
    isForced: true
  } : null;
  const [busy, setBusy] = useState(null);
  const [result, setResult] = useState(null);
  const [restorePath, setRestorePath] = useState("");
  const [restoreDest, setRestoreDest] = useState("/tmp/paperclip-restore");
  const [restoreFile, setRestoreFile] = useState("");
  const [keep, setKeep] = useState(10);
  const [offsiteKeep, setOffsiteKeep] = useState(null);
  const elapsedMs = useElapsedMs(busy != null);
  const runningNow = status?.backupRunning ?? null;
  useEffect(() => {
    if (busy !== "backup" && !runningNow) return;
    const t = setInterval(() => setRefreshTick((n) => n + 1), 3e4);
    return () => clearInterval(t);
  }, [busy, runningNow?.pid, runningNow?.startedAt]);
  useEffect(() => {
    if (!listing || !("loading" in listing) || !listing.loading) return;
    const t = setInterval(() => setRefreshTick((n) => n + 1), 4e3);
    return () => clearInterval(t);
  }, [listing && "loading" in listing ? listing.loading : false]);
  const triggerBackup = async () => {
    if (busy) return;
    setBusy("backup");
    setResult(null);
    try {
      const r = await runBackup({ companyId });
      if (r.alreadyRunning) {
        setResult({ ok: false, message: r.message ?? "Backup already running" });
      } else if (r.async || r.pid) {
        setResult({
          ok: true,
          message: r.message ?? `Backup started in background (pid=${r.pid})`
        });
      } else {
        setResult({
          ok: r.ok === true,
          exitCode: r.exitCode ?? null,
          message: r.ok === true ? "Backup pushed" : "Backup script failed",
          durationMs: r.durationMs,
          stdout: r.stdout,
          stderr: r.stderr
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
      const r = await pruneLocal({ keep });
      setResult({
        ok: r.ok === true,
        message: r.ok === true ? `Pruned, kept ${r.keep ?? keep}` : "Prune failed",
        durationMs: r.durationMs,
        stdout: r.stdout,
        stderr: r.stderr,
        keep: r.keep ?? keep,
        totalBytesBefore: r.totalBytesBefore,
        totalBytesAfter: r.totalBytesAfter,
        prunedCount: r.prunedCount
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
      const r = await restoreOffsite({
        companyId,
        path: restorePath || "latest",
        destDir: restoreDest
      });
      const usedPath = (r.remotePath ?? restorePath) || "latest";
      setResult({
        ok: r.ok === true,
        message: r.ok === true ? `Restored from ${usedPath}` : "Restore failed",
        durationMs: r.durationMs,
        stdout: r.stdout,
        stderr: r.stderr,
        remotePath: usedPath,
        destDir: r.destDir ?? restoreDest
      });
    } catch (err) {
      setResult({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(null);
    }
  };
  const triggerPruneOffsite = async () => {
    if (busy) return;
    const effectiveKeep = offsiteKeep ?? listing?.offsiteRetention?.keep ?? listing?.config?.offsiteKeep ?? 30;
    setBusy("prune-off");
    setResult(null);
    try {
      const r = await pruneOffsite({ companyId, keep: effectiveKeep });
      if (r.alreadyRunning) {
        const elapsed = typeof r.elapsedMs === "number" ? ` (already running for ${Math.round(r.elapsedMs / 1e3)}s)` : "";
        setResult({
          ok: false,
          message: r.message ?? `Offsite prune already running${elapsed}. Pass force:true to override.`
        });
        return;
      }
      if (r.async === true || r.startedAt) {
        setResult({
          ok: true,
          message: r.message ?? `Prune started in background (keep=${effectiveKeep}).`,
          keep: r.keep ?? effectiveKeep
        });
        return;
      }
      const pruned = r.offsitePruned ?? 0;
      const kept = r.offsiteKept ?? 0;
      setResult({
        ok: r.ok === true,
        message: r.ok === true ? pruned === 0 ? `Nothing to prune \u2014 already at or below keep=${effectiveKeep}.` : `Pruned ${pruned} offsite backups (kept newest ${kept}).` : r.message ?? "Prune failed",
        durationMs: r.durationMs,
        stdout: r.stdout,
        stderr: r.stderr,
        keep: r.keep ?? effectiveKeep,
        totalBytesBefore: r.totalBytesBefore,
        totalBytesAfter: r.totalBytesAfter,
        prunedCount: pruned
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
      const r = await restoreLocal({ filename: restoreFile, destDir: restoreDest });
      setResult({
        ok: r.ok === true,
        message: r.ok === true ? `Copied ${restoreFile}` : "Restore failed",
        durationMs: r.durationMs,
        stdout: r.stdout,
        stderr: r.stderr,
        destDir: r.destDir ?? restoreDest
      });
    } catch (err) {
      setResult({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(null);
    }
  };
  return /* @__PURE__ */ jsxs("article", { style: { display: "grid", gap: 16, padding: 16 }, children: [
    /* @__PURE__ */ jsxs("header", { children: [
      /* @__PURE__ */ jsx("h2", { style: { margin: 0, fontSize: 20 }, children: "Backup Manager" }),
      /* @__PURE__ */ jsxs("p", { style: { marginTop: 4, color: "var(--muted-foreground, #6b7280)", fontSize: 13 }, children: [
        "Offsite push (rclone \u2192 GDrive) and local DB-dump retention. The",
        " ",
        /* @__PURE__ */ jsx("strong", { children: "Cleanup (GDrive)" }),
        " tab is a comprehensive view of every backup leaf on gdrive with golden-flag protection and bulk stale cleanup."
      ] })
    ] }),
    /* @__PURE__ */ jsxs(
      "nav",
      {
        role: "tablist",
        style: {
          display: "flex",
          gap: 4,
          borderBottom: "1px solid var(--border, #e5e7eb)"
        },
        children: [
          /* @__PURE__ */ jsx(TabButton, { active: tab === "manager", onClick: () => setTab("manager"), children: "Backup manager" }),
          /* @__PURE__ */ jsx(TabButton, { active: tab === "cleanup", onClick: () => setTab("cleanup"), children: "Cleanup (GDrive)" }),
          /* @__PURE__ */ jsx(TabButton, { active: tab === "recovery", onClick: () => setTab("recovery"), children: "Force backup & recovery" })
        ]
      }
    ),
    tab === "manager" ? /* @__PURE__ */ jsxs(Fragment, { children: [
      /* @__PURE__ */ jsxs(
        "section",
        {
          style: {
            padding: 16,
            border: "1px solid var(--border, #e5e7eb)",
            borderRadius: 8,
            background: "color-mix(in oklab, var(--muted) 4%, var(--card))"
          },
          children: [
            /* @__PURE__ */ jsx("h3", { style: { marginTop: 0, fontSize: 16 }, children: "Backup locations" }),
            /* @__PURE__ */ jsx(
              "p",
              {
                style: {
                  marginTop: 0,
                  marginBottom: 8,
                  color: "var(--muted-foreground, #6b7280)",
                  fontSize: 12
                },
                children: "Every path the operator needs to know about."
              }
            ),
            /* @__PURE__ */ jsxs(
              "table",
              {
                style: {
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 12,
                  fontFamily: "ui-monospace, monospace"
                },
                children: [
                  /* @__PURE__ */ jsx("thead", { children: /* @__PURE__ */ jsxs(
                    "tr",
                    {
                      style: {
                        textAlign: "left",
                        color: "var(--muted-foreground, #6b7280)"
                      },
                      children: [
                        /* @__PURE__ */ jsx("th", { style: { padding: "4px 6px", width: 180 }, children: "What" }),
                        /* @__PURE__ */ jsx("th", { style: { padding: "4px 6px" }, children: "Path / Where" }),
                        /* @__PURE__ */ jsx("th", { style: { padding: "4px 6px", width: 200 }, children: "Note" })
                      ]
                    }
                  ) }),
                  /* @__PURE__ */ jsx("tbody", { children: (locationsData?.items ?? []).map((it) => /* @__PURE__ */ jsxs(
                    "tr",
                    {
                      style: { borderTop: "1px solid var(--border, #e5e7eb)" },
                      children: [
                        /* @__PURE__ */ jsx("td", { style: { padding: "4px 6px", color: "var(--muted-foreground, #6b7280)" }, children: it.id }),
                        /* @__PURE__ */ jsx("td", { style: { padding: "4px 6px", wordBreak: "break-all" }, children: it.path }),
                        /* @__PURE__ */ jsx("td", { style: { padding: "4px 6px", color: "var(--muted-foreground, #6b7280)" }, children: it.note || "" })
                      ]
                    },
                    it.id
                  )) })
                ]
              }
            )
          ]
        }
      ),
      error ? /* @__PURE__ */ jsxs(
        "div",
        {
          role: "alert",
          style: {
            padding: 12,
            border: "1px solid var(--destructive, #dc2626)",
            borderRadius: 6,
            background: "color-mix(in oklab, var(--destructive) 8%, var(--card))",
            color: "var(--destructive)"
          },
          children: [
            "Failed to load: ",
            error
          ]
        }
      ) : listing?.missingCompanyId ? /* @__PURE__ */ jsx(
        "div",
        {
          role: "alert",
          style: {
            padding: 12,
            border: "1px solid var(--border, #e5e7eb)",
            borderRadius: 6,
            background: "color-mix(in oklab, var(--muted) 30%, var(--card))",
            color: "var(--muted-foreground, #6b7280)"
          },
          children: "No active company. Open this page from a company context."
        }
      ) : null,
      /* @__PURE__ */ jsxs("section", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }, children: [
        /* @__PURE__ */ jsxs(
          "div",
          {
            style: {
              padding: 16,
              border: "1px solid var(--border, #e5e7eb)",
              borderRadius: 8
            },
            children: [
              /* @__PURE__ */ jsxs(
                "header",
                {
                  style: {
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 8
                  },
                  children: [
                    /* @__PURE__ */ jsx("h3", { style: { margin: 0, fontSize: 16 }, children: "Local DB dumps" }),
                    /* @__PURE__ */ jsxs("span", { style: { fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: [
                      listing?.local.count ?? "\u2014",
                      " files / ",
                      listing ? formatBytes(listing.local.totalBytes) : "\u2014"
                    ] })
                  ]
                }
              ),
              /* @__PURE__ */ jsx("div", { style: { maxHeight: 240, overflow: "auto", fontSize: 12 }, children: listing?.local.dumps.length ? /* @__PURE__ */ jsxs("table", { style: { width: "100%", borderCollapse: "collapse" }, children: [
                /* @__PURE__ */ jsx("thead", { children: /* @__PURE__ */ jsxs(
                  "tr",
                  {
                    style: {
                      textAlign: "left",
                      color: "var(--muted-foreground, #6b7280)"
                    },
                    children: [
                      /* @__PURE__ */ jsx("th", { style: { padding: "4px 6px" }, children: "File" }),
                      /* @__PURE__ */ jsx("th", { style: { padding: "4px 6px" }, children: "Modified" }),
                      /* @__PURE__ */ jsx("th", { style: { padding: "4px 6px", textAlign: "right" }, children: "Size" })
                    ]
                  }
                ) }),
                /* @__PURE__ */ jsx("tbody", { children: listing.local.dumps.map((d) => /* @__PURE__ */ jsxs(
                  "tr",
                  {
                    style: {
                      borderTop: "1px solid var(--border, #e5e7eb)",
                      background: restoreFile === d.filename ? "var(--accent, #f3f4f6)" : void 0,
                      cursor: "pointer"
                    },
                    onClick: () => setRestoreFile(d.filename),
                    children: [
                      /* @__PURE__ */ jsx(
                        "td",
                        {
                          style: {
                            padding: "4px 6px",
                            fontFamily: "ui-monospace, monospace"
                          },
                          children: d.filename
                        }
                      ),
                      /* @__PURE__ */ jsx("td", { style: { padding: "4px 6px" }, children: formatDate(d.mtime) }),
                      /* @__PURE__ */ jsx("td", { style: { padding: "4px 6px", textAlign: "right" }, children: formatBytes(d.sizeBytes) })
                    ]
                  },
                  d.filename
                )) })
              ] }) : /* @__PURE__ */ jsx("div", { style: { color: "var(--muted-foreground, #6b7280)" }, children: "No local DB dumps found." }) }),
              /* @__PURE__ */ jsxs(
                "div",
                {
                  style: {
                    display: "flex",
                    gap: 8,
                    alignItems: "end",
                    marginTop: 12,
                    flexWrap: "wrap"
                  },
                  children: [
                    /* @__PURE__ */ jsxs("label", { style: { display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }, children: [
                      "Keep",
                      /* @__PURE__ */ jsx(
                        "input",
                        {
                          type: "number",
                          min: 1,
                          max: 365,
                          value: keep,
                          onChange: (e) => setKeep(Math.max(1, Number(e.target.value) || 10)),
                          style: {
                            padding: "4px 8px",
                            border: "1px solid var(--border, #e5e7eb)",
                            borderRadius: 4,
                            width: 80
                          }
                        }
                      )
                    ] }),
                    /* @__PURE__ */ jsx(
                      ActionButton,
                      {
                        label: "Prune local dumps",
                        busy: busy === "prune",
                        onClick: triggerPrune,
                        variant: "danger",
                        hint: `Keep newest ${keep} file(s)`,
                        elapsedMs
                      }
                    ),
                    /* @__PURE__ */ jsx(
                      ActionButton,
                      {
                        label: "Restore local file",
                        busy: busy === "restore-loc",
                        onClick: triggerRestoreLocal,
                        hint: restoreFile ? `Copy ${restoreFile}` : "Select a file in the table first",
                        disabled: !restoreFile,
                        elapsedMs
                      }
                    )
                  ]
                }
              )
            ]
          }
        ),
        /* @__PURE__ */ jsxs(
          "div",
          {
            style: {
              padding: 16,
              border: "1px solid var(--border, #e5e7eb)",
              borderRadius: 8
            },
            children: [
              /* @__PURE__ */ jsxs(
                "header",
                {
                  style: {
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 8
                  },
                  children: [
                    /* @__PURE__ */ jsx("h3", { style: { margin: 0, fontSize: 16 }, children: "Offsite backups (GDrive)" }),
                    /* @__PURE__ */ jsxs("span", { style: { fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: [
                      listing?.offsite.count ?? "\u2014",
                      " entries \xB7 keep newest",
                      " ",
                      listing?.offsiteRetention?.keep ?? listing?.config?.offsiteKeep ?? 30
                    ] })
                  ]
                }
              ),
              /* @__PURE__ */ jsx("div", { style: { maxHeight: 240, overflow: "auto", fontSize: 12 }, children: listing?.offsite.backups.length ? /* @__PURE__ */ jsxs("table", { style: { width: "100%", borderCollapse: "collapse" }, children: [
                /* @__PURE__ */ jsx("thead", { children: /* @__PURE__ */ jsxs(
                  "tr",
                  {
                    style: {
                      textAlign: "left",
                      color: "var(--muted-foreground, #6b7280)"
                    },
                    children: [
                      /* @__PURE__ */ jsx("th", { style: { padding: "4px 6px" }, children: "Path" }),
                      /* @__PURE__ */ jsx("th", { style: { padding: "4px 6px" }, children: "Modified" }),
                      /* @__PURE__ */ jsx("th", { style: { padding: "4px 6px", textAlign: "right" }, children: "Size" })
                    ]
                  }
                ) }),
                /* @__PURE__ */ jsx("tbody", { children: listing.offsite.backups.map((b) => /* @__PURE__ */ jsxs(
                  "tr",
                  {
                    style: {
                      borderTop: "1px solid var(--border, #e5e7eb)",
                      background: restorePath === b.path ? "var(--accent, #f3f4f6)" : void 0,
                      cursor: "pointer"
                    },
                    onClick: () => setRestorePath(b.path),
                    children: [
                      /* @__PURE__ */ jsx(
                        "td",
                        {
                          style: {
                            padding: "4px 6px",
                            fontFamily: "ui-monospace, monospace"
                          },
                          children: b.path.split("/").slice(-2).join("/")
                        }
                      ),
                      /* @__PURE__ */ jsx("td", { style: { padding: "4px 6px" }, children: formatDate(b.modified) }),
                      /* @__PURE__ */ jsx("td", { style: { padding: "4px 6px", textAlign: "right" }, children: b.sizeBytes ? formatBytes(b.sizeBytes) : "\u2014" })
                    ]
                  },
                  b.path
                )) })
              ] }) : listing?.loading ? /* @__PURE__ */ jsxs(
                "div",
                {
                  style: {
                    color: "var(--muted-foreground, #6b7280)",
                    display: "flex",
                    alignItems: "center",
                    gap: 6
                  },
                  children: [
                    /* @__PURE__ */ jsx(
                      "span",
                      {
                        style: {
                          display: "inline-block",
                          width: 10,
                          height: 10,
                          borderRadius: "50%",
                          border: "2px solid var(--muted-foreground, #6b7280)",
                          borderTopColor: "transparent",
                          animation: "spin 1s linear infinite"
                        }
                      }
                    ),
                    "Scanning\u2026"
                  ]
                }
              ) : /* @__PURE__ */ jsx("div", { style: { color: "var(--muted-foreground, #6b7280)" }, children: "No offsite backups listed." }) }),
              /* @__PURE__ */ jsxs(
                "div",
                {
                  style: {
                    display: "flex",
                    gap: 8,
                    alignItems: "end",
                    marginTop: 12,
                    flexWrap: "wrap"
                  },
                  children: [
                    /* @__PURE__ */ jsxs("label", { style: { display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }, children: [
                      "Keep newest",
                      /* @__PURE__ */ jsx(
                        "input",
                        {
                          type: "number",
                          min: 0,
                          max: 1e4,
                          value: offsiteKeep ?? listing?.offsiteRetention?.keep ?? listing?.config?.offsiteKeep ?? 30,
                          onChange: (e) => setOffsiteKeep(Math.max(0, Math.min(1e4, Number(e.target.value) || 0))),
                          style: {
                            padding: "4px 8px",
                            border: "1px solid var(--border, #e5e7eb)",
                            borderRadius: 4,
                            width: 90
                          }
                        }
                      )
                    ] }),
                    /* @__PURE__ */ jsx(
                      ActionButton,
                      {
                        label: "Prune offsite (GDrive)",
                        busy: busy === "prune-off",
                        onClick: triggerPruneOffsite,
                        variant: "danger",
                        hint: "Deletes oldest GDrive folders beyond the keep count",
                        elapsedMs
                      }
                    ),
                    /* @__PURE__ */ jsx("span", { style: { fontSize: 11, color: "var(--muted-foreground, #6b7280)" }, children: (listing?.offsiteRetention?.candidates ?? 0) > 0 ? `${listing?.offsiteRetention?.candidates} candidate(s) to delete` : "No candidates to delete" })
                  ]
                }
              )
            ]
          }
        )
      ] }),
      /* @__PURE__ */ jsxs(
        "section",
        {
          style: {
            padding: 16,
            border: "1px solid var(--border, #e5e7eb)",
            borderRadius: 8
          },
          children: [
            /* @__PURE__ */ jsx("h3", { style: { marginTop: 0, fontSize: 16 }, children: "Run backup & restore" }),
            /* @__PURE__ */ jsxs("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }, children: [
              /* @__PURE__ */ jsx("div", { style: { display: "flex", flexDirection: "column", gap: 8 }, children: /* @__PURE__ */ jsx(
                ActionButton,
                {
                  label: runningNow ? "Backup running\u2026" : "Run backup now",
                  busy: busy === "backup" || runningNow != null,
                  onClick: triggerBackup,
                  hint: runningNow ? `Backup in background (pid=${runningNow.pid}); will refresh when done` : "Pushes latest DB + instance data to GDrive",
                  elapsedMs: runningNow ? Date.now() - new Date(runningNow.startedAt).getTime() : elapsedMs,
                  disabled: runningNow != null
                }
              ) }),
              /* @__PURE__ */ jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 8 }, children: [
                /* @__PURE__ */ jsxs("label", { style: { display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }, children: [
                  "Backup path (empty = latest)",
                  /* @__PURE__ */ jsx(
                    "input",
                    {
                      type: "text",
                      placeholder: "latest",
                      value: restorePath,
                      onChange: (e) => setRestorePath(e.target.value),
                      style: {
                        padding: "4px 8px",
                        border: "1px solid var(--border, #e5e7eb)",
                        borderRadius: 4,
                        fontFamily: "ui-monospace, monospace",
                        fontSize: 12
                      }
                    }
                  )
                ] }),
                /* @__PURE__ */ jsxs("label", { style: { display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }, children: [
                  "Restore destination",
                  /* @__PURE__ */ jsx(
                    "input",
                    {
                      type: "text",
                      value: restoreDest,
                      onChange: (e) => setRestoreDest(e.target.value),
                      style: {
                        padding: "4px 8px",
                        border: "1px solid var(--border, #e5e7eb)",
                        borderRadius: 4,
                        fontFamily: "ui-monospace, monospace",
                        fontSize: 12
                      }
                    }
                  )
                ] }),
                /* @__PURE__ */ jsx(
                  ActionButton,
                  {
                    label: "Restore from offsite",
                    busy: busy === "restore-off",
                    onClick: triggerRestoreOffsite,
                    variant: "danger",
                    hint: "Downloads + extracts the chosen backup",
                    elapsedMs
                  }
                )
              ] })
            ] })
          ]
        }
      )
    ] }) : null,
    tab === "cleanup" ? /* @__PURE__ */ jsx(
      CleanupPanel,
      {
        companyId,
        listing: cleanupListing ?? null,
        listingError: cleanupListingError,
        onRefresh: () => setRefreshTick((n) => n + 1)
      }
    ) : null,
    tab === "recovery" ? /* @__PURE__ */ jsx(
      ForceRecoverySection,
      {
        tierProgress,
        forceBackup,
        forceRestore,
        deleteRecoverySnapshots,
        uploadDailyBackup,
        uploadHourlyBackup,
        setTierKeep,
        recoverySnapshots: recoverySnapshots ?? null,
        recoverySnapshotsError,
        tierStatus: tierStatus ?? null,
        refreshRecoverySnapshots: () => setRefreshTick((n) => n + 1),
        forceRunning
      }
    ) : null,
    tab === "manager" ? /* @__PURE__ */ jsx(ResultBanner, { result, onDismiss: () => setResult(null) }) : null
  ] });
}
function TabButton({
  active,
  onClick,
  children
}) {
  return /* @__PURE__ */ jsx(
    "button",
    {
      type: "button",
      role: "tab",
      "aria-selected": active,
      onClick,
      style: {
        padding: "8px 14px",
        fontSize: 13,
        fontWeight: active ? 600 : 500,
        color: active ? "var(--foreground)" : "var(--muted-foreground, #6b7280)",
        background: "transparent",
        border: "none",
        borderBottom: active ? "2px solid var(--primary, #2563eb)" : "2px solid transparent",
        cursor: "pointer",
        marginBottom: -1
      },
      children
    }
  );
}
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
  tierProgress
}) {
  function formatTimestamp(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return String(iso);
      const pad = (n) => n < 10 ? "0" + n : "" + n;
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
  const [busy, setBusy] = useState(null);
  const [last, setLast] = useState(null);
  const [selected, setSelected] = useState({});
  const [showStubs, setShowStubs] = useState(false);
  const snaps = recoverySnapshots && Array.isArray(recoverySnapshots.snapshots) ? recoverySnapshots.snapshots : [];
  const visibleSnaps = showStubs ? snaps : snaps.filter((s) => (s.apparentBytes ?? 0) >= 1024 || (s.bytes ?? 0) >= 1024);
  const stubCount = snaps.length - visibleSnaps.length;
  const snapCount = visibleSnaps.length;
  const totalApparentBytes = recoverySnapshots && typeof recoverySnapshots.totalApparentBytes === "number" ? recoverySnapshots.totalApparentBytes : snaps.reduce((a, s) => a + (s.apparentBytes ?? 0), 0);
  const totalDeltaBytes = recoverySnapshots && typeof recoverySnapshots.totalDeltaBytes === "number" ? recoverySnapshots.totalDeltaBytes : snaps.reduce((a, s) => a + (s.deltaBytes ?? s.bytes ?? 0), 0);
  const savingsBytes = Math.max(0, totalApparentBytes - totalDeltaBytes);
  const savingsPct = totalApparentBytes > 0 ? Math.round(savingsBytes / totalApparentBytes * 100) : 0;
  const allSelected = snapCount > 0 && visibleSnaps.every((s) => !!selected[s.id]);
  const someSelected = visibleSnaps.some((s) => !!selected[s.id]);
  const selectedIds = visibleSnaps.filter((s) => !!selected[s.id]).map((s) => s.id);
  const toggleOne = (id) => {
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
      const next = {};
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
      const r = await forceBackup({});
      setLast({ ok: true, message: r?.message ?? `Force backup started (pid=${r?.pid})` });
    } catch (err) {
      setLast({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(null);
    }
  };
  const doForceRestore = async (id) => {
    setBusy(`force-restore-${id}`);
    setLast(null);
    try {
      const r = await forceRestore({ subcommand: "restore", id });
      setLast({ ok: !!(r && r.ok), message: r?.message ?? `exit ${r?.exitCode}` });
    } catch (err) {
      setLast({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(null);
    }
  };
  const doDelete = async (ids, opName) => {
    if (!ids || ids.length === 0) return;
    if (typeof window !== "undefined" && typeof window.confirm === "function") {
      const ok = window.confirm(
        `Delete ${ids.length} recovery snapshot${ids.length === 1 ? "" : "s"}?

${ids.join(
          "\n"
        )}

This permanently removes the hardlink snapshot directories from disk. The latest 2 snapshots are protected and will be skipped.`
      );
      if (!ok) return;
    }
    setBusy(opName);
    setLast(null);
    try {
      const r = await deleteRecoverySnapshots({ ids });
      const deletedCount = Array.isArray(r?.deleted) ? r.deleted.length : 0;
      const skippedCount = Array.isArray(r?.skipped) ? r.skipped.length : 0;
      const errCount = Array.isArray(r?.errors) ? r.errors.length : 0;
      const skippedMsg = skippedCount > 0 ? ` (${skippedCount} skipped \u2014 newest 2 protected)` : "";
      setLast({
        ok: !!(r && r.ok !== false && errCount === 0),
        message: (r?.message ?? `Deleted ${deletedCount}`) + skippedMsg
      });
      setSelected({});
      refreshRecoverySnapshots();
    } catch (err) {
      setLast({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(null);
    }
  };
  const doDeleteOne = (id) => doDelete([id], `force-delete-${id}`);
  const doDeleteSelected = () => doDelete(selectedIds.slice(), "force-delete-batch");
  function Tier({
    name,
    items,
    keep,
    count,
    last: last2,
    error,
    onUpload,
    onChangeKeep,
    busyKey,
    busy: busy2,
    progress
  }) {
    const idInput = `keep-input-${name}`;
    return /* @__PURE__ */ jsxs(
      "div",
      {
        style: {
          padding: 12,
          border: "1px solid var(--border, #e5e7eb)",
          borderRadius: 6,
          background: "var(--card, #fafafa)"
        },
        children: [
          /* @__PURE__ */ jsxs(
            "div",
            {
              style: {
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
                marginBottom: 6
              },
              children: [
                /* @__PURE__ */ jsxs("div", { children: [
                  /* @__PURE__ */ jsxs(
                    "strong",
                    {
                      style: {
                        fontSize: 13,
                        textTransform: "uppercase",
                        letterSpacing: 0.5,
                        color: name === "daily" ? "hsl(140, 60%, 35%)" : "hsl(35, 80%, 40%)"
                      },
                      children: [
                        name,
                        " tier"
                      ]
                    }
                  ),
                  /* @__PURE__ */ jsxs(
                    "span",
                    {
                      style: {
                        marginLeft: 8,
                        fontFamily: "ui-monospace, monospace",
                        fontSize: 12
                      },
                      children: [
                        "count ",
                        /* @__PURE__ */ jsx("strong", { children: count }),
                        " / ",
                        /* @__PURE__ */ jsx("strong", { children: keep })
                      ]
                    }
                  )
                ] }),
                /* @__PURE__ */ jsx(
                  ActionButton,
                  {
                    label: busy2 === busyKey ? "Uploading\u2026" : `Upload latest to ${name}`,
                    busy: busy2 === busyKey,
                    onClick: onUpload
                  }
                )
              ]
            }
          ),
          progress && progress.tier === name && progress.lines.length > 0 ? /* @__PURE__ */ jsx(
            "div",
            {
              "data-testid": `tier-progress-${name}`,
              style: {
                marginTop: 8,
                padding: "6px 8px",
                borderRadius: 4,
                background: "color-mix(in oklab, var(--muted) 15%, transparent)",
                fontFamily: "ui-monospace, monospace",
                fontSize: 11,
                color: "var(--muted-foreground, #6b7280)",
                maxHeight: 90,
                overflow: "auto"
              },
              children: progress.lines.map((line, i) => /* @__PURE__ */ jsx("div", { style: { whiteSpace: "pre-wrap" }, children: line }, i))
            }
          ) : null,
          last2 ? /* @__PURE__ */ jsxs(
            "div",
            {
              style: {
                fontSize: 11,
                fontFamily: "ui-monospace, monospace",
                color: "var(--muted-foreground, #6b7280)",
                marginBottom: 6
              },
              children: [
                "most recent: ",
                last2
              ]
            }
          ) : null,
          items && items.length ? /* @__PURE__ */ jsx(
            "div",
            {
              style: {
                fontSize: 11,
                fontFamily: "ui-monospace, monospace",
                maxHeight: 70,
                overflow: "auto",
                padding: 4,
                background: "var(--muted, #f9fafb)",
                border: "1px solid var(--border, #e5e7eb)",
                borderRadius: 4,
                marginBottom: 6
              },
              children: items.slice().sort((a, b) => a.id < b.id ? 1 : a.id > b.id ? -1 : 0).map((item) => /* @__PURE__ */ jsx("div", { style: { padding: "1px 0" }, children: item.id }, item.id))
            }
          ) : null,
          error ? /* @__PURE__ */ jsx(
            "div",
            {
              style: {
                fontSize: 11,
                color: "var(--destructive, #b91c1c)",
                marginBottom: 6
              },
              children: error
            }
          ) : null,
          /* @__PURE__ */ jsxs("div", { style: { display: "flex", alignItems: "center", gap: 6, fontSize: 12 }, children: [
            /* @__PURE__ */ jsx("span", { children: "Retention (keep):" }),
            /* @__PURE__ */ jsx(
              "input",
              {
                type: "number",
                min: 1,
                max: 365,
                defaultValue: keep,
                id: idInput,
                style: {
                  width: 60,
                  padding: "2px 6px",
                  border: "1px solid var(--border, #e5e7eb)",
                  borderRadius: 4,
                  color: "var(--foreground, #e5e7eb)",
                  background: "var(--card, #1f2937)"
                }
              }
            ),
            /* @__PURE__ */ jsx(
              "button",
              {
                type: "button",
                onClick: () => {
                  const inp = typeof document !== "undefined" ? document.getElementById(idInput) : null;
                  const v = inp && inp.value ? parseInt(inp.value, 10) : NaN;
                  onChangeKeep(v);
                },
                style: {
                  marginLeft: 4,
                  padding: "2px 8px",
                  fontSize: 11,
                  border: "1px solid transparent",
                  borderRadius: 4,
                  background: "#1e40af",
                  color: "#f8fafc",
                  cursor: "pointer"
                },
                children: "Save"
              }
            )
          ] })
        ]
      }
    );
  }
  function TierPanel({ progress }) {
    function doUpload(kind, action) {
      setBusy(`upload-${kind}`);
      setLast({ ok: true, message: `uploading latest snapshot to ${kind} tier\u2026` });
      action({}).then((r) => {
        setLast({
          ok: true,
          message: r?.message ?? `${kind} upload dispatched (pid=${r?.pid})`
        });
      }).catch((err) => {
        setLast({ ok: false, message: errorMessage(err) });
      }).finally(() => {
        setBusy(null);
        setTimeout(refreshRecoverySnapshots, 2e3);
      });
    }
    function doChangeKeep(tier, keepValue) {
      if (!Number.isFinite(keepValue) || keepValue < 1) {
        setLast({ ok: false, message: "keep must be a positive integer" });
        return;
      }
      setBusy(`set-keep-${tier}`);
      setTierKeep({ tier, keep: keepValue }).then((r) => {
        setLast({
          ok: !!(r && r.ok),
          message: r?.message ?? `Set ${tier} keep=${keepValue}`
        });
      }).catch((err) => {
        setLast({ ok: false, message: errorMessage(err) });
      }).finally(() => {
        setBusy(null);
        setTimeout(refreshRecoverySnapshots, 1500);
      });
    }
    return /* @__PURE__ */ jsxs(
      "div",
      {
        style: {
          marginTop: 8,
          padding: 10,
          border: "1px solid var(--border, #e5e7eb)",
          borderRadius: 6,
          background: "color-mix(in oklab, hsl(50, 60%, 95%) 30%, var(--card, #fff))"
        },
        children: [
          /* @__PURE__ */ jsxs(
            "div",
            {
              style: {
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 8
              },
              children: [
                /* @__PURE__ */ jsx("strong", { style: { fontSize: 13 }, children: "GDrive tiered backup" }),
                /* @__PURE__ */ jsx(
                  "span",
                  {
                    style: {
                      fontSize: 11,
                      color: "var(--muted-foreground, #6b7280)",
                      fontFamily: "ui-monospace, monospace"
                    },
                    children: tierStatus && tierStatus.enabled === false ? "disabled" : `root: ${tierStatus?.tierRoot ?? "Paperclip-Backups"}`
                  }
                )
              ]
            }
          ),
          tierStatus && tierStatus.enabled === false ? /* @__PURE__ */ jsx("div", { style: { fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: "Tiered backup is disabled in plugin config." }) : /* @__PURE__ */ jsxs("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }, children: [
            /* @__PURE__ */ jsx(
              Tier,
              {
                progress,
                name: "daily",
                items: tierStatus?.daily ?? [],
                keep: tierStatus?.keep?.daily ?? 3,
                count: tierStatus?.counts?.daily ?? 0,
                last: tierStatus?.lastUpload?.daily,
                error: tierStatus?.errors?.daily,
                onUpload: () => doUpload("daily", uploadDailyBackup),
                onChangeKeep: (v) => doChangeKeep("daily", v),
                busyKey: "upload-daily",
                busy
              }
            ),
            /* @__PURE__ */ jsx(
              Tier,
              {
                progress,
                name: "hourly",
                items: tierStatus?.hourly ?? [],
                keep: tierStatus?.keep?.hourly ?? 2,
                count: tierStatus?.counts?.hourly ?? 0,
                last: tierStatus?.lastUpload?.hourly,
                error: tierStatus?.errors?.hourly,
                onUpload: () => doUpload("hourly", uploadHourlyBackup),
                onChangeKeep: (v) => doChangeKeep("hourly", v),
                busyKey: "upload-hourly",
                busy
              }
            )
          ] })
        ]
      }
    );
  }
  return /* @__PURE__ */ jsxs(
    "section",
    {
      style: {
        marginTop: 16,
        padding: 16,
        border: "1px solid var(--border, #e5e7eb)",
        borderRadius: 8,
        background: "var(--card, #fafafa)"
      },
      children: [
        /* @__PURE__ */ jsxs(
          "header",
          {
            style: {
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 8
            },
            children: [
              /* @__PURE__ */ jsx("h3", { style: { margin: 0, fontSize: 16 }, children: "Force backup & recovery" }),
              /* @__PURE__ */ jsxs("div", { style: { display: "flex", gap: 8 }, children: [
                /* @__PURE__ */ jsx(
                  ActionButton,
                  {
                    label: busy === "force-backup" ? "Starting\u2026" : forceRunning ? "Snapshot running\u2026" : "Take recovery snapshot now",
                    busy: busy === "force-backup" || !!forceRunning,
                    onClick: doForceBackup,
                    hint: "calls recovery.sh snapshot --no-upload (local hardlink-incremental; no GDrive upload)"
                  }
                ),
                /* @__PURE__ */ jsx(
                  ActionButton,
                  {
                    label: open ? "Hide recovery points" : "Pick recovery point",
                    onClick: () => setOpen(!open)
                  }
                )
              ] })
            ]
          }
        ),
        /* @__PURE__ */ jsx(TierPanel, { progress: tierProgress }),
        forceRunning ? /* @__PURE__ */ jsx(
          "div",
          {
            style: {
              marginTop: 8,
              marginBottom: 8,
              padding: 10,
              background: "color-mix(in oklab, var(--primary) 8%, var(--card))",
              border: "1px solid color-mix(in oklab, var(--primary) 20%, var(--border))",
              borderRadius: 6
            },
            children: (() => {
              const stage = forceRunning.stage || "running";
              const stageLabel = stage === "uploading" ? "Uploading snapshot to Google Drive" : stage === "packing" ? "Packing worktree (tar+gzip)" : stage === "pruning" ? "Pruning old snapshots" : stage === "snapshotting" ? "Creating incremental snapshot (rsync --link-dest)" : stage === "snapshot" ? "Creating snapshot" : stage === "running" ? "Snapshot running" : stage;
              const progress = forceRunning.progress;
              return /* @__PURE__ */ jsxs("div", { style: { display: "flex", flexDirection: "column", gap: 6 }, children: [
                /* @__PURE__ */ jsxs(
                  "div",
                  {
                    style: {
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 12
                    },
                    children: [
                      /* @__PURE__ */ jsxs("div", { children: [
                        /* @__PURE__ */ jsx("strong", { style: { fontSize: 13 }, children: stageLabel }),
                        /* @__PURE__ */ jsxs(
                          "div",
                          {
                            style: {
                              color: "var(--muted-foreground, #6b7280)",
                              fontSize: 11,
                              fontFamily: "ui-monospace, monospace",
                              marginTop: 2
                            },
                            children: [
                              "pid ",
                              String(forceRunning.pid),
                              " \xB7 started ",
                              formatTimestamp(forceRunning.startedAt),
                              forceRunning.stageDetail ? ` \xB7 ${String(forceRunning.stageDetail)}` : ""
                            ]
                          }
                        )
                      ] }),
                      progress && progress.percent !== null && progress.percent !== void 0 ? /* @__PURE__ */ jsxs(
                        "span",
                        {
                          style: {
                            fontFamily: "ui-monospace, monospace",
                            fontSize: 13,
                            fontWeight: 600,
                            whiteSpace: "nowrap"
                          },
                          children: [
                            progress.percent.toFixed(1),
                            "%"
                          ]
                        }
                      ) : null
                    ]
                  }
                ),
                progress && progress.percent !== null && progress.percent !== void 0 ? /* @__PURE__ */ jsx(
                  "div",
                  {
                    style: {
                      height: 8,
                      background: "var(--muted, #f3f4f6)",
                      borderRadius: 4,
                      overflow: "hidden",
                      border: "1px solid var(--border, #e5e7eb)"
                    },
                    children: /* @__PURE__ */ jsx(
                      "div",
                      {
                        style: {
                          width: `${progress.percent}%`,
                          height: "100%",
                          background: "linear-gradient(90deg, var(--primary, #2563eb) 0%, color-mix(in oklab, var(--primary, #2563eb) 70%, white) 100%)",
                          transition: "width 0.6s ease"
                        }
                      }
                    )
                  }
                ) : null,
                progress && progress.totalBytes ? /* @__PURE__ */ jsxs(
                  "div",
                  {
                    style: {
                      color: "var(--muted-foreground, #6b7280)",
                      fontSize: 11,
                      fontFamily: "ui-monospace, monospace"
                    },
                    children: [
                      ((progress.uploadBytes ?? 0) / (1024 * 1024)).toFixed(1),
                      " MiB /",
                      " ",
                      (progress.totalBytes / (1024 * 1024)).toFixed(0),
                      " MiB \xB7 rclone pid",
                      " ",
                      String(progress.rclonePid),
                      (() => {
                        const child = forceRunning.children && progress.rclonePid ? forceRunning.children.find((c) => c.pid === progress.rclonePid) : null;
                        if (!child || !child.startedAt) return "";
                        const elapsedMs = Date.now() - new Date(child.startedAt).getTime();
                        if (elapsedMs <= 0 || (progress.uploadBytes ?? 0) <= 0) return "";
                        const rate = (progress.uploadBytes ?? 0) / (elapsedMs / 1e3);
                        const remaining = Math.max(0, progress.totalBytes - (progress.uploadBytes ?? 0));
                        if (rate <= 0) return "";
                        const etaSec = remaining / rate;
                        const etaLabel = etaSec >= 60 ? `${Math.round(etaSec / 60)} min` : `${Math.round(etaSec)} sec`;
                        return ` \xB7 ${(rate / (1024 * 1024)).toFixed(2)} MB/s \xB7 ETA ${etaLabel}`;
                      })()
                    ]
                  }
                ) : null,
                /* @__PURE__ */ jsx("div", { style: { fontSize: 11, color: "var(--muted-foreground, #6b7280)" }, children: "incremental rsync \u2014 typically finishes in seconds (only changed bytes are written; rest are hardlinks)" })
              ] });
            })()
          }
        ) : null,
        /* @__PURE__ */ jsxs("div", { style: { marginTop: 4, marginBottom: 8, fontSize: 12, color: "var(--muted-foreground, #6b7280)" }, children: [
          "Recovery snapshots: ",
          snapCount,
          " \xB7 logical ",
          Math.round(totalApparentBytes / (1024 * 1024)),
          " MiB if all restored \xB7 actual on-disk ",
          Math.round(totalDeltaBytes / (1024 * 1024)),
          " MiB (hardlink-deduped; saved",
          " ",
          savingsPct,
          "% / ",
          Math.round(savingsBytes / (1024 * 1024)),
          " MiB)"
        ] }),
        last ? /* @__PURE__ */ jsx(
          "div",
          {
            style: {
              marginTop: 8,
              padding: 8,
              fontFamily: "ui-monospace, monospace",
              fontSize: 12,
              color: last.ok ? "var(--muted-foreground, #6b7280)" : "var(--destructive, #dc2626)",
              background: "var(--muted, #f3f4f6)",
              borderRadius: 4
            },
            children: last.message
          }
        ) : null,
        open ? /* @__PURE__ */ jsxs("div", { style: { marginTop: 12 }, children: [
          recoverySnapshotsError ? /* @__PURE__ */ jsxs("div", { style: { color: "var(--destructive, #dc2626)", fontSize: 12, marginBottom: 8 }, children: [
            "Could not list snapshots: ",
            recoverySnapshotsError
          ] }) : null,
          stubCount > 0 ? /* @__PURE__ */ jsxs(
            "div",
            {
              style: {
                fontSize: 12,
                color: "var(--muted-foreground, #6b7280)",
                marginBottom: 8
              },
              children: [
                stubCount,
                " empty ",
                stubCount === 1 ? "stub" : "stubs",
                " hidden \u2014 only ",
                visibleSnaps.length,
                " real",
                " ",
                visibleSnaps.length === 1 ? "backup" : "backups",
                " on disk",
                " ",
                /* @__PURE__ */ jsx(
                  "button",
                  {
                    type: "button",
                    onClick: () => setShowStubs(!showStubs),
                    style: {
                      padding: "2px 8px",
                      fontSize: 11,
                      border: "1px solid transparent",
                      borderRadius: 4,
                      background: "var(--muted, #374151)",
                      cursor: "pointer",
                      color: "#f8fafc"
                    },
                    children: showStubs ? "Hide stubs" : `Show ${stubCount} stub${stubCount === 1 ? "" : "s"}`
                  }
                )
              ]
            }
          ) : null,
          visibleSnaps.length === 0 && stubCount === 0 ? /* @__PURE__ */ jsx("div", { style: { color: "var(--muted-foreground, #6b7280)", fontSize: 12 }, children: "No snapshots available." }) : null,
          visibleSnaps.length > 0 ? /* @__PURE__ */ jsxs(
            "div",
            {
              style: {
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "4px 10px",
                background: "var(--muted, #f3f4f6)",
                borderTop: "1px solid var(--border, #e5e7eb)",
                borderLeft: "1px solid var(--border, #e5e7eb)",
                borderRight: "1px solid var(--border, #e5e7eb)",
                fontSize: 12
              },
              children: [
                /* @__PURE__ */ jsx(
                  "input",
                  {
                    type: "checkbox",
                    checked: allSelected,
                    onChange: toggleAll,
                    "aria-label": "Select all snapshots"
                  }
                ),
                /* @__PURE__ */ jsx("span", { style: { flex: 1 }, children: allSelected ? `All ${visibleSnaps.length} selected` : someSelected ? `${selectedIds.length} selected` : "Select all" }),
                someSelected ? /* @__PURE__ */ jsx(
                  ActionButton,
                  {
                    label: `Delete selected (${selectedIds.length})`,
                    busy: busy === "force-delete-batch",
                    variant: "danger",
                    onClick: doDeleteSelected
                  }
                ) : null
              ]
            }
          ) : null,
          /* @__PURE__ */ jsx(
            "div",
            {
              style: { border: "1px solid var(--border, #e5e7eb)", borderRadius: 4 },
              children: (() => {
                const total = visibleSnaps.length;
                function ageColor(idx) {
                  if (total <= 1) return "hsl(120, 60%, 35%)";
                  const ratio = idx / (total - 1);
                  const hue = 120 - 120 * ratio;
                  return `hsl(${hue.toFixed(0)}, 55%, 38%)`;
                }
                return visibleSnaps.map((s, idx) => {
                  const isProtected = idx < 2;
                  const isMaster = idx === 0;
                  const tsColor = ageColor(idx);
                  return /* @__PURE__ */ jsxs(
                    "div",
                    {
                      style: {
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "6px 10px",
                        borderBottom: "1px solid var(--border, #e5e7eb)",
                        background: selected[s.id] ? "var(--accent, #f3f4f6)" : isMaster ? "color-mix(in oklab, hsl(120, 55%, 60%) 8%, var(--card, #fff))" : void 0
                      },
                      children: [
                        /* @__PURE__ */ jsx(
                          "input",
                          {
                            type: "checkbox",
                            checked: !!selected[s.id],
                            disabled: isProtected,
                            onChange: () => toggleOne(s.id),
                            "aria-label": `Select ${s.id}`
                          }
                        ),
                        /* @__PURE__ */ jsxs(
                          "div",
                          {
                            style: {
                              flex: 1,
                              fontFamily: "ui-monospace, monospace",
                              fontSize: 12
                            },
                            children: [
                              /* @__PURE__ */ jsxs("strong", { children: [
                                s.id,
                                isMaster ? " \xB7 \u25CF MASTER" : "",
                                isProtected && !isMaster ? " \xB7 protected" : ""
                              ] }),
                              /* @__PURE__ */ jsxs(
                                "div",
                                {
                                  style: {
                                    color: tsColor,
                                    fontSize: 11,
                                    fontWeight: isMaster ? 600 : 400
                                  },
                                  children: [
                                    s.apparentBytes ? `${Math.round(s.apparentBytes / (1024 * 1024))} MB${s.deltaBytes !== void 0 && s.deltaBytes !== null && s.apparentBytes ? ` (new +${s.deltaBytes >= 1024 * 1024 ? Math.round(s.deltaBytes / (1024 * 1024)) + " MB" : Math.max(1, Math.round(s.deltaBytes / 1024)) + " KB"})` : ""}` : "\u2014",
                                    " ",
                                    "\xB7 ",
                                    formatTimestamp(s.timestamp)
                                  ]
                                }
                              )
                            ]
                          }
                        ),
                        /* @__PURE__ */ jsx(
                          ActionButton,
                          {
                            label: busy === `force-restore-${s.id}` ? "Restoring\u2026" : "Restore",
                            busy: busy === `force-restore-${s.id}`,
                            onClick: () => doForceRestore(s.id),
                            variant: "danger"
                          }
                        ),
                        isProtected ? /* @__PURE__ */ jsx("span", { style: { fontSize: 11, color: "var(--muted-foreground, #6b7280)" }, children: " " }) : /* @__PURE__ */ jsx(
                          ActionButton,
                          {
                            label: busy === `force-delete-${s.id}` ? "Deleting\u2026" : "Delete",
                            busy: busy === `force-delete-${s.id}`,
                            variant: "danger",
                            onClick: () => doDeleteOne(s.id)
                          }
                        )
                      ]
                    },
                    s.id
                  );
                });
              })()
            }
          ),
          /* @__PURE__ */ jsx("div", { style: { marginTop: 8, display: "flex", gap: 8 }, children: /* @__PURE__ */ jsx(ActionButton, { label: "Refresh", onClick: refreshRecoverySnapshots }) })
        ] }) : null
      ]
    }
  );
}
function BackupSettingsPage({
  context
}) {
  const host = useHostContext();
  const companyId = context.companyId ?? host.companyId ?? null;
  const saveConfig = usePluginAction("save-config");
  const [busy, setBusy] = useState(null);
  const [config, setConfig] = useState(null);
  const [saved, setSaved] = useState(null);
  const listingConfigResult = usePluginData("config");
  const listingConfig = listingConfigResult?.data;
  const error = listingConfigResult?.error ? String(listingConfigResult.error) : null;
  useEffect(() => {
    if (listingConfig && !config) setConfig(listingConfig);
  }, [listingConfig, config]);
  const update = (k, v) => {
    if (!config) return;
    setConfig({ ...config, [k]: v });
  };
  const save = async () => {
    if (!config || busy) return;
    setBusy("save");
    setSaved(null);
    try {
      const r = await saveConfig({ ...config, companyId });
      setSaved({ ok: true, message: r.message ?? "Saved" });
      if (r.config) setConfig(r.config);
    } catch (err) {
      setSaved({ ok: false, message: errorMessage(err) });
    } finally {
      setBusy(null);
    }
  };
  if (error) {
    return /* @__PURE__ */ jsxs("div", { style: { padding: 16, color: "var(--destructive, #dc2626)" }, children: [
      "Failed to load settings: ",
      error
    ] });
  }
  if (!config) return /* @__PURE__ */ jsx("div", { style: { padding: 16 }, children: "Loading\u2026" });
  return /* @__PURE__ */ jsxs("article", { style: { display: "grid", gap: 16, padding: 16 }, children: [
    /* @__PURE__ */ jsx("h2", { style: { margin: 0, fontSize: 20 }, children: "Backup settings" }),
    /* @__PURE__ */ jsx("p", { style: { color: "var(--muted-foreground, #6b7280)", fontSize: 13 }, children: "Paths to the existing backup / restore / prune scripts." }),
    /* @__PURE__ */ jsxs(
      "div",
      {
        style: {
          display: "grid",
          gap: 12,
          padding: 16,
          border: "1px solid var(--border, #e5e7eb)",
          borderRadius: 8
        },
        children: [
          /* @__PURE__ */ jsx(
            Field,
            {
              label: "Paperclip home",
              value: String(config.paperclipHome ?? ""),
              onChange: (v) => update("paperclipHome", v)
            }
          ),
          /* @__PURE__ */ jsx(
            Field,
            {
              label: "Backups subdir (under paperclipHome)",
              value: String(config.backupsSubdir ?? ""),
              onChange: (v) => update("backupsSubdir", v)
            }
          ),
          /* @__PURE__ */ jsx(
            Field,
            {
              label: "backup-to-drive.sh",
              value: String(config.backupScript ?? ""),
              onChange: (v) => update("backupScript", v)
            }
          ),
          /* @__PURE__ */ jsx(
            Field,
            {
              label: "restore-from-drive.sh",
              value: String(config.restoreScript ?? ""),
              onChange: (v) => update("restoreScript", v)
            }
          ),
          /* @__PURE__ */ jsx(
            Field,
            {
              label: "prune-local-dumps.sh",
              value: String(config.pruneScript ?? ""),
              onChange: (v) => update("pruneScript", v)
            }
          ),
          /* @__PURE__ */ jsx(
            Field,
            {
              label: "rclone config",
              value: String(config.rcloneConfig ?? ""),
              onChange: (v) => update("rcloneConfig", v)
            }
          ),
          /* @__PURE__ */ jsx(
            Field,
            {
              label: "rclone remote",
              value: String(config.rcloneRemote ?? ""),
              onChange: (v) => update("rcloneRemote", v)
            }
          ),
          /* @__PURE__ */ jsxs("label", { style: { display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }, children: [
            "Default keep (newest N local dumps)",
            /* @__PURE__ */ jsx(
              "input",
              {
                type: "number",
                min: 1,
                max: 365,
                value: Number(config.defaultKeep ?? 10),
                onChange: (e) => update("defaultKeep", Math.max(1, Math.min(365, Number(e.target.value) || 10))),
                style: {
                  padding: "4px 8px",
                  border: "1px solid var(--border, #e5e7eb)",
                  borderRadius: 4,
                  width: 100
                }
              }
            )
          ] }),
          /* @__PURE__ */ jsxs("label", { style: { display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }, children: [
            "Offsite keep (newest N GDrive folders; 0 = never auto-prune)",
            /* @__PURE__ */ jsx(
              "input",
              {
                type: "number",
                min: 0,
                max: 1e4,
                value: Number(config.offsiteKeep ?? 30),
                onChange: (e) => update("offsiteKeep", Math.max(0, Math.min(1e4, Number(e.target.value) || 0))),
                style: {
                  padding: "4px 8px",
                  border: "1px solid var(--border, #e5e7eb)",
                  borderRadius: 4,
                  width: 100
                }
              }
            )
          ] }),
          /* @__PURE__ */ jsx(
            Field,
            {
              label: "Offsite auto-prune schedule",
              value: String(config.offsiteSchedule ?? ""),
              onChange: (v) => update("offsiteSchedule", v)
            }
          )
        ]
      }
    ),
    /* @__PURE__ */ jsx("div", { children: /* @__PURE__ */ jsx(ActionButton, { label: "Save settings", busy: busy === "save", onClick: save }) }),
    saved ? /* @__PURE__ */ jsx(
      "div",
      {
        style: {
          marginTop: 8,
          fontSize: 13,
          color: saved.ok ? "var(--success, #16a34a)" : "var(--destructive, #dc2626)"
        },
        children: saved.message
      }
    ) : null
  ] });
}
function Field({
  label,
  value,
  onChange
}) {
  return /* @__PURE__ */ jsxs("label", { style: { display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }, children: [
    label,
    /* @__PURE__ */ jsx(
      "input",
      {
        type: "text",
        value,
        onChange: (e) => onChange(e.target.value),
        style: {
          padding: "4px 8px",
          border: "1px solid var(--border, #e5e7eb)",
          borderRadius: 4,
          fontFamily: "ui-monospace, monospace",
          fontSize: 12
        }
      }
    )
  ] });
}
export {
  BackupDashboardWidget,
  BackupManagerPage,
  BackupSettingsPage,
  BackupSidebarNav
};
//# sourceMappingURL=index.js.map
