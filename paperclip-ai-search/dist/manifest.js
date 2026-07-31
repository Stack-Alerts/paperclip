/**
 * Paperclip AI Search — manifest.
 *
 * Smart, token-efficient search across Paperclip. Presets for common
 * queries, natural language for the rest. Uses the same model the
 * CEO is assigned to, so results look like something the operator
 * would have written themselves.
 */

const PLUGIN_ID = "paperclip.ai-search";
const PLUGIN_VERSION = "0.1.0";
const DISPLAY_NAME = "AI Search";
const DESCRIPTION =
    "Smart search across Paperclip. Pick a preset (no LLM) or type a natural-language query (LLM parses intent → API call). Uses the model the CEO is assigned to; results are short (identifier + title + status + link). Configure the LLM endpoint via the 'ai-search-llm-credentials' paperclip secret (JSON: {\"baseUrl\":\"...\",\"apiKey\":\"...\"}).";

const manifest = {
    id: PLUGIN_ID,
    apiVersion: 1,
    version: PLUGIN_VERSION,
    displayName: DISPLAY_NAME,
    description: DESCRIPTION,
    author: "Stack-Alerts",
    categories: ["ui", "automation"],
    capabilities: [
        "issues.read",
        "issue.comments.read",
        "agents.read",
        "companies.read",
        "plugin.state.read",
        "plugin.state.write",
        "instance.settings.register",
        "http.outbound",
        "ui.page.register",
        "ui.sidebar.register",
        "ui.dashboardWidget.register",
    ],
    entrypoints: {
        worker: "./dist/worker.js",
        ui: "./dist/ui/",
    },
    ui: {
        slots: [
            {
                type: "page",
                id: "ai-search-page",
                routePath: "ai-search",
                exportName: "AiSearchPage",
                displayName: "AI Search",
            },
            {
                type: "sidebar",
                id: "ai-search-sidebar",
                order: 120,
                exportName: "AiSearchSidebar",
                displayName: "AI Search",
            },
            {
                type: "dashboardWidget",
                id: "ai-search-widget",
                exportName: "AiSearchWidget",
                displayName: "Quick Search",
            },
        ],
    },
    instanceConfigSchema: {
        type: "object",
        additionalProperties: false,
        properties: {
            llmBaseUrl: {
                type: "string",
                title: "LLM base URL",
                description:
                    "Base URL for the LLM endpoint. Default: https://api.anthropic.com. " +
                    "Use your custom proxy URL if the CEO agent is configured with one.",
            },
            llmApiKey: {
                type: "string",
                title: "LLM API key",
                description:
                    "API key for the LLM endpoint. Stored in plugin state (not the paperclip " +
                    "secret vault, because plugin secrets.resolve is disabled on this server).",
            },
        },
    },
};

export default manifest;
export { PLUGIN_ID, PLUGIN_VERSION, DISPLAY_NAME };
