"""Add KPI metric groups.

Revision ID: a9c8b7d6e5f4
Revises: e7c4a1b2d3f9
Create Date: 2026-03-10 01:20:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a9c8b7d6e5f4"
down_revision = "e7c4a1b2d3f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kpi_metric_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_kpi_metric_groups_name"),
    )
    op.create_index("ix_kpi_metric_groups_name", "kpi_metric_groups", ["name"], unique=False)

    op.add_column("kpi_metrics", sa.Column("group_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_kpi_metrics_group_id"), "kpi_metrics", ["group_id"], unique=False)
    op.create_foreign_key(
        "fk_kpi_metrics_group_id_kpi_metric_groups",
        "kpi_metrics",
        "kpi_metric_groups",
        ["group_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_kpi_metrics_group_id_kpi_metric_groups", "kpi_metrics", type_="foreignkey")
    op.drop_index(op.f("ix_kpi_metrics_group_id"), table_name="kpi_metrics")
    op.drop_column("kpi_metrics", "group_id")

    op.drop_index("ix_kpi_metric_groups_name", table_name="kpi_metric_groups")
    op.drop_table("kpi_metric_groups")
