<!-- BEGIN:phase-scope -->
## Phase scope (set by board on BTCAAAAA-29339 — effective 2026-05-20)

This phase is **webui-only**. Active development is restricted to `packages/web-ui/`.
The web-ui must replicate all functionality of the desktop client (PyQt) — that is the phase deliverable.

Hard rules:
- Do not edit `src/` (backend Python), `tests/` outside webui's own `__tests__`, `scripts/`, `deploy/`, `alembic/`, `docs/`, or any PyQt files anywhere in the repo.
- Backend touches require a board-approved cross-scope ticket whose description names the specific file or subtree being opened.
- Each window has its own Paperclip project; agents assigned to a project may only write within their project's `localFolder` subtree (see project description for exact paths).
- Cross-window changes to shared code (`src/components/ui/`, `src/types/`, `src/hooks/`, `src/utils/`, top-level `src/lib/`) require a cross-window ticket with board awareness.

The window list and project mapping is canonical in [BTCAAAAA-29339#document-plan](/BTCAAAAA/issues/BTCAAAAA-29339#document-plan).

**Active Next.js root note:** Inside `packages/web-ui/`, the active App Router root is `app/` (not `src/app/`). When both directories exist, Next.js uses `app/` and ignores `src/app/`. New Next.js route subdirs must be created under `packages/web-ui/app/<window>/`. Components remain under `packages/web-ui/src/components/` (imported via the `@/` alias which maps to `packages/web-ui/src/`).
<!-- END:phase-scope -->

<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

<!-- BEGIN:branching-contract -->
# Branching Contract (mandatory for all code change)

Effective per [BTCAAAAA-30039](/BTCAAAAA/issues/BTCAAAAA-30039). Applies to every agent making code changes in this package.

1. Every code-change issue starts with: `git fetch origin && git switch -c {type}/BTCAAAAA-{n}-{kebab-slug} origin/main`. Verify with `git rev-parse --abbrev-ref HEAD` before the first commit.
2. Direct push to `origin/main` is FORBIDDEN. All merges go through PR + RepoSteward (or CEO GH_TOKEN fallback) per the merge-dispatch flow.
3. Closure comments MUST include a `Fix-SHA: <40-char-sha>` line on its own. Machine-parseable; closure-gate routine reads this.
4. Issue PATCH `status=done` is conditional on `git merge-base --is-ancestor <Fix-SHA> origin/main` returning rc=0. The closure-gate routine will reopen on violation.
5. Dev-server checkout: any agent that switches the working tree to a non-main branch MUST update the [dev-server-status document on BTCAAAAA-30031](/BTCAAAAA/issues/BTCAAAAA-30031#document-dev-server-status) within the same heartbeat.
<!-- END:branching-contract -->
