# BTC Trade Engine — Agent Instructions

## Branch-to-Main Merge Rule (MANDATORY)

**Root cause of past regressions:** Agents committed fixes to feature branches and marked
issues `done` without merging to `main`. The user then saw "regression" on main even though
the fix existed on a branch.

### Required flow for every fix or feature

1. Commit your work to a feature branch.
2. In the closing Paperclip comment, include the exact line:
   ```
   Fix-SHA: <full 40-char git sha>
   ```
3. Set the issue status to **`in_review`** — NOT `done`.
4. The merge-dispatch routine (`1a1065ea`) will open a PR, squash-merge it to `main`,
   and flip the issue to `done` automatically within 5 minutes.
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
