# ADR-0004: Memory Plugin Selection — Honcho vs. Hindsight

**Issue:** [BTCAAAAA-26392](/BTCAAAAA/issues/BTCAAAAA-26392)
**Author:** Architect (73eaab54)
**Status:** In Review
**Date:** 2026-05-14
**Priority:** CRITICAL
**Parent:** [BTCAAAAA-26251](/BTCAAAAA/issues/BTCAAAAA-26251) — Investigate this plugins

---

## Context

Paperclip agents need persistent, cross-run memory to maintain context across heartbeats. Two installable memory plugins are available:

- **Honcho** (`@honcho-ai/paperclip-honcho@0.1.2`) — by Plastic Labs. A memory system with deep reasoning capabilities (dialectic API, dreaming, representations). AGPL-3.0 license.
- **Hindsight** (`@vectorize-io/hindsight-paperclip@0.2.1`) — by Vectorize.io. A memory system with biomimetic architecture (retain/recall/reflect). MIT license.

Paperclip already has a native PARA-based file memory system (`para-memory-files` skill), but it is file-based and Markdown-only — it does not provide vector search, entity extraction, temporal reasoning, or consolidation. A plugin adds structured, queryable memory that agents can access programmatically at runtime.

### Current State

- Neither plugin is installed in this Paperclip instance.
- A `deploy/hindsight-start.sh` script exists in the repo, pointing to a separate venv (`/home/sirrus/projects/BTC_Engine_v3/venv`) — suggesting prior experimentation with Hindsight standalone, not via the Paperclip plugin.
- No Honcho assets exist in the repo.

---

## Decision: Adopt Hindsight as the Primary Memory Plugin

We will adopt **Hindsight** as the primary memory plugin for Paperclip. Honcho will not be adopted at this time but should be re-evaluated when its Paperclip plugin matures and if AGPL-3.0 licensing is acceptable for production deployment.

---

## Options Considered

### Option A: Hindsight (Recommended)

**How it works:**
- Installed once via `pnpm paperclipai plugin install @vectorize-io/hindsight-paperclip`
- Memory keyed to `companyId` + `agentId` — persists across all runs
- Lifecycle hooks: auto-recall at `run.started`, auto-retain on `comment.created` and `run.finished`
- 2 agent tools: `hindsight_recall(query)` and `hindsight_retain(content)`
- Self-hosted (embedded PostgreSQL via pg0) or cloud

**Memory model:**
- Banks (isolated memory namespaces) → World Facts / Experiences → Observations / Mental Models
- TEMPR retrieval: Semantic + Keyword + Graph + Temporal (4-strategy fusion with cross-encoder reranking)
- Observation consolidation: automatic deduplication, evidence tracking, freshness trends
- Configurable mission, directives, and disposition traits per bank

**Strengths:**
- **MIT license** — no copyleft risk. Safe for commercial/proprietary use.
- **Simpler surface area** — 2 tools (retain/recall) vs Honcho's 9. Less cognitive load for agents.
- **Superior retrieval** — TEMPR's 4-strategy parallel search (semantic, keyword, entity-graph, temporal) with reciprocal rank fusion and cross-encoder reranking. Built-in temporal reasoning ("what happened last spring?").
- **Paperclip-native integration depth** — hooks into `run.started`, `comment.created`, and `run.finished` events. Auto-recall before every heartbeat, auto-retain after every run.
- **More mature plugin** — v0.2.1 vs Honcho's v0.1.2. 13.3k GitHub stars vs 3.5k.
- **Embedded database** — pg0 (embedded PostgreSQL) means zero external DB dependencies for self-hosting. No need to manage a separate PostgreSQL instance.
- **Bank granularity** — configurable isolation (`per company`, `per agent`, or `per company+agent`).
- **Observation consolidation** — facts are automatically deduplicated, tracked with evidence provenance, and carry freshness trends. This reduces noise in memory retrieval.
- **Adapter-compatible** — works with all Paperclip adapters (Claude, Codex, Cursor, HTTP, Process).

