/**
 * Paperclip AI Search — constants.
 */
const PLUGIN_ID = "paperclip.ai-search";
const PLUGIN_VERSION = "0.1.0";
const STATE_KEYS = {
    config: "ai-search-config", // plugin state: { modelOverride, defaultLimit, recentQueries }
    recent: "ai-search-recent", // ring buffer of last N queries
};
const SECRET_NAME = "ai-search-llm-credentials";
const DEFAULT_LIMIT = 20;
const MAX_LIMIT = 50;
const LLM_TIMEOUT_MS = 8000;
const RECENT_QUERIES_MAX = 25;

// Built-in presets. Adding more = 0 LLM tokens, instant results.
const PRESETS = {
    "blocked": {
        label: "Blocked",
        icon: "🚧",
        filter: { status: "blocked" },
        hint: "All blocked tickets (any company)",
    },
    "in_progress": {
        label: "In progress",
        icon: "🔄",
        filter: { status: "in_progress" },
        hint: "Active work, not blocked",
    },
    "in_review": {
        label: "In review",
        icon: "👀",
        filter: { status: "in_review" },
        hint: "Tickets waiting on reviewer/board",
    },
    "orphans": {
        label: "No owner",
        icon: "🕳️",
        filter: { assigneeAgentId: null, assigneeUserId: null, statuses: ["todo", "in_progress", "in_review", "blocked"] },
        hint: "Active tickets with no assignee",
    },
    "high_priority": {
        label: "High priority",
        icon: "🔥",
        filter: { priority: "high" },
        hint: "Priority=high across all companies",
    },
    "critical": {
        label: "Critical",
        icon: "🚨",
        filter: { priority: "critical" },
        hint: "Priority=critical",
    },
    "today": {
        label: "Today",
        icon: "📅",
        filter: { createdAfter: "24h" },
        hint: "Created in the last 24 hours",
    },
    "liveness": {
        label: "Liveness incidents",
        icon: "⚠️",
        filter: { keyword: "liveness" },
        hint: "Open harness-liveness / recovery tickets",
    },
    "token_gap": {
        label: "Token-gap",
        icon: "🔑",
        filter: { keyword: "token-gap" },
        hint: "Token-gap / GitHub auth incidents",
    },
    "ai_recs": {
        label: "AI Recs webUI",
        icon: "🤖",
        filter: { keyword: "AI Recommendations" },
        hint: "AI Recommendations panel tickets",
    },
    "recovery": {
        label: "Recovery actions",
        icon: "🛟",
        filter: { keyword: "recovery" },
        hint: "Open recovery actions / in_review_without_action_path",
    },
    "ce_blocked": {
        label: "Closable (agent confirmed)",
        icon: "✅",
        filter: { keyword: "Resolved" },
        hint: "Issues where the board / agent has already posted a 'Resolved' comment",
    },
};

// Order of preset names for UI display
const PRESET_ORDER = [
    "blocked",
    "in_review",
    "in_progress",
    "orphans",
    "ce_blocked",
    "recovery",
    "liveness",
    "token_gap",
    "ai_recs",
    "high_priority",
    "critical",
    "today",
];

// Token-efficient keyword parser: no LLM. Maps simple English to API filters.
// All paths return {filter,scope,summary} or null.
function parseKeywordQuery(rawQuery) {
    const q = (rawQuery || "").toLowerCase().trim();
    if (!q) return null;
    // Handle exact preset match
    if (PRESETS[q]) {
        return {
            kind: "preset",
            presetKey: q,
            filter: { ...PRESETS[q].filter },
            summary: PRESETS[q].hint,
        };
    }
    // status:xxx
    let m = q.match(/^status\s*[:=]\s*(\w+)$/);
    if (m) {
        const s = m[1];
        if (["todo", "in_progress", "in_review", "blocked", "done", "cancelled", "backlog"].includes(s)) {
            return { kind: "filter", filter: { status: s }, summary: `status=${s}` };
        }
    }
    // priority:xxx
    m = q.match(/^priority\s*[:=]\s*(\w+)$/);
    if (m) {
        const p = m[1];
        if (["critical", "high", "medium", "low"].includes(p)) {
            return { kind: "filter", filter: { priority: p }, summary: `priority=${p}` };
        }
    }
    // assignee:me / unassigned / assignee:NAME
    m = q.match(/^assignee\s*[:=]\s*(.+)$/);
    if (m) {
        const who = m[1].trim();
        if (who === "me" || who === "i") {
            return { kind: "filter", filter: { assigneeUserId: "me" }, summary: "assigned to me" };
        }
        if (who === "none" || who === "unassigned") {
            return { kind: "filter", filter: { assigneeAgentId: null, assigneeUserId: null }, summary: "no owner" };
        }
        return { kind: "filter", filter: { assigneeSearch: who }, summary: `assignee ${who}` };
    }
    // priority keyword
    for (const p of ["critical", "high", "medium", "low"]) {
        if (q === p || q === p + " priority" || q === "p=" + p) {
            return { kind: "filter", filter: { priority: p }, summary: `priority=${p}` };
        }
    }
    // status keyword
    for (const s of ["todo", "in_progress", "in review", "in-review", "blocked", "done", "cancelled", "backlog"]) {
        if (q === s || q === s.replace("_", " ")) {
            const status = s.replace("-", "_");
            return { kind: "filter", filter: { status }, summary: `status=${status}` };
        }
    }
    // "blocked" / "in review" / "in progress" / "my inbox" / "active" / "orphans"
    if (q === "my inbox" || q === "my work" || q === "active") {
        return {
            kind: "filter",
            filter: { assigneeUserId: "me", statuses: ["todo", "in_progress", "in_review", "blocked"] },
            summary: "my active work",
        };
    }
    // "high" or "high priority" (already covered)
    // "stuck" / "no run"
    if (q === "stuck" || q === "stuck tickets" || q === "no run" || q === "no live run") {
        return {
            kind: "filter",
            filter: { inReviewNoAction: true },
            summary: "in_review with no live run",
        };
    }
    return null;
}

export {
    PLUGIN_ID,
    PLUGIN_VERSION,
    STATE_KEYS,
    SECRET_NAME,
    DEFAULT_LIMIT,
    MAX_LIMIT,
    LLM_TIMEOUT_MS,
    RECENT_QUERIES_MAX,
    PRESETS,
    PRESET_ORDER,
    parseKeywordQuery,
};
