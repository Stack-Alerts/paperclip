// Paperclip AI Search — UI bundle
// Self-contained: React + plugin-sdk + the search UI, all in one file.
// Uses React.createElement directly (no JSX transpile needed).

import { jsx as _jsx, jsxs as _jsxs, Fragment as _F } from "react/jsx-runtime";
import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import {
    useHostContext,
    useHostNavigation,
    usePluginData,
    usePluginAction,
} from "@paperclipai/plugin-sdk/ui";

// ── small UI helpers ────────────────────────────────────────────────────
function el(tag, props, ...children) {
    return _jsx(tag, props, ...children);
}
function Box(props) {
    return el(
        "div",
        {
            style: { display: "flex", flexDirection: "column", gap: 12, padding: 16 },
            ...props,
        },
        props.children,
    );
}
function Row(props) {
    return el(
        "div",
        { style: { display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }, ...props },
        props.children,
    );
}
function Spacer() {
    return el("div", { style: { flex: 1 } });
}
function Chip(props) {
    const palette = STATUS_PALETTE[props.status] || { bg: "var(--bg-muted, #f3f4f6)", fg: "var(--text-muted, #6b7280)" };
    return el(
        "span",
        {
            style: {
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
                padding: "2px 8px",
                borderRadius: 999,
                fontSize: 11,
                fontWeight: 500,
                background: palette.bg,
                color: palette.fg,
                textTransform: "lowercase",
                letterSpacing: 0.2,
                ...(props.style || {}),
            },
            title: props.title || props.status,
        },
        props.label,
    );
}
const STATUS_PALETTE = {
    blocked: { bg: "rgba(220, 38, 38, 0.12)", fg: "var(--accent-red, #b91c1c)" },
    cancelled: { bg: "rgba(107, 114, 128, 0.16)", fg: "var(--text-muted, #6b7280)" },
    done: { bg: "rgba(22, 163, 74, 0.14)", fg: "var(--accent-green, #15803d)" },
    in_progress: { bg: "rgba(37, 99, 235, 0.14)", fg: "var(--accent-blue, #1d4ed8)" },
    in_review: { bg: "rgba(234, 179, 8, 0.18)", fg: "var(--accent-amber, #92400e)" },
    todo: { bg: "rgba(107, 114, 128, 0.12)", fg: "var(--text-muted, #4b5563)" },
    backlog: { bg: "rgba(107, 114, 128, 0.08)", fg: "var(--text-muted, #6b7280)" },
};
const PRIORITY_PALETTE = {
    critical: { bg: "rgba(220, 38, 38, 0.18)", fg: "var(--accent-red, #991b1b)" },
    high: { bg: "rgba(234, 88, 12, 0.16)", fg: "var(--accent-orange, #9a3412)" },
    medium: { bg: "rgba(234, 179, 8, 0.14)", fg: "var(--accent-amber, #854d0e)" },
    low: { bg: "rgba(107, 114, 128, 0.10)", fg: "var(--text-muted, #4b5563)" },
};
function PriorityChip(props) {
    const p = (props.priority || "medium").toLowerCase();
    const palette = PRIORITY_PALETTE[p] || PRIORITY_PALETTE.medium;
    return el(
        "span",
        {
            style: {
                display: "inline-flex",
                alignItems: "center",
                padding: "1px 6px",
                borderRadius: 4,
                fontSize: 10,
                fontWeight: 600,
                textTransform: "uppercase",
                background: palette.bg,
                color: palette.fg,
                ...(props.style || {}),
            },
            title: "priority " + p,
        },
        p,
    );
}

