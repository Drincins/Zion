"""Link inventory instances and events to restaurant storage places.

Revision ID: f8c9d0e1f2a
Revises: f7b8c9d0e1f2
Create Date: 2026-03-20 20:30:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f8c9d0e1f2a"
down_revision: Union[str, Sequence[str], None] = "f7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("inv_item_instances", sa.Column("storage_place_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_inv_item_instances_storage_place_id",
        "inv_item_instances",
        "inv_storage_places",
        ["storage_place_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_inv_item_instances_storage_place_id",
        "inv_item_instances",
        ["storage_place_id"],
        unique=False,
    )
    op.create_index(
        "ix_inv_item_instances_rest_place",
        "inv_item_instances",
        ["restaurant_id", "storage_place_id"],
        unique=False,
    )

    op.add_column("inv_item_instance_events", sa.Column("from_storage_place_id", sa.Integer(), nullable=True))
    op.add_column("inv_item_instance_events", sa.Column("to_storage_place_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_inv_item_instance_events_from_storage_place_id",
        "inv_item_instance_events",
        "inv_storage_places",
        ["from_storage_place_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_inv_item_instance_events_to_storage_place_id",
        "inv_item_instance_events",
        "inv_storage_places",
        ["to_storage_place_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_inv_item_instance_events_from_storage_place_id",
        "inv_item_instance_events",
        ["from_storage_place_id"],
        unique=False,
    )
    op.create_index(
        "ix_inv_item_instance_events_to_storage_place_id",
        "inv_item_instance_events",
        ["to_storage_place_id"],
        unique=False,
    )
    op.create_index(
        "ix_inv_item_instance_events_from_place",
        "inv_item_instance_events",
        ["from_storage_place_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_inv_item_instance_events_to_place",
        "inv_item_instance_events",
        ["to_storage_place_id", "created_at"],
        unique=False,
    )

    op.add_column("inv_movement_events", sa.Column("from_storage_place_id", sa.Integer(), nullable=True))
    op.add_column("inv_movement_events", sa.Column("to_storage_place_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_inv_movement_events_from_storage_place_id",
        "inv_movement_events",
        "inv_storage_places",
        ["from_storage_place_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_inv_movement_events_to_storage_place_id",
        "inv_movement_events",
        "inv_storage_places",
        ["to_storage_place_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_inv_movement_events_from_storage_place_id",
        "inv_movement_events",
        ["from_storage_place_id"],
        unique=False,
    )
    op.create_index(
        "ix_inv_movement_events_to_storage_place_id",
        "inv_movement_events",
        ["to_storage_place_id"],
        unique=False,
    )
    op.create_index(
        "ix_inv_movement_events_from_place",
        "inv_movement_events",
        ["from_storage_place_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_inv_movement_events_to_place",
        "inv_movement_events",
        ["to_storage_place_id", "created_at"],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            DELETE FROM inv_storage_places
            WHERE scope_kind = 'company' OR restaurant_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE inv_storage_places
            SET scope_kind = 'restaurant'
            """
        )
    )
    op.alter_column(
        "inv_storage_places",
        "scope_kind",
        existing_type=sa.String(length=32),
        server_default="restaurant",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "inv_storage_places",
        "scope_kind",
        existing_type=sa.String(length=32),
        server_default="company",
        existing_nullable=False,
    )

    op.drop_index("ix_inv_movement_events_to_place", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_from_place", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_to_storage_place_id", table_name="inv_movement_events")
    op.drop_index("ix_inv_movement_events_from_storage_place_id", table_name="inv_movement_events")
    op.drop_constraint("fk_inv_movement_events_to_storage_place_id", "inv_movement_events", type_="foreignkey")
    op.drop_constraint("fk_inv_movement_events_from_storage_place_id", "inv_movement_events", type_="foreignkey")
    op.drop_column("inv_movement_events", "to_storage_place_id")
    op.drop_column("inv_movement_events", "from_storage_place_id")

    op.drop_index("ix_inv_item_instance_events_to_place", table_name="inv_item_instance_events")
    op.drop_index("ix_inv_item_instance_events_from_place", table_name="inv_item_instance_events")
    op.drop_index("ix_inv_item_instance_events_to_storage_place_id", table_name="inv_item_instance_events")
    op.drop_index("ix_inv_item_instance_events_from_storage_place_id", table_name="inv_item_instance_events")
    op.drop_constraint("fk_inv_item_instance_events_to_storage_place_id", "inv_item_instance_events", type_="foreignkey")
    op.drop_constraint("fk_inv_item_instance_events_from_storage_place_id", "inv_item_instance_events", type_="foreignkey")
    op.drop_column("inv_item_instance_events", "to_storage_place_id")
    op.drop_column("inv_item_instance_events", "from_storage_place_id")

    op.drop_index("ix_inv_item_instances_rest_place", table_name="inv_item_instances")
    op.drop_index("ix_inv_item_instances_storage_place_id", table_name="inv_item_instances")
    op.drop_constraint("fk_inv_item_instances_storage_place_id", "inv_item_instances", type_="foreignkey")
    op.drop_column("inv_item_instances", "storage_place_id")
