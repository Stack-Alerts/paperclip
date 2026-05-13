"""add_traceability_schema

Revision ID: 20260513_add_traceability_schema
Revises: 20260512_add_bug_files_updated_at
Create Date: 2026-05-13

ADR-0002: Add traceability schema for Requirement \u2192 TestCase \u2192 Issue
traceability layer alongside the existing Touch Index tables.

Four new tables:
  - trace_requirements   — Feature Design Requirements synced from Paperclip
  - trace_test_cases     — Test cases discovered from pytest collection
  - trace_issues         — Paperclip issues implementing/fixing requirements
  - trace_links          — Core traceability edges with confidence scoring

This migration is additive — no existing tables are modified.
"""
import sqlalchemy as sa
from alembic import op

revision = "20260513_add_traceability_schema"
down_revision = "20260512_add_bug_files_updated_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- trace_requirements ---
    op.create_table(
        "trace_requirements",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("identifier", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("priority", sa.String(20), nullable=True),
        sa.Column("labels", sa.JSONB(), nullable=True),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("paperclip_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata", sa.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identifier"),
    )
    op.create_index("idx_trace_requirements_status", "trace_requirements", ["status"])
    op.create_index("idx_trace_requirements_paperclip_id", "trace_requirements", ["paperclip_id"])

    # --- trace_test_cases ---
    op.create_table(
        "trace_test_cases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("identifier", sa.String(300), nullable=False),
        sa.Column("test_file", sa.String(500), nullable=False),
        sa.Column("test_function", sa.String(300), nullable=False),
        sa.Column("test_class", sa.String(300), nullable=True),
        sa.Column("markers", sa.JSONB(), nullable=True),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("tags", sa.JSONB(), nullable=True),
        sa.Column("language", sa.String(20), nullable=False, server_default=sa.text("'python'")),
        sa.Column("component", sa.String(200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identifier"),
    )
    op.create_index("idx_trace_test_cases_test_file", "trace_test_cases", ["test_file"])
    op.create_index("idx_trace_test_cases_component", "trace_test_cases", ["component"])

    # --- trace_issues ---
    op.create_table(
        "trace_issues",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("identifier", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("issue_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("paperclip_id", sa.UUID(), nullable=True),
        sa.Column("labels", sa.JSONB(), nullable=True),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identifier"),
    )
    op.create_index("idx_trace_issues_paperclip_id", "trace_issues", ["paperclip_id"])
    op.create_index("idx_trace_issues_issue_type", "trace_issues", ["issue_type"])
    op.create_index("idx_trace_issues_status", "trace_issues", ["status"])

    # Add self-referential FK for trace_issues.parent_id after table creation
    op.create_foreign_key(
        "fk_trace_issues_parent",
        "trace_issues", "trace_issues",
        ["parent_id"], ["id"],
    )

    # --- trace_links ---
    op.create_table(
        "trace_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("requirement_id", sa.UUID(), nullable=True),
        sa.Column("test_case_id", sa.UUID(), nullable=True),
        sa.Column("issue_id", sa.UUID(), nullable=True),
        sa.Column("link_type", sa.String(30), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("metadata", sa.JSONB(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("requirement_id", "test_case_id", "issue_id", "link_type",
                            name="uq_trace_link_edge"),
    )
    op.create_index("idx_trace_links_requirement_id", "trace_links", ["requirement_id"])
    op.create_index("idx_trace_links_test_case_id", "trace_links", ["test_case_id"])
    op.create_index("idx_trace_links_issue_id", "trace_links", ["issue_id"])
    op.create_index("idx_trace_links_link_type", "trace_links", ["link_type"])

    # Foreign keys for trace_links
    op.create_foreign_key(
        "fk_trace_links_requirement",
        "trace_links", "trace_requirements",
        ["requirement_id"], ["id"],
    )
    op.create_foreign_key(
        "fk_trace_links_test_case",
        "trace_links", "trace_test_cases",
        ["test_case_id"], ["id"],
    )
    op.create_foreign_key(
        "fk_trace_links_issue",
        "trace_links", "trace_issues",
        ["issue_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_trace_links_issue", "trace_links", type_="foreignkey")
    op.drop_constraint("fk_trace_links_test_case", "trace_links", type_="foreignkey")
    op.drop_constraint("fk_trace_links_requirement", "trace_links", type_="foreignkey")
    op.drop_table("trace_links")
    op.drop_constraint("fk_trace_issues_parent", "trace_issues", type_="foreignkey")
    op.drop_table("trace_issues")
    op.drop_table("trace_test_cases")
    op.drop_table("trace_requirements")
