"""Add KPI plan preferences storage.

Revision ID: b7f8c9d0e1f2
Revises: a7d8e9f0b1c2
Create Date: 2026-03-07 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7f8c9d0e1f2"
down_revision = "a7d8e9f0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kpi_plan_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("metric_id", sa.Integer(), nullable=False),
        sa.Column("plan_mode", sa.String(length=32), nullable=False, server_default="shared"),
        sa.Column("restaurant_id", sa.Integer(), nullable=True),
        sa.Column("is_dynamic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("selected_month", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["metric_id"], ["kpi_metrics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_kpi_plan_preferences_metric_id",
        "kpi_plan_preferences",
        ["metric_id"],
        unique=True,
    )
    op.create_index(
        "ix_kpi_plan_preferences_restaurant_id",
        "kpi_plan_preferences",
        ["restaurant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_kpi_plan_preferences_restaurant_id", table_name="kpi_plan_preferences")
    op.drop_index("ix_kpi_plan_preferences_metric_id", table_name="kpi_plan_preferences")
    op.drop_table("kpi_plan_preferences")
