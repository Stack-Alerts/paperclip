"""
Regression tests for BTCAAAAA-1720: edge case for processed-issue-with-transition
continue guard in Blast Radius worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1720
Fixed in commit: d8380cf
Component: src/blast_radius/worker.py

Root cause: when a previously processed issue transitions from a non-in_review
status (e.g. in_progress) to in_review, the _detect_transitions function
correctly identifies it as a transition (old status != in_review), but the
continue guard at line 207 in run_once must still skip it because the issue
is already in processed_issue_ids. Without this guard, the issue would be
re-processed on every poll cycle until it transitions out of in_review.

This file tests that:
  1. A processed issue that transitions to in_review is skipped (not reprocessed)
  2. Unprocessed issues in the same batch are still processed correctly
  3. The state file correctly preserves the processed issue and adds new ones
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1720"),
    pytest.mark.regression,
]

_IN_REVIEW_ISSUES = [
    {
        "id": "uuid-fix-1",
        "identifier": "BTCAAAAA-100",
        "title": "Fix null pointer in loader",
        "status": "in_review",
        "labels": [{"name": "fix"}],
    },
    {
        "id": "uuid-bug-1",
        "identifier": "BTCAAAAA-101",
        "title": "Bug: trade list empty",
        "status": "in_review",
        "labels": [{"name": "bug"}],
    },
    {
        "id": "uuid-fr-1",
        "identifier": "BTCAAAAA-200",
        "title": "Add trailing stop feature",
        "status": "in_review",
        "labels": [{"name": "feature"}],
    },
    {
        "id": "uuid-title-match",
        "identifier": "BTCAAAAA-102",
        "title": "Fix regression in optimizer",
        "status": "in_review",
        "labels": [],
    },
]


def _patch_state(tmp_path: Path, data: dict | None = None) -> Path:
    state_file = tmp_path / "blast_radius_state.json"
    if data is not None:
        state_file.write_text(json.dumps(data))
    return state_file


class TestBTCAAAAA1720Regression:
    """Regression tests: processed issue with transition continue guard."""

    def test_skips_processed_issue_that_also_transitioned(self, tmp_path: Path) -> None:
        """A processed issue whose status transitioned to in_review must be
        skipped by the continue guard rather than re-processed."""
        import blast_radius.worker as worker_mod

        state_file = _patch_state(
            tmp_path,
            {
                "processed_issue_ids": ["uuid-bug-1"],
                "issue_statuses": {"uuid-bug-1": "in_progress"},
            },
        )
        issues = _IN_REVIEW_ISSUES

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch(
                "blast_radius.worker._fetch_in_review_issues",
                return_value=issues,
            ),
            patch(
                "blast_radius.worker.generate_and_post",
                return_value={"ok": True},
            ) as mock_gen,
        ):
            results = worker_mod.run_once(dry_run=False)

        # uuid-bug-1 was in_progress -> IS a transition, but already processed -> continue
        # uuid-fix-1 and uuid-title-match are new -> processed
        assert len(results) == 2
        assert mock_gen.call_count == 2
        state = json.loads(state_file.read_text())
        # uuid-bug-1 preserved from initial state, uuid-fix-1 and uuid-title-match added
        assert len(state.get("processed_issue_ids", [])) == 3

    def test_new_fix_issues_processed_normally(self, tmp_path: Path) -> None:
        """Unprocessed fix/bug issues in the same batch are still processed."""
        import blast_radius.worker as worker_mod

        state_file = _patch_state(tmp_path)
        issues = _IN_REVIEW_ISSUES

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch(
                "blast_radius.worker._fetch_in_review_issues",
                return_value=issues,
            ),
            patch(
                "blast_radius.worker.generate_and_post",
                return_value={"ok": True},
            ) as mock_gen,
        ):
            results = worker_mod.run_once(dry_run=False)

        assert len(results) == 3  # 3 fix/bug issues (100, 101, 102)
        assert mock_gen.call_count == 3
        state = json.loads(state_file.read_text())
        assert len(state.get("processed_issue_ids", [])) == 3

    def test_processed_issue_skipped_with_no_transition(self, tmp_path: Path) -> None:
        """A processed issue already in_review is not even detected as a transition."""
        import blast_radius.worker as worker_mod

        state_file = _patch_state(
            tmp_path,
            {
                "processed_issue_ids": ["uuid-fix-1"],
                "issue_statuses": {"uuid-fix-1": "in_review"},
            },
        )
        issues = _IN_REVIEW_ISSUES

        with (
            patch.object(worker_mod, "_STATE_PATH", state_file),
            patch(
                "blast_radius.worker._fetch_in_review_issues",
                return_value=issues,
            ),
            patch(
                "blast_radius.worker.generate_and_post",
                return_value={"ok": True},
            ) as mock_gen,
        ):
            results = worker_mod.run_once(dry_run=False)

        # uuid-fix-1 is already processed AND already in_review -> no transition detected
        assert len(results) == 2  # 101 and 102 are transitions
        assert mock_gen.call_count == 2