**Weaknesses:**
- **Shallower reasoning** — `reflect()` is a single-operation analysis vs Honcho's multi-tier dialectic reasoning system (5 levels from Minimal to Max). No autonomous "dreaming" (background reasoning).
- **No multi-peer paradigm** — Hindsight is bank-centric, not entity/peer-centric. It doesn't model user-agent-group relationships.
- **No cross-session representations** — Hindsight doesn't build persistent peer profiles across sessions the way Honcho does. Accumulation is through observations, not identity models.
- **Version velocity risk** — 54 releases in ~5 months (Dec 2025 – May 2026). Rapid iteration could indicate instability or shifting APIs.

### Option B: Honcho (Deferred)

**How it works:**
- Install via `pnpm paperclipai plugin install @honcho-ai/paperclip-honcho`
- Memory keyed to `workspaceId` — sessions tied to peer interactions
- 9 agent tools: `search`, `chat`, `create_conclusion`, `get_config`, `set_config`, + status/setup/interview/config slash commands
- Self-hosted (FastAPI + PostgreSQL + pgvector) or cloud ($2/M messages + per-query costs)

**Memory model:**
- Workspaces → Peers → Sessions → Messages
- Background deriver: representation updates, session summarization, peer card generation
- Dreaming: asynchronous background reasoning (pattern identification, hypothesis testing, conclusion weighting)
- 5-tier dialectic API: Minimal ($0.001) → Max ($0.50) reasoning depth

**Strengths:**
- **Best-in-class reasoning** — SOTA on LongMem, LoCoMo, BEAM benchmarks. 60-90% token savings claimed.
- **Peer paradigm** — models any entity (users, agents, groups, NPCs) uniformly. Supports multi-agent, group chat scenarios.
- **Dreaming** — autonomous background reasoning (pattern identification, hypothesis testing). This is unique — no other memory system offers this.
- **Cross-session identity** — peer representations persist and improve across all sessions. This is stronger than Hindsight's observation-only model.
- **Custom reasoning models (Neuromancer)** — achieves SOTA at lower cost/latency than frontier models.
- **MCP tools** — search, chat, create_conclusion, get_config, set_config. More tools = more control for agents.
- **Claude Code integration** — deep integration with Claude Desktop/Code (the runtime backing most Paperclip agents). Git-aware, multi-host, team support.

**Weaknesses:**
- **AGPL-3.0 license** — copyleft. Hosting Honcho as part of a proprietary system triggers source-disclosure obligations. This is a hard blocker for many commercial deployments.
- **Younger plugin** — v0.1.2 (published 3 weeks ago) vs Hindsight's v0.2.1 (4 weeks ago). 3 versions vs 3 versions, but the integration depth for Paperclip events appears less mature.
- **9 tools vs 2** — more tools means more surface area for agent errors, higher token costs in system prompts, and more configuration complexity.
- **External PostgreSQL dependency** — requires managing a PostgreSQL + pgvector instance for self-hosting, vs Hindsight's embedded pg0.
- **Cost model complexity** — $2/M ingested messages + per-query costs across 5 reasoning tiers vs Hindsight's simpler self-hosted model. Cloud pricing may be unpredictable.
- **Overlap with Paperclip native** — Honcho's peer representations and session management overlap with Paperclip's own issue/agent/run lifecycle. This could create confusion about the system of record for agent state.

### Option C: Both (Not Recommended)

Running both plugins simultaneously would create:
- **Dual system of record** — memories split across two systems with no unified query interface
- **Token bloat** — both plugins injecting context into system prompts, potentially exceeding context windows
- **Semantic drift** — Hindsight's observations and Honcho's representations would diverge, creating contradictory memory
- **Operational overhead** — two services to monitor, two cost models, two configuration surfaces

---

## Architecture Analysis

### Memory Architecture in Paperclip

