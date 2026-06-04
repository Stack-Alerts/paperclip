# Contributing to BTC Trade Engine PaperClip

## Setup

### Git Hooks

This repository uses git hooks to enforce consistency and automate common tasks.

#### Auto-Push Hook (post-commit)

When you commit to the `main` branch, a post-commit hook automatically pushes your commit to `origin/main` within 60 seconds. This prevents race conditions where local commits diverge from the remote.

**What it does:**
- Runs automatically after every commit
- Only activates on the `main` branch
- Pushes to `origin/main` asynchronously
- Warns (but does not block) if push fails
- Silently succeeds on non-main branches

**How it works:**
The hook is located at `.githooks/post-commit` and is registered via:
```bash
git config core.hooksPath .githooks
```

This configuration is set automatically when you clone the repository.

**Troubleshooting:**
If the hook doesn't run:
1. Verify the configuration: `git config core.hooksPath`
2. Verify the hook is executable: `ls -l .githooks/post-commit`
3. Check git's debug output: `GIT_TRACE=1 git commit --allow-empty -m "test"`

If pushes are failing:
- Check your network connection and SSH key setup
- Verify you have push permissions to `origin/main`
- The warning message will appear in your commit output

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
