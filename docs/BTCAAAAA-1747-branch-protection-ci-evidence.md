# BTCAAAAA-1747: Branch Protection + CI Evidence

## Status

- Issue: BTCAAAAA-1747 (W1: GitHub admin — branch protection + CI URL evidence)
- Unblocks: BTCAAAAA-1486
- Priority: Critical
- Agent: RepoSteward (f2fb75fd-a40d-4ee9-a7d0-6920808d2c4c)

## Branch Protection Specification for `main`

Per GITHUB_EXPERT protocol, the following branch protection rules must be applied to `main`:

| Setting | Required | Rationale |
|---|---|---|
| Require PR review | Yes | No direct pushes to main |
| Required approving reviews | 1 | Minimum code review |
| Dismiss stale reviews | Yes | New commits invalidate old approvals |
| Require status checks | Yes | All CI must pass before merge |
| Status checks required | All 9 workflows | See inventory below |
| Require up-to-date branches | Yes | Prevents merge skew |
| Require conversation resolution | Yes | All comments resolved |
| Enforce for admins | Yes | No exceptions |
| Allow force pushes | No | Prohibited |
| Allow deletions | No | Prohibited |

### Implementation Blocker

GITHUB_TOKEN (fine-grained PAT) lacks API access to this repo.
SSH git access works, but all REST API endpoints return 404.

**Fix**: Create a PAT with `Administration: Read/Write` + `Contents: Read/Write`
permissions granted to `Stack-Alerts/BTC-Trade-Engine-PaperClip`,
or use a classic PAT with `repo` scope.

Once fixed, apply with:
```
gh api repos/Stack-Alerts/BTC-Trade-Engine-PaperClip/branches/main/protection \
  --method PUT \
  --input branch-protection-settings.json
```

## CI Workflow Inventory

All 9 workflows in `.github/workflows/`:

### CI Gateway Workflows (run on push/PR to main)

| Workflow | File | Trigger | Purpose |
|---|---|---|---|
| Lint | `lint.yml` | push/PR main | Ruff T201 + DTZ003 checks |
| Test & Coverage | `test.yml` | push/PR main | pytest + coverage gate (20%) + real-data regression |
| Module Lock Gate | `lock-gate.yml` | push/PR main | Concurrent module lock prevention |

### Worker Workflows (scheduled / event-driven)

| Workflow | File | Cadence | Purpose |
|---|---|---|---|
| Blast Radius | `blast-radius-worker.yml` | every 5min | fix→in_review detection + reports |
| Impact Gate | `impact-gate-worker.yml` | every 5min | Gate on in_review fixes |
| Touch Index Bug | `touch-index-bug-worker.yml` | every 15min | Bug file ref ingestion |
| Touch Index FR | `touch-index-fr-worker.yml` | every 15min | FDR file ref ingestion |
| Stale Run Backfill | `backfill-close-stale-runs.yml` | hourly | Auto-close stale runs |
| OpenCode Watchdog | `opencode-watchdog.yml` | every 15min | Kill hanging processes |

### CI Base URL

```
https://github.com/Stack-Alerts/BTC-Trade-Engine-PaperClip/actions
```

## Repository Health

### Stale Branches

| Branch | Last Commit | Recommendation |
|---|---|---|
| `feature/BTCAAAAA-700-qt-ui-tests-ci-job` | `04c66d7 docs(qa)` | Evaluate for completeness or delete |
| `fix/BTCAAAAA-929-weight-backfill-repair-harden-preview-threshold` | `3eb50f9 fix` | Delete — appears merged |

### Active Branches

| Branch | Status |
|---|---|
| `main` | Up to date with origin |
| No other local branches | Clean |

## Deliverables Status

- [x] Branch protection rules specified
- [x] CI workflow inventory documented (9 workflows)
- [ ] BLOCKED: API branch protection application (needs PAT with admin scope)
- [ ] BLOCKED: CI run URLs (needs PAT with actions:read scope)
