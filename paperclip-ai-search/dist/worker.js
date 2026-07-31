/**
 * Paperclip AI Search — worker.
 *
 * Token-efficient search across Paperclip issues, approvals, runs.
 *
 *  - Preset queries  (preset name like "blocked")          -> direct API, 0 LLM tokens
 *  - Keyword queries (status:foo, priority:bar, etc.)      -> direct API, 0 LLM tokens
 *  - Natural language ("open AI recs blocked this week")   -> LLM parses intent to a
 *                                                              structured filter, then API call (~250 output tokens)
 *  - Always returns a compact result list:
 *      { id, kind, identifier, title, status, priority, assignee, link, snippet, score }
 *
 * Model: by default, the model assigned to the active CEO (read once at startup).
 *        Override via the plugin settings page.
 * Endpoint: configurable via the `ai-search-llm-credentials` paperclip secret
 *            (JSON {"baseUrl":"https://api.minimax.io/anthropic","apiKey":"sk-cp-..."}).
 *            Falls back to Anthropic default if the secret is missing/invalid.
 */

import { definePlugin, runWorker } from "@paperclipai/plugin-sdk";
import {
    STATE_KEYS,
    SECRET_NAME,
    DEFAULT_LIMIT,
    MAX_LIMIT,
    LLM_TIMEOUT_MS,
    RECENT_QUERIES_MAX,
    PRESETS,
    PRESET_ORDER,
    parseKeywordQuery,
} from "./constants.js";

// ─── Company-id resolution ────────────────────────────────────────────────
// The SDK doesn't expose `ctx.companyId` directly on the worker context for
// action / data calls, but it does include the calling user's companyId in
// the request body that arrives as `params`. We pick the first available
// signal: explicit param, the data call's companyId field, or a fallback
// to the first company returned by `companies.list` for the operator.
async function resolveCompanyId(ctx, params) {
    if (params && params.companyId) return params.companyId;
    try {
        const list = await ctx.companies.list();
        const arr = list && (list.items || list.companies || list);
        if (Array.isArray(arr) && arr.length) return arr[0].id;
    } catch (_) { /* ignore */ }
    return null;
}

// ─── LLM endpoint resolution ────────────────────────────────────────────────
// LLM credentials are stored directly in plugin state. Paperclip server
// disables `secrets.resolve` for plugin workers by default ("company-scoped
// plugin config" not yet implemented), so the plugin reads the credentials
// from a state key set via the setLLMCredentials action. The state value is
// {baseUrl, apiKey} as a plain object.
async function resolveLlmConfig(ctx, companyId) {
    // 1. Try plugin instance config (operator-provided)
    let baseUrl = null, apiKey = null;
    try {
        const cfg = await ctx.config.get();
        if (cfg && typeof cfg.llmBaseUrl === "string" && typeof cfg.llmApiKey === "string") {
            baseUrl = cfg.llmBaseUrl.trim();
            apiKey = cfg.llmApiKey.trim();
        }
    } catch (_) { /* ignore */ }
    // 2. Fall back to plugin state
    if (!baseUrl || !apiKey) {
        try {
            const stored = await ctx.state.get({ scopeKind: "instance", stateKey: "ai-search-llm-credentials", companyId });
            if (stored && typeof stored === "object" && stored.baseUrl && stored.apiKey) {
                baseUrl = String(stored.baseUrl).trim();
                apiKey = String(stored.apiKey).trim();
            }
        } catch (_) { /* ignore */ }
    }
    if (baseUrl && apiKey) {
        return { baseUrl: baseUrl.replace(/\/+$/, ""), apiKey, source: "configured" };
    }
    return { baseUrl: "https://api.anthropic.com", apiKey: null, source: "default" };
}

