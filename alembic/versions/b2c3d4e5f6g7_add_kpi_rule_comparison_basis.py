"""Add comparison basis to KPI rules.

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-05 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6g7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    comparison_basis = sa.Enum(
        "absolute",
        "plan_percent",
        "plan_delta_percent",
        name="kpi_rule_comparison_basis",
    )
    comparison_basis.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "kpi_rules",
        sa.Column(
            "comparison_basis",
            comparison_basis,
            nullable=False,
            server_default="plan_percent",
        ),
    )
    op.alter_column("kpi_rules", "comparison_basis", server_default=None)


def downgrade() -> None:
    op.drop_column("kpi_rules", "comparison_basis")
    comparison_basis = sa.Enum(
        "absolute",
        "plan_percent",
        "plan_delta_percent",
        name="kpi_rule_comparison_basis",
    )
    comparison_basis.drop(op.get_bind(), checkfirst=True)
