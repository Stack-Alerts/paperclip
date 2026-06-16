# Stale-Code Archival Policy

## Motivation

Archived code that remains on disk at its original path is a hazard: agents
discover it via glob/search, assume it is live, and make changes against
stale logic. This caused the Strategy Browser regression ([BTCAAAAA-26568](/BTCAAAAA/issues/BTCAAAAA-26568)).

## Rule

Every file or directory that is **archived** (moved into an `archive/` subtree,
replaced by a new implementation, or otherwise marked dead) MUST:

1. Be removed from its original on-disk location (`git rm` if tracked, plain
   `rm -rf` if untracked).
2. Have its original path appended to `.gitignore` so no agent ever rebuilds
   or restores it at that location.
3. Be documented in the issue that performed the archival.

**An archival is not complete until the original path is git-rm'd AND
.gitignore'd.**

## Enforcement

- All agents MUST check `.gitignore` before searching or globbing for source
  files. Any path listed in `.gitignore` is off-limits for editing.
- PRs that touch paths listed in `.gitignore` MUST be rejected.
- Code review MUST verify that archived paths are cleaned up, not left as
  stale stubs.

<!-- BEGIN:merge-governance -->
## Merge governance — REQUIRED FOR ALL CODE CHANGES

Effective per [BTCAAAAA-30046](/BTCAAAAA/issues/BTCAAAAA-30046) (Phase 2 of the merge-governance roll-out drafted on [BTCAAAAA-30038](/BTCAAAAA/issues/BTCAAAAA-30038#document-process-audit)). Supersedes the preliminary contract on [BTCAAAAA-30039](/BTCAAAAA/issues/BTCAAAAA-30039). Applies to every agent making code changes in this repo.

### 1. Branch naming — one issue, one branch

Every code change starts with a fresh branch off `origin/main`:

```
git fetch origin
git switch -c fix/BTCAAAAA-NNN-kebab-slug origin/main
# or feat/, chore/, docs/, test/, refactor/ — pick by the verb in the issue title
```

Verify before the first commit:

```
git rev-parse --abbrev-ref HEAD   # must equal fix/BTCAAAAA-NNN-kebab-slug
```

One issue → one branch. Do not piggyback a second issue onto someone else's branch.

### 2. Single-owner rule

Once a branch carries the `BTCAAAAA-NNN` identifier in its name, **only that issue's assignee commits to it**. Other agents who notice related work open a follow-up issue (with their own branch) — they do not push commits onto a sibling's branch.

This is non-negotiable. The failure mode it prevents is cross-wired closures: a commit on someone else's branch cannot satisfy `--is-ancestor origin/main` for *your* issue without first being merged via *their* PR — which the closure-gate routine ([BTCAAAAA-30040](/BTCAAAAA/issues/BTCAAAAA-30040)) will catch and reopen.

When multiple agents are active on the same workspace, use `git worktree add /tmp/btc-NNN -b feat/BTCAAAAA-NNN-slug origin/main` to isolate your branch from sibling sessions that may rotate `HEAD` mid-task.

### 3. Pre-commit working-tree check (hard self-check)

Before `git add`, every agent runs:

```
git rev-parse --abbrev-ref HEAD
```

The output **must** equal the branch you cut for this issue. If it doesn't, abort, switch branches (or cut a new one), and re-stage. Failure mode observed today: the [BTCAAAAA-30034](/BTCAAAAA/issues/BTCAAAAA-30034) token-gap chain landed commits on three unrelated feature branches because agents staged changes against whatever branch was checked out, not the one the issue belonged to. That is the bug this clause exists to stop.

The repo-wide lint script `scripts/lint-branch-name.sh` automates the branch-name check — run it before committing or wire it into your editor's git hook. Enforcement at commit-time lands in Phase 3 ([BTCAAAAA-30040](/BTCAAAAA/issues/BTCAAAAA-30040)).

### 4. `Fix-SHA:` tag contract

Every closure comment (the one accompanying `status=done` or `status=in_review`) MUST include exactly one line of the form:

```
Fix-SHA: <40-char-sha>
```

Regex: `^Fix-SHA: [0-9a-f]{40}$`

The SHA must be the HEAD of the branch implementing the fix **at the time the closure comment is posted**. The closure-gate routine ([BTCAAAAA-30040](/BTCAAAAA/issues/BTCAAAAA-30040)) parses this line:

- **No `Fix-SHA:` line** → issue auto-reopens with a comment naming the gap.
- **Malformed SHA** (wrong length, non-hex, more than one matching line) → auto-reopens.
- **Valid SHA but not yet on `origin/main`** → status forced to `in_review`, not `done`.

### 5. Ancestry self-check before posting close-out

Run this immediately before posting the closure comment:

```
git fetch origin
git merge-base --is-ancestor <fix-sha> origin/main; echo rc=$?
```

- **`rc=0`** → safe to mark `done`. Attach the rc line to the closure comment as evidence.
- **`rc≠0`** → the commit is not yet on `origin/main`. Post the closure comment with `status=in_review` and name the merge-dispatch owner (CEO or RepoSteward). Do NOT PATCH `status=done`; the closure-gate routine will reopen it.

The CEO/RepoSteward merge-dispatch flow ([BTCAAAAA-30041](/BTCAAAAA/issues/BTCAAAAA-30041)) is what flips `in_review` → `done` after the PR lands on `origin/main`.

### 6. One issue, one PR

Every PR description references exactly one `BTCAAAAA-NNN` identifier. If commit subjects in your branch reference a different identifier, those commits do not belong on this branch — extract them to their own branch and open a separate PR. Direct push to `origin/main` is FORBIDDEN; all merges go through PR + RepoSteward (or CEO `GH_TOKEN` fallback).

### 7. Dev-server status update on checkout

Any agent that switches the working tree to a non-`main` branch MUST update the [dev-server-status document on BTCAAAAA-30031](/BTCAAAAA/issues/BTCAAAAA-30031#document-dev-server-status) within the same heartbeat. This is how the next agent on the box knows which branch is loaded and avoids accidentally committing against it.

### 8. Closure-comment template

Copy/paste this block at issue closure. Fill in the bracketed slots; keep the `Fix-SHA:` line exactly as formatted.

````markdown
## Closure — BTCAAAAA-NNN

**Outcome:** [one sentence: what is now true that wasn't before]

**Evidence:**
- Screenshot: [URL or relative path under `docs/screenshots/`]
- Smoke test rc: [paste exact command and rc, or "N/A — docs-only change"]

**Branch:** `fix/BTCAAAAA-NNN-kebab-slug`

**Ancestry check:**
```
$ git merge-base --is-ancestor <fix-sha> origin/main; echo rc=$?
rc=0     # paste actual rc — 0 = done, ≠0 = in_review
```

Fix-SHA: 0123456789abcdef0123456789abcdef01234567
````

The `Fix-SHA:` line must be on its own, must match `^Fix-SHA: [0-9a-f]{40}$`, and the SHA must be the branch HEAD when posted.

### Out of scope for this section

- Automated enforcement at commit-time → Phase 3 ([BTCAAAAA-30040](/BTCAAAAA/issues/BTCAAAAA-30040)).
- Merge dispatch from `in_review` → `done` → Phase 4a ([BTCAAAAA-30041](/BTCAAAAA/issues/BTCAAAAA-30041)).
- GitHub branch protection rules → Phase 4b ([BTCAAAAA-30042](/BTCAAAAA/issues/BTCAAAAA-30042)).
<!-- END:merge-governance -->

## Dev Server Entry Points (BTCAAAAA-31132)

To eliminate operator confusion between the supervised and ephemeral dev servers, the
legacy `./start.sh` has been split into two distinct, clearly named entry points:

### `./start-dev.sh` — Supervised, canonical launcher (port `:3010`)

**Use this for:** The board, QA, production-like testing, integration with systemd health checks.

```bash
./start-dev.sh          # Start/verify server, then exit
./start-dev.sh --watch  # Start/verify, then tail journalctl logs
```

**Behavior:**
- Runs on port `:3010` (same as `btc-dev-server.service`)
- Ensures the systemd unit is `active`; restarts if `inactive` or `failed`
- Waits for HTTP 200 on `http://localhost:3010/`
- Inherits all branch gating from the systemd unit
  ([BTCAAAAA-30590](/BTCAAAAA/issues/BTCAAAAA-30590),
   [BTCAAAAA-31114](/BTCAAAAA/issues/BTCAAAAA-31114))
- Returns 0 on success, non-zero on failure

### `./start-test.sh [--branch <name>]` — Ephemeral test instance (port `:3000`)

**Use this for:** Quick iteration, branch-specific testing (non-`main`), sandboxed development.

```bash
./start-test.sh                   # Test on :3000, default branch
./start-test.sh --branch feature  # Test on :3000, switch to feature branch first
```

**Behavior:**
- Spawns a standalone `next dev -p 3000` (not under systemd)
- Does NOT register with systemd; pure ephemeral process
- Prints a warning: "THIS IS A TEST INSTANCE"
- Optional `--branch <name>` to test non-`main` code without affecting `:3010`
- Runs indefinitely until you press Ctrl+C

**Note:** Next.js prevents multiple dev servers in the same directory (BTCAAAAA-30626).
If `btc-dev-server.service` is already running on `:3010`, you must stop it first:
```bash
systemctl --user stop btc-dev-server.service
./start-test.sh --branch feature-branch
```

### `./start.sh` (deprecated)

The original `./start.sh` is deprecated and now prints a deprecation notice. Use one of
the above instead.

## Dev/Test Stack Lifecycle Management (BTCAAAAA-33697)

The development stack consists of three services. When they hang or crash, use these
commands to stop, diagnose, and recover without CEO intervention.

### Services

| Service | Port | Script | systemd Unit |
|---------|------|--------|--------------|
| Backend API | `:8765` | `start_api.sh` | `btc-dev-backend.service` |
| Supervised Web UI | `:3010` | `start-dev.sh` | `btc-dev-server.service` |
| Ephemeral Test Web UI | `:3000` | `start-test.sh` | (not under systemd) |

### Diagnostics

```bash
./status-dev.sh  # Health check for all three services
```

Prints:
- HTTP probe result (2s timeout) for each service
- PID, uptime, and uptime of each
- Backend SHA from `/health` endpoint (main branch verification)
- Git state (HEAD vs `origin/main` with drift detection)

Exits 0 if all healthy, non-zero if any service is degraded.

### Stopping Services

```bash
./stop-dev.sh       # Stop supervised web UI (:3010)
./stop-backend.sh   # Stop backend API (:8765)
./stop-test.sh      # Stop ephemeral test instance (:3000)
```

Each script:
1. Sends `SIGTERM` to the process/service
2. Waits 5 seconds for graceful shutdown
3. If still running, sends `SIGKILL`
4. Reports success/failure

### Restarting with Smart Hang Detection (BTCAAAAA-33696 Recovery)

```bash
./restart-dev.sh [--clean]                    # Restart supervised web UI
./restart-backend.sh                           # Restart backend API
./restart-test.sh [--clean] [--branch <name>] # Restart ephemeral test
```

**Smart hang detection logic:**

When a service hangs (the BTCAAAAA-29995 scenario), the process is alive and the port is
bound, but the HTTP endpoint is unresponsive. The restart scripts detect this automatically:

1. **Stop the service** (graceful shutdown, 5s timeout)
2. **Detect hang:** Is the port still bound? Is `/health` (or `/` for web UI) responding?
   - Probe 3 times with 2s timeout each
   - If all 3 probes fail but port is bound → **hang detected**
3. **Kill immediately:** If hang detected, send `SIGKILL` directly (don't wait for graceful shutdown)
4. **Restart fresh:** Start the service and poll for HTTP 200 (30s timeout)

This prevents the operator from waiting indefinitely for a graceful shutdown that will never
come. Total recovery time: <15s for most scenarios (confirmed by acceptance testing on
BTCAAAAA-33697).

**Example: hung backend (port bound, but uvicorn deadlocked)**

```bash
./restart-backend.sh
# [restart-backend] ★ restarting backend API...
# [restart-backend] stopping current instance...
#   [stop-backend] ...
# [restart-backend] checking for hangs...
# [restart-backend] ⚠ hang detected, force-killing...
# [restart-backend] starting btc-dev-backend.service...
# [restart-backend] waiting for HTTP 200 on /health...
# [restart-backend] attempt 1/30 → ✓ ready
#
# ✓ Backend restarted successfully
```

**Options:**

- `./restart-dev.sh --clean` — Also removes `.next/dev` cache before restart
- `./restart-test.sh --clean` — Also removes `.next` cache before restart
- `./restart-test.sh --branch <name>` — Switch to branch before restart

### Related Issues

- **[BTCAAAAA-29995](/BTCAAAAA/issues/BTCAAAAA-29995)** — Root cause: uvicorn deadlock during high load
- **[BTCAAAAA-33696](/BTCAAAAA/issues/BTCAAAAA-33696)** — Watchdog fixes (systemd WatchdogSec=, uvicorn diagnostics)
- **[BTCAAAAA-31132](/BTCAAAAA/issues/BTCAAAAA-31132)** — Original split of start.sh into start-dev.sh and start-test.sh
- **[BTCAAAAA-31234](/BTCAAAAA/issues/BTCAAAAA-31234)** — Wrapper PATH design

## Mandatory Heartbeat Exit — Disposition Checklist (BTCAAAAA-36752)

Every agent in this company MUST end every heartbeat with exactly one final
disposition. This is the safety net for the paperclip skill's Step 8 checklist
— same rules, distilled for cross-agent consistency regardless of which skill
subset loads in a given run. The `paperclip` skill is the source of truth for
the full procedure; this section is the minimum invariant.

Before you exit ANY heartbeat, make exactly one of these API calls with the
`X-Paperclip-Run-Id: $PAPERCLIP_RUN_ID` header:

| Disposition       | When to use                                                                                  | PATCH payload (one of)                                                                                                                  |
| ----------------- | -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `done`            | Work is complete, verification recorded, no follow-up remains.                               | `{"status":"done","comment":"<what was done and why>"}`                                                                                |
| `in_review`       | A real reviewer path exists (board user, approval, typed participant, pending interaction).    | `{"status":"in_review","comment":"<what is ready and who reviews>"}`                                                                   |
| `blocked`         | Cannot continue until first-class `blockedByIssueIds` resolve or a named owner acts.         | `{"status":"blocked","blockedByIssueIds":["<id>"],"comment":"<blocker + named unblock owner/action>"}`                                   |
| Delegated follow-up | Next work belongs in a new issue, not on this one.                                         | `POST /api/companies/{companyId}/issues` with `parentId` + `goalId`, then close parent or leave it `in_progress` with explicit monitor. |
| `in_progress`     | ONLY if a live continuation path exists: active run, queued continuation, or monitor.         | `{"status":"in_progress","comment":"<what is done, what remains, who/what wakes you>"}`                                                |

**Non-negotiable rules:**

- NEVER exit a heartbeat with the run still in flight and no status update.
  A comment or a "Remaining" bullet is **evidence**, not a disposition — the
  recovery watchdog will flag it as `clear_next_step` and auto-create a
  corrective run.
- The four disposition calls are mutually exclusive. Pick one; do not stack
  status changes in a single PATCH.
- If you discover the work belongs to a different agent, do NOT post a comment
  and exit — use `POST /api/companies/{companyId}/issues` to create a child
  issue with `parentId` + `goalId` so the wake handoff is structured.
- If you hit a turn or time limit, PATCH the most accurate status you can with
  a `comment` that names what's done and what's next — `in_progress` is valid
  here only when an active run or monitor will resume you.

**Why this is here:** [BTCAAAAA-36752](/BTCAAAAA/issues/BTCAAAAA-36752) —
the disposition-miss recovery pattern from the Perplexity research paper is a
real risk in this company. The `paperclip` skill already enforces this in
Step 8, but agents that load a reduced skill subset or suffer context drift
in long sessions can still skip the final PATCH. This block is the last-line
defense loaded from the workspace itself.