async function resolveModelName(ctx, companyId, override) {
    if (override) return override;
    // 1. From plugin state
    try {
        const cfg = await ctx.state.get({ scopeKind: "instance", stateKey: STATE_KEYS.config, companyId });
        if (cfg && cfg.modelOverride) return cfg.modelOverride;
    } catch (_) { /* ignore */ }
    // 2. From the active CEO agent's adapter_config.model
    if (companyId) {
        try {
            const list = await ctx.agents.list({ companyId });
            const arr = list && (list.items || list.agents || list);
            const ceo = (Array.isArray(arr) ? arr : []).find((a) => a.role === "ceo" && a.status === "running")
                || (Array.isArray(arr) ? arr : []).find((a) => a.role === "ceo")
                || null;
            if (ceo && ceo.adapterConfig && ceo.adapterConfig.model) {
                return ceo.adapterConfig.model;
            }
        } catch (_) { /* ignore */ }
    }
    return "claude-sonnet-4-5";
}

// ─── Filter → API query string ─────────────────────────────────────────────
function buildQuery(filter) {
    const f = filter || {};
    const qs = new URLSearchParams();
    qs.set("limit", String(Math.min(Number(f.limit) || DEFAULT_LIMIT, MAX_LIMIT)));
    if (f.statuses && f.statuses.length) {
        qs.set("status", f.statuses.join(","));
    } else if (f.status) {
        qs.set("status", f.status);
    }
    if (f.priority) qs.set("priority", f.priority);
    if (f.assigneeAgentId === null) qs.set("assigneeAgentId", "");
    if (f.assigneeUserId === null) qs.set("assigneeUserId", "");
    if (f.assigneeUserId === "me") {
        // caller already passed auth — we don't know their userId from inside the
        // worker, so the dedicated endpoint below is more reliable. But for
        // /issues?q= we can still set status; the operator-level filter is best
        // done via /agents/me/inbox-lite. Leave this branch for now.
    }
    if (f.assigneeSearch) qs.set("q", `assignee:${f.assigneeSearch}`);
    if (f.createdAfter === "24h") {
        const d = new Date(Date.now() - 24 * 60 * 60 * 1000);
        qs.set("createdAfter", d.toISOString());
    }
    if (f.keyword) {
        const existing = qs.get("q");
        qs.set("q", existing ? `${existing} ${f.keyword}` : f.keyword);
    }
    return qs.toString();
}

// ─── Compact result shaping ───────────────────────────────────────────────
function shapeIssue(issue, score = 1) {
    return {
        id: issue.id,
        kind: "issue",
        identifier: issue.identifier,
        title: issue.title,
        status: issue.status,
        priority: issue.priority || "medium",
        assignee: issue.assigneeAgentId
            ? `agent:${(issue.assigneeAgentId || "").slice(0, 8)}`
            : (issue.assigneeUserId ? `user:${issue.assigneeUserId}` : null),
        companyId: issue.companyId,
        updatedAt: issue.updatedAt,
        link: `/BTCAAAAA/issues/${issue.identifier}`,
        snippet: (issue.description || "").slice(0, 220).replace(/\s+/g, " ").trim(),
        score,
    };
}

function shapeApproval(a, score = 1) {
    return {
        id: a.id,
        kind: "approval",
        identifier: a.id.slice(0, 8),
        title: (a.payload && a.payload.title) || a.kind || "Approval",
        status: a.status,
        priority: null,
        assignee: null,
        companyId: a.companyId,
        updatedAt: a.updatedAt,
        link: `/BTCAAAAA/approvals/${a.id}`,
        snippet: (a.payload && a.payload.summary) || "",
        score,
    };
}

// ─── Score issues by query relevance (cheap, no LLM) ───────────────────────
function scoreByText(text, queryTerms) {
    if (!text) return 0;
    const t = text.toLowerCase();
    let s = 0;
    for (const term of queryTerms) {
        if (!term) continue;
        const idx = t.indexOf(term.toLowerCase());
        if (idx >= 0) s += 1 + (idx === 0 ? 0.5 : 0) + (term.length > 4 ? 0.2 : 0);
    }
    return s;
}

