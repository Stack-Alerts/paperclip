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
