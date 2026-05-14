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
