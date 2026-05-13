"""Regression tests for BTCAAAAA-25886: Staff BTCAAAAA-25426 roadmap children.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25886
Component: docs/roadmap/BTCAAAAA-25426-heartbeat-summary.md,
            docs/roadmap/PRODUCT_GAP_ANALYSIS.md,
            docs/roadmap/SPRINT1-PLAN.md,
            docs/roadmap/child-issues/CHILD-001-strategy-factory.md,
            docs/roadmap/child-issues/CHILD-002-ci-walkforward-pipeline.md,
            docs/roadmap/child-issues/CHILD-003-binance-testnet-paper-trading.md,
            docs/roadmap/child-issues/CHILD-004-backtest-analysis-report.md,
            docs/roadmap/child-issues/CHILD-004-deliverable.md,
            docs/roadmap/child-issues/CHILD-005-ai-consultant-internal-rollout.md

Root cause: N/A — product strategy deliverable.  BTCAAAAA-25426 produced a
product gap analysis and 4-sprint improvement roadmap with 5 Sprint 1 child
issues.  Each child issue specifies owner, priority, estimate, and acceptance
criteria.  CHILD-004 (backtest matrix analysis) was completed with a full
deliverable.  This issue verifies all children are properly staffed with owners
and the CHILD-004 deliverable is in place.

This file verifies the roadmap children exist and are properly staffed with
owners, priorities, and acceptance criteria.  The canonical documents live
under docs/roadmap/ and must not drift.
"""

from __future__ import annotations

import os
import re

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25886"),
    pytest.mark.regression,
]

ROADMAP_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "roadmap")
CHILD_ISSUES_DIR = os.path.join(ROADMAP_DIR, "child-issues")


class TestRoadmapChildrenExist:
    """All 5 Sprint 1 child issue spec documents must exist."""

    SPEC_FILES = [
        "CHILD-001-strategy-factory.md",
        "CHILD-002-ci-walkforward-pipeline.md",
        "CHILD-003-binance-testnet-paper-trading.md",
        "CHILD-004-backtest-analysis-report.md",
        "CHILD-005-ai-consultant-internal-rollout.md",
    ]

    @pytest.fixture(scope="class")
    def child_dir(self) -> str:
        assert os.path.isdir(CHILD_ISSUES_DIR), (
            f"Child issues directory not found: {CHILD_ISSUES_DIR}"
        )
        return CHILD_ISSUES_DIR

    def test_child_issues_directory_exists(self):
        assert os.path.isdir(CHILD_ISSUES_DIR)

    def test_all_child_spec_files_present(self, child_dir):
        for fname in self.SPEC_FILES:
            path = os.path.join(child_dir, fname)
            assert os.path.isfile(path), f"Missing child issue spec: {fname}"

    def test_ch004_deliverable_exists(self, child_dir):
        path = os.path.join(child_dir, "CHILD-004-deliverable.md")
        assert os.path.isfile(path), "CHILD-004 deliverable is missing"

    def test_no_extra_unexpected_specs(self, child_dir):
        md_files = [f for f in os.listdir(child_dir) if f.endswith(".md")]
        expected = set(self.SPEC_FILES) | {"CHILD-004-deliverable.md"}
        extra = set(md_files) - expected
        assert not extra, f"Unexpected files in child-issues/: {extra}"


class TestRoadmapParentDocumentation:
    """Parent roadmap documents must exist."""

    PARENT_FILES = [
        "BTCAAAAA-25426-heartbeat-summary.md",
        "PRODUCT_GAP_ANALYSIS.md",
        "SPRINT1-PLAN.md",
    ]

    def test_parent_docs_exist(self):
        for fname in self.PARENT_FILES:
            path = os.path.join(ROADMAP_DIR, fname)
            assert os.path.isfile(path), f"Missing parent doc: {fname}"

    def test_heartbeat_summary_has_child_table(self):
        path = os.path.join(ROADMAP_DIR, "BTCAAAAA-25426-heartbeat-summary.md")
        assert os.path.isfile(path)
        with open(path) as f:
            content = f.read()
        assert "CHILD-001" in content
        assert "CHILD-002" in content
        assert "CHILD-003" in content
        assert "CHILD-004" in content
        assert "CHILD-005" in content

    def test_product_gap_analysis_approved(self):
        path = os.path.join(ROADMAP_DIR, "PRODUCT_GAP_ANALYSIS.md")
        assert os.path.isfile(path)
        with open(path) as f:
            content = f.read()
        assert "APPROVED" in content, "Gap analysis not in APPROVED status"

    def test_sprint1_plan_has_definition_of_done(self):
        path = os.path.join(ROADMAP_DIR, "SPRINT1-PLAN.md")
        assert os.path.isfile(path)
        with open(path) as f:
            content = f.read()
        assert "Definition of Sprint Done" in content


