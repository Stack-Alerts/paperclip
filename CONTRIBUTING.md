# Contributing to BTC Trade Engine PaperClip

## Setup

### Initial Repository Configuration

After cloning this repository, configure git hooks:

```bash
git config core.hooksPath .githooks
```

This is a one-time setup that enables the post-commit auto-push hook for the `main` branch.

### Git Hooks

This repository uses git hooks to enforce consistency and automate common tasks.

#### Auto-Push Hook (post-commit)

When you commit to the `main` branch, a post-commit hook automatically pushes your commit to `origin/main` within 60 seconds. This prevents race conditions where local commits diverge from the remote (see BTCAAAAA-29995 for context).

**What it does:**
- Runs automatically after every commit
- Only activates on the `main` branch
- Pushes to `origin/main` with a 30-second timeout
- Warns (but does not block) if push fails
- Silently succeeds on non-main branches

**How it works:**
The hook is located at `.githooks/post-commit` and is enabled by the git config above.

**Verification:**
To verify the hook is working correctly:
```bash
git commit --allow-empty -m "test: verify hook"
sleep 2
git fetch
git log origin/main..HEAD  # Should be empty if push succeeded
```

The commit should be pushed to origin/main within 3-5 seconds.

**Troubleshooting:**
If the hook doesn't run:
1. Verify the configuration: `git config core.hooksPath` (should output `.githooks`)
2. Verify the hook is executable: `ls -l .githooks/post-commit` (should show `x` permissions)
3. Check git's debug output: `GIT_TRACE=1 git commit --allow-empty -m "test"`

If pushes are failing:
- Check your network connection and SSH key setup
- Verify you have push permissions to `origin/main`
- The warning message will appear in your commit output when the hook runs

## Branch Strategy

- `main` - Production branch. All commits are automatically pushed to origin.
- `feature/*` - Feature branches for new functionality
- `fix/*` - Bug fix branches
- `refactor/*` - Refactoring branches
- `hotfix/*` - Emergency fixes

## Commit Messages

Follow the conventional commits format:
```
[TYPE]: Brief description

Types: feat, fix, refactor, perf, test, docs, chore, merge
```

Examples:
- `feat: add new user authentication`
- `fix: resolve memory leak in cache`
- `docs: update API documentation`

## Pre-commit Checklist

Before pushing, verify:
- No credentials, API keys, or tokens in any file
- Type hints on all public functions
- No `print()` debugging statements
- Tests pass locally

## Code Review

All PRs require review before merge. Link to related issues and provide context for reviewers.
