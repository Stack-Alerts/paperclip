# Runbook: Dependency Graph

**Last updated:** 2026-05-12
**Owner:** RepoSteward

---

## 1. Overview

`dep_graph.json` is a JSON file at the repo root that encodes the import dependency graph between all Python source files. It is used by the lock gate for reverse lookup queries ("which locked files would this change impact?").

**File:** `dep_graph.json`
**Generator:** `scripts/regenerate_dep_graph.py`
**Workflow:** `dep-graph-refresh.yml`

---

## 2. Refresh Cadence

| Trigger | Cadence | Description |
|---|---|---|
| Scheduled | Nightly @ 02:00 UTC | Standard regeneration |
| Manual | `workflow_dispatch` | On-demand refresh |

The nightly run executes after `dep-graph-refresh.yml` at 02:00 UTC. On changes, it auto-commits the updated `dep_graph.json` with `[skip ci]` to avoid triggering another CI cycle.

---

## 3. Manual Refresh

```bash
# From repo root
python scripts/regenerate_dep_graph.py

# Check what changed
git diff dep_graph.json

# Commit if changed
git add dep_graph.json
git commit -m "chore(dep-graph): manual regeneration"
git push
```

---

## 4. Manual Trigger (GitHub Actions)

```bash
gh workflow run dep-graph-refresh.yml
```

---

## 5. Interpreting the Output

The dependency graph is structured as:

```json
{
  "src/optimizer_v3/core.py": [
    "src/optimizer_v3/database/models.py",
    "src/optimizer_v3/config.py"
  ],
  ...
}
```

Each key is a source file. Its value is the list of files it imports (within the repo — external/third-party imports are excluded).

### Usage in Lock Gate

The lock gate queries `dep_graph.json` to determine if a PR touching a locked file also impacts other locked files transitively. If so, it blocks the PR unless a valid exception exists.

---

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `dep_graph.json` not updated | Script error or no import changes | Run `scripts/regenerate_dep_graph.py` manually, check for errors |
| Stale graph | Nightly run failed | Check `dep-graph-refresh` workflow logs, re-run |
| Graph shows incorrect deps | Missing or extra imports in source | Fix imports in source, re-run regeneration |

---

## 7. Related Documents

- [lock-gate.md](../lock-gate.md) — lock gate architecture
- [runbook-module-lock.md](runbook-module-lock.md) — lock gate operations
- [runbook-ci-cd.md](runbook-ci-cd.md) — nightly workflow scheduling
- [scripts/regenerate_dep_graph.py](../../scripts/regenerate_dep_graph.py)
