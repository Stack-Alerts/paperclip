# Isolated Test Instances — `start-test-iso.sh`

> Operator guide for the worktree-per-instance test launcher. Implemented
> in [BTCAAAAA-38277](/BTCAAAAA/issues/BTCAAAAA-38277). Motivation and
> background in [BTCAAAAA-38260](/BTCAAAAA/issues/BTCAAAAA-38260).

## What it is

`start-test-iso.sh` is the **isolated** variant of the test launcher. Each
instance runs in its **own git worktree** under `~/btc-test-worktrees/`,
with a **deterministic per-branch port in `:4000–:4999`**. Multiple
instances can run side-by-side without colliding with each other or with
the supervised dev server on `:3010`.

Use it when you need:

- **Concurrent branches** — QA a `feature-a` instance while you keep a
  `feature-b` instance alive.
- **Detached SHA testing** — pin an instance to a specific commit to
  reproduce a bug report.
- **Clean isolation** — the primary worktree is never touched, so a dirty
  index on `main` does not break the test instance.

## Quick start

Run an instance for the current default branch (`main`):

```bash
./start-test-iso.sh
# → creates ~/btc-test-worktrees/main, allocates :PORT, opens dev log tail
```

Run an instance for a feature branch (uses the same branch name as the
worktree and as the registry key):

```bash
./start-test-iso.sh feature/awesome
# → ~/btc-test-worktrees/feature_awesome, deterministic :PORT
```

Run detached at a specific commit (for bug reproduction):

```bash
./start-test-iso.sh feature/awesome@5a74fdb9
# → same registry key, detached HEAD, no auto-pulls
```

## Command surface

| Command                       | Purpose                                                |
| ----------------------------- | ------------------------------------------------------ |
| `./start-test-iso.sh`         | Start an instance for `main` (default subcommand)      |
| `./start-test-iso.sh <br>`    | Start an instance for branch `<br>`                    |
| `./start-test-iso.sh --list`  | Show all live + stale registry rows                    |
| `./start-test-iso.sh --status <br>` | Print registry row, pid liveness, port bind       |
| `./start-test-iso.sh --stop <br>`   | SIGTERM the instance and remove its worktree     |
| `./start-test-iso.sh --restart <br>` | Stop, re-pull, start fresh                          |
| `./start-test-iso.sh --nuke <br>`   | Stop + delete worktree + delete registry row      |
| `./start-test-iso.sh --logs <br>`   | Tail the dev log (`Ctrl-C` to exit)              |
| `./start-test-iso.sh --doctor`      | Diagnose stale rows, foreign port holders, orphans |

Every subcommand accepts `--help` / `-h` for one-page usage.

### Examples

```bash
# Inventory
./start-test-iso.sh --list
# KEY                                BRANCH                           PORT    PID      STATUS
# ----------------------------------------------------------------------------------------
# main                               main                             4273    41872    running
# feature_awesome                    feature/awesome                  4502    41904    running

# Inspect one instance
./start-test-iso.sh --status feature/awesome
# → key:        feature_awesome
# → branch:     feature/awesome
# → port:       4502
# → pid:        41904  (alive)
# → worktree:   /home/you/btc-test-worktrees/feature_awesome
# → started_at: 2026-06-24T19:45:01Z

# Stop cleanly (worktree kept on disk)
./start-test-iso.sh --stop feature/awesome

# Wipe the worktree + registry row (irreversible for that branch)
./start-test-iso.sh --nuke feature/awesome

# Tail logs of the running instance
./start-test-iso.sh --logs main

# Diagnose after a crash or hard reboot
./start-test-iso.sh --doctor
# → may report: stale registry rows (pid gone),
#   foreign pid holding an allocated port, orphan worktrees on disk
```

## Port allocation

Ports are mapped **deterministically** from a registry key:

```
port = 4000 + ( cksum(key) mod 1000 )
```

