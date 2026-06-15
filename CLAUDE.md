# BTC Trade Engine — Agent Instructions

## Branch-to-Main Merge Rule (MANDATORY)

**Root cause of past regressions:** Agents committed fixes to feature branches and marked
issues `done` without merging to `main`. The user then saw "regression" on main even though
the fix existed on a branch.

### Required flow for every fix or feature

1. Commit your work to a feature branch, then **`git push`** it (the merge opens a PR from
   the remote branch ref — a local-only commit never merges).
2. In the closing Paperclip comment, include the exact line:
   ```
   Fix-SHA: <full 40-char git sha>
   ```
3. Set the issue status to **`in_review`** — NOT `done`.
4. **Trigger the merge immediately** (primary path — do not wait for the periodic sweep):
   ```
   python3 scripts/merge_dispatch_routine.py --issue <issue-id>
   ```
   This opens a PR, squash-merges it to `main`, and flips the issue to `done`.
   The periodic merge-dispatch routine (`1a1065ea`) is only a backup that sweeps anything
   missed; it now acts on any `in_review` issue with a pushed Fix-SHA (no interaction gate).
5. The Phase-3 closure-gate routine (`a6e59e24`) will reopen any issue where the
   Fix-SHA is not an ancestor of `origin/main`.

**Never set an issue to `done` yourself when the fix is on a feature branch.**
The automation closes it after the merge lands. Setting `done` early bypasses all
merge-gate and ancestry checks.

### When it is safe to set `done` directly

Only if ALL of the following are true:
- The commit was made directly to `main` (not a feature branch), AND
- `git branch --contains <sha>` shows `main`, AND
- The issue is documentation-only, process-only, or has no code artifact.

### Building block protection

Files under `src/detectors/building_blocks/**` must NOT be modified without explicit
user authorization. These are completed, validated signal detectors. Any change to them
resets calibrated statistics and requires a full re-baseline.

## Paperclip Issue Closing Checklist

Before marking any issue `done`:
- [ ] `git branch --contains <fix-sha>` includes `main`
- [ ] Fix-SHA line is in the closing comment
- [ ] For UI changes: dev server starts and golden path was tested
