"""Add restaurant scope to KPI plan/fact.

Revision ID: a1b2c3d4e5f6
Revises: 9c1d4e5f6a7b
Create Date: 2026-02-05 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "9c1d4e5f6a7b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "kpi_plan_facts",
        sa.Column(
            "restaurant_id",
            sa.Integer(),
            sa.ForeignKey("restaurants.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.drop_constraint("uq_kpi_plan_facts_metric_period", "kpi_plan_facts", type_="unique")
    op.drop_index("ix_kpi_plan_facts_metric_period", table_name="kpi_plan_facts")
    op.create_unique_constraint(
        "uq_kpi_plan_facts_metric_period",
        "kpi_plan_facts",
        ["metric_id", "restaurant_id", "year", "month"],
    )
    op.create_index(
        "ix_kpi_plan_facts_metric_period",
        "kpi_plan_facts",
        ["metric_id", "restaurant_id", "year", "month"],
    )


def downgrade() -> None:
    op.drop_index("ix_kpi_plan_facts_metric_period", table_name="kpi_plan_facts")
    op.drop_constraint("uq_kpi_plan_facts_metric_period", "kpi_plan_facts", type_="unique")
    op.create_unique_constraint(
        "uq_kpi_plan_facts_metric_period",
        "kpi_plan_facts",
        ["metric_id", "year", "month"],
    )
    op.create_index(
        "ix_kpi_plan_facts_metric_period",
        "kpi_plan_facts",
        ["metric_id", "year", "month"],
    )
    op.drop_column("kpi_plan_facts", "restaurant_id")
