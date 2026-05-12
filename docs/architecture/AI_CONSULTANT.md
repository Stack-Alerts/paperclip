# AI Consultant — Architecture

**Version:** 0.1.0
**Last updated:** 2026-05-12
**Owner:** DocWriter / CTO

---

## 1. Overview

The AI Consultant is a ReAct (Reasoning + Acting) agent that provides LLM-powered trading intelligence. It answers natural-language queries about strategy performance, signal behavior, and configuration via tool calls against the database and signal catalog.

### 1.1 Components

```
ai_consultant/
  consultant_service.py  — ReAct loop: LLM ↔ tools, session management
  signal_catalog.py      — Building block registry with live stats augmentation
  audit_writer.py        — Dual-write audit log (PostgreSQL + JSONL)
  provider.py            — LLM provider abstraction (OpenAI, Anthropic, Ollama)
  db/                    — Database query engines
```

---

## 2. Consultant Service

**File:** `consultant_service.py`

Orchestrates a ReAct-pattern loop:

```
User message
    ↓
ConsultantService.chat(session_id, message)
    ↓
1. Load or create Session (turn_count, total_cost, message history)
2. Build system prompt (includes signal catalog context)
3. Call LLM provider
4. If tool_calls returned:
   a. Execute each tool
   b. Feed results back to LLM
   c. Repeat up to 10 iterations (ReAct loop)
5. Return final response
```

### 2.1 Session Management

```python
@dataclass
class Session:
    session_id: str
    messages: list[dict]
    created_at: str
    total_cost: float
    turn_count: int
```

Sessions accumulate message history. When context approaches 80% of model token limit (`_SUMMARIZE_AT = 0.80`), the service triggers automatic summarization to compress history.

### 2.2 Token Limits

| Model | Limit |
|---|---|
| claude-sonnet-4-6 | 200K |
| claude-opus-4-7 | 200K |
| claude-haiku-4-5 | 200K |
| gpt-4o | 128K |
| gpt-4o-mini | 128K |
| llama3 | 8,192 |

---

## 3. Signal Catalog

**File:** `signal_catalog.py`

Provides compressed context (~5K tokens) for LLM system prompts about available building blocks.

### 3.1 Data Flow

```
Building Block Registry (YAML/JSON files)
    ↓
SignalCatalogService.load_registry()
    ↓ + live stats from DB
CatalogEntry → context_string() → ~5K token prompt fragment
```

### 3.2 API

| Method | Returns | Purpose |
|---|---|---|
| `context_string()` | str | Compressed catalog for system prompts |
| `search(query)` | list[dict] | Ranked signal matches for tool calls |
| `get_signal_info(name)` | dict | Single signal detail |
| `list_signals_by_type(category)` | list | Category listing |

### 3.3 Data Types

```python
@dataclass
class SignalStats:
    signal_name: str
    total_occurrences: int
    trades_triggered: int
    trigger_rate: float | None
    win_rate: float | None
    profit_factor: float | None
    avg_pnl: str | None
    best_timeframe: str | None

@dataclass
class CatalogEntry:
    name: str
    category: str
    weight: int
    direction: str
    description: str
    valid_signals: list[str]
    signal_tiers: dict
    tags: list[str]
    stats: dict[str, SignalStats]
```

---

## 4. LLM Provider Abstraction

**File:** `provider.py`

Config-driven factory for multiple LLM backends.

### 4.1 Interface

```python
class LLMProvider(abc.ABC):
    chat(messages, tools) → ChatResponse
    estimate_cost(prompt_tokens, completion_tokens) → float

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]

@dataclass
class ChatResponse:
    content: str
    tool_calls: list[ToolCall]
    prompt_tokens: int
    completion_tokens: int
    model: str
```

### 4.2 Backends

| Backend | Provider String | Config |
|---|---|---|
| OpenAI | `openai` | `OPENAI_API_KEY` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` |
| Ollama | `ollama` | `OLLAMA_*` env vars |

Selected via `LLM_PROVIDER` env var. `create_provider()` factory reads the env and returns the correct implementation.

### 4.3 Retry Logic

```python
@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0      # exponential backoff
    max_delay: float = 60.0
    jitter: bool = True
```

---

## 5. Audit Writer

**File:** `audit_writer.py`

Dual-write audit log for all AI Consultant activity. Failures are logged to stderr and never propagate.

### 5.1 Event Types

| Event | Description |
|---|---|
| `SESSION_START` | New consultant session |
| `SESSION_END` | Session terminated |
| `TOOL_CALL` | Tool executed |
| `LLM_CALL` | LLM provider called |
| `PROPOSAL_GENERATED` | AI proposed a change |
| `PROPOSAL_APPROVED` | User approved a proposal |
| `PROPOSAL_REJECTED` | User rejected a proposal |
| `CHANGE_APPLIED` | Change executed |
| `ROLLBACK_EXECUTED` | Change rolled back |

### 5.2 Writes

| Target | Mechanism | Availability |
|---|---|---|
| PostgreSQL | `asyncpg` INSERT into `ai_consultant_audit` table | Conditional (requires DB) |
| JSONL file | Append to `~/.btc_trade_engine/audit/ai_consultant.jsonl` | Always |

### 5.3 Table Schema

```sql
CREATE TABLE ai_consultant_audit (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    user_id TEXT,
    strategy_id TEXT,
    payload JSONB,
    token_cost_usd NUMERIC(10,6)
);
```

---

## 6. Configuration

Consultant reads the following env vars:

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `anthropic` | Backend selection |
| `OPENAI_API_KEY` | — | OpenAI auth |
| `ANTHROPIC_API_KEY` | — | Anthropic auth |
| `POSTGRES_*` | — | DB connection for live stats |

---

## 7. Related Documents

- [signal_catalog.py](../../src/ai_consultant/signal_catalog.py)
- [consultant_service.py](../../src/ai_consultant/consultant_service.py)
- [BUILDING_BLOCKS_API_REFERENCE.md](../building-blocks/BUILDING_BLOCKS_API_REFERENCE.md)
- [DATABASE_GUIDE.md](DATABASE_GUIDE.md) — ai_consultant_audit table
