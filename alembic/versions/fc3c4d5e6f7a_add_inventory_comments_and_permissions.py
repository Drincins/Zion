"""Add inventory comments/notes and new permissions.

Revision ID: fc3c4d5e6f7a
Revises: fb2b3c4d5e6f
Create Date: 2026-01-12 00:20:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "fc3c4d5e6f7a"
down_revision: Union[str, Sequence[str], None] = "fb2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("inv_items", sa.Column("note", sa.Text(), nullable=True))
    op.add_column("inv_item_records", sa.Column("comment", sa.Text(), nullable=True))

    op.create_table(
        "inv_item_changes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("inv_items.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("field", sa.String(length=64), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("changed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_inv_item_changes_item", "inv_item_changes", ["item_id"])

    # Permissions seeding
    permissions = [
        ("inventory.balance.view", "Склад: просмотр баланса", "Просмотр сводных остатков по складу.", "Склад"),
        ("inventory.movements.view", "Склад: просмотр движений", "Просмотр движений склада.", "Склад"),
        ("inventory.movements.manage", "Склад: управление движениями", "Создание и редактирование движений склада.", "Склад"),
        ("inventory.movements.delete", "Склад: удаление движений", "Удаление движений склада.", "Склад"),
        ("inventory.nomenclature.view", "Склад: просмотр номенклатуры", "Просмотр групп/категорий/товаров склада.", "Склад"),
        ("inventory.nomenclature.manage", "Склад: управление номенклатурой", "Создание и редактирование групп/категорий/товаров.", "Склад"),
        ("inventory.nomenclature.delete", "Склад: удаление номенклатуры", "Удаление групп/категорий/товаров.", "Склад"),
    ]
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO permissions (code, name, display_name, description, responsibility_zone)
            VALUES (:code, :disp, :disp, :desc, :zone)
            ON CONFLICT (code) DO NOTHING
            """
        ),
        [{"code": c, "disp": n, "desc": d, "zone": z} for c, n, d, z in permissions],
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE code IN (
                'inventory.balance.view',
                'inventory.movements.view',
                'inventory.movements.manage',
                'inventory.movements.delete',
                'inventory.nomenclature.view',
                'inventory.nomenclature.manage',
                'inventory.nomenclature.delete'
            )
            """
        )
    )
    op.drop_index("ix_inv_item_changes_item", table_name="inv_item_changes")
    op.drop_table("inv_item_changes")
    op.drop_column("inv_item_records", "comment")
    op.drop_column("inv_items", "note")
