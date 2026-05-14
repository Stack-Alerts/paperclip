"""
REQ-DATA-003 Verification: Database layer under optimizer_v3/database
provides unified ORM access for 9 managers.

Validates:
- All ORM managers are correctly connected and operational
- Schema integrity across all tables
- Connection handling and pool behavior
- End-to-end cross-manager workflow
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import text, inspect


# ---------------------------------------------------------------------------
# Schema integrity
# ---------------------------------------------------------------------------

_REQUIRED_MANAGER_TABLES = {
    "strategies",
    "strategy_versions",
    "strategy_block_versions",
    "ai_recommendations",
    "strategy_test_results",
    "validation_reports",
}
_REQUIRED_CORE_TABLES = {
    "optimization_runs",
    "strategy_variations",
    "signal_events",
    "signal_metrics",
    "training_sessions",
    "session_states",
    "backtest_results",
}
_REQUIRED_TRACE_TABLES = {
    "trace_requirements",
    "trace_test_cases",
    "trace_issues",
    "trace_links",
}
_ALL_REQUIRED_TABLES = (
    _REQUIRED_MANAGER_TABLES | _REQUIRED_CORE_TABLES | _REQUIRED_TRACE_TABLES
)

# Each specialised manager should have at least these columns to be "operational"
_MANAGER_COLUMNS = {
    "strategies": {"strategy_id", "name", "created_at", "updated_at"},
    "strategy_versions": {
        "version_id", "strategy_id", "version_number", "name",
        "blocks", "parameters", "entry_conditions", "exit_conditions",
        "risk_management", "backtest_config", "created_at",
    },
    "ai_recommendations": {
        "recommendation_id", "strategy_id", "recommendation_type",
        "title", "description", "rationale", "suggested_changes",
        "applied", "confidence_score", "created_at",
    },
    "strategy_test_results": {
        "result_id", "strategy_id", "version_id", "test_type",
        "test_config", "start_date", "end_date", "metrics", "created_at",
    },
    "validation_reports": {
        "report_id", "strategy_id", "version_id",
        "is_valid", "total_issues", "issues", "created_at",
    },
}


class TestSchemaIntegrity:
    def test_all_required_tables_exist(self, db_manager_for_testing):
        inspector = inspect(db_manager_for_testing.engine)
        existing = set(inspector.get_table_names())
        missing = _ALL_REQUIRED_TABLES - existing
        assert not missing, (
            f"Missing required tables: {sorted(missing)}"
        )

    def test_manager_tables_have_required_columns(self, db_manager_for_testing):
        inspector = inspect(db_manager_for_testing.engine)
        for table, required_cols in _MANAGER_COLUMNS.items():
            existing_cols = {c["name"] for c in inspector.get_columns(table)}
            missing_cols = required_cols - existing_cols
            assert not missing_cols, (
                f"Table '{table}' missing required columns: {sorted(missing_cols)}"
            )

    def test_manager_tables_have_primary_key(self, db_manager_for_testing):
        inspector = inspect(db_manager_for_testing.engine)
        for table in _REQUIRED_MANAGER_TABLES:
            pk = inspector.get_pk_constraint(table)
            assert pk and pk.get("constrained_columns"), (
                f"Table '{table}' has no primary key"
            )

    @pytest.mark.parametrize("table", sorted(_REQUIRED_MANAGER_TABLES))
    def test_manager_table_is_not_empty_if_data_exists(self, db_manager_for_testing, table):
        """Verify manager table is queryable (does not crash on empty result)."""
        with db_manager_for_testing.session_scope() as session:
            result = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        assert isinstance(result, int), (
            f"Table '{table}' should be queryable; got {type(result)}"
        )


# ---------------------------------------------------------------------------
# Connection handling
# ---------------------------------------------------------------------------

class TestConnectionHandling:
    def test_test_connection_returns_true(self, db_manager_for_testing):
        assert db_manager_for_testing.test_connection() is True

    def test_connection_info_returns_dict(self, db_manager_for_testing):
        info = db_manager_for_testing.get_connection_info()
        assert isinstance(info, dict)
        assert "driver" in info
        assert "host" in info
        assert "database" in info

    def test_engine_is_postgresql(self, db_manager_for_testing):
        driver = db_manager_for_testing.engine.url.drivername
        assert "postgresql" in driver
        assert "sqlite" not in driver

    def test_session_scope_commits_successfully(self, db_manager_for_testing):
        with db_manager_for_testing.session_scope() as session:
            result = session.execute(text("SELECT 1")).scalar()
        assert result == 1

    def test_close_does_not_raise(self, db_manager_for_testing):
        """Closing should be a no-op safe to call for cleanup."""
        db_manager_for_testing.close()


# ---------------------------------------------------------------------------
# DatabaseManager unified facade
# ---------------------------------------------------------------------------

class TestDatabaseManagerUnifiedFacade:
    def test_manager_has_strategy_submanager(self, db_manager_for_testing):
        from src.optimizer_v3.database.strategy_manager import StrategyDatabaseManager
        assert isinstance(db_manager_for_testing.strategy, StrategyDatabaseManager)

    def test_manager_has_ai_recommendations_submanager(self, db_manager_for_testing):
        from src.optimizer_v3.database.ai_recommendations_manager import AIRecommendationsManager
        assert isinstance(db_manager_for_testing.ai_recommendations, AIRecommendationsManager)

    def test_manager_has_test_results_submanager(self, db_manager_for_testing):
        from src.optimizer_v3.database.test_results_manager import TestResultsManager
        assert isinstance(db_manager_for_testing.test_results, TestResultsManager)


# ---------------------------------------------------------------------------
# Strategy manager (via DatabaseManager.strategy)
# ---------------------------------------------------------------------------

class TestStrategyDatabaseManager:
    def test_create_strategy_returns_id(self, db_manager_for_testing):
        strategy_id = db_manager_for_testing.strategy.create_strategy("REQ-DATA-003 Test")
        assert strategy_id.startswith("strategy_")
        assert len(strategy_id) > len("strategy_")

    def test_create_strategy_version_returns_uuid(self, db_manager_for_testing):
        sid = db_manager_for_testing.strategy.create_strategy("Version Test")
        vid = db_manager_for_testing.strategy.create_strategy_version({
            "strategy_id": sid,
            "name": "Version Test v1",
            "description": "REQ-DATA-003 test version",
            "blocks": [{"name": "block1", "signals": [], "parameters": {}}],
            "signals": {},
            "parameters": {"param1": "value1"},
            "entry_conditions": {},
            "exit_conditions": [],
            "risk_management": {},
            "backtest_config": {},
        })
        import uuid as _uuid
        try:
            _uuid.UUID(vid)
        except ValueError:
            pytest.fail(f"Version ID is not a valid UUID: {vid!r}")

    def test_get_all_strategies_after_create(self, db_manager_for_testing):
        sid = db_manager_for_testing.strategy.create_strategy("GetAll Test")
        strategies = db_manager_for_testing.strategy.get_all_strategies()
        ids = [s["strategy_id"] for s in strategies]
        assert sid in ids

    def test_get_create_strategy_with_empty_name_raises(self, db_manager_for_testing):
        with pytest.raises(ValueError):
            db_manager_for_testing.strategy.create_strategy("   ")

    def test_create_version_missing_required_fields_raises(self, db_manager_for_testing):
        sid = db_manager_for_testing.strategy.create_strategy("Invalid Version Test")
        with pytest.raises(ValueError, match="Missing required fields"):
            db_manager_for_testing.strategy.create_strategy_version({
                "strategy_id": sid,
            })


# ---------------------------------------------------------------------------
# AI recommendations manager (via DatabaseManager.ai_recommendations)
# ---------------------------------------------------------------------------

class TestAIRecommendationsManager:
    def test_create_recommendation_returns_uuid(self, db_manager_for_testing):
        sid = db_manager_for_testing.strategy.create_strategy("AI Rec Test")
        rid = db_manager_for_testing.ai_recommendations.create_recommendation({
            "strategy_id": sid,
            "recommendation_type": "performance",
            "title": "Test Recommendation",
            "description": "A test recommendation for REQ-DATA-003",
            "rationale": "Testing database orchestration",
            "suggested_changes": {"parameter": "value"},
            "confidence_score": 0.85,
        })
        import uuid as _uuid
        try:
            _uuid.UUID(rid)
        except ValueError:
            pytest.fail(f"Recommendation ID is not a valid UUID: {rid!r}")

    def test_get_recommendation_returns_data(self, db_manager_for_testing):
        sid = db_manager_for_testing.strategy.create_strategy("Get Rec Test")
        rid = db_manager_for_testing.ai_recommendations.create_recommendation({
            "strategy_id": sid,
            "recommendation_type": "risk",
            "title": "Retrievable Rec",
            "description": "Can we get it back?",
            "rationale": "Test retrieval",
            "suggested_changes": {"risk": 0.02},
        })
        rec = db_manager_for_testing.ai_recommendations.get_recommendation(rid)
        assert rec is not None
        assert rec["title"] == "Retrievable Rec"
        assert rec["recommendation_type"] == "risk"

    def test_get_strategy_recommendations_filters(self, db_manager_for_testing):
        sid = db_manager_for_testing.strategy.create_strategy("Filter Rec Test")
        db_manager_for_testing.ai_recommendations.create_recommendation({
            "strategy_id": sid,
            "recommendation_type": "signal",
            "title": "Signal Rec",
            "description": "Signal improvement",
            "rationale": "Better signals",
            "suggested_changes": {},
        })
        recs = db_manager_for_testing.ai_recommendations.get_strategy_recommendations(sid)
        assert len(recs) >= 1
        assert any(r["strategy_id"] == sid for r in recs)

    def test_mark_applied_and_verify(self, db_manager_for_testing):
        sid = db_manager_for_testing.strategy.create_strategy("Apply Test")
        rid = db_manager_for_testing.ai_recommendations.create_recommendation({
            "strategy_id": sid,
            "recommendation_type": "entry",
            "title": "Apply Me",
            "description": "Should be marked applied",
            "rationale": "Test apply",
            "suggested_changes": {},
        })
        result = db_manager_for_testing.ai_recommendations.mark_applied(
            rid, "00000000-0000-0000-0000-000000000000"
        )
        assert result is True
        rec = db_manager_for_testing.ai_recommendations.get_recommendation(rid)
        assert rec["applied"] is True

    def test_create_recommendation_missing_required_raises(self, db_manager_for_testing):
        with pytest.raises(ValueError, match="Missing required fields"):
            db_manager_for_testing.ai_recommendations.create_recommendation({
                "strategy_id": "nope",
            })


# ---------------------------------------------------------------------------
# Test results manager (via DatabaseManager.test_results)
# ---------------------------------------------------------------------------

class TestTestResultsManager:
    def _create_version_for_test(self, db):
        sid = db.strategy.create_strategy("TestResult Strategy")
        vid = db.strategy.create_strategy_version({
            "strategy_id": sid,
            "name": "TestResult v1",
            "blocks": [{"name": "b1", "signals": [], "parameters": {}}],
            "signals": {},
            "parameters": {},
            "entry_conditions": {},
            "exit_conditions": [],
            "risk_management": {},
            "backtest_config": {},
            "tags": ["test"],
        })
        return sid, vid

    def test_create_test_result_returns_uuid(self, db_manager_for_testing):
        sid, vid = self._create_version_for_test(db_manager_for_testing)
        rid = db_manager_for_testing.test_results.create_test_result({
            "strategy_id": sid,
            "strategy_version_id": vid,
            "test_type": "backtest",
            "test_config": {"timeframe": "1h"},
            "start_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "end_date": datetime(2024, 6, 1, tzinfo=timezone.utc),
            "metrics": {
                "sharpe_ratio": 1.5,
                "total_return_pct": 12.0,
                "max_drawdown_pct": 5.0,
                "win_rate": 0.55,
                "profit_factor": 1.8,
                "total_trades": 42,
            },
        })
        import uuid as _uuid
        try:
            _uuid.UUID(rid)
        except ValueError:
            pytest.fail(f"Test result ID is not a valid UUID: {rid!r}")

    def test_get_test_result_returns_full_data(self, db_manager_for_testing):
        sid, vid = self._create_version_for_test(db_manager_for_testing)
        rid = db_manager_for_testing.test_results.create_test_result({
            "strategy_id": sid,
            "strategy_version_id": vid,
            "test_type": "forward_test",
            "test_config": {"timeframe": "4h"},
            "start_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "end_date": datetime(2024, 6, 1, tzinfo=timezone.utc),
            "metrics": {"sharpe_ratio": 0.9, "total_return_pct": 5.0},
        })
        result = db_manager_for_testing.test_results.get_test_result(rid)
        assert result is not None
        assert result["test_type"] == "forward_test"
        assert result["sharpe_ratio"] == 0.9
        assert "metrics" in result

    def test_get_strategy_test_results_filters(self, db_manager_for_testing):
        sid, vid = self._create_version_for_test(db_manager_for_testing)
        db_manager_for_testing.test_results.create_test_result({
            "strategy_id": sid,
            "strategy_version_id": vid,
            "test_type": "backtest",
            "test_config": {},
            "start_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "end_date": datetime(2024, 2, 1, tzinfo=timezone.utc),
            "metrics": {"total_return_pct": 3.0},
        })
        results = db_manager_for_testing.test_results.get_strategy_test_results(sid)
        assert len(results) >= 1
        assert all(r["strategy_id"] == sid for r in results)

    def test_create_missing_required_fields_raises(self, db_manager_for_testing):
        with pytest.raises(ValueError, match="Missing required fields"):
            db_manager_for_testing.test_results.create_test_result({})


# ---------------------------------------------------------------------------
# Cross-manager end-to-end workflow
# ---------------------------------------------------------------------------

class TestCrossManagerWorkflow:
    def test_full_lifecycle(self, db_manager_for_testing):
        db = db_manager_for_testing

        # 1. Create a strategy
        sid = db.strategy.create_strategy("E2E Strategy")

        # 2. Create a version
        vid = db.strategy.create_strategy_version({
            "strategy_id": sid,
            "name": "E2E v1",
            "blocks": [{"name": "signal_breakout", "signals": [], "parameters": {"period": 20}}],
            "signals": {},
            "parameters": {"period": 20},
            "entry_conditions": {},
            "exit_conditions": [],
            "risk_management": {"max_position_pct": 0.10},
            "backtest_config": {"timeframe": "1h"},
        })

        # 3. Record a test result
        result_id = db.test_results.create_test_result({
            "strategy_id": sid,
            "strategy_version_id": vid,
            "test_type": "backtest",
            "test_config": {"timeframe": "1h"},
            "start_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "end_date": datetime(2024, 3, 1, tzinfo=timezone.utc),
            "metrics": {
                "sharpe_ratio": 2.1,
                "profit_factor": 2.5,
                "win_rate": 0.62,
                "total_return_pct": 18.5,
                "max_drawdown_pct": 4.2,
                "total_trades": 85,
            },
        })

        # 4. Create an AI recommendation
        rec_id = db.ai_recommendations.create_recommendation({
            "strategy_id": sid,
            "strategy_version_id": vid,
            "recommendation_type": "parameter",
            "title": "Increase period to 50",
            "description": "The 20-period breakout is too noisy",
            "rationale": "Sharpe improves with higher period",
            "suggested_changes": {"parameters": {"period": 50}},
            "confidence_score": 0.92,
        })

        # 5. Verify the chain
        fetched_result = db.test_results.get_test_result(result_id)
        assert fetched_result is not None
        assert fetched_result["sharpe_ratio"] == 2.1

        fetched_rec = db.ai_recommendations.get_recommendation(rec_id)
        assert fetched_rec is not None
        assert fetched_rec["recommendation_type"] == "parameter"

        # 6. Verify strategy listing
        strategies = db.strategy.get_all_strategies()
        assert any(s["strategy_id"] == sid for s in strategies)
