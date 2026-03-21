"""Add inventory movement events table.

Revision ID: e9a5c1b7d4f2
Revises: d7a9c3e1b2f4
Create Date: 2026-02-18 20:20:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e9a5c1b7d4f2"
down_revision: Union[str, Sequence[str], None] = "d7a9c3e1b2f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "inv_movement_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("inv_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("item_code", sa.String(length=64), nullable=True),
        sa.Column("item_name", sa.String(length=255), nullable=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("inv_groups.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("inv_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kind_id", sa.Integer(), sa.ForeignKey("inv_kinds.id", ondelete="SET NULL"), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("from_location_kind", sa.String(length=32), nullable=True),
        sa.Column("from_restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("from_subdivision_id", sa.Integer(), sa.ForeignKey("restaurant_subdivisions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("to_location_kind", sa.String(length=32), nullable=True),
        sa.Column("to_restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("to_subdivision_id", sa.Integer(), sa.ForeignKey("restaurant_subdivisions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("field", sa.String(length=64), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
    )
    op.create_index("ix_inv_movement_events_action_type", "inv_movement_events", ["action_type"])
    op.create_index("ix_inv_movement_events_actor_id", "inv_movement_events", ["actor_id"])
    op.create_index("ix_inv_movement_events_item_id", "inv_movement_events", ["item_id"])
    op.create_index("ix_inv_movement_events_item_code", "inv_movement_events", ["item_code"])
    op.create_index("ix_inv_movement_events_group_id", "inv_movement_events", ["group_id"])
    op.create_index("ix_inv_movement_events_category_id", "inv_movement_events", ["category_id"])
    op.create_index("ix_inv_movement_events_kind_id", "inv_movement_events", ["kind_id"])
    op.create_index("ix_inv_movement_events_from_restaurant_id", "inv_movement_events", ["from_restaurant_id"])
    op.create_index("ix_inv_movement_events_to_restaurant_id", "inv_movement_events", ["to_restaurant_id"])
    op.create_index("ix_inv_movement_events_from_subdivision_id", "inv_movement_events", ["from_subdivision_id"])
    op.create_index("ix_inv_movement_events_to_subdivision_id", "inv_movement_events", ["to_subdivision_id"])
    op.create_index("ix_inv_movement_events_created_at", "inv_movement_events", ["created_at"])
    op.create_index(
        "ix_inv_movement_events_item_created",
        "inv_movement_events",
        ["item_id", "created_at"],
    )
    op.create_index(
        "ix_inv_movement_events_action_created",
        "inv_movement_events",
        ["action_type", "created_at"],
    )
    op.create_index(
        "ix_inv_movement_events_from_rest",
        "inv_movement_events",
        ["from_location_kind", "from_restaurant_id"],
    )
    op.create_index(
        "ix_inv_movement_events_to_rest",
        "inv_movement_events",
        ["to_location_kind", "to_restaurant_id"],
    )
    op.create_index(
        "ix_inv_movement_events_from_sub",
        "inv_movement_events",
        ["from_location_kind", "from_subdivision_id"],
    )
    op.create_index(
        "ix_inv_movement_events_to_sub",
        "inv_movement_events",
        ["to_location_kind", "to_subdivision_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_inv_movement_events_to_sub", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_from_sub", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_to_rest", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_from_rest", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_action_created", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_item_created", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_created_at", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_to_subdivision_id", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_from_subdivision_id", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_to_restaurant_id", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_from_restaurant_id", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_kind_id", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_category_id", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_group_id", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_item_code", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_item_id", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_actor_id", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_action_type", table_name="inv_movement_events")
    op.drop_table("inv_movement_events")
