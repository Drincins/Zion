"""Add default payroll adjustment types to KPI metrics.

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-02-05 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c3d4e5f6g7h8"
down_revision = "b2c3d4e5f6g7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "kpi_metrics",
        sa.Column(
            "bonus_adjustment_type_id",
            sa.Integer(),
            sa.ForeignKey("payroll_adjustment_types.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "kpi_metrics",
        sa.Column(
            "penalty_adjustment_type_id",
            sa.Integer(),
            sa.ForeignKey("payroll_adjustment_types.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("kpi_metrics", "penalty_adjustment_type_id")
    op.drop_column("kpi_metrics", "bonus_adjustment_type_id")

