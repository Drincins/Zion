"""Add workplace restaurant reference for users.

Revision ID: e3d4f5a6b7c8
Revises: d2c4e8a7b1f0
Create Date: 2025-12-23 19:15:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3d4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "d2c4e8a7b1f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("workplace_restaurant_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_users_workplace_restaurant_id_restaurants",
        "users",
        "restaurants",
        ["workplace_restaurant_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_users_workplace_restaurant_id",
        "users",
        ["workplace_restaurant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_users_workplace_restaurant_id", table_name="users")
    op.drop_constraint(
        "fk_users_workplace_restaurant_id_restaurants",
        "users",
        type_="foreignkey",
    )
    op.drop_column("users", "workplace_restaurant_id")
