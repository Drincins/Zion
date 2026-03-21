"""Add granular inventory permissions.

Revision ID: f4a5b6c7d8e9
Revises: f3e4d5c6b7a8
Create Date: 2026-03-18 13:40:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "f3e4d5c6b7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


metadata = sa.MetaData()
permissions_table = sa.Table(
    "permissions",
    metadata,
    sa.Column("id", sa.Integer),
    sa.Column("code", sa.String),
    sa.Column("name", sa.String),
    sa.Column("description", sa.String),
    sa.Column("display_name", sa.String),
    sa.Column("responsibility_zone", sa.String),
)

INVENTORY_PERMISSION_DEFINITIONS = [
    {
        "code": "inventory.nomenclature.create",
        "name": "Склад: создание номенклатуры",
        "display_name": "Склад: создание номенклатуры",
        "description": "Создание групп, категорий, видов и карточек товаров склада.",
        "responsibility_zone": "Склад",
    },
    {
        "code": "inventory.nomenclature.edit",
        "name": "Склад: редактирование номенклатуры",
        "display_name": "Склад: редактирование номенклатуры",
        "description": "Редактирование групп, категорий, видов и карточек товаров склада.",
        "responsibility_zone": "Склад",
    },
    {
        "code": "inventory.movements.create",
        "name": "Склад: создание движений",
        "display_name": "Склад: создание движений",
        "description": "Создание приходов, перемещений, списаний и корректировок склада.",
        "responsibility_zone": "Склад",
    },
    {
        "code": "inventory.movements.edit",
        "name": "Склад: редактирование движений",
        "display_name": "Склад: редактирование движений",
        "description": "Редактирование сохраненных операций и складских движений.",
        "responsibility_zone": "Склад",
    },
]


def upgrade() -> None:
    bind = op.get_bind()
    existing_codes = {
        row.code for row in bind.execute(sa.select(permissions_table.c.code))
    }

    for item in INVENTORY_PERMISSION_DEFINITIONS:
        values = {
            "name": item["name"],
            "display_name": item["display_name"],
            "description": item["description"],
            "responsibility_zone": item["responsibility_zone"],
        }
        if item["code"] in existing_codes:
            bind.execute(
                sa.update(permissions_table)
                .where(permissions_table.c.code == item["code"])
                .values(**values)
            )
        else:
            bind.execute(
                permissions_table.insert().values(code=item["code"], **values)
            )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        permissions_table.delete().where(
            permissions_table.c.code.in_([item["code"] for item in INVENTORY_PERMISSION_DEFINITIONS])
        )
    )
