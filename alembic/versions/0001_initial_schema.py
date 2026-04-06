"""initial schema: projects, agent_runs, cost_records, human_gates

Revision ID: 0001
Revises:
Create Date: 2026-04-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# ============================================================
# REVISION IDENTIFIERS
# ============================================================
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ============================================================
# MIGRATIONS
# ============================================================


def upgrade() -> None:
    """Create all four core AutoForge tables and their indexes."""

    op.create_table(
        "projects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("project_id", sa.VARCHAR(length=100), nullable=False),
        sa.Column("name", sa.VARCHAR(length=255), nullable=False),
        sa.Column("client_name", sa.VARCHAR(length=255), nullable=False),
        sa.Column(
            "status",
            sa.VARCHAR(length=50),
            server_default=sa.text("'intake'"),
            nullable=False,
        ),
        sa.Column("manifest_path", sa.VARCHAR(length=500), nullable=True),
        sa.Column("github_repo", sa.VARCHAR(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("approved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id"),
    )

    op.create_table(
        "agent_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("run_id", sa.VARCHAR(length=100), nullable=False),
        sa.Column("project_id", sa.VARCHAR(length=100), nullable=False),
        sa.Column("agent_name", sa.VARCHAR(length=100), nullable=False),
        sa.Column("issue_id", sa.VARCHAR(length=50), nullable=True),
        sa.Column("branch", sa.VARCHAR(length=255), nullable=True),
        sa.Column(
            "status",
            sa.VARCHAR(length=50),
            server_default=sa.text("'running'"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "tokens_in",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "tokens_out",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("model", sa.VARCHAR(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index("idx_agent_runs_project_id", "agent_runs", ["project_id"])
    op.create_index("idx_agent_runs_status", "agent_runs", ["status"])

    op.create_table(
        "cost_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("run_id", sa.VARCHAR(length=100), nullable=False),
        sa.Column("project_id", sa.VARCHAR(length=100), nullable=False),
        sa.Column("model", sa.VARCHAR(length=100), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column(
            "recorded_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_cost_records_project_id", "cost_records", ["project_id"])

    op.create_table(
        "human_gates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("gate_id", sa.VARCHAR(length=100), nullable=False),
        sa.Column("project_id", sa.VARCHAR(length=100), nullable=False),
        sa.Column("gate_type", sa.VARCHAR(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.VARCHAR(length=50),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("github_issue_url", sa.VARCHAR(length=500), nullable=True),
        sa.Column("telegram_message_id", sa.VARCHAR(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.VARCHAR(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gate_id"),
    )
    op.create_index("idx_human_gates_project_id", "human_gates", ["project_id"])
    op.create_index("idx_human_gates_status", "human_gates", ["status"])


def downgrade() -> None:
    """Drop all four core AutoForge tables and their indexes."""

    op.drop_index("idx_human_gates_status", table_name="human_gates")
    op.drop_index("idx_human_gates_project_id", table_name="human_gates")
    op.drop_table("human_gates")

    op.drop_index("idx_cost_records_project_id", table_name="cost_records")
    op.drop_table("cost_records")

    op.drop_index("idx_agent_runs_status", table_name="agent_runs")
    op.drop_index("idx_agent_runs_project_id", table_name="agent_runs")
    op.drop_table("agent_runs")

    op.drop_table("projects")
