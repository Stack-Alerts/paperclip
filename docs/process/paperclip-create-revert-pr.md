# Skill: paperclip-create-revert-pr

Use this skill whenever you are asked to author a PR that reverts one or more
prior commits. It exists because PR #118 (BTCAAAAA-36822) scoped its revert to
"what the original commit added" instead of "every live caller of the symbol
being deleted." Nine call sites added by later PRs were quietly removed.

The skill is one rule: **before deleting a symbol, you must enumerate every
caller that exists on `main` right now and decide, per caller, whether the
revert preserves or removes it.** A revert PR description is incomplete
without that audit.

## When this skill is required

- The board, an issue, or a code owner asks for a revert (full or partial).
- You are about to delete or change the signature of a public symbol that
  was introduced (or modified) by a commit you are reverting.
- The PR title or description uses the verbs `revert`, `reverts`, or
  `reverting`.

If none of those apply, this skill does not apply — use a normal change PR.

## The contract (what the PR must contain)

1. Name every commit being reverted.
2. For every public symbol the revert touches (deletes, renames, or changes
   the signature of), enumerate every caller that exists on the merge base
   right now.
3. Walk forward through commit history between the original commit and the
   tip of `main`, listing the PRs that added new callers since.
4. For each caller, mark `preserve` or `remove with this PR` and say why.
5. Put the table in the PR description under the fixed heading
   `## Caller audit`. The heading is exact — the workflow check matches on
   that string.

The check in `.github/workflows/pr-revert-caller-audit-check.yml` will fail
the PR if the title or body uses a revert verb without that heading.

## How to do the audit (mechanical recipe)

For each symbol the revert touches, the agent must run:

```bash
# 1. Identify the symbol(s) the revert deletes or signature-changes.
git show <revert-target-sha> -- <path> | grep -E '^\+def |^\+class |^\+async def '

# 2. List every file on main that currently calls the symbol.
git grep -n "<symbol>" -- ':!tests/**' ':!**/*.md'

# 3. List every commit that added or modified a call site since the
#    original change landed.
git log --oneline --pickaxe-regex -S"<symbol>" <original-sha>..HEAD -- <path>

# 4. For each caller, record the PR that added it and the disposition.
```

The audit is per-symbol. If the revert touches three symbols, the table has
three sections (or three tables). Do not merge the rows.

## Required PR-description shape

```markdown
## Caller audit

Reverting: `<sha-1>` (PR #<N>), `<sha-2>` (PR #<M>)
Symbol(s) under audit: `DatabaseManager.scoped_managers`, `ScopedManagers`

### `DatabaseManager.scoped_managers`

| Caller (file:line) | Added by             | Disposition | Reason                                    |
| ------------------ | -------------------- | ----------- | ----------------------------------------- |
| `src/foo.py:42`    | PR #14 (d2dade6c1)   | remove      | original target of this revert            |
| `src/bar.py:88`    | PR #57 (a7007d8fd)   | **preserve**| unrelated feature, depends on the symbol  |
| ...                | ...                  | ...         | ...                                       |
```

If the disposition is `preserve` anywhere in the table, the revert is
**partial**. State that explicitly in the PR title — e.g.
`partial revert of d2dade6c1 (preserving N later callers)`.

## Dry-run example: PR #118

A worked example using the exact data PR #118 should have produced lives at
[docs/process/revert-pr-118-caller-audit-dry-run.md](./revert-pr-118-caller-audit-dry-run.md).
It enumerates the nine callers PR #118 removed without acknowledging and
shows what the audit table should have looked like.

## Why the heading matters

The PR check is intentionally dumb: it greps the PR body for a `revert` verb
and then greps for `## Caller audit`. That is the whole gate. Agents will be
tempted to put the table under a different heading, behind a `<details>`,
or attached as a comment after merge. None of those satisfy the check. The
heading goes in the PR description body at PR-creation time.

## Reviewer's job

Reviewers must:

- spot-check the `git grep` and `git log -S` invocations the audit claims;
- verify that every `preserve` row is in fact preserved by the diff
  (the symbol is still used at the cited site after the PR is applied);
- reject the PR if a `preserve` row's caller is removed by the diff.

## See also

- `.github/workflows/pr-revert-caller-audit-check.yml` — the enforcing workflow.
- `scripts/check_revert_pr_caller_audit.py` — the check script (runnable
  locally with `--body-file <pr-body.md>`).
- BTCAAAAA-37740 — the issue that introduced this skill.
- BTCAAAAA-36822 / PR #118 — the incident this skill prevents.
