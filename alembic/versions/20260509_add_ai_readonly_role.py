"""add_ai_readonly_role

Revision ID: 20260509_add_ai_readonly_role
Revises: 20260215_add_strategy_type
Create Date: 2026-05-09

Creates the ai_readonly PostgreSQL role with SELECT-only grants on all relevant
result tables. This role is used exclusively by the AI Consultant query engine.
No INSERT/UPDATE/DELETE/DROP is ever granted.
"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '20260509_add_ai_readonly_role'
down_revision = '20260215_add_strategy_type'
branch_labels = None
depends_on = None

# Tables the AI Consultant is allowed to SELECT from.
# Extend this list when new tables are added to the results DB.
_READABLE_TABLES = [
    'strategies',
    'strategy_versions',
    'strategy_block_versions',
    'strategy_test_results',
    'signal_events',
    'signal_metrics',
    'backtest_results',
    'optimization_runs',
    'strategy_variations',
    'ai_recommendations',
    'validation_reports',
]


def upgrade():
    conn = op.get_bind()

    # 1. Create role if it does not already exist (idempotent).
    conn.execute(sa.text(
        "DO $$ BEGIN "
        "  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ai_readonly') THEN "
        "    CREATE ROLE ai_readonly NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT; "
        "  END IF; "
        "END $$;"
    ))

    # 2. Grant CONNECT on the database so the role can connect at all.
    conn.execute(sa.text(
        "GRANT CONNECT ON DATABASE optimizer_v3 TO ai_readonly;"
    ))

    # 3. Grant USAGE on the public schema.
    conn.execute(sa.text(
        "GRANT USAGE ON SCHEMA public TO ai_readonly;"
    ))

    # 4. Grant SELECT on each approved table — one statement per table so that
    #    if a table does not yet exist (e.g. in test DBs) the migration fails
    #    loudly rather than silently skipping grants.
    for table in _READABLE_TABLES:
        conn.execute(sa.text(
            f"GRANT SELECT ON TABLE {table} TO ai_readonly;"
        ))

    # 5. Explicitly REVOKE all write privileges to make the intent crystal-clear.
    #    PostgreSQL does not grant these by default to a new role, but being
    #    explicit here satisfies security audit requirements.
    conn.execute(sa.text(
        "REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public FROM ai_readonly;"
    ))

    # 6. Ensure future tables in the schema do NOT automatically get write grants.
    conn.execute(sa.text(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON TABLES FROM ai_readonly;"
    ))


def downgrade():
    conn = op.get_bind()

    # Revoke all grants and drop the role.
    for table in _READABLE_TABLES:
        conn.execute(sa.text(
            f"REVOKE ALL PRIVILEGES ON TABLE {table} FROM ai_readonly;"
        ))

    conn.execute(sa.text(
        "REVOKE ALL PRIVILEGES ON SCHEMA public FROM ai_readonly;"
    ))
    conn.execute(sa.text(
        "REVOKE CONNECT ON DATABASE optimizer_v3 FROM ai_readonly;"
    ))
    conn.execute(sa.text(
        "DROP ROLE IF EXISTS ai_readonly;"
    ))
