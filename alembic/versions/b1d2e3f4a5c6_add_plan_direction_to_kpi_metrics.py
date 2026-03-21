"""Add plan direction to KPI metrics.

Revision ID: b1d2e3f4a5c6
Revises: a9c8b7d6e5f4
Create Date: 2026-03-10 02:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b1d2e3f4a5c6"
down_revision = "a9c8b7d6e5f4"
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
        "kpi_metrics",
        sa.Column(
            "plan_direction",
            PLAN_DIRECTION_ENUM,
            nullable=False,
            server_default="higher_better",
        ),
    )
    op.execute("UPDATE kpi_metrics SET plan_direction = 'higher_better' WHERE plan_direction IS NULL")
    op.alter_column("kpi_metrics", "plan_direction", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_column("kpi_metrics", "plan_direction")
    PLAN_DIRECTION_ENUM.drop(bind, checkfirst=True)
