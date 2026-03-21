"""Add responsibility zone grouping to permissions.

Revision ID: 3c9d5a27c2f1
Revises: f20a2f8c1f5f
Create Date: 2025-11-20 12:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision = "3c9d5a27c2f1"
down_revision = "f20a2f8c1f5f"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None


permission_table = table(
    "permissions",
    column("code", sa.String()),
    column("responsibility_zone", sa.String()),
)

ZONE_MAPPING = {
    "system.admin": "Системные",
    "staff.manage_all": "Сотрудники",
    "staff.manage_subordinates": "Сотрудники",
    "staff.view_sensitive": "Сотрудники",
    "roles.manage": "Системные",
    "positions.manage": "Системные",
    "users.view": "Пользователи",
    "users.manage": "Пользователи",
    "companies.view": "Справочники",
    "companies.manage": "Справочники",
    "restaurants.view": "Справочники",
    "restaurants.manage": "Справочники",
    "inventory.view": "Склад",
    "inventory.manage": "Склад",
    "payroll.view": "Финансы",
    "payroll.manage": "Финансы",
    "training.view": "Тренинги",
    "training.manage": "Тренинги",
    "iiko.view": "Интеграции iiko",
    "iiko.manage": "Интеграции iiko",
    "iiko_products.read": "Интеграции iiko",
    "iiko_olap_read.view": "Интеграции iiko",
    "iiko_olap_product.manage": "Интеграции iiko",
    "staff_portal.access": "Тайм-контроль",
    "staff_employees.view": "Сотрудники",
    "staff_employees.manage": "Сотрудники",
    "employees_card.view": "Сотрудники",
    "employees_card.manage": "Сотрудники",
    "access_control.read": "Системные",
    "access_control.manage": "Системные",
}


def upgrade() -> None:
    op.add_column("permissions", sa.Column("responsibility_zone", sa.String(), nullable=True))
    bind = op.get_bind()
    for code, zone in ZONE_MAPPING.items():
        bind.execute(
            permission_table.update()
            .where(permission_table.c.code == code)
            .values(responsibility_zone=zone)
        )


def downgrade() -> None:
    op.drop_column("permissions", "responsibility_zone")
