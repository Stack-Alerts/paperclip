# OpenCode Ghost-Run Watchdog

## Problem

The `opencode_local` adapter with `deepseek-v4-flash-free` can hang silently:
- The process starts (`opencode run --model opencode/deepseek-v4-flash-free`)
- The free-tier API returns errors or silently drops the connection
- The adapter has `timeoutSec: 0` (no timeout) configured by default
- The process runs indefinitely, consuming resources and ghost-running

## Solution

Two complementary tools:

### 1. Timeout Wrapper (`opencode-timeout-wrapper.sh`)

Wraps `opencode` with `timeout(1)` to kill processes that exceed the duration.

**Usage via adapter config:**
```json
{
  "command": "/path/to/repo/scripts/opencode-timeout-wrapper.sh",
  "model": "opencode/deepseek-v4-flash-free"
}
```

Controls:
- `PAPERCLIP_OPENCODE_TIMEOUT_SEC` env var (default: 1800 / 30 min)
- `PAPERCLIP_OPENCODE_BIN` env var (default: `opencode`)

### 2. Process Watchdog (`opencode_watchdog.py`)

Three detection layers, each sufficient to trigger a kill:

| Layer | Trigger | Rationale |
|-------|---------|-----------|
| **Low-CPU ghost** | elapsed > 30 min AND cpu ≤ 0.5% | Process is alive but doing no work (typical adapter hang) |
| **Output-inactive ghost** | elapsed > 30 min AND no stdout/stderr writes in 10 min | Catches retry-loop processes burning >0.5% CPU but producing no output |
| **Absolute max-age** | elapsed > 60 min (unconditional) | Last resort — kill any opencode process older than 1 hour regardless of CPU or output |

**Usage:**
```bash
python scripts/opencode_watchdog.py                         # normal run
python scripts/opencode_watchdog.py --dry-run                # report only
python scripts/opencode_watchdog.py --verbose                # verbose logging
python scripts/opencode_watchdog.py --max-age 7200           # custom max age
python scripts/opencode_watchdog.py --threshold 900          # custom silent threshold
```

**Install as systemd timer (run every 15 min):**
```bash
bash scripts/setup_opencode_watchdog.sh          # install
bash scripts/setup_opencode_watchdog.sh --status # check
bash scripts/setup_opencode_watchdog.sh --remove # uninstall
```

### 3. GitHub Actions Workflow

`.github/workflows/opencode-watchdog.yml` runs the watchdog on `*/15 * * * *`.
Useful for self-hosted runners. On standard GitHub runners it runs as a dry-run
(since it cannot see local processes).

## Logs

- `~/.paperclip/opencode_watchdog.log` — all runs
- `~/.paperclip/opencode_watchdog_killed.log` — killed processes only (includes reason code)

## Testing

```bash
# Dry-run (safe)
python scripts/opencode_watchdog.py --dry-run --verbose

# Verify wrapper
PAPERCLIP_OPENCODE_TIMEOUT_SEC=5 \
  ./scripts/opencode-timeout-wrapper.sh run --help
```
