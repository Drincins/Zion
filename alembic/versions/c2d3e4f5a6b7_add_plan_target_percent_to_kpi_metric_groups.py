"""Add plan target percent to KPI metric groups.

Revision ID: c2d3e4f5a6b7
Revises: b1d2e3f4a5c6
Create Date: 2026-03-10 15:10:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c2d3e4f5a6b7"
down_revision = "b1d2e3f4a5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "kpi_metric_groups",
        sa.Column("plan_target_percent", sa.Numeric(5, 2), nullable=False, server_default="100"),
    )
    op.execute("UPDATE kpi_metric_groups SET plan_target_percent = 100 WHERE plan_target_percent IS NULL")
    op.alter_column("kpi_metric_groups", "plan_target_percent", server_default=None)


def downgrade() -> None:
    op.drop_column("kpi_metric_groups", "plan_target_percent")