// ── main page ───────────────────────────────────────────────────────────
function AiSearchPage(_props) {
    const host = useHostContext() || {};
    const hostNavigation = useHostNavigation();
    const presetsQuery = usePluginData("presets", {}, { refetchInterval: 60000 });
    const statusQuery = usePluginData("status", {}, { refetchInterval: 30000 });
    const searchAction = usePluginAction("search");
    const recordQuery = usePluginAction("recordQuery");
    const getRecent = usePluginAction("getRecent");

    const [q, setQ] = useState("");
    const [pending, setPending] = useState(null);
    const [results, setResults] = useState(null);
    const [error, setError] = useState(null);
    const [recent, setRecent] = useState([]);
    const [showSettings, setShowSettings] = useState(false);
    const inputRef = useRef(null);

    const doSearch = useCallback(
        async (overrideQ) => {
            const query = (overrideQ != null ? String(overrideQ) : q).trim();
            setQ(query);
            if (!query) {
                setResults(null);
                setError(null);
                return;
            }
            setError(null);
            setPending(query);
            try {
                const r = await searchAction.mutate({ query, limit: 25, summaries: false });
                const j = r && r.data ? r.data : r;
                setResults(j);
                setPending(null);
                if (query && recordQuery) {
                    try { await recordQuery.mutate({ query }); } catch (_) { /* ignore */ }
                    try {
                        const recentRes = await getRecent.mutate({});
                        if (Array.isArray(recentRes)) setRecent(recentRes);
                    } catch (_) { /* ignore */ }
                }
            } catch (err) {
                setError(String(err && err.message ? err.message : err));
                setPending(null);
            }
        },
        [q, searchAction, recordQuery, getRecent],
    );

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const r = await getRecent.mutate({});
                if (cancelled) return;
                if (Array.isArray(r)) setRecent(r);
            } catch (_) { /* ignore */ }
        })();
        return () => { cancelled = true; };
    }, [getRecent]);

    useEffect(() => {
        if (inputRef.current) inputRef.current.focus();
    }, []);

    const presetList = (presetsQuery.data && presetsQuery.data.data) || presetsQuery.data || [];
    const statusData = (statusQuery.data && statusQuery.data.data) || statusQuery.data || null;

    const openResult = (r) => {
        if (!r || !r.link) return;
        if (hostNavigation && typeof hostNavigation.navigate === "function") {
            hostNavigation.navigate(r.link);
        } else if (typeof window !== "undefined" && r.link) {
            window.location.href = r.link;
        }
    };

    return el(
        Box,
        { style: { maxWidth: 980, margin: "0 auto", padding: 24 } },
        el(Row, { style: { justifyContent: "space-between", alignItems: "flex-start" } },
            el(
                "div",
                { style: { display: "flex", flexDirection: "column", gap: 2 } },
                el("h1", { style: { margin: 0, fontSize: 22, fontWeight: 600 }, children: "AI Search" }),
                el(
                    "p",
                    { style: { margin: 0, fontSize: 13, color: "var(--text-muted, #6b7280)" }, children:
                        "Search across Paperclip. Pick a preset for instant results, or type a question for the LLM." +
                        (statusData && statusData.llm && !statusData.llm.configured
                            ? " ⚠️ LLM not configured — call the setLLMCredentials action to enable natural language."
                            : ""),
                    },
                ),
            ),
            el(
                "button",
                {
                    onClick: () => setShowSettings(!showSettings),
                    style: {
                        padding: "4px 10px", fontSize: 12, borderRadius: 6,
                        border: "1px solid var(--border, #e5e7eb)",
                        background: "transparent", color: "var(--text-secondary, #4b5563)",
                        cursor: "pointer",
                    },
                    children: showSettings ? "Hide status" : "Status",
                },
            ),
        ),
        showSettings ? el(AiSearchStatus, { statusData }) : null,
        el(SearchBar, { q, setQ, onSubmit: doSearch, inputRef, pending }),
        recent && recent.length ? el(RecentQueries, { recent, onPick: doSearch }) : null,
        el(Presets, { presets: Array.isArray(presetList) ? presetList : [], onPick: doSearch, disabled: !!pending }),
        error ? el("div", { style: { color: "var(--accent-red, #b91c1c)", fontSize: 13 }, children: "Error: " + error }) : null,
        pending ? el("div", { style: { color: "var(--text-muted, #6b7280)", fontSize: 13 }, children: "Searching for \"" + pending + "\"…" }) : null,
        results ? el(Results, { results, onOpen: openResult }) : null,
    );
}

