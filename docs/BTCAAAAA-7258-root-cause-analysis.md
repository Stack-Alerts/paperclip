# BTCAAAAA-7258 — Root Cause Analysis: 1747→Audit Gap

## Summary

**False closure of BTCAAAAA-1747.** The issue was marked `done` at 07:29 despite
its own evidence document (committed at 07:05) explicitly flagging the
GITHUB_TOKEN credential gap as an unresolved blocker. Protection was never
applied and has remained absent through all subsequent attempts.

## Timeline

| Time | Event |
|---|---|
| 07:05 | 1747 evidence doc committed — flags PAT token as blocker |
| 07:29 | BTCAAAAA-1747 marked `done` (premature — blocker unresolved) |
| 09:27 | `apply-branch-protection.yml` committed (workflow approach attempted) |
| 09:27 | 1747 CI evidence doc pushed to main |
| 10:27 | Audit (BTCAAAAA-1348) finds `main` unprotected |
| 13:40 | YAML parsing fix for workflow |
| 18:12 | Enhanced payload + audit gate added |
| 18:18 | Idempotent PUT + RepoSteward assessment |
| 23:12 | workflow_dispatch + diagnostics added |
| 23:17 | Minimal payload (no checks) attempted |
| (now) | All 4 enforcement attempts failed — same credential gap |

## Reconciliation: Which hypothesis fits?

**Hypothesis 1: False closure** ✓ — CONFIRMED
- 1747 was marked done 2 hours before the workflow file was even created
- The evidence doc explicitly acknowledges the PAT blocker as unresolved
- No API call was ever made to set branch protection

**Hypothesis 2: Reverted** ✗ — REJECTED
- No evidence protection was ever applied (no API call succeeded)
- Nothing to revert

**Hypothesis 3: Scope mismatch** ✗ — REJECTED
- 1747's own spec lists the full required state (PR reviews, checks, admins, etc.)
- The scope was correct; execution failed

## Blocker (unchanged since 07:05)

The GITHUB_TOKEN (fine-grained PAT `github_pat_...`) lacks API-level access
to `Stack-Alerts/BTC-Trade-Engine-PaperClip`. It is authorized only for:
`AMD-debug`, `paperclip`, `zsh`. Additionally, the GitHub Actions runner's
built-in GITHUB_TOKEN lacks `administration: write` (org-level restriction or
non-admin actor).

## Automation Ready

`scripts/apply-branch-protection.sh` — two-step enforcer:
1. Basic protection (PR reviews, enforce admins, block force pushes)
2. Full protection with 7 required status checks

Run when a valid admin token is available:
```bash
gh auth login --with-token < /path/to/admin/token
./scripts/apply-branch-protection.sh
```
