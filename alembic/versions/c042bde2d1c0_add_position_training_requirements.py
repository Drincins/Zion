"""Add position training requirements table.

Revision ID: c042bde2d1c0
Revises: f1b7d13a1a2c
Create Date: 2025-12-03 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c042bde2d1c0"
down_revision = "f1b7d13a1a2c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "position_training_requirements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("position_id", sa.Integer(), sa.ForeignKey("positions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type_id", sa.Integer(), sa.ForeignKey("training_event_types.id", ondelete="CASCADE"), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index(
        "ix_position_training_requirements_position_id",
        "position_training_requirements",
        ["position_id"],
    )
    op.create_index(
        "ix_position_training_requirements_event_type_id",
        "position_training_requirements",
        ["event_type_id"],
    )
    op.create_unique_constraint(
        "uq_position_training_requirements_position_event",
        "position_training_requirements",
        ["position_id", "event_type_id"],
    )
    op.alter_column("position_training_requirements", "required", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "uq_position_training_requirements_position_event",
        "position_training_requirements",
        type_="unique",
    )
    op.drop_index(
        "ix_position_training_requirements_event_type_id",
        table_name="position_training_requirements",
    )
    op.drop_index(
        "ix_position_training_requirements_position_id",
        table_name="position_training_requirements",
    )
    op.drop_table("position_training_requirements")
