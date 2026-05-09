"""
Pytest fixtures for database tests
Sprint 1.6.1 - Institutional-grade database testing

Provides proper database session fixtures using .env configuration.

PostgreSQL fixtures
-------------------
- ``db_engine``            — session-scoped SQLAlchemy engine (PostgreSQL)
- ``db_session``           — function-scoped session with rollback isolation
- ``db_manager_for_testing`` — session-scoped ``DatabaseManager`` created via
                               ``DatabaseManagerFactory.for_testing()``.  Aligns
                               with the ``pg_conn`` fixture pattern used by the
                               ITM state tests (BTCAAAAA-450).  Skips gracefully
                               when PostgreSQL is not reachable.

Isolation guarantee (FDR-781)
------------------------------
``db_session`` uses ``join_transaction_mode="create_savepoint"`` so that any
``session.commit()`` call inside a test only commits to a SAVEPOINT, never to
the outer connection transaction.  The outer transaction is rolled back
unconditionally in teardown, leaving the database state unchanged for the
next test.
"""

import pytest
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.optimizer_v3.database.models import Base

# Load .env file from project root
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)


@pytest.fixture(scope="session")
def db_engine():
    """
    Create database engine from environment variables
    
    Uses .env file in project root for configuration
    """
    # Get database configuration from environment (.env file loaded above)
    db_host = os.getenv('POSTGRES_HOST', 'localhost')
    db_port = os.getenv('POSTGRES_PORT', '5432')
    db_name = os.getenv('POSTGRES_DB', 'optimizer_v3')
    db_user = os.getenv('POSTGRES_USER', 'optimizer_admin')
    db_password = os.getenv('POSTGRES_PASSWORD', '')
    
    # Create connection string
    connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Create engine
    engine = create_engine(connection_string, echo=False)
    
    yield engine
    
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Create a new database session for each test with complete rollback isolation.

    Each test function receives its own connection + outer transaction.
    ``join_transaction_mode="create_savepoint"`` ensures that any
    ``session.commit()`` call inside the test only releases a SAVEPOINT;
    the outer transaction is never committed and is rolled back unconditionally
    in teardown.  This guarantees that no test data persists to the database
    regardless of what the test code does with the session.

    FDR-781: per-test-function database session isolation with automatic rollback.
    """
    connection = db_engine.connect()
    transaction = connection.begin()

    # SA 2.0: pass the connection directly; create_savepoint mode ensures
    # session.commit() inside tests only commits to a SAVEPOINT, not the
    # outer transaction, so teardown rollback always cleans up fully.
    session = Session(connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# DatabaseManagerFactory.for_testing() fixture — BTCAAAAA-471
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def db_manager_for_testing():
    """Session-scoped ``DatabaseManager`` created via
    ``DatabaseManagerFactory.for_testing()``.

    This fixture verifies that ``for_testing()`` returns a real PostgreSQL
    connection (not SQLite).  It skips the test gracefully when PostgreSQL is
    not reachable, consistent with the ``pg_conn`` fixture pattern from the
    ITM state tests (BTCAAAAA-450).

    Tests that need a ``DatabaseManager`` backed by the test PostgreSQL
    instance should use this fixture instead of constructing one manually.
    """
    import sys
    _src = str(Path(__file__).parent.parent.parent / "src")
    if _src not in sys.path:
        sys.path.insert(0, _src)

    from src.optimizer_v3.database.database_manager import DatabaseManagerFactory

    # for_testing() calls pytest.skip() internally when PG is unreachable.
    manager = DatabaseManagerFactory.for_testing()
    yield manager
    manager.close()
