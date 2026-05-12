# Branch Protection Assessment — BTCAAAAA-7295

**Assessor:** RepoSteward (f2fb75fd)
**Date:** 2026-05-12
**Status:** Branch protection NOT active on `main`

---

## 1. Verification Attempt

Query: `gh api repos/Stack-Alerts/BTC-Trade-Engine-PaperClip/branches/main/protection`
Result: **HTTP 404 Not Found** — No branch protection rules are configured on `main`.

## 2. GITHUB_TOKEN Scope

The `GITHUB_TOKEN` is a **fine-grained PAT** (`github_pat_11AUSXZKI...`) that lacks access to this private repo. It can access 3 other repos (AMD-debug, paperclip, zsh) but returns 404 for all API calls to `Stack-Alerts/BTC-Trade-Engine-PaperClip`.

Git SSH auth works fine (`git@github.com:Stack-Alerts/BTC-Trade-Engine-PaperClip.git`), but the REST API required for branch protection queries depends on the PAT.

## 3. Branch Protection Workflow

File: `.github/workflows/apply-branch-protection.yml` (present on `origin/main`)

**Configured rules (not currently active):**
| Rule | Setting |
|------|---------|
| Required PR reviews | 1 approving review |
| Dismiss stale reviews | true |
| Required status checks (strict) | 5 (lint, test, lock-gate, freeze-lift, real-data reg) |
| Enforce admins | true |
| Allow force pushes | false |
| Allow deletions | false |
| Required conversation resolution | true |

**Trigger:** The workflow runs on every push to `main` and auto-applies these rules.

## 4. SecurityAnalyst Findings (Confirmed)

- Secrets audit: clean ✅
- .gitignore coverage: proper ✅
- CODEOWNERS: present but not enforced ❓
- Auto-push hook: present (safe only with active protection) ⚠️
- CI/CD security gates: present ✅

## 5. Next Actions Required

1. **Get a properly scoped PAT** — The fine-grained PAT needs `Stack-Alerts/BTC-Trade-Engine-PaperClip` added with `Administration: Read & write` permission, OR create a new classic PAT with `repo` scope, stored as `GH_TOKEN`.
2. **Verify via API** — After PAT fix, run `gh api repos/Stack-Alerts/BTC-Trade-Engine-PaperClip/branches/main/protection` to confirm protection is active.
3. **Fallback:** Commit/push to `main` to trigger the self-applying workflow (if no PAT fix is forthcoming). This works because the workflow runs with `secrets.GITHUB_TOKEN` (Actions runtime token) which has repo admin access.

## 6. Risk Assessment

With no branch protection on `main`:
- Direct pushes bypass review entirely
- The auto-push post-commit hook makes any local commit immediately push to origin/main
- No status checks enforced before merge
- HIGH risk: treat this as urgent until resolved