// ─── Apply post-fetch text filter for inReviewNoAction / keyword ──────────
function postFilter(issues, filter, originalQuery) {
    if (!Array.isArray(issues)) return [];
    const f = filter || {};
    if (f.inReviewNoAction) {
        return issues.filter(
            (i) => i.status === "in_review" && !i.checkoutRunId && !i.executionRunId,
        );
    }
    if (originalQuery && originalQuery.length > 0) {
        const terms = originalQuery
            .toLowerCase()
            .split(/[\s,]+/)
            .filter((t) => t.length >= 2);
        if (terms.length) {
            return issues
                .map((i) => {
                    const text = `${i.title || ""} ${i.description || ""}`;
                    const s = scoreByText(text, terms);
                    return { i, s };
                })
                .filter(({ s }) => s > 0)
                .sort((a, b) => b.s - a.s)
                .map(({ i }) => i);
        }
    }
    return issues;
}

// ─── LLM call (Anthropic format; works with most proxies) ─────────────────
async function callLlm(ctx, llmConfig, model, systemPrompt, userPrompt, maxOutTokens) {
    if (!llmConfig.apiKey) {
        throw new Error("no api key configured (set the ai-search-llm-credentials paperclip secret)");
    }
    const url = `${llmConfig.baseUrl}/v1/messages`;
    const body = {
        model,
        max_tokens: maxOutTokens || 400,
        system: systemPrompt,
        messages: [{ role: "user", content: userPrompt }],
        stream: false, // ensure JSON response (not SSE)
    };
    const started = Date.now();
    const res = await ctx.http.fetch(url, {
        method: "POST",
        headers: {
            "content-type": "application/json",
            "accept": "application/json",
            "x-api-key": llmConfig.apiKey,
            "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify(body),
    });
    const rawBody = typeof res.text === "function"
        ? await res.text()
        : (res.body || "");
    if (res.status < 200 || res.status >= 300) {
        throw new Error(`LLM ${res.status}: ${String(rawBody).slice(0, 200)}`);
    }
    ctx.logger.info("ai-search: LLM raw response (first 400): " + String(rawBody).slice(0, 400));
    const elapsed = Date.now() - started;
    if (res.status < 200 || res.status >= 300) {
        throw new Error(`LLM ${res.status}: ${(res.body || "").slice(0, 200)}`);
    }
    const parsed = JSON.parse(String(rawBody) || "{}");
    const text = (parsed.content || [])
        .map((c) => (c && c.type === "text" ? c.text : ""))
        .filter(Boolean)
        .join("\n")
        .trim();
    return { text, elapsedMs: elapsed, usage: parsed.usage || null, model: parsed.model || model };
}

// ─── LLM filter extraction (one short call) ─────────────────────────────────
const INTENT_SYSTEM = `You are a Paperclip search-query parser. Given a natural-language query, output ONLY a JSON object describing which Paperclip filter to apply. Schema:
{"status":"todo|in_progress|in_review|blocked|done|cancelled|backlog|ANY","priorities":["critical","high","medium","low"],"assignee":"me|agent:<name>|user:<id>|none|ANY","keywords":["..."],"createdAfter":"24h|7d|ANY","summary":"<=80 char human-readable summary of what you parsed"}
Rules:
- Output ONLY the JSON object, no other text.
- Use "ANY" for fields the user did not specify.
- "open", "active", "doing" -> status "in_progress"
- "stuck", "no run", "no live run", "in review without action" -> status "in_review" + include "inReviewNoAction": true
- "no owner", "orphan", "unassigned" -> assignee "none"
- "mine", "my work" -> assignee "me"
- "today", "yesterday" -> createdAfter
- Be aggressive with keywords (3-6) extracted from the query for q= matching.
- If the query is a question ("what did i work on yesterday"), include rich keywords.`;

async function extractIntentViaLlm(ctx, llmConfig, model, query) {
    const userPrompt = `Query: ${query}\n\nJSON:`;
    const { text, elapsedMs, usage } = await callLlm(
        ctx,
        llmConfig,
        model,
        INTENT_SYSTEM,
        userPrompt,
        220,
    );
    let parsed;
    try {
        // Defensive parse: find first { ... } in the output
        const start = text.indexOf("{");
        const end = text.lastIndexOf("}");
        if (start < 0 || end < 0) throw new Error("no json");
        parsed = JSON.parse(text.slice(start, end + 1));
    } catch (err) {
        return { ok: false, error: `llm parse: ${err.message}`, raw: text };
    }
    return { ok: true, intent: parsed, elapsedMs, usage };
}

function intentToFilter(intent) {
    if (!intent || typeof intent !== "object") return null;
    const f = {};
    if (intent.status && intent.status !== "ANY") f.status = intent.status;
    if (Array.isArray(intent.priorities) && intent.priorities.length) {
        f.priority = intent.priorities[0];
    }
    if (intent.assignee === "me") f.assigneeUserId = "me";
    else if (intent.assignee === "none") {
        f.assigneeAgentId = null;
        f.assigneeUserId = null;
    } else if (typeof intent.assignee === "string" && intent.assignee !== "ANY") {
        f.assigneeSearch = intent.assignee.replace(/^(agent|user):/, "");
    }
    if (intent.createdAfter && intent.createdAfter !== "ANY") {
        f.createdAfter = intent.createdAfter;
    }
    if (Array.isArray(intent.keywords) && intent.keywords.length) {
        f.keyword = intent.keywords.join(" ");
    }
    if (intent.inReviewNoAction) f.inReviewNoAction = true;
    return f;
}

// ─── LLM result summary (optional, one tiny call after fetch) ─────────────
async function summarizeViaLlm(ctx, llmConfig, model, query, results) {
    if (!results || results.length === 0) return null;
    if (!llmConfig.apiKey) return null;
    const systemPrompt =
        "You are a paperclip assistant that writes terse one-line summaries of search results. " +
        "Each input is a JSON result. Return ONLY a JSON array of one-line summaries, same order, same length, no commentary. " +
        "Each summary must be <= 90 chars, lead with the most relevant fact for the user's query, plain text.";
    const userPrompt = `Query: ${query}\n\nResults:\n${JSON.stringify(
        results.slice(0, 10).map((r) => ({
            id: r.identifier,
            title: r.title,
            status: r.status,
            priority: r.priority,
        })),
    )}\n\nJSON:`;
    try {
        const { text, elapsedMs, usage } = await callLlm(
            ctx, llmConfig, model, systemPrompt, userPrompt, 400,
        );
        const start = text.indexOf("[");
        const end = text.lastIndexOf("]");
        if (start < 0 || end < 0) return null;
        const parsed = JSON.parse(text.slice(start, end + 1));
        if (!Array.isArray(parsed)) return null;
        return { summaries: parsed, elapsedMs, usage };
    } catch (_) {
        return null;
    }
}

// ─── The unified search action ────────────────────────────────────────────
async function runSearch(ctx, params) {
    const started = Date.now();
    const query = (params && params.query ? String(params.query) : "").trim();
    const requestedLimit = Math.min(
        Math.max(1, Number(params && params.limit) || DEFAULT_LIMIT),
        MAX_LIMIT,
    );
    const wantSummaries = !!(params && params.summaries);

    const companyId = await resolveCompanyId(ctx, params);
    if (!companyId) {
        return { ok: false, error: "could not determine companyId" };
    }

    // 1. Determine intent (preset / keyword / LLM)
    let intent = { kind: "filter", filter: {}, summary: "" };
    let llmParseMs = 0;
    let llmUsage = null;

    const presetMatch = PRESETS[query.toLowerCase()];
    if (presetMatch) {
        intent = { kind: "preset", presetKey: query.toLowerCase(), filter: { ...presetMatch.filter }, summary: presetMatch.hint };
    } else {
        const kw = parseKeywordQuery(query);
        if (kw) {
            intent = kw;
        } else if (query.length > 0) {
            // LLM path: only when we have an LLM configured
            const llmConfig = await resolveLlmConfig(ctx, companyId);
            const model = await resolveModelName(ctx, companyId, null);
            if (llmConfig.apiKey) {
                try {
                    const result = await extractIntentViaLlm(ctx, llmConfig, model, query);
                    if (result.ok) {
                        const f = intentToFilter(result.intent);
                        intent = { kind: "llm", filter: f || {}, summary: result.intent.summary || "smart search" };
                        llmParseMs = result.elapsedMs;
                        llmUsage = result.usage;
                    } else {
                        // LLM gave bad output — fall back to keyword search
                        intent = { kind: "filter", filter: { keyword: query }, summary: "keyword search (LLM parse failed)" };
                    }
                } catch (err) {
                    intent = { kind: "filter", filter: { keyword: query }, summary: `keyword search (LLM error: ${String(err.message).slice(0, 80)})` };
                }
            } else {
                // No LLM, no preset, no keyword: do a plain keyword search
                intent = { kind: "filter", filter: { keyword: query }, summary: "keyword search (configure ai-search-llm-credentials secret to enable natural language)" };
            }
        }
    }

    // 2. Build API call (use the SDK's typed clients)
    const filter = { ...intent.filter, limit: requestedLimit };
    const fetchStarted = Date.now();
    let data = [];
    try {
        if (filter.assigneeUserId === "me") {
            const r = await ctx.issues.inboxLite ? await ctx.issues.inboxLite({ limit: requestedLimit })
                : await ctx.issues.list({ assigneeUserId: "me", limit: requestedLimit, companyId });
            data = (r && (r.items || r.issues || r)) || [];
            if (!Array.isArray(data)) data = [];
        } else {
            // Build the issues.list params from our filter
            const listParams = { companyId, limit: requestedLimit };
            if (filter.status) listParams.status = filter.status;
            if (filter.priorities && filter.priorities.length) {
                listParams.priority = filter.priorities[0];
            } else if (filter.priority) {
                listParams.priority = filter.priority;
            }
            if (filter.assigneeAgentId === null) listParams.assigneeAgentId = null;
            if (filter.assigneeUserId === null) listParams.assigneeUserId = null;
            const r = await ctx.issues.list(listParams);
            data = (r && (r.items || r.issues || r)) || [];
            if (!Array.isArray(data)) data = [];
        }
    } catch (err) {
        return { ok: false, error: `paperclip list: ${String(err.message || err).slice(0, 200)}`, query };
    }
    const fetchMs = Date.now() - fetchStarted;

    // 4. Post-filter (e.g., inReviewNoAction)
    data = postFilter(data, filter, query);

    // 5. If "orphans" preset, also override statuses
    if (intent.presetKey === "orphans") {
        data = data.filter((i) => !i.assigneeAgentId && !i.assigneeUserId);
    }
    // 6. Limit again
    if (data.length > requestedLimit) data = data.slice(0, requestedLimit);

    // 7. Shape compact results
    const results = data.map((i) => shapeIssue(i, 1));

    // 8. Optional LLM summary (one more tiny call)
    let summaryMeta = null;
    if (wantSummaries && results.length > 0) {
        const llmConfig = await resolveLlmConfig(ctx, companyId);
        const model = await resolveModelName(ctx, companyId, null);
        if (llmConfig.apiKey) {
            summaryMeta = await summarizeViaLlm(ctx, llmConfig, model, query, results);
        }
    }

    return {
        ok: true,
        query,
        intent: { kind: intent.kind, presetKey: intent.presetKey || null, summary: intent.summary },
        filter,
        count: results.length,
        results,
        summaries: summaryMeta ? summaryMeta.summaries : null,
        meta: {
            totalMs: Date.now() - started,
            llmParseMs,
            llmUsage,
            fetchMs,
            apiCalls: 1 + (summaryMeta ? 1 : 0) + (intent.kind === "llm" ? 1 : 0),
        },
    };
}

// ─── Plugin entrypoint ────────────────────────────────────────────────────
const plugin = definePlugin({
    async setup(ctx) {
    // data: search — same logic, no LLM overhead in the request
    ctx.data.register("search", async (params) => runSearch(ctx, params || {}));
    // data: presets — list of available presets
    ctx.data.register("presets", async () => {
        const list = PRESET_ORDER.map((k) => PRESETS[k]).filter(Boolean);
        return list;
    });
    // data: status — diagnostic for the settings page
    ctx.data.register("status", async (params) => {
        const companyId = await resolveCompanyId(ctx, params);
        const llmConfig = await resolveLlmConfig(ctx, companyId);
        const model = await resolveModelName(ctx, companyId, null);
        return {
            plugin: { id: "paperclip.ai-search", version: "0.1.0" },
            llm: {
                configured: !!llmConfig.apiKey,
                source: llmConfig.source,
                baseUrl: llmConfig.baseUrl,
                model,
            },
            presets: PRESET_ORDER.length,
        };
    });
    // action: search — same as data
    ctx.actions.register("search", async (params) => runSearch(ctx, params || {}));
    // action: presets — list presets
    ctx.actions.register("presets", async () => PRESET_ORDER.map((k) => PRESETS[k]).filter(Boolean));
    // action: setModel — set a per-plugin model override
    ctx.actions.register("setModel", async (params) => {
        const companyId = await resolveCompanyId(ctx, params);
        const modelOverride = (params && params.model) ? String(params.model).trim() : null;
        const cfg = (await ctx.state.get({ scopeKind: "instance", stateKey: STATE_KEYS.config, companyId })) || {};
        cfg.modelOverride = modelOverride;
        cfg.updatedAt = new Date().toISOString();
        await ctx.state.set({ scopeKind: "instance", stateKey: STATE_KEYS.config, companyId }, cfg);
        return { ok: true, modelOverride };
    });
    // action: setLLMCredentials — store the LLM base URL + API key directly in
    // plugin state. Paperclip server disables secrets.resolve for plugins
    // by default, so we keep creds in plugin state. The state value is
    // {baseUrl, apiKey} as a plain object.
    ctx.actions.register("setLLMCredentials", async (params) => {
        const companyId = await resolveCompanyId(ctx, params);
        const baseUrl = (params && params.baseUrl ? String(params.baseUrl) : "").trim();
        const apiKey = (params && params.apiKey ? String(params.apiKey) : "").trim();
        if (!baseUrl || !apiKey) {
            return { ok: false, error: "baseUrl and apiKey are required" };
        }
        await ctx.state.set({ scopeKind: "instance", stateKey: "ai-search-llm-credentials", companyId }, { baseUrl, apiKey });
        return { ok: true, baseUrl };
    });

    // action: clearLLMCredentials — remove the LLM credentials so the plugin
    // falls back to keyword search.
    ctx.actions.register("clearLLMCredentials", async (params) => {
        const companyId = await resolveCompanyId(ctx, params);
        try {
            await ctx.state.delete({ scopeKind: "instance", stateKey: "ai-search-llm-credentials", companyId });
            return { ok: true };
        } catch (err) {
            return { ok: false, error: String(err && err.message ? err.message : err) };
        }
    });

    // action: getRecent — show last N queries for autocomplete
    ctx.actions.register("getRecent", async (params) => {
        const companyId = await resolveCompanyId(ctx, params);
        try {
            const recent = await ctx.state.get({ scopeKind: "instance", stateKey: STATE_KEYS.recent, companyId });
            return Array.isArray(recent) ? recent : [];
        } catch (_) {
            return [];
        }
    });

    // record query in recent (called by the UI after each search)
    ctx.actions.register("recordQuery", async (params) => {
        const companyId = await resolveCompanyId(ctx, params);
        const q = (params && params.query ? String(params.query) : "").trim();
        if (!q) return { ok: false };
        let recent = [];
        try {
            recent = (await ctx.state.get({ scopeKind: "instance", stateKey: STATE_KEYS.recent, companyId })) || [];
            if (!Array.isArray(recent)) recent = [];
        } catch (_) { recent = []; }
        recent = [q, ...recent.filter((x) => x !== q)].slice(0, RECENT_QUERIES_MAX);
        await ctx.state.set({ scopeKind: "instance", stateKey: STATE_KEYS.recent, companyId }, recent);
        return { ok: true };
    });

    return {
        async onHealth() {
            return { status: "ok" };
        },
    };
},

    async onHealth() {
        return { status: "ok" };
    },
});

export default plugin;
runWorker(plugin, import.meta.url);

