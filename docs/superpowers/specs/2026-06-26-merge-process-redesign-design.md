# Merge Process Redesign — BTCAAAAA-38557

**Status:** draft for review
**Author:** CEO agent (73e7ef43-1337-47f8-9cf2-8db91ebcf555)
**Date:** 2026-06-26
**Scope:** fix the merge dispatch pipeline so 28-item backlog clears in <24h and stays clear

## Problem (with data)

CEO report: "29 in queue" — actual is **28** (18 in_review issues + 10 open PRs).

### Queue A — `in_review` issues (18)

Of 18 in_review issues, **0 carry a `Fix-SHA:` line in any comment.** The merge-dispatch routine (`scripts/merge_dispatch_routine.py`, function `extract_fix_sha_from_comments` at L315) parses a line-anchored regex `^Fix-SHA: ([0-9a-f]{40})$` from issue comments. With no SHA, the routine logs `no_fix_sha` and skips — it cannot dispatch anything in this queue.

Composition of the 18:
- **16 code-work items** sitting in_review waiting for an agent to post the missing SHA. These are dispatchable as soon as the SHA appears.
- **2 non-code items** mis-filed in the code queue:
  - BTC-37887 "Redeploy Dev to current main (commit f3ebaeed0)" — operational, no code artifact
  - BTC-30570 "PaperClip Speech to Text Input" — likely a plugin install / config change, no SHA possible

### Queue B — open PRs (10)

