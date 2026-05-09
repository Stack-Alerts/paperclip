"""Add ai_consultant_audit table

Revision ID: 20260509_ai_consultant_audit
Revises: 20260215_add_strategy_type
Create Date: 2026-05-09

P1.5 — Audit Log Schema: captures all AI Consultant activity for compliance.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260509_ai_consultant_audit"
down_revision = "20260509_add_ai_readonly_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_consultant_audit",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("session_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column(
            "timestamp",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("strategy_id", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("token_cost_usd", sa.Numeric(precision=18, scale=8), nullable=True),
    )

    op.create_index(
        "idx_ai_audit_session_id",
        "ai_consultant_audit",
        ["session_id"],
    )
    op.create_index(
        "idx_ai_audit_event_type",
        "ai_consultant_audit",
        ["event_type"],
    )
    op.create_index(
        "idx_ai_audit_timestamp",
        "ai_consultant_audit",
        ["timestamp"],
    )
    op.create_index(
        "idx_ai_audit_strategy_id",
        "ai_consultant_audit",
        ["strategy_id"],
        postgresql_where=sa.text("strategy_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_ai_audit_strategy_id", table_name="ai_consultant_audit")
    op.drop_index("idx_ai_audit_timestamp", table_name="ai_consultant_audit")
    op.drop_index("idx_ai_audit_event_type", table_name="ai_consultant_audit")
    op.drop_index("idx_ai_audit_session_id", table_name="ai_consultant_audit")
    op.drop_table("ai_consultant_audit")