class TestChildIssueStaffing:
    """Each child issue spec must have an owner and priority assigned."""

    CHILDREN = [
        ("CHILD-001-strategy-factory.md", "Dev"),
        ("CHILD-002-ci-walkforward-pipeline.md", "DevOps"),
        ("CHILD-003-binance-testnet-paper-trading.md", "Dev"),
        ("CHILD-004-backtest-analysis-report.md", "ProductStrategist"),
        ("CHILD-005-ai-consultant-internal-rollout.md",
         r"Dev \+ StrategyResearcher \+ CTO"),
    ]

    @pytest.fixture(scope="class")
    def child_dir(self) -> str:
        assert os.path.isdir(CHILD_ISSUES_DIR)
        return CHILD_ISSUES_DIR

    def test_all_have_owner_assigned(self, child_dir):
        for fname, owner_pattern in self.CHILDREN:
            path = os.path.join(child_dir, fname)
            assert os.path.isfile(path), f"Missing: {fname}"
            with open(path) as f:
                content = f.read()
            match = re.search(r"\*\*Owner:\*\*\s*(.+)", content)
            assert match, f"No owner field found in {fname}"
            owner = match.group(1).strip()
            assert re.match(owner_pattern, owner), (
                f"{fname}: expected owner matching '{owner_pattern}', got '{owner}'"
            )

    def test_all_have_priority(self, child_dir):
        for fname, _ in self.CHILDREN:
            path = os.path.join(child_dir, fname)
            with open(path) as f:
                content = f.read()
            match = re.search(r"\*\*Priority:\*\*\s*(P[0-4])", content)
            assert match, f"No priority field found in {fname}"
            priority = match.group(1)
            assert priority in {"P0", "P1", "P2"}, (
                f"{fname}: unexpected priority '{priority}'"
            )

    def test_all_have_estimate(self, child_dir):
        for fname, _ in self.CHILDREN:
            path = os.path.join(child_dir, fname)
            with open(path) as f:
                content = f.read()
            assert re.search(r"\*\*Estimate:\*\*", content), (
                f"No estimate field found in {fname}"
            )

    def test_all_have_acceptance_criteria(self, child_dir):
        for fname, _ in self.CHILDREN:
            path = os.path.join(child_dir, fname)
            with open(path) as f:
                content = f.read()
            assert "### AC-" in content or "## Acceptance Criteria" in content, (
                f"No acceptance criteria found in {fname}"
            )

    def test_all_have_user_story(self, child_dir):
        for fname, _ in self.CHILDREN:
            path = os.path.join(child_dir, fname)
            with open(path) as f:
                content = f.read()
            assert "## User Story" in content or "As a" in content, (
                f"No user story found in {fname}"
            )


class TestCh004Deliverable:
    """CHILD-004 deliverable (backtest matrix analysis report) must be complete."""

    def test_deliverable_has_executive_summary(self):
        path = os.path.join(CHILD_ISSUES_DIR, "CHILD-004-deliverable.md")
        with open(path) as f:
            content = f.read()
        assert "Executive Summary" in content
        assert "Key finding:" in content or "Key finding" in content

    def test_deliverable_has_trade_analysis(self):
        path = os.path.join(CHILD_ISSUES_DIR, "CHILD-004-deliverable.md")
        with open(path) as f:
            content = f.read()
        assert "Trade Export" in content or "4,346" in content

    def test_deliverable_has_recommendations(self):
        path = os.path.join(CHILD_ISSUES_DIR, "CHILD-004-deliverable.md")
        with open(path) as f:
            content = f.read()
        assert "Recommendation" in content or "Top 3" in content

    def test_deliverable_has_open_questions(self):
        path = os.path.join(CHILD_ISSUES_DIR, "CHILD-004-deliverable.md")
        with open(path) as f:
            content = f.read()
        assert "Open Questions" in content or "Confluence thresholds" in content
