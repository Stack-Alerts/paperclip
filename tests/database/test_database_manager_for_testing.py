"""
Tests for DatabaseManagerFactory.for_testing() — BTCAAAAA-471

Verifies that for_testing() returns a real PostgreSQL connection
(not an SQLite shim) and that the returned DatabaseManager behaves
correctly against the test database.

These tests skip gracefully when PostgreSQL is not reachable, consistent
with the pg_conn fixture pattern introduced in BTCAAAAA-450.
"""

import os
import sys
import pytest
from pathlib import Path

from src.optimizer_v3.database.database_manager import DatabaseManager, DatabaseManagerFactory


# ---------------------------------------------------------------------------
# Tests against the for_testing() factory method
# ---------------------------------------------------------------------------

class TestDatabaseManagerForTesting:
    """Unit tests for DatabaseManagerFactory.for_testing()."""

    def test_for_testing_returns_database_manager_instance(self, db_manager_for_testing):
        """for_testing() must return a DatabaseManager, not None or wrong type."""
        assert isinstance(db_manager_for_testing, DatabaseManager), (
            "DatabaseManagerFactory.for_testing() must return a DatabaseManager instance"
        )

    def test_for_testing_connection_string_is_postgresql(self, db_manager_for_testing):
        """Connection string must use postgresql:// driver, not sqlite://."""
        driver = db_manager_for_testing.engine.url.drivername
        assert "postgresql" in driver, (
            f"for_testing() must return a PostgreSQL connection, got driver: {driver!r}. "
            "SQLite shim must not be used."
        )

    def test_for_testing_no_sqlite_in_driver(self, db_manager_for_testing):
        """Explicitly assert that sqlite is not used."""
        driver = db_manager_for_testing.engine.url.drivername
        assert "sqlite" not in driver, (
            f"for_testing() must NOT return an SQLite connection. Got driver: {driver!r}"
        )

    def test_for_testing_connection_info_has_expected_keys(self, db_manager_for_testing):
        """get_connection_info() returns required keys for a real DB."""
        info = db_manager_for_testing.get_connection_info()
        for key in ("driver", "host", "port", "database", "username"):
            assert key in info, f"Connection info missing key: {key!r}"

    def test_for_testing_host_is_not_none(self, db_manager_for_testing):
        """A PostgreSQL manager must have a non-null host."""
        info = db_manager_for_testing.get_connection_info()
        assert info["host"] is not None, (
            "for_testing() connection must have a host (SQLite :memory: has no host)"
        )

    def test_for_testing_database_is_not_memory(self, db_manager_for_testing):
        """The database name must not be ':memory:' (SQLite in-memory marker)."""
        info = db_manager_for_testing.get_connection_info()
        db_name = info.get("database", "")
        assert ":memory:" not in str(db_name), (
            "for_testing() must not use an in-memory SQLite database"
        )

    def test_for_testing_can_execute_select_one(self, db_manager_for_testing):
        """A live PostgreSQL connection must handle a simple SELECT 1."""
        from sqlalchemy import text
        with db_manager_for_testing.session_scope() as session:
            result = session.execute(text("SELECT 1")).scalar()
        assert result == 1, f"Expected SELECT 1 to return 1, got {result!r}"

    def test_for_testing_pool_size_is_one(self, db_manager_for_testing):
        """Pool size for the test manager must be 1 (lightweight test config)."""
        pool_size = db_manager_for_testing.engine.pool.size()
        assert pool_size == 1, (
            f"Test DatabaseManager pool_size should be 1, got {pool_size}"
        )


# ---------------------------------------------------------------------------
# Regression: ensure SQLite shim is gone from the factory
# ---------------------------------------------------------------------------

class TestNoSQLiteShimInForTesting:
    """Regression tests ensuring the SQLite shim has been fully removed."""

    def test_for_testing_method_signature_has_no_in_memory_param(self):
        """The old in_memory parameter must no longer exist."""
        import inspect
        sig = inspect.signature(DatabaseManagerFactory.for_testing)
        assert "in_memory" not in sig.parameters, (
            "The in_memory parameter was part of the SQLite shim — it must be removed. "
            f"Current parameters: {list(sig.parameters)}"
        )

    def test_for_testing_source_has_no_sqlite_connection_string(self):
        """Source code of for_testing() must contain no sqlite:/// connection strings."""
        import inspect
        source = inspect.getsource(DatabaseManagerFactory.for_testing)
        assert "sqlite:///" not in source, (
            "DatabaseManagerFactory.for_testing() source still contains a sqlite:/// "
            "connection string. All SQLite connection strings must be removed."
        )