function SearchBar(props) {
    return el(
        "form",
        {
            onSubmit: (e) => { e.preventDefault(); props.onSubmit && props.onSubmit(); },
            style: { display: "flex", gap: 8, marginTop: 8 },
        },
        el("input", {
            ref: props.inputRef,
            value: props.q,
            onChange: (e) => props.setQ(e.target.value),
            placeholder: "Search issues, approvals, runs…  (try: blocked, status:in_progress, in review without action, or a question)",
            disabled: !!props.pending,
            style: {
                flex: 1,
                padding: "10px 14px",
                fontSize: 14,
                border: "1px solid var(--border, #d1d5db)",
                borderRadius: 8,
                outline: "none",
                background: "var(--bg-card, #fff)",
                color: "var(--text-primary, #111827)",
            },
        }),
        el(
            "button",
            {
                type: "submit",
                disabled: !!props.pending,
                style: {
                    padding: "10px 18px",
                    fontSize: 14,
                    fontWeight: 500,
                    borderRadius: 8,
                    border: "none",
                    background: props.pending ? "var(--bg-muted, #e5e7eb)" : "var(--accent-blue, #2563eb)",
                    color: props.pending ? "var(--text-muted, #6b7280)" : "#fff",
                    cursor: props.pending ? "wait" : "pointer",
                },
                children: props.pending ? "Searching…" : "Search",
            },
        ),
    );
}