```
Paperclip Agent Wake
       │
       ├── Plugin Hook: run.started
       │       │
       │       ├── [Hindsight] recall(issue context) → inject context into system prompt
       │       │
       │       └── [Paperclip Native] para-memory-files → file-based knowledge graph
       │
       ├── Agent Does Work (heartbeat)
       │       │
       │       ├── hindsight_recall("specific query") ← optional mid-run recall
       │       └── hindsight_retain("fact learned")  ← optional mid-run retention
       │
       └── Plugin Hook: run.finished / comment.created
               │
               └── [Hindsight] retain(run output / comment) → persist to bank
```

### Complementarity with Native PARA Memory

Paperclip's native `para-memory-files` system is:
- **File-based** — Markdown files in `~/.paperclip/` structured as Projects/Areas/Resources/Archives
- **Human-editable** — manual knowledge graph, not programmatic
- **Private to agent** — not shared across agents in a company

Hindsight complements this by providing:
- **Programmatic retention** — agents can `retain()` during heartbeats without file I/O
- **Cross-agent sharing** — banks keyed to `companyId` allow shared company-wide memory
- **Vector search** — semantic recall vs file-based grep
- **Automatic consolidation** — facts deduplicated into observations without agent intervention

These systems do not conflict — PARA is the long-term, human-curated knowledge base; Hindsight is the runtime, agent-accessible working memory.

### Security Posture

| Concern | Hindsight | Honcho |
|---------|-----------|--------|
| Self-hosted | Yes (embedded pg0) | Yes (external PG required) |
| Cloud option | Yes (ui.hindsight.vectorize.io) | Yes (api.honcho.dev) |
| Data at rest | PostgreSQL (pg0) | PostgreSQL + pgvector |
| API auth | API key (config) | API key (env var) |
| License | MIT (permissive) | AGPL-3.0 (copyleft) |
| Data sharing | Per bank isolation | Per workspace isolation |

Both support self-hosting for sensitive data. Hindsight's embedded PostgreSQL (pg0) means no external DB dependency — lower attack surface for self-hosted deployments.

### Latency & Throughput

| Operation | Hindsight | Honcho |
|-----------|-----------|--------|
| Retain | ~50-200ms (async LLM call for extraction) | ~50ms (DB write) + async deriver |
| Recall | ~100-500ms (4-strategy parallel + fusion) | ~200ms (context() with summary) |
| Reasoning | ~1-5s (reflect, single LLM call) | ~200ms-30s (5 tiers, background dreaming) |

Hindsight's recall is slightly heavier (4 strategies + cross-encoder) but within acceptable latency for a pre-heartbeat context injection. Honcho's `context()` is faster (~200ms) but provides less structured recall — deeper reasoning requires the `chat()` endpoint (up to 30s async).

---

## Pricing Comparison

### Hindsight
- **Self-hosted:** $0 (MIT license). Infrastructure costs: compute for pg0 + LLM API calls (OpenAI/Anthropic/Gemini/Groq).
- **Cloud:** Free tier available. Paid plans not publicly documented. Likely usage-based on retain/recall/reflect volume.

### Honcho
- **Self-hosted:** $0 source code (AGPL-3.0). Infrastructure costs: PostgreSQL + pgvector + compute for FastAPI + background workers + LLM API calls (Anthropic/Gemini/OpenAI).
- **Cloud:** Memory: $2/M messages ingested. Reasoning: $0.001/q (Minimal) to $0.50/q (Max). Startups (<$5M raised): $1,000 credits. Enterprise: custom.

**For a Paperclip agent with ~100 heartbeats/day, 10 agents, 30-day month:**
- Honcho cloud ingestion alone: ~30K messages/month → $0.06 (ingestion only, pre-reasoning). Reasoning adds variable cost.
- Hindsight self-hosted: $0 (plugin cost) + LLM API calls for extraction/retrieval (~$5-20/month for gpt-4o-mini).

