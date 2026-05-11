"""Unit tests for touch_index.quality data quality monitoring.

All external I/O (DB engine, Paperclip API) is mocked so tests run offline.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from touch_index.quality import (
    CoverageReport,
    FreshnessReport,
    ConsistencyReport,
    QualityReport,
    compute_coverage,
    compute_freshness,
    check_consistency,
    run_quality_checks,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scalar_result(val, rows=None):
    r = MagicMock()
    r.scalar = MagicMock(return_value=val)
    if rows is not None:
        r.fetchall = MagicMock(return_value=rows)
    else:
        r.fetchall = MagicMock(return_value=[])
    return r


def _make_engine(execute_results):
    """Return an engine whose connect() context-manager yields a conn
    whose execute() returns results from *execute_results* in order."""
    idx = [0]

    def _execute(*a, **kw):
        i = idx[0]
        idx[0] += 1
        if i < len(execute_results):
            return execute_results[i]
        return _make_scalar_result(0)

    conn = MagicMock()
    conn.execute = _execute
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)
    engine = MagicMock()
    engine.connect = MagicMock(return_value=ctx)
    return engine


def _make_coverage(**kw):
    defaults = dict(
        total_fdr_issues=0,
        indexed_fdr_issues=0,
        coverage_pct=0.0,
        missing_issue_identifiers=[],
    )
    defaults.update(kw)
    return CoverageReport(**defaults)


def _make_freshness(**kw):
    defaults = dict(
        total_rows=0, max_age_hours=0.0, min_age_hours=0.0,
        stale_rows=0, stale_threshold_hours=168,
    )
    defaults.update(kw)
    return FreshnessReport(**defaults)


def _make_consistency(**kw):
    defaults = dict(
        null_owner_rows=0, null_updated_at_rows=0,
        duplicate_pairs=0, orphan_fr_issue_ids=[],
    )
    defaults.update(kw)
    return ConsistencyReport(**defaults)


# ---------------------------------------------------------------------------
# compute_coverage
# ---------------------------------------------------------------------------


class TestComputeCoverage:
    def test_full_coverage(self):
        engine = _make_engine([
            _make_scalar_result(2),           # COUNT(DISTINCT fr_identifier)
            _make_scalar_result(0, rows=[      # DISTINCT fr_identifier rows
                ("BTCAAAAA-100",),
                ("BTCAAAAA-101",),
            ]),
        ])

        with patch("touch_index.quality._paginate", return_value=[
            {"identifier": "BTCAAAAA-100"},
            {"identifier": "BTCAAAAA-101"},
        ]) as mock_api:
            report = compute_coverage(engine)

        assert report.total_fdr_issues == 2
        assert report.indexed_fdr_issues == 2
        assert report.coverage_pct == 100.0
        assert report.missing_issue_identifiers == []
        mock_api.assert_called_once()

    def test_partial_coverage(self):
        engine = _make_engine([
            _make_scalar_result(1),
            _make_scalar_result(0, rows=[("BTCAAAAA-100",)]),
        ])

        with patch("touch_index.quality._paginate", return_value=[
            {"identifier": "BTCAAAAA-100"},
            {"identifier": "BTCAAAAA-101"},
            {"identifier": "BTCAAAAA-102"},
        ]):
            report = compute_coverage(engine)

        assert report.total_fdr_issues == 3
        assert report.indexed_fdr_issues == 1
        assert report.coverage_pct == pytest.approx(33.3, rel=0.1)
        assert report.missing_issue_identifiers == ["BTCAAAAA-101", "BTCAAAAA-102"]

    def test_zero_indexed(self):
        engine = _make_engine([
            _make_scalar_result(0),
            _make_scalar_result(0, rows=[]),
        ])

        with patch("touch_index.quality._paginate", return_value=[
            {"identifier": "BTCAAAAA-100"},
            {"identifier": "BTCAAAAA-101"},
        ]):
            report = compute_coverage(engine)

        assert report.total_fdr_issues == 2
        assert report.indexed_fdr_issues == 0
        assert report.coverage_pct == 0.0
        assert len(report.missing_issue_identifiers) == 2

    def test_zero_fdr_issues(self):
        engine = _make_engine([
            _make_scalar_result(0),
            _make_scalar_result(0, rows=[]),
        ])

        with patch("touch_index.quality._paginate", return_value=[]):
            report = compute_coverage(engine)

        assert report.total_fdr_issues == 0
        assert report.indexed_fdr_issues == 0
        assert report.coverage_pct == 0.0
        assert report.missing_issue_identifiers == []


# ---------------------------------------------------------------------------
# compute_freshness
# ---------------------------------------------------------------------------


class TestComputeFreshness:
    def test_empty_table(self):
        now = datetime.now(timezone.utc)
        engine = _make_engine([
            _make_scalar_result(0),   # COUNT(*)
            _make_scalar_result(None),  # MIN(updated_at) — None
            _make_scalar_result(None),  # MAX(updated_at) — None
            _make_scalar_result(0),     # stale count
        ])

        with patch("touch_index.quality.datetime") as mock_dt:
            mock_dt.now.return_value = now
            
            report = compute_freshness(engine)

        assert report.total_rows == 0
        assert report.max_age_hours == 0.0
        assert report.stale_rows == 0

    def test_fresh_data(self):
        now = datetime(2026, 5, 12, 12, 0, 0, tzinfo=timezone.utc)
        old_dt = datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)

        engine = _make_engine([
            _make_scalar_result(5),     # COUNT(*)
            _make_scalar_result(old_dt), # MIN
            _make_scalar_result(now),    # MAX
            _make_scalar_result(0),      # stale
        ])

        with patch("touch_index.quality.datetime") as mock_dt_patch:
            mock_dt_patch.now.return_value = now
            mock_dt_patch.timedelta = __import__("datetime").timedelta
            report = compute_freshness(engine)

        assert report.total_rows == 5
        assert report.max_age_hours == 24.0
        assert report.stale_rows == 0


# ---------------------------------------------------------------------------
# check_consistency
# ---------------------------------------------------------------------------


class TestCheckConsistency:
    def test_clean_data(self):
        """When data is clean, all counts are zero and no orphans."""
        engine = _make_engine([
            _make_scalar_result(0),  # null_owner
            _make_scalar_result(0),  # null_updated
            _make_scalar_result(0),  # duplicates
            _make_scalar_result(0, rows=[]),  # DISTINCT fr_issue_ids
        ])

        with patch(
            "touch_index.paperclip_client.get_issue_by_id",
            return_value={"id": "exists"},
        ):
            report = check_consistency(engine)

        assert report.null_owner_rows == 0
        assert report.null_updated_at_rows == 0
        assert report.duplicate_pairs == 0
        assert report.orphan_fr_issue_ids == []

    def test_detects_null_owner(self):
        """Rows with sentinel owner UUID are counted."""
        engine = _make_engine([
            _make_scalar_result(3),  # null_owner
            _make_scalar_result(0),  # null_updated
            _make_scalar_result(0),  # duplicates
            _make_scalar_result(0, rows=[]),  # DISTINCT
        ])

        with patch(
            "touch_index.paperclip_client.get_issue_by_id",
            return_value={"id": "exists"},
        ):
            report = check_consistency(engine)

        assert report.null_owner_rows == 3
        assert report.null_updated_at_rows == 0
        assert report.duplicate_pairs == 0

    def test_detects_orphans(self):
        """Issue IDs not found in Paperclip are reported as orphans."""
        engine = _make_engine([
            _make_scalar_result(0),  # null_owner
            _make_scalar_result(0),  # null_updated
            _make_scalar_result(0),  # duplicates
            _make_scalar_result(0, rows=[("orphan-1",), ("orphan-2",)]),
        ])

        with patch(
            "touch_index.paperclip_client.get_issue_by_id",
            return_value=None,
        ):
            report = check_consistency(engine)

        assert len(report.orphan_fr_issue_ids) == 2
        assert "orphan-1" in report.orphan_fr_issue_ids


# ---------------------------------------------------------------------------
# run_quality_checks
# ---------------------------------------------------------------------------


class TestRunQualityChecks:
    def test_all_pass(self):
        engine = MagicMock()

        with (
            patch("touch_index.quality.compute_coverage",
                  return_value=_make_coverage(
                      total_fdr_issues=2, indexed_fdr_issues=2, coverage_pct=100.0)),
            patch("touch_index.quality.compute_freshness",
                  return_value=_make_freshness(total_rows=5, max_age_hours=2.0)),
            patch("touch_index.quality.check_consistency",
                  return_value=_make_consistency()),
        ):
            report = run_quality_checks(engine)

        assert report.passed is True
        assert report.coverage is not None
        assert report.freshness is not None
        assert report.consistency is not None

    def test_low_coverage_fails(self):
        engine = MagicMock()

        with (
            patch("touch_index.quality.compute_coverage",
                  return_value=_make_coverage(
                      total_fdr_issues=10, indexed_fdr_issues=5, coverage_pct=50.0)),
            patch("touch_index.quality.compute_freshness",
                  return_value=_make_freshness(total_rows=5, max_age_hours=1.0)),
            patch("touch_index.quality.check_consistency",
                  return_value=_make_consistency()),
        ):
            report = run_quality_checks(engine)

        assert report.passed is False

    def test_stale_rows_fails(self):
        engine = MagicMock()

        with (
            patch("touch_index.quality.compute_coverage",
                  return_value=_make_coverage(
                      total_fdr_issues=2, indexed_fdr_issues=2, coverage_pct=100.0)),
            patch("touch_index.quality.compute_freshness",
                  return_value=_make_freshness(
                      total_rows=5, stale_rows=3, stale_threshold_hours=168)),
            patch("touch_index.quality.check_consistency",
                  return_value=_make_consistency()),
        ):
            report = run_quality_checks(engine)

        assert report.passed is False

    def test_consistency_issues_fail(self):
        engine = MagicMock()

        with (
            patch("touch_index.quality.compute_coverage",
                  return_value=_make_coverage(
                      total_fdr_issues=2, indexed_fdr_issues=2, coverage_pct=100.0)),
            patch("touch_index.quality.compute_freshness",
                  return_value=_make_freshness(total_rows=5, max_age_hours=1.0)),
            patch("touch_index.quality.check_consistency",
                  return_value=_make_consistency(null_owner_rows=2)),
        ):
            report = run_quality_checks(engine)

        assert report.passed is False

    def test_exception_in_coverage_still_runs_others(self):
        engine = MagicMock()

        with (
            patch("touch_index.quality.compute_coverage",
                  side_effect=RuntimeError("API timeout")),
            patch("touch_index.quality.compute_freshness",
                  return_value=_make_freshness(total_rows=5)),
            patch("touch_index.quality.check_consistency",
                  return_value=_make_consistency()),
        ):
            report = run_quality_checks(engine)

        assert report.passed is False
        assert report.coverage is None
        assert report.freshness is not None
        assert report.consistency is not None
