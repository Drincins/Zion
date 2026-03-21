"""Add inventory kinds and item instances.

Revision ID: d7a9c3e1b2f4
Revises: c6e8b1d2f3a4
Create Date: 2026-02-17 20:45:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d7a9c3e1b2f4"
down_revision: Union[str, Sequence[str], None] = "c6e8b1d2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "inv_kinds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("inv_categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("inv_groups.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("name", "category_id", name="uq_inv_kinds_name_category"),
    )
    op.create_index("ix_inv_kinds_category_id", "inv_kinds", ["category_id"])
    op.create_index("ix_inv_kinds_group_id", "inv_kinds", ["group_id"])
    op.create_index("ix_inv_kinds_group_category", "inv_kinds", ["group_id", "category_id"])

    op.add_column("inv_items", sa.Column("kind_id", sa.Integer(), nullable=True))
    op.create_index("ix_inv_items_kind_id", "inv_items", ["kind_id"])
    op.create_foreign_key(
        "fk_inv_items_kind_id_inv_kinds",
        "inv_items",
        "inv_kinds",
        ["kind_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Seed one default kind per category and attach existing items to it.
    op.execute(
        """
        INSERT INTO inv_kinds (name, category_id, group_id)
        SELECT 'Прочее', c.id, c.group_id
        FROM inv_categories c
        ON CONFLICT (name, category_id) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE inv_items i
        SET kind_id = k.id
        FROM inv_kinds k
        WHERE i.kind_id IS NULL
          AND k.category_id = i.category_id
          AND k.group_id = i.group_id
          AND k.name = 'Прочее'
        """
    )
    op.alter_column("inv_items", "kind_id", nullable=False)
    op.create_index("ix_inv_items_group_category_kind", "inv_items", ["group_id", "category_id", "kind_id"])

    op.create_table(
        "inv_item_instances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("inv_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("instance_code", sa.String(length=80), nullable=False),
        sa.Column("location_kind", sa.String(length=32), nullable=False, server_default=sa.text("'warehouse'")),
        sa.Column("restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("subdivision_id", sa.Integer(), sa.ForeignKey("restaurant_subdivisions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("item_id", "sequence_no", name="uq_inv_item_instances_item_seq"),
        sa.UniqueConstraint("instance_code", name="uq_inv_item_instances_code"),
    )
    op.create_index("ix_inv_item_instances_item_id", "inv_item_instances", ["item_id"])
    op.create_index("ix_inv_item_instances_instance_code", "inv_item_instances", ["instance_code"])
    op.create_index("ix_inv_item_instances_restaurant_id", "inv_item_instances", ["restaurant_id"])
    op.create_index("ix_inv_item_instances_subdivision_id", "inv_item_instances", ["subdivision_id"])
    op.create_index(
        "ix_inv_item_instances_kind_rest",
        "inv_item_instances",
        ["location_kind", "restaurant_id"],
    )
    op.create_index(
        "ix_inv_item_instances_kind_sub",
        "inv_item_instances",
        ["location_kind", "subdivision_id"],
    )

    # Backfill positive stock balances as assigned instances in restaurants.
    op.execute(
        """
        DO $$
        DECLARE
            rec RECORD;
            seq_start INTEGER;
            seq_no INTEGER;
        BEGIN
            FOR rec IN
                SELECT s.item_id, s.restaurant_id, GREATEST(COALESCE(s.quantity, 0), 0)::INTEGER AS qty, i.code AS code
                FROM inv_item_stock s
                JOIN inv_items i ON i.id = s.item_id
                WHERE COALESCE(s.quantity, 0) > 0
            LOOP
                SELECT COALESCE(MAX(ii.sequence_no), 0)
                INTO seq_start
                FROM inv_item_instances ii
                WHERE ii.item_id = rec.item_id;

                FOR seq_no IN 1..rec.qty LOOP
                    INSERT INTO inv_item_instances (
                        item_id,
                        sequence_no,
                        instance_code,
                        location_kind,
                        restaurant_id,
                        subdivision_id
                    )
                    VALUES (
                        rec.item_id,
                        seq_start + seq_no,
                        rec.code || '-' || LPAD((seq_start + seq_no)::TEXT, 2, '0'),
                        'restaurant',
                        rec.restaurant_id,
                        NULL
                    );
                END LOOP;
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_inv_item_instances_kind_sub", table_name="inv_item_instances")
    op.drop_index("ix_inv_item_instances_kind_rest", table_name="inv_item_instances")
    op.drop_index("ix_inv_item_instances_subdivision_id", table_name="inv_item_instances")
    op.drop_index("ix_inv_item_instances_restaurant_id", table_name="inv_item_instances")
    op.drop_index("ix_inv_item_instances_instance_code", table_name="inv_item_instances")
    op.drop_index("ix_inv_item_instances_item_id", table_name="inv_item_instances")
    op.drop_table("inv_item_instances")

    op.drop_index("ix_inv_items_group_category_kind", table_name="inv_items")
    op.drop_constraint("fk_inv_items_kind_id_inv_kinds", "inv_items", type_="foreignkey")
    op.drop_index("ix_inv_items_kind_id", table_name="inv_items")
    op.drop_column("inv_items", "kind_id")

    op.drop_index("ix_inv_kinds_group_category", table_name="inv_kinds")
    op.drop_index("ix_inv_kinds_group_id", table_name="inv_kinds")
    op.drop_index("ix_inv_kinds_category_id", table_name="inv_kinds")
    op.drop_table("inv_kinds")