`gh pr list --state open` returns 10 PRs:
- **8 BEHIND main** (PR #213, #224, #225, #233, #235, #236, #242) — mergeable but stale; routine skips these (it expects SHA → branch lookup, not PR existence as a signal)
- **2 CONFLICTING** (PR #231, #232) — DIRTY, no auto-resolution path

### Root cause

The pipeline was designed for the simple case: one agent, one fix, one PR, one SHA comment. It assumes the SHA comment is produced reliably. Three structural mismatches prevent this assumption from holding at scale:

1. **No SHA enforcement at the `in_review` boundary.** Agents transition to in_review without writing a SHA. The routine sees no SHA, dispatches nothing.
2. **No lane for non-code items.** Redeploys, plugin installs, and config rotations can't carry a SHA but sit in the same status as code merges.
3. **No rebase or conflict-guard.** BEHIND and CONFLICTING PRs have no automated recovery path.

The current architecture punishes scale: as more agents fan out from parent issues, the SHA discipline breaks, the queue grows, and the routine is the bottleneck.

## Goals

- Clear the current 28-item backlog in <24h with zero manual CEO intervention.
- Make the routine **never** see an `in_review` issue without the data it needs to dispatch.
- Separate the code-merge queue from the board-action queue so they cannot starve each other.
- Cut the per-merge cycle from "human nudge → routine fires → squash" to "routine fires on its own."

## Non-goals

- New paperclip status enum (deferred — would require server-side status enum change and coordinated migration).
- Event-sourced pipeline (overkill, multi-week).
- Replacing the merge dispatch routine entirely.
- Touching `src/detectors/building_blocks/**` (project rule).

## Architecture

Two queues, one enforcement layer at the boundary, one routine per queue.

```
                        ┌──────────────────────┐
   agent finishes ────▶ │ paperclip-api PATCH  │
                        │ status=in_review     │
                        └─────────┬────────────┘
                                  │
                       validates body / comments
                                  │
                ┌─────────────────┴───────────────────┐
                │                                     │
       has Fix-SHA line?                    has [no-sha: <reason>]?
                │                                     │
                ▼                                     ▼
       ┌─────────────────┐                  ┌──────────────────┐
       │ code-merge queue │                  │ board-action queue│
       │ (existing, fixed) │                 │ (new)             │
       └────────┬─────────┘                  └────────┬──────────┘
                │                                     │
                ▼                                     ▼
       merge_dispatch_routine            action_dispatch_routine
                │                                     │
                ▼                                     ▼
       squash-merge + closure_gate      action executed + closure_gate
                │                                     │
                └──────────┬──────────────────────────┘
                           ▼
                       status=done
```

## Components

### 1. Server-side enforcement (paperclip-api)

**Ownership:** the validation step lives in the `paperclip-api` codebase (sibling repo, not this repo). Implementation is a single PR there with a corresponding paperclip-client SDK bump. This repo (`BTC-Trade-Engine-PaperClip`) only consumes the new validation via the standard `npx paperclipai issue update` path.

A new validation step on `PATCH /api/issues/:id` when `status=in_review`:

- Parse the request body's comment field (if any) AND the issue's prior comments for **either**:
  - A line-anchored `Fix-SHA: <40-hex>` token (existing convention), OR
  - A `[no-sha: <reason>]` tag (new convention) where `<reason>` is one of `redeploy | install | config | process`
- If neither is found → return `422 Unprocessable Entity` with body:
  ```json
  {
    "error": "in_review_requires_token",
    "remediation": "Add a 'Fix-SHA: <40-hex>' comment (code work) or '[no-sha: <reason>]' comment (board action) before transitioning to in_review. Allowed no-sha reasons: redeploy, install, config, process."
  }
  ```
- If both are present → prefer Fix-SHA (it's the stronger signal).
- Skip validation if the issue is already in_review (idempotent PATCH).

This is a server-side guard. Client-side reminders are not sufficient — the bottleneck is exactly that agents forget the comment.

### 2. `merge_dispatch_routine.py` (existing, no logic change)

Once Queue A issues always carry a SHA, this routine works as-is. We do not modify it.

### 3. `action_dispatch_routine.py` (new)

Mirrors the structure of `merge_dispatch_routine.py`:

- `find_awaiting_action_issues()` — fetches `status=in_review` issues whose latest comment carries a `[no-sha: <reason>]` tag
- For each, dispatch the corresponding action:
  - `[no-sha: redeploy]` → POST to a deploy hook (script `scripts/redeploy_dev.sh` ships as part of this change since it does not yet exist)
  - `[no-sha: install]` → run `npx paperclipai plugin install <plugin-id>` with the plugin name from the comment
  - `[no-sha: config]` → write the config value + comment with the new state
  - `[no-sha: process]` → no-op + comment confirming the process step is done
- PATCH `status=done` with evidence comment

Reuses the same:
- Watermark file pattern (`data/action_dispatch_watermark.json`)
- `WATERMARK_FILE`, `ROUTINE_TIMEOUT_SECONDS`, `MAX_DEFERRAL_API_CALLS` constants
- `X-Paperclip-Run-Id` header

### 4. `closure_gate_routine.py` (extended)

Add a parallel verification path:

- If the done issue has `[no-sha: <reason>]` → verify the action evidence (redeploy timestamp, install confirmation, config diff, process attestation) instead of SHA ancestor-of-main
- All other existing checks (fabrication, smoke runner, deferral detection) apply unchanged

## Comment conventions

| Token | Where | Meaning |
|-------|-------|---------|
| `Fix-SHA: <40-hex>` | bare line in any comment | code work, this SHA carries the fix |
| `[no-sha: redeploy]` | bare line in any comment | board action: redeploy dev to a commit |
| `[no-sha: install]` | bare line in any comment | board action: install a plugin |
| `[no-sha: config]` | bare line in any comment | board action: change a config value |
| `[no-sha: process]` | bare line in any comment | board action: process step (no code/deploy) |

The bare-line requirement (line-anchored) is critical — markdown bold, bullets, or quotes break the regex. CLAUDE.md already enforces this for Fix-SHA; we extend it to the new tags.

## Data flow

**Code work:**
1. Agent finishes → writes commit on feature branch → `git push`
2. Agent posts comment with `Fix-SHA: <40-hex>`
3. Agent PATCHes `status=in_review` (server validates SHA present)
4. `merge_dispatch_routine` agent-finish hook fires → opens/updates PR → squash-merges → PATCHes done
5. `closure_gate_routine` verifies SHA is ancestor of `origin/main`

**Board action:**
1. Operator / agent decides on action → posts comment with `[no-sha: <reason>]` and required parameters
2. Operator / agent PATCHes `status=in_review` (server validates tag present)
3. `action_dispatch_routine` agent-finish hook fires → executes action → posts evidence comment → PATCHes done
4. `closure_gate_routine` verifies evidence (per-reason)

## Error handling

| Failure | Behavior |
|---------|----------|
| PATCH in_review with no token | 422 with remediation message |
| Agent posts `[no-sha: install]` but comment lacks plugin name | `action_dispatch` returns action-failed, posts comment asking for plugin name, leaves issue in_review |
| Action handler throws | Log + retry once + post failure comment with stack trace + leave in_review (NOT done) |
| Closure gate finds evidence missing | Reopen to in_review with disposition comment |
| Squash-merge fails (CI gates) | Routine leaves in_review, posts status comment, retries next sweep |

## Testing

### Unit tests (in `tests/test_*_routine.py`)

- `test_extract_fix_sha_*` (existing) — regression coverage
- `test_extract_no_sha_tag` — parses `[no-sha: <reason>]` with valid + invalid reasons
- `test_dispatch_action_redeploy` — posts evidence comment, transitions done
- `test_dispatch_action_unknown_reason` — logs error, leaves in_review

### Integration tests

- `test_in_review_without_token_rejected` — PATCH returns 422 with remediation
- `test_in_review_with_fix_sha_accepted` — PATCH returns 200, routine picks up
- `test_in_review_with_no_sha_redeploy_accepted` — PATCH returns 200, action routine picks up
- `test_closure_gate_no_sha_redeploy_verifies_evidence` — fake action posted → closure passes

### End-to-end smoke

- One real feature branch, one real `[no-sha: install]` issue (e.g., BTC-30570 if appropriate) → driven through the whole pipeline.

## Migration plan (clear the 28-item backlog)

### Day 1 (today, immediate, no code change)

**BTC-37887 "Redeploy Dev"**: this matches `[no-sha: redeploy]`. Operator posts the tag comment, the routine (once shipped) handles it. Until shipped: I post the tag comment + manual PATCH back to in_review with the redeploy action noted.

**BTC-30570 "Speech to Text Input"**: clarify the deliverable. If it's a plugin install, tag `[no-sha: install] <plugin-id>`.

**16 code items in_review**: agents responsible for each must post the missing Fix-SHA. If the agent is idle, this issue (BTC-38557) escalates them. We do NOT batch-post SHAs centrally — that breaks accountability.

### Day 1-2 (the code change)

Ship the enforcement + action_dispatch_routine in one PR. Behind a feature flag (`MERGE_PROCESS_V2_ENABLED=true`) for the first 24h. Monitor queue depth.

### Day 2-3 (cleanup)

8 BEHIND PRs: dispatch routine picks them up after rebase (or we add a `rebase_runner` script — separate ticket).
2 CONFLICTING PRs (PR #231, #232): these need conflict resolution from the original author. Tag those PRs with a "needs-rebase" comment so a rebase runner picks them up next sweep.

## Open questions for CEO

1. **Action handlers**: do `redeploy | install | config | process` cover the cases, or are there others I should plan for? (Looking at past in_review items, these four cover the observed patterns.)
2. **Server-side enforcement UX**: prefer `422 reject` (forces agents to comply) or `200 with warning comment` (lets them through, slows queue)? My recommendation: 422 reject. Soft warnings don't work at scale — agents skip them.
3. **The 2 non-code items today**: should I classify them now or wait for the v2 routine to ship first? My recommendation: classify them now so the moment v2 ships the backlog drains.

## Rollout risk

- **Low**: enforcement + new routine is additive. Existing `merge_dispatch_routine` and `closure_gate_routine` unchanged unless closure_gate's evidence path is touched. Feature flag means we can disable v2 if it misbehaves.
- **Watch items**: closure_gate verifier for `[no-sha: <reason>]` items must be airtight or done items reopen silently. Smoke test BTC-30570 (plugin install) end-to-end before flipping the flag for all issues.

## What this does NOT solve

- **PR throughput on the runners.** If the runner queue is the actual bottleneck (queued CI checks > merge rate), this design doesn't help. We need a separate ticket for runner capacity.
- **Agent discipline in posting SHAs at the right moment.** Enforcement catches the omission at PATCH time, but a late SHA (after the agent has mentally moved on) still costs a wake cycle. This is a behavior change that takes a sprint to stabilize.
- **Stale PRs left behind by ex-features.** BTC-38529 branch-reaper shipped recently; that handles abandoned branches. The merge queue is a different problem.

## Out of scope (deferred)

- Approach B (new `awaiting_action` status) — would be cleaner long-term but requires server-side status enum change. Worth revisiting once v2 stabilizes.
- Event-sourced pipeline — overkill.
- Replacing the dispatch routine with a workflow engine — out of scope for this fix.