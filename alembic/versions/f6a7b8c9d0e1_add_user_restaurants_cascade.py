"""Add CASCADE delete for user_restaurants.user_id.

Revision ID: f6a7b8c9d0e1
Revises: e1c2d3f4a5b6
Create Date: 2025-01-10 00:00:00
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "f6a7b8c9d0e1"
down_revision = "e1c2d3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("user_restaurants_user_id_fkey", "user_restaurants", type_="foreignkey")
    op.create_foreign_key(
        "user_restaurants_user_id_fkey",
        "user_restaurants",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("user_restaurants_user_id_fkey", "user_restaurants", type_="foreignkey")
    op.create_foreign_key(
        "user_restaurants_user_id_fkey",
        "user_restaurants",
        "users",
        ["user_id"],
        ["id"],
    )
