"""add_sales_granular_permissions

Revision ID: e6b7c8d9a0f1
Revises: d5b8f1a3c2e4
Create Date: 2026-02-21 23:30:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e6b7c8d9a0f1"
down_revision: Union[str, Sequence[str], None] = "d5b8f1a3c2e4"
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

PERMISSION_DEFINITIONS = [
    {
        "code": "sales.report.view_qty",
        "display_name": "Продажи: отчет (количество)",
        "description": "Просмотр отчетов по продажам без денежных показателей.",
        "responsibility_zone": "Продажи",
    },
    {
        "code": "sales.report.view_money",
        "display_name": "Продажи: отчет (суммы)",
        "description": "Просмотр денежных показателей в отчетах по продажам и выручке.",
        "responsibility_zone": "Продажи",
    },
    {
        "code": "sales.tables.view",
        "display_name": "Продажи: настройки столов (просмотр)",
        "description": "Просмотр карт локаций, залов, зон и столов.",
        "responsibility_zone": "Продажи",
    },
    {
        "code": "sales.tables.manage",
        "display_name": "Продажи: настройки столов (управление)",
        "description": "Создание и редактирование карт локаций, залов, зон и столов.",
        "responsibility_zone": "Продажи",
    },
    {
        "code": "sales.dishes.view",
        "display_name": "Продажи: настройки блюд (просмотр)",
        "description": "Просмотр номенклатуры и порционных коэффициентов.",
        "responsibility_zone": "Продажи",
    },
    {
        "code": "sales.dishes.manage",
        "display_name": "Продажи: настройки блюд (управление)",
        "description": "Редактирование порционных коэффициентов и категорий блюд.",
        "responsibility_zone": "Продажи",
    },
    {
        "code": "restaurants.settings.view",
        "display_name": "Рестораны: настройки синхронизации (просмотр)",
        "description": "Просмотр настроек синхронизации продаж ресторана.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "restaurants.settings.manage",
        "display_name": "Рестораны: настройки синхронизации (управление)",
        "description": "Редактирование настроек синхронизации продаж ресторана.",
        "responsibility_zone": "Администрирование",
    },
]


def upgrade() -> None:
    bind = op.get_bind()
    existing_codes = {row.code for row in bind.execute(sa.select(permissions_table.c.code))}

    for item in PERMISSION_DEFINITIONS:
        values = {
            "name": item["display_name"],
            "description": item["description"],
            "display_name": item["display_name"],
            "responsibility_zone": item["responsibility_zone"],
        }
        if item["code"] in existing_codes:
            bind.execute(
                sa.update(permissions_table)
                .where(permissions_table.c.code == item["code"])
                .values(**values)
            )
        else:
            bind.execute(permissions_table.insert().values(code=item["code"], **values))


def downgrade() -> None:
    # Keep seeded permissions on downgrade to avoid dropping assigned access rights.
    pass

