# Git & GitHub Push Workflow

This document defines the mandatory git workflow for the BTC Trade Engine repo.
All contributors (human and AI agents) follow these standards.

---

## 1. Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready code. Always green CI. |
| `feature/*` | New features or capabilities |
| `fix/*` | Bug fixes |
| `refactor/*` | Code restructuring without behavior change |
| `hotfix/*` | Urgent production fixes |
| `experimental/*` | Research or testing branches |

**Examples:** `feature/ma-crossover-strategy`, `fix/order-fill-handler`, `hotfix/daily-loss-limit-bypass`

---

## 2. Commit Message Format

```
[TYPE]: Brief description (50 chars max)

Optional detailed explanation of what changed and why.

- Change 1
- Change 2

Co-Authored-By: Paperclip <noreply@paperclip.ing>
```

**Commit Types:**

| Type | Use For |
|------|---------|
| `feat` | New feature or capability |
| `fix` | Bug fix or correction |
| `refactor` | Code restructuring without behavior change |
| `perf` | Performance improvement |
| `test` | Tests added or modified |
| `docs` | Documentation updates |
| `chore` | Build, config, or dependency changes |
| `merge` | Merge commits (auto-generated) |

Never use: `WIP`, `fix stuff`, `update`, `changes`.

---

## 3. Definition of Done — Push Checklist

Every issue marked `done` in Paperclip MUST have its work committed and pushed to GitHub.
Run this checklist before closing any Paperclip issue:

```bash
# 1. Pre-commit safety
python -m py_compile <changed_file>   # syntax valid
ruff check <changed_file>             # no lint errors

# 2. Verify working state
git status                             # understand dirty tree
git diff --stat HEAD                   # review unstaged changes

# 3. Stage and commit
git add <specific_files>              # never `git add .` blindly
git commit -m "fix(BTCAAAAA-XX): ..."

# 4. Push immediately after commit
git push origin main                   # or feature branch

# 5. Verify push succeeded
git log -1 origin/main                 # confirm remote is updated
```

---

## 4. Push Workflow (Standard)

```bash
# Before pushing
git log -n3 --oneline     # verify commits are correct
git status                 # verify no untracked surprises

# Push
git push origin <branch>

# Verify
git fetch origin
git log --oneline origin/main | head -5  # confirm remote matches local
```

**Important:** Run `git fetch origin` after pushing to refresh local remote-tracking refs.
Without this, `git status` may show "ahead by N commits" even when remote is up to date.

---

## 5. Merge Protocol (Feature Branches → main)

```bash
# 1. Verify source branch is clean
git status   # must be clean

# 2. Check for conflicts before merging
git merge --no-commit --no-ff <feature-branch>

# 3a. If conflicts: STOP — resolve conflicts, then commit
# 3b. If clean: execute merge
git merge -m "merge: <feature-branch> into main"

# 4. Push
git push origin main

# 5. Verify
git log --oneline | head -3
```

**Never fast-forward merge feature branches into main.** Always use `--no-ff`.

---

## 6. Pre-Commit Safety Checklist

Block any PR or commit that fails:

- [ ] Code syntax valid: `python -m py_compile <file>` passes
- [ ] No linting errors (`ruff check` or `flake8` passes)
- [ ] No `print()` debugging statements left in code
- [ ] No hardcoded file paths (use variables or config)
- [ ] **No credentials, API keys, or tokens in any file**
- [ ] Type hints present on all public functions
- [ ] Comments explain WHY, not WHAT
- [ ] NautilusTrader type compliance: no bare `float` for Price/Quantity/Money

---

## 7. Keeping Remote Tracking Refs Fresh

A common issue: `git status` shows "ahead by N commits" even after pushing.
This happens when local remote-tracking refs are stale.

**Fix:**
```bash
git fetch origin
git status   # now shows accurate state
```

**Root cause:** `git push` updates the remote but does not always refresh the local
remote-tracking ref if there is a race condition or background pull. Always run
`git fetch` after pushing to verify the push succeeded and refs are current.

---

## 8. Remote URL — Use SSH, Not HTTPS

The `BTC_Engine_v3` repo remote must be configured with the SSH URL, not HTTPS.
HTTPS remotes for `github.com/Stack-Alerts/*` return `403 Write access not granted`
even with a valid token because the SSH key is the authorised credential.

**Check and fix:**
```bash
git remote -v   # should show git@github.com:Stack-Alerts/BTC_Engine_v3.git

# If it shows https:// — fix it:
git remote set-url origin git@github.com:Stack-Alerts/BTC_Engine_v3.git
```

The `BTC-Trade-Engine-PaperClip` repo is already on SSH and is unaffected.

---

## 9. Secrets Policy

- `.env` is in `.gitignore` — never commit it
- `.env.example` contains only placeholder values — safe to commit
- Any real credential found in git history = treat as compromised, escalate to SecurityAnalyst + CTO immediately
- Review `git diff --cached` before every commit to catch accidental credential inclusion

---

## 9. Stale Branch Cleanup

RepoSteward audits branches > 30 days old without commits.
Merged feature branches are deleted after merge to keep the remote clean:

```bash
# Delete merged feature branch locally and remotely
git branch -d feature/my-feature
git push origin --delete feature/my-feature
```

---

## 10. Agent Push Protocol (Paperclip AI Agents)

When a Paperclip agent completes work and marks an issue `done`:

1. Commit with proper type prefix and Paperclip issue reference: `fix(BTCAAAAA-XX): ...`
2. Include `Co-Authored-By: Paperclip <noreply@paperclip.ing>` in commit body
3. Push immediately: `git push origin main`
4. Run `git fetch origin && git log -1 origin/main` to confirm remote updated
5. Only then mark the Paperclip issue as `done`

This ensures GitHub always reflects the actual state of completed work.

---

## 11. Automated Push-Sync Gate (BTCAAAAA-76)

Two enforcement mechanisms are installed to prevent the "committed but not pushed" failure mode.

### 11a. post-commit Hook (auto-push)

A `post-commit` git hook automatically pushes the current branch to `origin` after
every commit. It is installed in `.git/hooks/post-commit`.

**Install on a fresh clone:**
```bash
cp scripts/hooks/post-commit .git/hooks/post-commit
chmod +x .git/hooks/post-commit
```

**Opt out for a single commit (emergency only):**
```bash
NO_AUTO_PUSH=1 git commit -m "feat: ..."
```

The hook is non-blocking: if `git push` fails it prints a warning and exits 0 so the
commit is not aborted. Agents must resolve push failures before closing any issue.

### 11b. verify-push-sync.sh (pre-close gate)

Run this script **before** marking any Paperclip issue as `done`:

```bash
scripts/verify-push-sync.sh
```

Exit codes:
- `0` — remote is in sync (pushed successfully if needed)
- `1` — push failed or remote is ahead (diverged)
- `2` — uncommitted changes present (commit first)

**Check-only mode** (no push, just report):
```bash
scripts/verify-push-sync.sh --check-only
```

**Revised agent close sequence:**
1. Commit with proper type prefix + issue ref + Co-Authored-By footer
2. Run `scripts/verify-push-sync.sh` — gate must exit 0
3. Only then mark the Paperclip issue as `done`
