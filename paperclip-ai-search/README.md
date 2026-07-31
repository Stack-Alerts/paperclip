# Paperclip AI Search

Smart, token-efficient search across Paperclip. Pick a preset for an instant
LLM-free result, or type a natural-language question and have the LLM parse
intent → fire a single API call.

## What it does

- **Presets** (0 LLM tokens) — `Blocked`, `In progress`, `In review`, `No owner`, `High priority`, `Critical`, `Today`, `Liveness incidents`, `Token-gap`, `AI Recs webUI`, `Recovery actions`, `Closable (agent confirmed)`
- **Keyword queries** (0 LLM tokens) — `status:foo`, `priority:bar`, `assignee:me`, `unassigned`, `mine`, `active`, `stuck`, `no run`
- **Natural language** (~250 output tokens) — *"open AI Recs blocked this week"*, *"what did the CEO work on yesterday"*, *"find recovery issues from this morning"*
- Returns compact results: identifier + title + status + priority + assignee + 1-line snippet + deep link

## Model

By default the plugin uses the model assigned to the **active CEO agent**
(read from `/api/companies/{cid}/agents` → `adapterConfig.model` at startup).
You can override via `ai-search/setModel` action or the API:

```
POST /api/plugins/{id}/actions/setModel
{ "model": "claude-sonnet-4-5" }
```

Override is stored in `plugin.state` (scopeKind=instance) under
`ai-search-config`.

## LLM endpoint configuration

The plugin reads the LLM credentials from a paperclip secret named
**`ai-search-llm-credentials`** (JSON value):

```json
{
  "baseUrl": "https://api.minimax.io/anthropic",
  "apiKey": "sk-cp-..."
}
```

If the secret is missing or invalid, the plugin falls back to the
Anthropic default (`https://api.anthropic.com`) and the **keyword / preset
paths still work** — only natural-language queries will return a friendly
"keyword search (configure secret to enable natural language)" hint.

To create the secret:
```
POST /api/companies/{cid}/secrets
{ "name": "ai-search-llm-credentials", "provider": "local_encrypted", "key": "<json-stringified>" }
```

The `baseUrl` can be any Anthropic-compatible endpoint (Anthropic API,
an OpenAI-compatible proxy, etc.). The plugin calls
`POST {baseUrl}/v1/messages` with the standard Anthropic request format
(`x-api-key` + `anthropic-version`).

## Slots

| Slot | Path / Type | Export |
| --- | --- | --- |
| Page | `/ai-search` | `AiSearchPage` |
| Sidebar | — | `AiSearchSidebar` |
| Dashboard widget | — | `AiSearchWidget` |

## Data endpoints

- `search` — main search data (used by the page)
- `presets` — list of presets
- `status` — diagnostic for the settings page (LLM configured? model?)

## Actions

- `search` — same as data
- `presets` — same as data
- `setModel` — override the model
- `getRecent` — last 25 queries for autocomplete
- `recordQuery` — persist a query to recent history

## Token economy

- **Preset hit** (most common): 0 LLM tokens, 1 paperclip API call, ~100ms
- **Keyword hit**: 0 LLM tokens, 1 paperclip API call, ~100ms
- **NL hit** (uncommon): 1 LLM call (~200 in / 250 out), 1 paperclip API call, ~1-3s
- **Optional summary**: 1 more tiny LLM call (~250 out), 0 paperclip calls

Most of the time you only spend paperclip-API tokens (1 query, ≤25 results).

## Install (local install via Paperclip API)

```bash
curl -X POST http://127.0.0.1:3100/api/plugins/install \
  -H 'Content-Type: application/json' \
  -d '{"packageName":"/home/sirrus/paperclip-mods/paperclip-ai-search","isLocalPath":true}'
```

## License

MIT
