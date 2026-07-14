# AGENTS.md

Guidance for human and AI contributors working in this repository.

## 1. Purpose

Paperclip is a control plane for AI-agent companies.
The current implementation target is V1 and is defined in `doc/SPEC-implementation.md`.

## 2. Read This First

Before making changes, read in this order:

1. `doc/GOAL.md`
2. `doc/PRODUCT.md`
3. `doc/SPEC-implementation.md`
4. `doc/DEVELOPING.md`
5. `doc/DATABASE.md`

`doc/SPEC.md` is long-horizon product context.
`doc/SPEC-implementation.md` is the concrete V1 build contract.

## 3. Repo Map

- `server/`: Express REST API and orchestration services
- `ui/`: React + Vite board UI
- `packages/db/`: Drizzle schema, migrations, DB clients
- `packages/shared/`: shared types, constants, validators, API path constants
- `packages/adapters/`: agent adapter implementations (Claude, Codex, Cursor, etc.)
- `packages/adapter-utils/`: shared adapter utilities
- `packages/plugins/`: plugin system packages
- `doc/`: operational and product docs

## 4. Dev Setup (Auto DB)

Use embedded PGlite in dev by leaving `DATABASE_URL` unset.

```sh
pnpm install
pnpm dev
```

This starts:

- API: `http://localhost:3100`
- UI: `http://localhost:3100` (served by API server in dev middleware mode)

Quick checks:

```sh
curl http://localhost:3100/api/health
curl http://localhost:3100/api/companies
```

Reset local dev DB:

```sh
rm -rf data/pglite
pnpm dev
```

## 5. Core Engineering Rules

1. Keep changes company-scoped.
Every domain entity should be scoped to a company and company boundaries must be enforced in routes/services.

2. Keep contracts synchronized.
If you change schema/API behavior, update all impacted layers:
- `packages/db` schema and exports
- `packages/shared` types/constants/validators
- `server` routes/services
- `ui` API clients and pages

3. Preserve control-plane invariants.
- Single-assignee task model
- Atomic issue checkout semantics
- Approval gates for governed actions
- Budget hard-stop auto-pause behavior
- Activity logging for mutating actions

4. Do not replace strategic docs wholesale unless asked.
Prefer additive updates. Keep `doc/SPEC.md` and `doc/SPEC-implementation.md` aligned.

5. Keep repo plan docs dated and centralized.
When you are creating a plan file in the repository itself, new plan documents belong in `doc/plans/` and should use `YYYY-MM-DD-slug.md` filenames. This does not replace Paperclip issue planning: if a Paperclip issue asks for a plan, update the issue `plan` document per the `paperclip` skill instead of creating a repo markdown file.

6. Attach inspectable generated artifacts.
When your task produces a user-inspectable deliverable file, follow the Paperclip skill's "Generated Artifacts and Work Products" workflow before final disposition. In this repo, prefer the self-contained skill helper at `skills/paperclip/scripts/paperclip-upload-artifact.sh` so the file is available through the Paperclip API, create/update an artifact work product when the file is the deliverable, link the uploaded artifact in the final issue comment, and then set status. Do not rely on local filesystem paths as the only access path. If an important file intentionally remains workspace-only, create/update a work product with `metadata.resourceRef.kind: "workspace_file"` and a workspace-relative path, then name that work product and path in the final comment. Treat browse/search as a fallback for recovering workspace files, not the preferred deliverable path. See `doc/AGENT-ARTIFACTS.md` for details and `.mp4`/`.webm` examples.

## 6. Database Change Workflow

When changing data model:

1. Edit `packages/db/src/schema/*.ts`
2. Ensure new tables are exported from `packages/db/src/schema/index.ts`
3. Generate migration:

```sh
pnpm db:generate
```

4. Validate compile:

```sh
pnpm -r typecheck
```

Notes:
- `packages/db/drizzle.config.ts` reads compiled schema from `dist/schema/*.js`
- `pnpm db:generate` compiles `packages/db` first

## 7. Verification Before Hand-off

Default local/agent test path:

```sh
pnpm test
```

This is the cheap default and only runs the Vitest suite. Browser suites stay opt-in:

```sh
pnpm test:e2e
pnpm test:release-smoke
```

Run the browser suites only when your change touches them or when you are explicitly verifying CI/release flows.

For normal issue work, run the smallest relevant verification first. Do not default to repo-wide typecheck/build/test on every heartbeat when a narrower check is enough to prove the change.

