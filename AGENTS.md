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

# Branching Contract (mandatory for all code change)

Effective per [BTCAAAAA-30039](/BTCAAAAA/issues/BTCAAAAA-30039). Applies to every agent making code changes in this repo.

1. Every code-change issue starts with: `git fetch origin && git switch -c {type}/BTCAAAAA-{n}-{kebab-slug} origin/main`. Verify with `git rev-parse --abbrev-ref HEAD` before the first commit.
2. Direct push to `origin/main` is FORBIDDEN. All merges go through PR + RepoSteward (or CEO GH_TOKEN fallback) per the merge-dispatch flow.
3. Closure comments MUST include a `Fix-SHA: <40-char-sha>` line on its own. Machine-parseable; closure-gate routine reads this.
4. Issue PATCH `status=done` is conditional on `git merge-base --is-ancestor <Fix-SHA> origin/main` returning rc=0. The closure-gate routine will reopen on violation.
5. Dev-server checkout: any agent that switches the working tree to a non-main branch MUST update the [dev-server-status document on BTCAAAAA-30031](/BTCAAAAA/issues/BTCAAAAA-30031#document-dev-server-status) within the same heartbeat.
