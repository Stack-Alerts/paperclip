# Touch Index Quality Monitoring

**Last updated:** 2026-05-12
**Owner:** DocWriter

---

## 1. Overview

The Touch Index Quality module (`src/touch_index/quality.py`) monitors data quality for the `touch_index_fr_files` and `touch_index_bug_files` tables. It provides coverage, freshness, and consistency checks callable from validation scripts, ingestion workers, or cron jobs.

**File:** `src/touch_index/quality.py`

---

## 2. Quality Reports

### 2.1 CoverageReport

Measures what fraction of FDR issues in Paperclip have corresponding rows in the touch index.

```python
@dataclass
class CoverageReport:
    total_fdr_issues: int           # Total FDR-labelled issues in Paperclip
    indexed_fdr_issues: int         # FDR issues present in touch_index_fr_files
    coverage_pct: float             # indexed / total * 100
    missing_issue_identifiers: list[str]  # FDRs not yet indexed
```

### 2.2 FreshnessReport

Measures how recently the touch index was updated.

```python
@dataclass
class FreshnessReport:
    total_rows: int                 # Total rows in the table
    max_age_hours: float            # Oldest row age
    min_age_hours: float            # Newest row age
    stale_rows: int                 # Rows older than threshold
    stale_threshold_hours: int      # Configurable threshold (default: 168 = 7 days)
```

### 2.3 ConsistencyReport

Detects data integrity issues.

```python
@dataclass
class ConsistencyReport:
    null_owner_rows: int            # Rows missing fr_owner_agent_id
    null_updated_at_rows: int       # Rows missing updated_at
    duplicate_pairs: int            # Duplicate (file_path, fr_issue_id) pairs
    unknown_source_rows: int        # Rows with unrecognized source value
    orphan_fr_issue_ids: list[str]  # FR issue IDs not found in Paperclip
```

### 2.4 QualityReport — Composite

```python
@dataclass
class QualityReport:
    coverage: CoverageReport | None
    freshness: FreshnessReport | None
    consistency: ConsistencyReport | None
    passed: bool           # True when all checks pass
```

---

## 3. Usage

### Standalone Check

```bash
python -c "from touch_index.quality import run_quality_checks; print(run_quality_checks())"
```

### From Validation Scripts

Called by `scripts/validate_touch_index_fr.py` and `scripts/validate_touch_index_bug.py` which are invoked automatically at the end of each ingestion worker run.

### Programmatic

```python
from sqlalchemy import create_engine
from touch_index.quality import (
    compute_coverage,
    compute_freshness,
    compute_consistency,
    QualityReport,
)

engine = create_engine("postgresql://...")

coverage = compute_coverage(engine)
freshness = compute_freshness(engine, stale_threshold_hours=168)
consistency = compute_consistency(engine)

report = QualityReport(
    coverage=coverage,
    freshness=freshness,
    consistency=consistency,
    passed=all([
        coverage.coverage_pct >= 95.0,
        freshness.stale_rows == 0,
        consistency.null_owner_rows == 0,
        consistency.duplicate_pairs == 0,
    ])
)
print(report.to_dict())
```

---

## 4. Validation Scripts

| Script | Table | Stale Threshold | Called By |
|---|---|---|---|
| `scripts/validate_touch_index_fr.py` | `touch_index_fr_files` | 168 hours (7 days) | `touch-index-fr-worker.yml` |
| `scripts/validate_touch_index_bug.py` | `touch_index_bug_files` | 30 days | `touch-index-bug-worker.yml` |

Both scripts run on `if: always()` — they execute even when the ingestion worker fails, to ensure quality monitoring is never skipped.

---

## 5. Expected SLAs

| Metric | Target | Alert Threshold |
|---|---|---|
| FR issue coverage | >95% | <90% |
| Bug issue coverage | >95% | <90% |
| Max row age | <168 hours | >336 hours |
| Stale rows | 0 | >0 (alert) |
| Null owner rows | 0 | >0 |
| Duplicate file-issue pairs | 0 | >0 |

---

## 6. Related Documents

- [TOUCH_INDEX_FR_WORKER.md](TOUCH_INDEX_FR_WORKER.md) — FR ingestion architecture
- [TOUCH_INDEX_BUG_WORKER.md](TOUCH_INDEX_BUG_WORKER.md) — Bug ingestion architecture
- [DATABASE_GUIDE.md](DATABASE_GUIDE.md) — touch_index schema
- [runbook-ci-cd.md](../runbook-ci-cd.md) — worker pipeline triggering validation
- [src/touch_index/quality.py](../../src/touch_index/quality.py)
