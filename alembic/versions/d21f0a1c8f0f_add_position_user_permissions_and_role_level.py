"""Introduce position/user permission links and role hierarchy level.

Revision ID: d21f0a1c8f0f
Revises: a4d6d0b2f1e2
Create Date: 2025-10-30 11:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d21f0a1c8f0f"
down_revision: Union[str, Sequence[str], None] = "a4d6d0b2f1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "position_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("position_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["position_id"], ["employee_positions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("position_id", "permission_id", name="uq_position_permissions_position_permission"),
    )
    op.create_index(
        "ix_position_permissions_position_id",
        "position_permissions",
        ["position_id"],
        unique=False,
    )
    op.create_index(
        "ix_position_permissions_permission_id",
        "position_permissions",
        ["permission_id"],
        unique=False,
    )

    op.create_table(
        "user_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "permission_id", name="uq_user_permissions_user_permission"),
    )
    op.create_index(
        "ix_user_permissions_user_id",
        "user_permissions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_permissions_permission_id",
        "user_permissions",
        ["permission_id"],
        unique=False,
    )

    op.add_column(
        "roles",
        sa.Column("level", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column(
            "has_full_restaurant_access",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )

    op.alter_column("roles", "level", server_default=None)
    op.alter_column("users", "has_full_restaurant_access", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_user_permissions_permission_id", table_name="user_permissions")
    op.drop_index("ix_user_permissions_user_id", table_name="user_permissions")
    op.drop_table("user_permissions")

    op.drop_index("ix_position_permissions_permission_id", table_name="position_permissions")
    op.drop_index("ix_position_permissions_position_id", table_name="position_permissions")
    op.drop_table("position_permissions")

    op.drop_column("users", "has_full_restaurant_access")
    op.drop_column("roles", "level")
