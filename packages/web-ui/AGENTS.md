<!-- BEGIN:phase-scope -->
## Phase scope (set by board on BTCAAAAA-29339 — effective 2026-05-20)

This phase is **webui-only**. Active development is restricted to `packages/web-ui/`.
The web-ui must replicate all functionality of the desktop client (PyQt) — that is the phase deliverable.

Hard rules:
- Do not edit `src/` (backend Python), `tests/` outside webui's own `__tests__`, `scripts/`, `deploy/`, `alembic/`, `docs/`, or any PyQt files anywhere in the repo.
- Backend touches require a board-approved cross-scope ticket whose description names the specific file or subtree being opened.
- Each window has its own Paperclip project; agents assigned to a project may only write within their project's `localFolder` subtree (see project description for exact paths).
- Cross-window changes to shared code (`src/components/ui/`, `src/types/`, `src/hooks/`, `src/utils/`, top-level `src/lib/`) require a cross-window ticket with board awareness.

The window list and project mapping is canonical in [BTCAAAAA-29339#document-plan](/BTCAAAAA/issues/BTCAAAAA-29339#document-plan).

**Active Next.js root note:** Inside `packages/web-ui/`, the active App Router root is `app/` (not `src/app/`). When both directories exist, Next.js uses `app/` and ignores `src/app/`. New Next.js route subdirs must be created under `packages/web-ui/app/<window>/`. Components remain under `packages/web-ui/src/components/` (imported via the `@/` alias which maps to `packages/web-ui/src/`).
<!-- END:phase-scope -->

<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

<!-- BEGIN:merge-governance -->
## Merge governance — REQUIRED FOR ALL CODE CHANGES

Effective per [BTCAAAAA-30046](/BTCAAAAA/issues/BTCAAAAA-30046) (Phase 2 of the merge-governance roll-out drafted on [BTCAAAAA-30038](/BTCAAAAA/issues/BTCAAAAA-30038#document-process-audit)). Supersedes the preliminary contract on [BTCAAAAA-30039](/BTCAAAAA/issues/BTCAAAAA-30039). Applies to every agent making code changes in this package.

Full contract lives in the repo-root [`/AGENTS.md` § Merge governance](../../AGENTS.md#merge-governance--required-for-all-code-changes). The clauses below are the operational summary; if these conflict with the root document, the root document wins.

### 1. Branch naming — one issue, one branch

```
git fetch origin
git switch -c fix/BTCAAAAA-NNN-kebab-slug origin/main
git rev-parse --abbrev-ref HEAD   # must equal fix/BTCAAAAA-NNN-kebab-slug
```

One issue → one branch. Use `feat/`, `chore/`, `docs/`, `test/`, or `refactor/` as the prefix depending on the verb in the issue title.

### 2. Single-owner rule

Once a branch carries the `BTCAAAAA-NNN` identifier, only that issue's assignee commits to it. Other agents open a follow-up issue with their own branch — they do not push commits onto a sibling's branch. When the workspace is shared and `HEAD` may rotate mid-task, isolate via `git worktree add /tmp/btc-NNN -b fix/BTCAAAAA-NNN-slug origin/main`.

### 3. Pre-commit working-tree check

Before `git add`, run `git rev-parse --abbrev-ref HEAD` and confirm it matches your issue branch. `scripts/lint-branch-name.sh` (repo-root) automates the branch-name validation. Failure mode this prevents: the [BTCAAAAA-30034](/BTCAAAAA/issues/BTCAAAAA-30034) token-gap chain that landed commits across three unrelated feature branches.

### 4. `Fix-SHA:` tag contract

Every closure comment includes exactly one line: `Fix-SHA: <40-char-sha>`. Regex: `^Fix-SHA: [0-9a-f]{40}$`. The SHA is the HEAD of the implementing branch at the time the comment is posted. The closure-gate routine ([BTCAAAAA-30040](/BTCAAAAA/issues/BTCAAAAA-30040)) parses it; missing or malformed lines auto-reopen the issue.

### 5. Ancestry self-check

Before marking `done`:

```
git fetch origin
git merge-base --is-ancestor <fix-sha> origin/main; echo rc=$?
```

`rc=0` → `done`. `rc≠0` → `in_review`, awaiting merge dispatch from CEO/RepoSteward ([BTCAAAAA-30041](/BTCAAAAA/issues/BTCAAAAA-30041)).

### 6. One issue, one PR

PR description references exactly one `BTCAAAAA-NNN`. Direct push to `origin/main` is FORBIDDEN.

### 7. Dev-server status update

Any agent switching the working tree off `main` MUST update the [dev-server-status document on BTCAAAAA-30031](/BTCAAAAA/issues/BTCAAAAA-30031#document-dev-server-status) within the same heartbeat.

### 8. Closure-comment template

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
<!-- END:merge-governance -->
