"""Add plan direction to KPI metric groups.

Revision ID: 0f1e2d3c4b5a
Revises: e5f6a7b8c9d0
Create Date: 2026-03-10 18:20:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0f1e2d3c4b5a"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


PLAN_DIRECTION_ENUM = sa.Enum(
    "higher_better",
    "lower_better",
    name="kpi_plan_direction",
)


def upgrade() -> None:
    bind = op.get_bind()
    PLAN_DIRECTION_ENUM.create(bind, checkfirst=True)
    op.add_column(
        "kpi_metric_groups",
        sa.Column(
            "plan_direction",
            PLAN_DIRECTION_ENUM,
            nullable=False,
            server_default="higher_better",
        ),
    )
    op.execute("UPDATE kpi_metric_groups SET plan_direction = 'higher_better' WHERE plan_direction IS NULL")
    op.alter_column("kpi_metric_groups", "plan_direction", server_default=None)


def downgrade() -> None:
    op.drop_column("kpi_metric_groups", "plan_direction")
