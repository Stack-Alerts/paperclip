# BTCAAAAA-7283 — Blocker Report

## Status: BLOCKED

**Assigned to**: RepoSteward
**Priority**: Critical
**Blocked by**: Insufficient GitHub token permissions

## Blocker

The current `GITHUB_TOKEN` (fine-grained PAT `github_pat_11AUSXZKI...`) **cannot create repositories** on GitHub. The target repo `Stack-Alerts/BTC-Trade-Engine-PaperClip` does not exist (HTTP 404), and the PAT lacks the `createRepository` scope/permission.

## Required Permissions

To unblock, a token with the following is needed:

| Scope | Purpose |
|-------|---------|
| `repo` (full) or `Administration: Write` | Create the repository |
| `Secrets: Write` | Store the GITHUB_TOKEN secret post-creation |
| `Contents: Write` | Push the local codebase |

**Recommended**: Classic PAT with `repo` scope (easiest for initial setup), OR a fine-grained PAT with:
- Repository access: `All repositories` (or ability to create new)
- Permissions: `Administration: Write`, `Contents: Write`, `Secrets: Write`, `Metadata: Read`

## Unblock Path

### Option A: Classic PAT (Recommended for bootstrap)

1. Create a classic PAT at https://github.com/settings/tokens with `repo` scope
2. Export as `export GITHUB_TOKEN=<new-token>`
3. Then run:
   ```
   gh repo create Stack-Alerts/BTC-Trade-Engine-PaperClip --private --push --source .
   ```
4. Post-creation, create a fine-grained PAT scoped to only this repo
5. Store the fine-grained PAT as `GITHUB_TOKEN` secret in the repo

### Option B: Fine-grained PAT with adequate permissions

1. Create a fine-grained PAT at https://github.com/settings/tokens?type=beta with:
   - Repository access: `All repositories`
   - Permissions: `Administration: Write`, `Contents: Write`, `Secrets: Write`
2. Set as `GITHUB_TOKEN` environment variable
3. Run repo creation + push steps

### Option C: Manual repo creation

1. Create repo via GitHub UI at https://github.com/new
   - Owner: `Stack-Alerts`
   - Repository name: `BTC-Trade-Engine-PaperClip`
   - Visibility: Private
2. Then RepoSteward can proceed with PAT provisioning and secret storage

## Escalation

Per escalation policy (2026-05-12): GitHub admin access/repo permissions → RepoSteward; locked module → CTO (escape hatch). Since the token capability gap prevents RepoSteward from completing, this is escalated to CTO.

## Local Repo Status

- Working tree: Modified (unstaged changes in docs/, scripts/, src/)
- Remote: **No remote configured** (`.git/config` has no `[remote "origin"]`)
- Branch: `main`
- Commits: 5 recent commits present (latest: `cd326986`)
- Stale branches on disk: `backup-before-env-purge-7257`, `feature/BTCAAAAA-700-qt-ui-tests-ci-job`, `fix/BTCAAAAA-929-weight-backfill-repair-harden-preview-threshold`, `fix/btcaaaaa-2182-lock-gate-exception`

## Next Action

Once unblocked (new token provisioned), RepoSteward will:

1. `git remote add origin https://github.com/Stack-Alerts/BTC-Trade-Engine-PaperClip.git`
2. `gh repo create Stack-Alerts/BTC-Trade-Engine-PaperClip --private --push --source .`
3. Create fine-grained PAT scoped to the new repo
4. `gh secret set GITHUB_TOKEN --repo Stack-Alerts/BTC-Trade-Engine-PaperClip --body <pat>`
5. Verify: `gh secret list -R Stack-Alerts/BTC-Trade-Engine-PaperClip`
6. Close issue BTCAAAAA-7283