Run this full check before claiming repo work done in a PR-ready hand-off, or when the change scope is broad enough that targeted checks are not sufficient:

```sh
pnpm -r typecheck
pnpm test:run
pnpm build
```

If anything cannot be run, explicitly report what was not run and why.

### 7.4 Fix-SHA Closure Gate

When a company has `closureGateFixSha` set to `enforce` on its record, an
agent (any role — engineer, manager, …) cannot PATCH an issue to
`status: "done"` without including a `Fix-SHA: <40-hex-sha>` line in
the closure comment (optionally followed by `Fix-Target: <branch>`).
If the SHA is not reachable on the issue's configured remote branch,
the request is rejected with `422 Unprocessable Entity`.

The gate has three modes, settable per company via
`PATCH /api/companies/{companyId}` with `{ "closureGateFixSha": "..." }`:

- `off` (default) — no enforcement, no warnings.
- `advisory` — closure is allowed regardless, but missing / unreachable
  SHAs are logged as warnings.
- `enforce` — closure is rejected with `422` and a `details.reason`
  of `missing_fix_sha` or `unreachable_sha`.

Board (user) actors are never gated. The contract and the
mode-behavior table live in [doc/CLI.md → Per-company config flags](doc/CLI.md#per-company-config-flags).

Agent contract when `enforce` is on:

- Include a `Fix-SHA: <40-hex-sha>` line in your closure comment body.
- Optionally include `Fix-Target: <branch>` on the next line; defaults
  to `main` if omitted.
- Optionally include `Fix-Repo: <url>` on its own line to override the
  `git ls-remote` target URL for this closure. Use this when the issue
  inherits an `executionWorkspaces.repoUrl` that is *not* the repo where
  the fix actually landed (e.g. Paperclip-side rollout decisions on a
  different fork). Absent the line, the gate uses the workspace's
  configured `repoUrl`. A malformed or unreachable `Fix-Repo:` URL
  produces the same `422` (`details.reason = "git_error"`) the gate
  would emit for an unreachable SHA on the default repo.
- The SHA must be reachable on `<repo-url>@<target>` of the issue's
  configured execution workspace — or on the `Fix-Repo:` override if
  one is present (`git ls-remote --quiet` is used under the hood,
  results are cached for 60s).
- If you have no comment body, the gate falls back to the most recent
  persisted comment on the issue (desc, limit 1).

## 8. API and Auth Expectations

- Base path: `/api`
- Board access is treated as full-control operator context
- Agent access uses bearer API keys (`agent_api_keys`), hashed at rest
- Agent keys must not access other companies

When adding endpoints:

- apply company access checks
- enforce actor permissions (board vs agent)
- write activity log entries for mutations
- return consistent HTTP errors (`400/401/403/404/409/422/500`)

## 9. UI Expectations

- Keep routes and nav aligned with available API surface
- Use company selection context for company-scoped pages
- Surface failures clearly; do not silently ignore API errors

## 10. Pull Request Requirements

When creating a pull request (via `gh pr create` or any other method), you **must** read and fill in every section of [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md). Do not craft ad-hoc PR bodies — use the template as the structure for your PR description. Required sections:

- **Thinking Path** — trace reasoning from project context to this change (see `CONTRIBUTING.md` for examples)
- **What Changed** — bullet list of concrete changes
- **Verification** — how a reviewer can confirm it works
- **Risks** — what could go wrong
- **Model Used** — the AI model that produced or assisted with the change (provider, exact model ID, context window, capabilities). Write "None — human-authored" if no AI was used.
- **Checklist** — all items checked

## 11. Definition of Done

A change is done when all are true:

1. Behavior matches `doc/SPEC-implementation.md`
2. Typecheck, tests, and build pass
3. Contracts are synced across db/shared/server/ui
4. Docs updated when behavior or commands change
5. PR description follows the [PR template](.github/PULL_REQUEST_TEMPLATE.md) with all sections filled in (including Model Used)

## 11a. Fork-Specific: HenkDz/paperclip

This is a fork of `paperclipai/paperclip` with QoL patches and a **built-in** Hermes adapter story on branch `feat/externalize-hermes-adapter` ([tree](https://github.com/HenkDz/paperclip/tree/feat/externalize-hermes-adapter)).

### Branch Strategy

- `feat/externalize-hermes-adapter` now ships `hermes_local` and `hermes_gateway` as built-in core adapters.
- Older fork branches may still document plugin-only Hermes; treat this file as authoritative for the current branch.

### Hermes (built-in)

- `hermes_local` is available without Adapter manager installation and runs the local Hermes CLI.
- `hermes_gateway` is available without Adapter manager installation and calls an already-running Hermes API server.
- Operators may still install external Hermes packages through Adapter manager to override/shadow the built-ins.
- Optional: `file:` entry in `~/.paperclip/adapter-plugins.json` remains useful for local development of override packages.

### Local Dev

- Fork runs on port 3101+ (auto-detects if 3100 is taken by upstream instance)
- `npx vite build` hangs on NTFS — use `node node_modules/vite/bin/vite.js build` instead
- Server startup from NTFS takes 30-60s — don't assume failure immediately
- Kill ALL paperclip processes before starting: `pkill -f "paperclip"; pkill -f "tsx.*index.ts"`
- Vite cache survives `rm -rf dist` — delete both: `rm -rf ui/dist ui/node_modules/.vite`

### Fork QoL Patches (not in upstream)

These are local modifications in the fork's UI. If re-copying source, these must be re-applied:

1. **stderr_group** — amber accordion for MCP init noise in `RunTranscriptView.tsx`
2. **tool_group** — accordion for consecutive non-terminal tools (write, read, search, browser)
3. **Dashboard excerpt** — `LatestRunCard` strips markdown, shows first 3 lines/280 chars

### Plugin System

PR #2218 (`feat/external-adapter-phase1`) adds external adapter support. See root `AGENTS.md` for full details.

- Adapters can be loaded as external plugins via `~/.paperclip/adapter-plugins.json`
- The plugin-loader should have ZERO hardcoded adapter imports — pure dynamic loading
- `createServerAdapter()` must include ALL optional fields (especially `detectModel`)
- Built-in UI adapters can shadow external plugin parsers; external override pause/resume should restore the built-in parser.
- Reference external adapters: Droid (npm); Hermes can also be tested as an override package.

## 12. Golden Snapshot Branch Workflow (BTC Trade Engine)

The worktree `~/paperclip-btcaaaaa-main` is snapshotted into
`Stack-Alerts/PaperClip_Mods` (the private paperclip-mods fork) on
`golden-{UTC}` branches for emergency recovery.

### Branch types
- `golden-YYYY-MM-DD-HHMM`            — mutable; auto-updated by a
  github-actions bot that propagates backup-plugin fixes from this worktree.
- `golden-frozen-YYYY-MM-DD-HHMM`     — immutable; branch protection enforced
  (see below) so even the bot cannot push.

UTC timestamp is captured at the moment the rsync finishes. The Z prefix is
implied (not literal in the branch name).

### Snapshot contents (per branch)
- Full rsync of `~/paperclip-btcaaaaa-main` rooted at the branch root.
- Includes: source code, `dist/`, `pnpm-lock.yaml`, `AGENTS.md`,
  `.paperclip/config.json`, all `packages/plugins/*`.
- Excludes: `node_modules/`, `secrets/master.key`, `secrets/.env`,
  `.paperclip/.env` (contains `PAPERCLIP_AGENT_JWT_SECRET`), `data/`,
  `logs/`, `.paperclip-wip-backup-*/`, `err.txt`, `pnpm-lock.yaml.bak`,
  `pr.json`, `report/`, `screenshots/`, `releases/`.
- A `GOLDEN-SNAPSHOT.md` sits at the branch root with: source commit +
  timestamp, build procedure, plugin reference (versions and what each does),
  scheduled jobs, restore options, update procedure.

### Updating an existing golden branch
**Never automatic.** Only the user requests. Use:

```bash
cd /home/sirrus/paperclip-mods
git checkout <branch>
find . -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
rsync -a --exclude='node_modules' --exclude='.git' \
    --exclude='.paperclip-wip-backup-*' --exclude='err.txt' \
    --exclude='pnpm-lock.yaml.bak' \
    /home/sirrus/paperclip-btcaaaaa-main/ ./
# Update GOLDEN-SNAPSHOT.md with new commit SHA + timestamp
git add -A
git add -f dist/ packages/*/dist/ server/dist/ cli/dist/ ui/dist/   # force-add if .gitignore excludes
git commit -m "golden snapshot: paperclip-btcaaaaa-main @ <sha> (<UTC>)"
git push -u origin <branch>
```

### Branch protection (for `golden-frozen-*` only)
Apply once per new frozen branch via `gh` CLI as `Stack-Alerts` (token in keyring):

```bash
gh api -X PUT \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  repos/Stack-Alerts/PaperClip_Mods/branches/<BRANCH>/protection \
  --input <(echo '{
    "required_status_checks": null,
    "enforce_admins": true,
    "required_pull_request_reviews": {
      "dismiss_stale_reviews": true,
      "require_code_owner_reviews": false,
      "required_approving_review_count": 1
    },
    "restrictions": null,
    "required_linear_history": true,
    "allow_force_pushes": false,
    "allow_deletions": false,
    "block_creations": false,
    "required_conversation_resolution": false,
    "lock_branch": false,
    "allow_fork_syncing": false
  }')
```

Then verify by attempting `git push origin <branch>` as admin — must be
rejected with `GH006: Protected branch hook declined`. Revert any test commit
with `git reset --hard HEAD~1`.

The github-actions bot's direct push will fail with the same error, so the
frozen branch stays at its committed state.

### Restoring from a golden branch
1. `git clone -b <branch> git@github.com:Stack-Alerts/PaperClip_Mods.git paperclip-btcaaaaa-main`
2. `pnpm install --frozen-lockfile`
3. `pnpm --filter @paperclipai/{shared,plugin-sdk,server,ui} build`
4. Generate fresh secrets: `export PAPERCLIP_AGENT_JWT_SECRET=$(openssl rand -hex 32)`
5. `./start.sh`

The DB is not in the git branch. To restore the database:
- `./scripts/recovery.sh doctor` for smart flow
- `./scripts/recovery.sh restore <id>` from `/home/sirrus/paperclip-snapshots/`
- `/home/sirrus/.paperclip/scripts/restore-from-drive.sh list` for offsite gdrive

See `GOLDEN-SNAPSHOT.md` on any golden branch for the full restore procedure.

## 13. Safe Development Process (BTC Trade Engine)

Per-paperclip-mods work — every code change in `paperclip-btcaaaaa-main`
must flow through this gate chain. The scripts enforce it; this section
documents what each step guarantees.

### 13.1 Lifecycle (single agent, single issue)

```
  ┌───────────────────────┐   ┌──────────────────────────┐   ┌────────────────────┐
  │ 1. safedev preflight  │ → │ 2. implement + commit    │ → │ 3. premerge gate   │
  │    scripts/agent-     │   │    pre/post-merge hooks  │   │    scripts/agent-  │
  │    safedev.sh         │   │    auto-snapshot         │   │    premerge-check  │
  └───────────────────────┘   └──────────────────────────┘   └────────────────────┘
                                                                      │
                                                                      ▼
                                                            ┌────────────────────┐
                                                            │ 4. push to merge   │
                                                            │    queue (gate     │
                                                            │    pre-push hook)  │
                                                            └────────────────────┘
```

### 13.2 Step 1 — `scripts/agent-safedev.sh`

Run BEFORE touching any code. The script:

1. Verifies the worktree is `paperclip-btcaaaaa-main`.
2. Refuses to run if the working tree is dirty (commit or stash first).
3. Fetches the latest from `$REMOTE` (default `fork`).
4. Verifies `HEAD` contains the latest `$REMOTE/btcaaaaa-main`
   (override with `--base <remote/ref>` or `PAPERCLIP_SAFEDEV_BASE_REF`).
5. Calls `scripts/recovery.sh snapshot --no-upload` and parses the
   snapshot ID from the output.
6. Verifies the snapshot directory exists at
   `/home/sirrus/paperclip-snapshots/$SNAPSHOT_ID/`.
7. Writes a receipt to `$GIT_DIR/paperclip-safedev.receipt` capturing:
   `head`, `base_ref`, `base_sha`, `branch`, `snapshot_id`, `issue_ref`,
   `completed_at`.

```bash
./scripts/agent-safedev.sh                       # full preflight
./scripts/agent-safedev.sh --remote <name>       # override remote (default: fork)
./scripts/agent-safedev.sh --base <remote/ref>   # override base
./scripts/agent-safedev.sh --issue <ref>         # stamp issue ref in receipt
```

Exit codes: `0` ok · `1` invalid/wrong worktree · `2` dirty tree ·
`3` fetch/base resolution · `4` snapshot failed · `5` branch behind base.

Paste the resulting status block into the Paperclip issue comment so the
board can see the pre-implementation recovery point.

### 13.3 Step 2 — implement and commit

- Work in the Paperclip-provisioned worktree (already isolated per agent).
- Each `git commit` and `git merge` fires the `pre-commit` / `post-merge`
  hooks, which background-snapshot via `recovery.sh snapshot --no-upload`.
- Snapshots are non-blocking and hardlinked into
  `/home/sirrus/paperclip-snapshots/` so disk cost stays flat.
- Keep the working tree clean at the end of each commit cycle
  (`git status --short` empty) so the premerge gate can run.

### 13.4 Step 3 — `scripts/agent-premerge-check.sh`

Run BEFORE pushing to the merge queue. The script:

1. Verifies the worktree is `paperclip-btcaaaaa-main`.
2. Refuses to run if the working tree is dirty.
3. Re-fetches `$REMOTE` and re-checks the base-ref ancestor invariant.
4. Reads `$GIT_DIR/paperclip-safedev.receipt` and rejects if the receipt
   is missing, incomplete, or points at a base ref / SHA that no longer
   matches the live state.
5. Verifies the recovery snapshot directory still exists.
6. Runs, in order, with all output captured to
   `$GIT_DIR/paperclip-premerge/<short-head>-<stamp>.log`:
   - `git diff --check $BASE_REF...HEAD` (whitespace audit)
   - `pnpm test` (iteration 1 of 2)
   - `pnpm test` (iteration 2 of 2) — **required**, per the
     "iterate tests at least twice" mandate.
   - `pnpm -r typecheck`
   - `pnpm build`
7. Verifies HEAD and the working tree are unchanged after the checks.
8. Writes `$GIT_DIR/paperclip-premerge.receipt` capturing `head`,
   `base_ref`, `base_sha`, `snapshot_id`, `test_iterations=2`,
   `typecheck=passed`, `build=passed`, `log`, `completed_at`.

```bash
./scripts/agent-premerge-check.sh
./scripts/agent-premerge-check.sh --remote <name>      # override remote
./scripts/agent-premerge-check.sh --base <remote/ref>  # override base
```

Exit codes: `0` ok · `1` invalid · `2` dirty tree · `3` fetch/base ·
`4` base not ancestor · `5` safedev receipt / snapshot invalid ·
`6` HEAD or tree drifted while checks were running.

If any check fails, the receipt is NOT written. Fix the issue, commit
the fix, and re-run the gate.

### 13.5 Step 4 — push to the merge queue

`scripts/git-hooks/pre-push` is a `git` hook installed by
`scripts/git-hooks/install.sh`. For any push to `fork/btcaaaaa-main` or
`fork/main`:

1. Refuses to push unless `$GIT_DIR/paperclip-premerge.receipt` exists.
2. Refuses unless the receipt's `head=` matches `git rev-parse HEAD`.

Pushes to **other refs** (feature branches, PR heads, golden branches)
are unaffected — only the merge queue is gated.

```bash
# install hooks once per worktree:
./scripts/git-hooks/install.sh

# verify hooks are wired:
ls -l "$(git rev-parse --git-dir)/hooks/" | grep -E 'pre-(commit|push)|post-merge'
```

If the hook refuses the push, run the premerge gate first:
```bash
./scripts/agent-premerge-check.sh
git push fork <branch>:<target>
```

### 13.6 Receipt chain invariants

- The safedev receipt must predate the implementation (snapshot ID
  matches a directory under `/home/sirrus/paperclip-snapshots/`).
- The premerge receipt must descend from the safedev HEAD
  (`git merge-base --is-ancestor safedev.head HEAD`).
- Re-running `agent-safedev.sh` overwrites the safedev receipt; re-run
  the premerge gate too so both receipts agree on HEAD.
- Both receipts are stored in `$(git rev-parse --git-dir)/` and are
  intentionally **not** tracked in git. They are per-worktree state,
  not source code.

### 13.7 Recovering from a failed gate

- If `pnpm test` fails twice: fix the underlying issue, recommit, rerun.
- If `pnpm -r typecheck` fails: same.
- If `pnpm build` fails: same.
- If the safedev receipt is missing: re-run `scripts/agent-safedev.sh`.
- If the premerge hook rejects the push and the safedev receipt is
  stale: re-run `scripts/agent-safedev.sh`, recommit (so the snapshot
  captures the new HEAD), then re-run `scripts/agent-premerge-check.sh`.
- If disk space is tight: `scripts/recovery.sh prune` removes snapshots
  older than the configured retention window; do not delete snapshot
  directories by hand — the directory name encodes the recovery ID the
  gate verifies against.
