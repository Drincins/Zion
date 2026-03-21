"""Add KPI plan/fact table and eq comparison operator.

Revision ID: 8a9b0c1d2e3f
Revises: 7b3c9f1a2d4e
Create Date: 2026-02-05 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8a9b0c1d2e3f"
down_revision = "7b3c9f1a2d4e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("ALTER TYPE kpi_comparison_operator ADD VALUE IF NOT EXISTS 'eq'")

    op.create_table(
        "kpi_plan_facts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("metric_id", sa.Integer(), sa.ForeignKey("kpi_metrics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("plan_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("fact_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("metric_id", "year", "month", name="uq_kpi_plan_facts_metric_period"),
    )
    op.create_index(
        "ix_kpi_plan_facts_metric_period",
        "kpi_plan_facts",
        ["metric_id", "year", "month"],
    )


def downgrade() -> None:
    op.drop_index("ix_kpi_plan_facts_metric_period", table_name="kpi_plan_facts")
    op.drop_table("kpi_plan_facts")