Hindsight is significantly cheaper to operate at Paperclip scale.

---

## Recommendation

### Adopt Hindsight (Option A) now.

**Rationale:**

1. **License safety (MIT vs AGPL-3.0).** This is the decisive factor. AGPL-3.0 creates real legal risk for a proprietary trading platform. MIT is universally safe.

2. **Simpler agent surface (2 tools vs 9).** Paperclip agents already manage complex workflows — issue checkout, repo operations, comment threads, git commits. A 2-tool memory interface (retain/recall) is the right abstraction level. Honcho's 9 tools (search, chat, create_conclusion, get_config, set_config, + slash commands) add cognitive load with marginal benefit given Paperclip's native tooling already covers some of these.

3. **Better Paperclip integration.** Hindsight hooks into the Paperclip lifecycle deeply (run.started recall, comment.created retain, run.finished retain). This is "install and forget" — agents get memory without explicit tool calls. Honcho's integration appears less lifecycled.

4. **TEMPR retrieval superiority.** For an agent that needs to answer questions like "what did we decide about the risk gate last week?", Hindsight's 4-strategy fusion (semantic + keyword + graph + temporal) will outperform Honcho's single-strategy semantic search.

5. **Lower operational burden.** Embedded pg0 vs external PostgreSQL management. No per-query pricing to track. No background worker fleet to operate.

### Defer Honcho (Option B).

Honcho's peer paradigm, deep reasoning, and dreaming are genuinely impressive capabilities. Re-evaluate when:

1. **The Paperclip plugin reaches ≥v0.5.0** (indicating production maturity and richer Paperclip lifecycle hooks)
2. **Commercial licensing (non-AGPL) becomes available** — Plastic Labs may offer enterprise licenses
3. **A concrete use case emerges** that Hindsight cannot satisfy — e.g., multi-agent group conversations where peer identity models are required, or background dreaming for autonomous pattern discovery

### Do NOT adopt both (Option C rejected).

Dual memory systems create a split-brain problem with no compensating benefit.

---

## Consequences

### Positive
- Agents gain persistent, queryable cross-run memory without code changes
- Company-wide shared memory enables agents to build on each other's discoveries
- TEMPR retrieval handles temporal queries ("last week", "in June") that file-based memory cannot
- Self-hosted option keeps all memory data within our infrastructure

### Negative
- One more service to deploy/monitor (Hindsight API server)
- LLM API costs for memory extraction and retrieval (mitigated by using Groq/cheaper models)
- Migration cost if we later switch to Honcho (bank → workspace data migration)
- Rapid Hindsight release cadence may require frequent dependency updates

### Neutral
- Memory plugin does not replace PARA file-based memory — it complements it. PARA remains the long-term curated knowledge base.
- The Hindsight evaluation pipeline [BTCAAAAA-26239](/BTCAAAAA/issues/BTCAAAAA-26239) owns smoke testing — this ADR does not duplicate that work.

---

## References

- Hindsight Paperclip plugin: `@vectorize-io/hindsight-paperclip@0.2.1` ([npm](https://www.npmjs.com/package/@vectorize-io/hindsight-paperclip))
- Hindsight documentation: https://hindsight.vectorize.io
- Hindsight source: https://github.com/vectorize-io/hindsight (13.3k stars, MIT)
- Honcho Paperclip plugin: `@honcho-ai/paperclip-honcho@0.1.2` ([npm](https://www.npmjs.com/package/@honcho-ai/paperclip-honcho))
- Honcho documentation: https://honcho.dev/docs
- Honcho source: https://github.com/plastic-labs/honcho (3.5k stars, AGPL-3.0)
- Hindsight evaluation pipeline: [BTCAAAAA-26239](/BTCAAAAA/issues/BTCAAAAA-26239)
- Parent investigation task: [BTCAAAAA-26251](/BTCAAAAA/issues/BTCAAAAA-26251)
- Paperclip plugin SDK: `@paperclipai/plugin-sdk`
