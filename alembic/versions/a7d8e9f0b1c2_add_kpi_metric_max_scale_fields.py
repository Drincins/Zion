"""Add max scale fields for KPI metrics.

Revision ID: a7d8e9f0b1c2
Revises: e1f2a3b4c5d6
Create Date: 2026-03-05 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a7d8e9f0b1c2"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "kpi_metrics",
        sa.Column("use_max_scale", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "kpi_metrics",
        sa.Column("max_scale_value", sa.Numeric(14, 4), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("kpi_metrics", "max_scale_value")
    op.drop_column("kpi_metrics", "use_max_scale")