The same branch always gets the same port — restarting an instance
preserves the URL. Allocation never returns `:3000` or `:3010` (defended
in depth with a `PROTECTED_PORTS` allow-list; the canonical supervised
dev server on `:3010` is never displaced).

## Storage layout

| Path                                                  | Purpose                          |
| ----------------------------------------------------- | -------------------------------- |
| `$BTC_TEST_WORKTREES` (default `~/btc-test-worktrees`) | Worktree root                   |
| `~/btc-test-worktrees/<safe-branch>/`                 | Per-instance worktree            |
| `~/.btc-test-iso/registry.json`                       | Live instance state (atomic write) |
| `~/.btc-test-iso/registry.lock`                       | `flock` guard for atomic updates |
| `<worktree>/packages/web-ui/.start-test-iso.pid`      | PID file for liveness checks     |
| `<worktree>/packages/web-ui/dev.log`                  | Next.js dev output (use `--logs`) |
| `<worktree>/packages/web-ui/.env.local`               | Per-instance `PORT=<n>` injected |

`safe-branch` replaces `/` with `_`, strips leading `+`, and caps at
96 chars (with an 8-hex hash suffix on truncation). A worktree
directory collision gets the same suffix treatment.

## Branch resolution

The first positional argument resolves the worktree to launch:

| Form              | Behavior                                                   |
| ----------------- | ---------------------------------------------------------- |
| *(omitted)*       | `main` (origin/main tip at start time)                     |
| `<branch>`        | Named branch; auto-pulled unless `--no-pull`               |
| `<branch>@<sha>`  | Detached at `<sha>` (7+ hex); **never auto-pulled**        |

A registry row keyed on `<branch>` (the `@<sha>` is launch-time only),
so `--status feature/awesome@5a74fdb9` resolves to the same row as
`--status feature/awesome`.

## Failure modes you will hit

**Port held by a foreign process.** The script prints the holder's PID,
etime, and command, then prompts `Action? [k/r/c]`. Use
`--kill-existing`, `--reuse-existing`, or `--cancel-on-conflict` to
skip the prompt in automation. `k` SIGTERMs the holder and waits up to
5 s; `r` exits 0 and reuses; `c` exits 1.

**`btc-dev-server.service` already on `:3010`.** Expected and harmless
— the isolated instance never touches `:3010`. If you actually need to
free `:3010`, stop the unit: `systemctl --user stop btc-dev-server.service`.

**Dirty primary worktree.** A fresh instance is built from a **new**
worktree, not the current one, so a dirty index on `main` does not
break the test. Fix the primary worktree separately.

**Stale registry row after a hard reboot.** PIDs in the registry go
away, but the row remains. `--doctor` flags them; `--stop <branch>`
cleans them up.

**Port already in use by a different instance.** Two branches can
collide only if their cksum hashes collide (≈ 1/1000). Re-launch with
`--nuke <offending-branch>` to free the row and the port, or accept the
interactive prompt to kill the foreign holder.

**`--doctor` output is noisy after a crash.** That is the point —
each line is a fixable condition with a one-line remediation
(`./start-test-iso.sh --stop <key>`).

## Cross-references

- `start-test.sh` (legacy ephemeral instance on `:3000`). **Use
  `start-test-iso.sh` instead** unless you specifically need the
  single-instance ephemeral mode (e.g. fast smoke against a
  pre-`start-test-iso.sh` commit).
- `start-dev.sh` — supervised canonical launcher on `:3010` under
  `btc-dev-server.service`. **This is the system of record for "what
  the next agent sees".** `start-test-iso.sh` is for parallel branch
  testing, not for replacing the supervised dev server.
- [BTCAAAAA-38260](/BTCAAAAA/issues/BTCAAAAA-38260) — motivation and
  design constraints.
- [BTCAAAAA-38277](/BTCAAAAA/issues/BTCAAAAA-38277) — implementation
  PR; squash-merged on `origin/main` via PR #215.
