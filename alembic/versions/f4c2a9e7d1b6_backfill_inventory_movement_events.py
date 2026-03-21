"""Backfill inventory movement events from legacy tables.

Revision ID: f4c2a9e7d1b6
Revises: e9a5c1b7d4f2
Create Date: 2026-02-18 23:05:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f4c2a9e7d1b6"
down_revision: Union[str, Sequence[str], None] = "e9a5c1b7d4f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO inv_movement_events (
            created_at,
            action_type,
            actor_id,
            item_id,
            item_code,
            item_name,
            group_id,
            category_id,
            kind_id,
            quantity,
            from_location_kind,
            from_restaurant_id,
            to_location_kind,
            to_restaurant_id,
            comment
        )
        SELECT
            r.created_at,
            CASE WHEN r.quantity < 0 THEN 'writeoff' ELSE 'quantity_increase' END,
            r.user_id,
            r.item_id,
            i.code,
            i.name,
            r.group_id,
            r.category_id,
            i.kind_id,
            r.quantity,
            CASE WHEN r.quantity < 0 THEN 'restaurant' ELSE NULL END,
            CASE WHEN r.quantity < 0 THEN r.restaurant_id ELSE NULL END,
            CASE WHEN r.quantity >= 0 THEN 'restaurant' ELSE NULL END,
            CASE WHEN r.quantity >= 0 THEN r.restaurant_id ELSE NULL END,
            r.comment
        FROM inv_item_records r
        JOIN inv_items i ON i.id = r.item_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM inv_movement_events e
            WHERE e.item_id = r.item_id
              AND e.created_at = r.created_at
              AND COALESCE(e.quantity, 0) = COALESCE(r.quantity, 0)
              AND COALESCE(e.actor_id, 0) = COALESCE(r.user_id, 0)
              AND COALESCE(e.comment, '') = COALESCE(r.comment, '')
              AND e.action_type IN ('quantity_increase', 'writeoff', 'record_created')
        );
        """
    )

    op.execute(
        """
        INSERT INTO inv_movement_events (
            created_at,
            action_type,
            actor_id,
            item_id,
            item_code,
            item_name,
            group_id,
            category_id,
            kind_id,
            field,
            old_value,
            new_value,
            comment
        )
        SELECT
            c.changed_at,
            CASE WHEN c.field IN ('cost', 'default_cost') THEN 'cost_changed' ELSE 'item_updated' END,
            c.changed_by,
            c.item_id,
            i.code,
            i.name,
            i.group_id,
            i.category_id,
            i.kind_id,
            c.field,
            c.old_value,
            c.new_value,
            'История изменений карточки'
        FROM inv_item_changes c
        JOIN inv_items i ON i.id = c.item_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM inv_movement_events e
            WHERE e.item_id = c.item_id
              AND e.created_at = c.changed_at
              AND COALESCE(e.actor_id, 0) = COALESCE(c.changed_by, 0)
              AND COALESCE(e.field, '') = COALESCE(c.field, '')
              AND COALESCE(e.old_value, '') = COALESCE(c.old_value, '')
              AND COALESCE(e.new_value, '') = COALESCE(c.new_value, '')
              AND e.action_type IN ('item_updated', 'cost_changed')
        );
        """
    )


def downgrade() -> None:
    # Irreversible data migration.
    pass