function RecentQueries(props) {
    return el(
        "div",
        { style: { display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", fontSize: 12 } },
        el("span", { style: { color: "var(--text-muted, #6b7280)" }, children: "Recent:" }),
        ...(props.recent || []).slice(0, 8).map((q, i) =>
            el(
                "button",
                {
                    key: "r" + i,
                    onClick: () => props.onPick && props.onPick(q),
                    style: {
                        padding: "2px 8px",
                        fontSize: 11,
                        border: "1px solid var(--border, #e5e7eb)",
                        borderRadius: 999,
                        background: "transparent",
                        color: "var(--text-secondary, #4b5563)",
                        cursor: "pointer",
                    },
                    children: q,
                },
            ),
        ),
    );
}

function Presets(props) {
    if (!props.presets || props.presets.length === 0) return null;
    return el(
        "div",
        { style: { display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" } },
        el("span", { style: { fontSize: 12, color: "var(--text-muted, #6b7280)", marginRight: 4 }, children: "Presets:" }),
        ...props.presets.map((p, i) =>
            el(
                "button",
                {
                    key: "p" + (p.label || i),
                    onClick: () => props.onPick && props.onPick(p.label || p.key),
                    disabled: props.disabled,
                    title: p.hint || p.label,
                    style: {
                        padding: "6px 12px",
                        fontSize: 12,
                        fontWeight: 500,
                        borderRadius: 999,
                        border: "1px solid var(--border, #e5e7eb)",
                        background: "var(--bg-card, #fff)",
                        color: "var(--text-primary, #111827)",
                        cursor: props.disabled ? "wait" : "pointer",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                    },
                    children: el(
                        _F,
                        { children: [
                            el("span", { children: p.icon || "•" }),
                            el("span", { children: p.label || p.key }),
                        ] },
                    ),
                },
            ),
        ),
    );
}

function AiSearchStatus(props) {
    const d = props.statusData;
    if (!d) return el("div", { style: { fontSize: 12, color: "var(--text-muted, #6b7280)" }, children: "Loading status…" });
    return el(
        "div",
        {
            style: {
                marginTop: 8,
                padding: 10,
                fontSize: 12,
                border: "1px solid var(--border, #e5e7eb)",
                borderRadius: 8,
                background: "var(--bg-muted, #f9fafb)",
                color: "var(--text-secondary, #374151)",
                fontFamily: "ui-monospace, monospace",
            },
            children: JSON.stringify(d, null, 2),
        },
    );
}

function Results(props) {
    const r = props.results;
    if (!r || !r.results || r.results.length === 0) {
        return el(
            "div",
            {
                style: {
                    padding: 16,
                    fontSize: 13,
                    color: "var(--text-muted, #6b7280)",
                    border: "1px dashed var(--border, #e5e7eb)",
                    borderRadius: 8,
                },
                children: r && r.intent
                    ? `No results for "${r.query}" (${r.intent.summary || r.intent.kind}).`
                    : "No results.",
            },
        );
    }
    return el(
        Box,
        { style: { gap: 8 } },
        el(
            "div",
            { style: { fontSize: 12, color: "var(--text-muted, #6b7280)" }, children:
                `${r.count} result${r.count === 1 ? "" : "s"} for "${r.query}" — ${r.intent && r.intent.summary ? r.intent.summary : r.intent && r.intent.kind}` +
                (r.meta && r.meta.totalMs != null ? ` · ${r.meta.totalMs}ms` : "") +
                (r.meta && r.meta.apiCalls ? ` · ${r.meta.apiCalls} API call${r.meta.apiCalls === 1 ? "" : "s"}` : ""),
            },
        ),
        ...r.results.map((item, i) => el(ResultRow, { key: "r" + i, item, onOpen: () => props.onOpen && props.onOpen(item) })),
    );
}

function ResultRow(props) {
    const item = props.item;
    return el(
        "div",
        {
            onClick: props.onOpen,
            style: {
                display: "flex",
                flexDirection: "column",
                gap: 4,
                padding: 12,
                border: "1px solid var(--border, #e5e7eb)",
                borderRadius: 8,
                background: "var(--bg-card, #fff)",
                cursor: "pointer",
            },
        },
        el(Row, { style: { gap: 8, alignItems: "center" } },
            el("span", { style: { fontFamily: "ui-monospace, monospace", fontSize: 12, fontWeight: 600, color: "var(--text-secondary, #4b5563)" }, children: item.identifier || item.id }),
            el(Chip, { status: item.status, label: item.status }),
            item.priority ? el(PriorityChip, { priority: item.priority }) : null,
            el(Spacer),
            item.assignee ? el("span", { style: { fontSize: 11, color: "var(--text-muted, #6b7280)" }, children: item.assignee }) : null,
        ),
        el("div", { style: { fontSize: 14, fontWeight: 500, color: "var(--text-primary, #111827)" }, children: item.title || "(untitled)" }),
        item.snippet ? el(
            "div",
            { style: { fontSize: 12, color: "var(--text-muted, #4b5563)", lineHeight: 1.4 }, children: item.snippet + (item.snippet.length >= 220 ? "…" : "") },
        ) : null,
        item.link ? el(
            "div",
            { style: { fontSize: 11, color: "var(--accent-blue, #2563eb)", fontFamily: "ui-monospace, monospace" }, children: item.link },
        ) : null,
    );
}

// ── sidebar entry ──────────────────────────────────────────────────────
function AiSearchSidebar(_props) {
    const hostNavigation = useHostNavigation();
    const path = "/ai-search";
    const href = hostNavigation && typeof hostNavigation.resolveHref === "function"
        ? hostNavigation.resolveHref(path)
        : path;
    const linkProps = hostNavigation && typeof hostNavigation.linkProps === "function"
        ? hostNavigation.linkProps(path)
        : {};
    const isActive = typeof window !== "undefined" && window.location.pathname === href;
    return el(
        "a",
        {
            ...linkProps,
            href,
            "aria-current": isActive ? "page" : undefined,
            style: {
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "6px 10px",
                fontSize: 13,
                fontWeight: 500,
                color: isActive ? "var(--accent, #2563eb)" : "inherit",
                textDecoration: "none",
            },
            children: "🔍  AI Search",
        },
    );
}

// ── dashboard widget ──────────────────────────────────────────────────
function AiSearchWidget(_props) {
    const [q, setQ] = useState("");
    const hostNavigation = useHostNavigation();
    const onSubmit = useCallback((e) => {
        e.preventDefault();
        const qq = q.trim();
        if (!qq) return;
        const path = "/ai-search?q=" + encodeURIComponent(qq);
        if (hostNavigation && typeof hostNavigation.navigate === "function") {
            hostNavigation.navigate(path);
        } else if (typeof window !== "undefined") {
            window.location.href = path;
        }
    }, [q, hostNavigation]);
    return el(
        "form",
        { onSubmit, style: { display: "flex", gap: 6, padding: 8 } },
        el("input", {
            value: q,
            onChange: (e) => setQ(e.target.value),
            placeholder: "Search…",
            style: {
                flex: 1, padding: "6px 10px", fontSize: 13,
                border: "1px solid var(--border, #d1d5db)",
                borderRadius: 6, outline: "none",
                background: "var(--bg-card, #fff)",
            },
        }),
        el(
            "button",
            { type: "submit", style: {
                padding: "6px 12px", fontSize: 12,
                border: "none", borderRadius: 6,
                background: "var(--accent-blue, #2563eb)", color: "#fff", cursor: "pointer",
            }, children: "Go" },
        ),
    );
}

// Export with names matching the manifest entrypoints
export {
    AiSearchPage,
    AiSearchSidebar,
    AiSearchWidget,
};
export default AiSearchPage;
