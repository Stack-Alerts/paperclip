"""Unit tests for blast_radius.query — no live DB required."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import ProgrammingError

from blast_radius.query import (
    BlastRadiusData,
    FRImpact,
    RegressionRisk,
    query_blast_radius,
    to_json_dict,
)


def _mock_result(rows: list, scalar_return=None) -> MagicMock:
    """Return a mock DB result.

    - .fetchall() returns *rows*
    - .scalar() returns *scalar_return* if provided, else default MagicMock
    """
    m = MagicMock()
    m.fetchall.return_value = rows
    if scalar_return is not None:
        m.scalar.return_value = scalar_return
    return m


class TestQueryBlastRadius:
    def test_empty_file_list_returns_empty_data(self):
        data = query_blast_radius([], engine=MagicMock())
        assert isinstance(data, BlastRadiusData)
        assert data.fr_impact_set == []
        assert data.regression_set == []
        assert data.downstream_set == []

    def test_queries_all_three_sets(self):
        engine = MagicMock()
        conn = engine.connect.return_value.__enter__.return_value
        # Call order: fr_impact -> regression -> downstream (count)
        conn.execute.side_effect = [
            _mock_result(
                [
                    MagicMock(
                        fr_identifier="FDR-100",
                        fr_owner_agent_id="agent-a",
                        fr_issue_id="issue-a",
                    )
                ]
            ),
            _mock_result(
                [
                    MagicMock(
                        bug_identifier="BTCAAAAA-500",
                        bug_issue_id="bug-uuid",
                    )
                ]
            ),
            _mock_result([], scalar_return=0),  # downstream count = 0 -> skip query
        ]

        data = query_blast_radius(["src/foo.py"], engine=engine)

        assert len(data.fr_impact_set) == 1
        assert data.fr_impact_set[0].fr_identifier == "FDR-100"
        assert data.fr_impact_set[0].fr_owner_agent_id == "agent-a"
        assert len(data.regression_set) == 1
        assert data.regression_set[0].bug_identifier == "BTCAAAAA-500"
        assert data.downstream_set == []

    def test_downstream_queries_when_count_positive(self):
        engine = MagicMock()
        conn = engine.connect.return_value.__enter__.return_value
        # Call order: fr_impact -> regression -> downstream (count, then query)
        conn.execute.side_effect = [
            _mock_result([]),  # fr: no results
            _mock_result([]),  # regression: no results
            _mock_result([], scalar_return=5),  # downstream count = 5 > 0
            _mock_result(
                [  # downstream query
                    MagicMock(dep_file="src/dep.py"),
                    MagicMock(dep_file="src/dep2.py"),
                ]
            ),
        ]

        data = query_blast_radius(["src/foo.py"], engine=engine)

        assert len(data.downstream_set) == 2
        assert "src/dep.py" in data.downstream_set
        assert "src/dep2.py" in data.downstream_set

    def test_passes_file_paths_to_db(self):
        engine = MagicMock()
        conn = engine.connect.return_value.__enter__.return_value

        conn.execute.side_effect = [
            _mock_result([]),  # fr
            _mock_result([]),  # regression
            _mock_result([], scalar_return=0),  # downstream count = 0
        ]

        query_blast_radius(["src/a.py", "src/b.py"], engine=engine)

        calls = conn.execute.call_args_list
        assert len(calls) >= 3
        # calls[0] = fr_impact: args[0]=SQL, args[1]={"paths": [...]}
        # calls[1] = regression: args[0]=SQL, args[1]={"paths": [...]}
        # calls[2] = downstream count: args[0]=SQL (no paths)
        for i in (0, 1):
            _args, _kwargs = calls[i]
            assert len(_args) == 2  # SQL + params
            paths = _args[1].get("paths")
            assert paths is not None, f"call {i} missing paths"
            assert "src/a.py" in paths
            assert "src/b.py" in paths

    def test_no_engine_creates_and_disposes(self):
        """When no engine is passed, get_engine is called and disposed."""
        from blast_radius.query import query_blast_radius

        engine = MagicMock()
        conn = engine.connect.return_value.__enter__.return_value
        conn.execute.side_effect = [
            _mock_result([]),  # fr
            _mock_result([]),  # regression
            _mock_result([], scalar_return=0),  # downstream count = 0
        ]

        with patch("blast_radius.query.get_engine", return_value=engine) as mock_get:
            data = query_blast_radius(["src/foo.py"])

        assert data.fr_impact_set == []
        assert data.regression_set == []
        assert data.downstream_set == []
        mock_get.assert_called_once()
        engine.dispose.assert_called_once()

    # BTCAAAAA-41534: when the Postgres service container starts with an empty
    # database (CI scenario), the touch_index_* tables don't exist and
    # SQLAlchemy raises ProgrammingError (wrapping psycopg2.errors.UndefinedTable).
    # query_blast_radius must degrade to an empty result instead of raising,
    # otherwise the blast-radius worker reports issues_with_errors=1 and the
    # monitor opens a critical auto-alert even though the schema is the only
    # missing piece.
    def test_undefined_table_returns_empty_data(self):
        engine = MagicMock()
        conn = engine.connect.return_value.__enter__.return_value
        # Simulate "relation does not exist" on every sub-query.
        conn.execute.side_effect = ProgrammingError(
            "select", {}, Exception('relation "touch_index_fr_files" does not exist')
        )

        data = query_blast_radius(["src/foo.py"], engine=engine)

        assert data.fr_impact_set == []
        assert data.regression_set == []
        assert data.downstream_set == []
        assert data.downstream_note == "Phase 2 dep graph not yet available"
        # Each catch must roll back so the next sub-query can run cleanly.
        assert conn.rollback.call_count >= 1

    def test_undefined_table_on_single_query_does_not_block_others(self):
        """First query missing, second still runs and returns data."""
        engine = MagicMock()
        conn = engine.connect.return_value.__enter__.return_value
        # FR raises; regression returns one row; downstream count=0.
        conn.execute.side_effect = [
            ProgrammingError("select", {}, Exception("undefined table")),
            _mock_result(
                [MagicMock(bug_identifier="BTCAAAAA-500", bug_issue_id="bug-uuid")]
            ),
            _mock_result([], scalar_return=0),
        ]

        data = query_blast_radius(["src/foo.py"], engine=engine)

        assert data.fr_impact_set == []
        assert len(data.regression_set) == 1
        assert data.regression_set[0].bug_identifier == "BTCAAAAA-500"
        assert data.downstream_set == []
        # FR's ProgrammingError must trigger a rollback so regression can run.
        conn.rollback.assert_called_once_with()

    # BTCAAAAA-41534: even when ProgrammingError is caught, Postgres leaves the
    # transaction in an aborted state. Without an explicit rollback, the next
    # sub-query against the same connection raises `InFailedSqlTransaction`
    # (a different exception class — not ProgrammingError) and the worker
    # still reports issues_with_errors=1. Verify the rollback path handles this
    # case so the unit-level test mirrors real Postgres semantics.
    def test_in_failed_sql_transaction_after_undefined_table(self):
        """First query raises UndefinedTable; next raises InFailedSqlTransaction
        unless the catch path rolled the transaction back."""
        engine = MagicMock()
        conn = engine.connect.return_value.__enter__.return_value
        # First call: real Postgres would abort the transaction here.
        # Second call: real Postgres raises InFailedSqlTransaction.
        # With our rollback fix, the catch in _query_fr_impact calls
        # conn.rollback() before returning [], so the second call's
        # ProgrammingError-like error is caught by the next sub-query's
        # own try/except — no propagation.
        conn.execute.side_effect = [
            ProgrammingError(
                "select", {}, Exception('relation "touch_index_fr_files" does not exist')
            ),
            ProgrammingError(
                "select",
                {},
                Exception("current transaction is aborted, commands ignored"),
            ),
            _mock_result([], scalar_return=0),
        ]

        data = query_blast_radius(["src/foo.py"], engine=engine)

        assert data.fr_impact_set == []
        assert data.regression_set == []
        assert data.downstream_set == []
        # Rollback called for the FR catch + regression catch = 2.
        assert conn.rollback.call_count == 2


class TestToJsonDict:
    def test_serializes_empty_data(self):
        data = BlastRadiusData()
        result = to_json_dict(data)

        assert result["fr_impact_set"] == []
        assert result["regression_set"] == []
        assert result["downstream_set"] == []
        assert result["downstream_note"] == "Phase 2 dep graph not yet available"

    def test_serializes_fr_impact(self):
        data = BlastRadiusData(
            fr_impact_set=[
                FRImpact(
                    fr_identifier="FDR-100",
                    fr_owner_agent_id="agent-uuid",
                    fr_issue_id="issue-uuid",
                )
            ]
        )
        result = to_json_dict(data)

        assert len(result["fr_impact_set"]) == 1
        assert result["fr_impact_set"][0]["fr_identifier"] == "FDR-100"

    def test_serializes_regression(self):
        data = BlastRadiusData(
            regression_set=[
                RegressionRisk(
                    bug_identifier="BTCAAAAA-500",
                    bug_issue_id="bug-uuid",
                )
            ]
        )
        result = to_json_dict(data)

        assert len(result["regression_set"]) == 1
        assert result["regression_set"][0]["bug_identifier"] == "BTCAAAAA-500"

    def test_downstream_note_none_when_downstream_populated(self):
        data = BlastRadiusData(
            downstream_set=["src/dep.py"],
        )
        result = to_json_dict(data)

        assert result["downstream_set"] == ["src/dep.py"]
        assert result["downstream_note"] is None


class TestFRImpact:
    def test_dataclass_fields(self):
        fr = FRImpact(
            fr_identifier="FDR-100",
            fr_owner_agent_id="agent-uuid",
            fr_issue_id="issue-uuid",
        )
        assert fr.fr_identifier == "FDR-100"
        assert fr.fr_owner_agent_id == "agent-uuid"
        assert fr.fr_issue_id == "issue-uuid"


class TestRegressionRisk:
    def test_dataclass_fields(self):
        r = RegressionRisk(
            bug_identifier="BTCAAAAA-500",
            bug_issue_id="bug-uuid",
        )
        assert r.bug_identifier == "BTCAAAAA-500"
        assert r.bug_issue_id == "bug-uuid"
