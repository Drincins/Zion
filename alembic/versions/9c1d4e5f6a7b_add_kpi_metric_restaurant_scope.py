"""Add restaurant scope fields to KPI metrics.

Revision ID: 9c1d4e5f6a7b
Revises: 8a9b0c1d2e3f
Create Date: 2026-02-05 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9c1d4e5f6a7b"
down_revision = "8a9b0c1d2e3f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "kpi_metrics",
        sa.Column("all_restaurants", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "kpi_metrics",
        sa.Column("restaurant_ids", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("kpi_metrics", "restaurant_ids")
    op.drop_column("kpi_metrics", "all_restaurants")
