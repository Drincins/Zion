"""Add inventory settings catalogs.

Revision ID: f7b8c9d0e1f2
Revises: f6b7c8d9e0f1
Create Date: 2026-03-20 16:05:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6b7c8d9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INSTANCE_EVENT_TYPES = (
    {
        "code": "quantity_increase",
        "name": "Поступление",
        "description": "Автоматическое событие прихода единицы товара.",
        "is_manual": False,
        "is_active": True,
        "status_key": None,
        "status_label": None,
        "sort_order": 10,
    },
    {
        "code": "quantity_adjusted",
        "name": "Корректировка",
        "description": "Автоматическая корректировка количества единиц товара.",
        "is_manual": False,
        "is_active": True,
        "status_key": None,
        "status_label": None,
        "sort_order": 20,
    },
    {
        "code": "transfer",
        "name": "Перемещение",
        "description": "Автоматическое перемещение единицы товара между локациями.",
        "is_manual": False,
        "is_active": True,
        "status_key": None,
        "status_label": None,
        "sort_order": 30,
    },
    {
        "code": "writeoff",
        "name": "Списание",
        "description": "Автоматическое списание единицы товара.",
        "is_manual": False,
        "is_active": True,
        "status_key": None,
        "status_label": None,
        "sort_order": 40,
    },
    {
        "code": "repair",
        "name": "Ремонт",
        "description": "Ручное сервисное событие для ремонта единицы товара.",
        "is_manual": True,
        "is_active": True,
        "status_key": "repair",
        "status_label": "В ремонте",
        "sort_order": 100,
    },
    {
        "code": "maintenance",
        "name": "ТО",
        "description": "Ручное сервисное событие для технического обслуживания.",
        "is_manual": True,
        "is_active": True,
        "status_key": "maintenance",
        "status_label": "На ТО",
        "sort_order": 110,
    },
    {
        "code": "inspection",
        "name": "Проверка",
        "description": "Ручное сервисное событие для проверки состояния единицы товара.",
        "is_manual": True,
        "is_active": True,
        "status_key": "inspection",
        "status_label": "Проверяется",
        "sort_order": 120,
    },
    {
        "code": "note",
        "name": "Комментарий",
        "description": "Ручное текстовое событие без смены статуса единицы товара.",
        "is_manual": True,
        "is_active": True,
        "status_key": None,
        "status_label": None,
        "sort_order": 130,
    },
)


def upgrade() -> None:
    op.create_table(
        "inv_instance_event_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_manual", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status_key", sa.String(length=64), nullable=True),
        sa.Column("status_label", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_inv_instance_event_types_code"),
    )
    op.create_index(
        "ix_inv_instance_event_types_manual_active",
        "inv_instance_event_types",
        ["is_manual", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_inv_instance_event_types_sort",
        "inv_instance_event_types",
        ["sort_order", "name"],
        unique=False,
    )

    op.create_table(
        "inv_storage_places",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("scope_kind", sa.String(length=32), nullable=False, server_default="company"),
        sa.Column("restaurant_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inv_storage_places_restaurant_id",
        "inv_storage_places",
        ["restaurant_id"],
        unique=False,
    )
    op.create_index(
        "ix_inv_storage_places_scope_sort",
        "inv_storage_places",
        ["scope_kind", "sort_order", "name"],
        unique=False,
    )

    bind = op.get_bind()
    table = sa.table(
        "inv_instance_event_types",
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("is_active", sa.Boolean()),
        sa.column("is_manual", sa.Boolean()),
        sa.column("status_key", sa.String()),
        sa.column("status_label", sa.String()),
        sa.column("sort_order", sa.Integer()),
    )
    bind.execute(table.insert(), list(INSTANCE_EVENT_TYPES))


def downgrade() -> None:
    op.drop_index("ix_inv_storage_places_scope_sort", table_name="inv_storage_places")
    op.drop_index("ix_inv_storage_places_restaurant_id", table_name="inv_storage_places")
    op.drop_table("inv_storage_places")

    op.drop_index("ix_inv_instance_event_types_sort", table_name="inv_instance_event_types")
    op.drop_index("ix_inv_instance_event_types_manual_active", table_name="inv_instance_event_types")
    op.drop_table("inv_instance_event_types")
