# Dry-Run: `paperclip-create-revert-pr` Applied to PR #118

This is a worked example of the skill in `paperclip-create-revert-pr.md`
applied retroactively to **PR #118** ("[Automated] Merge
`fix/BTCAAAAA-36822-revert-session-model` (18d0df17)"), which was authored
to satisfy board order **BTCAAAAA-36822** ("revert d2dade6c1").

The executing agent in PR #118 scoped the revert to "what `d2dade6c1`
added" and removed every `with db.scoped_managers() as scoped:` block in
`src/api/app.py`. Six follow-up PRs landed between `d2dade6c1`
(2026-05-26) and the revert (2026-06-17) and had added nine new call
sites on top of the original ones. Those nine were silently deleted.
BTCAAAAA-37218 / BTCAAAAA-37731 are the cleanup work to restore the
symbol and re-wire those sites.

The table below is the `## Caller audit` block PR #118 should have
contained. The skill's gate workflow would have blocked the PR until it
appeared.

## Reproduction commands

```bash
# 1. The symbol the revert deletes:
git show d2dade6c1 -- src/optimizer_v3/database/database_manager.py \
  | grep -E '^\+\s*(def |class )' | head
# -> ScopedManagers (class), DatabaseManager.scoped_managers (method)

# 2. Commits between the original change and the revert that added
#    new call sites to `scoped_managers`:
git log --oneline --pickaxe-regex -S"scoped_managers" \
  d2dade6c1..18d0df17^ -- src/api/app.py
# -> 1aaca517a feat(BTCAAAAA-36002): Config Discovery REST endpoint + web UI integration
#    bd47e0b41 feat(BTCAAAAA-33599): implement revert endpoint and wire Undo to actually revert strategy state
#    e68bc846d feat(BTCAAAAA-32954): wire validator Fix buttons to backend auto-fix endpoint
#    cc5da736d feat(BTCAAAAA-32954): connect web UI validation to backend InstitutionalValidator
#    a7007d8fd feat(BTCAAAAA-31183): backend REST contract for WebUI BackTesting (unblocks BTCAAAAA-31180)
#    84aa69c93 fix(BTCAAAAA-30023): persist Strategy Builder Save through to the DB

# 3. Every `with db.scoped_managers()` call site removed by the revert:
git show 18d0df17 -- src/api/app.py \
  | grep -nE '^-\s*with db\.scoped_managers\(\) as scoped:'
# -> nine deletions (see table below)
```

## `## Caller audit` (what PR #118 should have published)

Reverting: `d2dade6c1` (PR #14, fix(BTCAAAAA-29978))
Symbols under audit: `DatabaseManager.scoped_managers`, `ScopedManagers`,
`scoped.strategy`, `scoped.test_results`, `scoped.ai_recommendations`

### `DatabaseManager.scoped_managers` — `src/api/app.py` call sites

| # | Endpoint (caller)            | Added by                                         | Disposition  | Reason                                                                       |
|---|------------------------------|--------------------------------------------------|--------------|------------------------------------------------------------------------------|
| 1 | `sb_list_strategies`         | `d2dade6c1` PR #14 (BTCAAAAA-29978/29971)         | remove       | original target of this revert                                               |
| 2 | `sb_get_strategy_versions`   | `d2dade6c1` PR #14 (BTCAAAAA-29978/29971)         | remove       | original target of this revert                                               |
| 3 | `sb_get_strategy_version`    | `d2dade6c1` PR #14 (BTCAAAAA-29978/29971)         | remove       | original target of this revert                                               |
| 4 | `sb_get_strategy`            | `d2dade6c1` PR #14 (BTCAAAAA-29978/29971)         | remove       | original target of this revert                                               |
| 5 | `sb_create_strategy`         | `d2dade6c1` PR #14 (BTCAAAAA-29978/29971)         | remove       | original target of this revert                                               |
| 6 | `sb_delete_strategy`         | `d2dade6c1` PR #14 (BTCAAAAA-29978/29971)         | remove       | original target of this revert                                               |
| 7 | `sb_delete_strategy_versions`| `d2dade6c1` PR #14 (BTCAAAAA-29978/29971)         | remove       | original target of this revert                                               |
| 8 | `sb_duplicate_strategy`      | `d2dade6c1` PR #14 (BTCAAAAA-29978/29971)         | remove       | original target of this revert                                               |
| 9 | `sb_save_strategy` (persist) | `84aa69c93` fix(BTCAAAAA-30023)                   | **preserve** | unrelated Save persistence fix; depends on per-call session for safe write   |
| 10| `sb_backtest_*` REST handlers| `a7007d8fd` feat(BTCAAAAA-31183)                  | **preserve** | unblocks BTCAAAAA-31180 Web UI backtesting; new endpoint, not in `d2dade6c1` |
| 11| `sb_validate_strategy`       | `cc5da736d` feat(BTCAAAAA-32954)                  | **preserve** | InstitutionalValidator wiring landed after `d2dade6c1`                       |
| 12| `sb_apply_validator_fix`     | `e68bc846d` feat(BTCAAAAA-32954)                  | **preserve** | validator Fix-button endpoint; new caller, post-`d2dade6c1`                  |
| 13| `sb_revert_strategy`         | `bd47e0b41` feat(BTCAAAAA-33599)                  | **preserve** | strategy-revert endpoint, depends on transactional scoped session            |
| 14| `sb_config_discovery_*`      | `1aaca517a` feat(BTCAAAAA-36002)                  | **preserve** | Config Discovery REST endpoint added after `d2dade6c1`                       |
| 15| `sb_save_strategy_v2`        | `1aaca517a` feat(BTCAAAAA-36002)                  | **preserve** | uses scoped session for atomic config write                                  |
| 16| `sb_list_recommendations`    | `cc5da736d` feat(BTCAAAAA-32954)                  | **preserve** | new AI-recommendations read path, post-`d2dade6c1`                           |
| 17| `sb_persist_recommendation`  | `cc5da736d` feat(BTCAAAAA-32954)                  | **preserve** | new AI-recommendations write path, post-`d2dade6c1`                          |

Rows 1–8 are the original `sb_*` endpoints `d2dade6c1` introduced — those
match the board's intent for the revert. Rows 9–17 are the **nine
unrevertet callers** added by six later PRs. PR #118 removed all of them
without acknowledging that they existed.

### What the dry-run flags

- The revert is **partial**, not full. PR #118's title should have read
  something like `partial revert of d2dade6c1 (preserving 9 later callers)`.
- The PR description had no `## Caller audit` heading, so the
  `pr-revert-caller-audit-check` workflow (added by BTCAAAAA-37740) would
  have failed the check and blocked the merge until the table was added.
- A reviewer following the skill's "Reviewer's job" section would have
  rejected the PR because rows 9–17 carry `preserve` but the diff removes
  the call sites at those endpoints.

### Outcome trail

- The deletion landed on `main` at `18d0df17` on 2026-06-17.
- BTCAAAAA-37218 ("click-to-highlight" UI regression) and the broader
  scoped-session restoration work were opened to undo the collateral damage.
- BTCAAAAA-37731 / commit `37033dfd0` restores `ScopedManagers` and
  `DatabaseManager.scoped_managers()` and rewires the preserved callers.
- BTCAAAAA-37740 (this issue) installs the skill and gate workflow so the
  same scope error cannot reach `main` again.
