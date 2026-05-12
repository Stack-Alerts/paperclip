# Touch Index — Git Extractor

**Last updated:** 2026-05-12
**Owner:** DocWriter

---

## 1. Overview

The Git Extractor (`src/touch_index/git_extractor.py`) extracts file paths changed by a Paperclip issue by scanning git commit messages for the issue identifier (e.g. `BTCAAAAA-1085`). This is the primary data source for the Touch Index bug-close and FR ingestion workers.

### How It Works

```
Issue identifier (e.g. "BTCAAAAA-1085")
    │
    ▼
git log --all --format=%H --grep=BTCAAAAA-1085
    │  finds all commits referencing the issue
    ▼
For each commit SHA:
    git diff-tree --no-commit-id -r --name-only <SHA>
    │  extracts the list of touched files
    ▼
Deduplicated file list → upserted into touch_index_*_files tables
```

### Strategy

The project enforces conventional commits with Paperclip issue IDs in the scope token (e.g. `fix(touch-index): handle missing updatedAt in backfill FR filter`). This makes `git log --grep` a reliable strategy for mapping issues to affected files.

---

## 2. API

### `get_commit_hashes(issue_identifier, repo)`

Returns all commit SHAs whose message contains the given issue identifier.

```python
hashes = get_commit_hashes("BTCAAAAA-1085")
# → ["a1b2c3d4", "e5f6g7h8", ...]
```

### `get_files_for_commit(sha, repo)`

Returns the list of files changed in a single commit.

```python
files = get_files_for_commit("a1b2c3d4")
# → ["src/touch_index/db.py", "src/touch_index/worker.py"]
```

### `get_files_for_issue(issue_identifier, repo)`

Combines the above two: finds all commits for an issue, collects all files, deduplicates.

```python
files = get_files_for_issue("BTCAAAAA-1085")
# → ["src/touch_index/db.py", "src/touch_index/worker.py", "tests/test_touch_index.py"]
```

### `get_all_referenced_issue_ids(repo)`

Scans the full git history and returns all unique `BTCAAAAA-NNN` identifiers found in commit messages. Used by the quality module to determine which done issues are eligible for bug-file indexing.

```python
ids = get_all_referenced_issue_ids()
# → {"BTCAAAAA-1", "BTCAAAAA-2", "BTCAAAAA-1085", ...}
```

---

## 3. Coverage Characteristics

| Aspect | Detail |
|---|---|
| **Scope** | All branches (`git log --all`) |
| **Matching** | Substring match on issue ID in commit message |
| **Files** | Changed files per commit via `git diff-tree --name-only` |
| **Timeout** | 30 seconds per git command |
| **Failure mode** | Logs warning, returns empty list — never crashes |

### Limitations

- Issues referenced only in PR descriptions (not commit messages) are NOT detected
- Squash merges that lose individual commit messages may reduce coverage
- Only `BTCAAAAA-\d+` pattern is matched; other ID formats are ignored

---

## 4. Related Documents

- [TOUCH_INDEX_FR_WORKER.md](architecture/TOUCH_INDEX_FR_WORKER.md) — FR ingestion pipeline
- [TOUCH_INDEX_BUG_WORKER.md](architecture/TOUCH_INDEX_BUG_WORKER.md) — Bug ingestion pipeline
- [TOUCH_INDEX_QUALITY.md](architecture/TOUCH_INDEX_QUALITY.md) — Data quality monitoring
- [DATABASE_GUIDE.md](architecture/DATABASE_GUIDE.md) — touch_index table schemas
- [src/touch_index/git_extractor.py](../src/touch_index/git_extractor.py)
