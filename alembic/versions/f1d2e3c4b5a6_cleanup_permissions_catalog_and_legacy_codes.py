"""Cleanup permissions catalog and remove legacy duplicate rights.

Revision ID: f1d2e3c4b5a6
Revises: f0b1c2d3e4f5
Create Date: 2026-02-23 23:59:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1d2e3c4b5a6"
down_revision: Union[str, Sequence[str], None] = "f0b1c2d3e4f5"
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
role_permissions_table = sa.Table(
    "role_permissions",
    metadata,
    sa.Column("id", sa.Integer),
    sa.Column("role_id", sa.Integer),
    sa.Column("permission_id", sa.Integer),
)
position_permissions_table = sa.Table(
    "position_permissions",
    metadata,
    sa.Column("id", sa.Integer),
    sa.Column("position_id", sa.Integer),
    sa.Column("permission_id", sa.Integer),
)
user_permissions_table = sa.Table(
    "user_permissions",
    metadata,
    sa.Column("id", sa.Integer),
    sa.Column("user_id", sa.Integer),
    sa.Column("permission_id", sa.Integer),
)


PERMISSION_UPSERTS = [
    {
        "code": "checklists.edit_all",
        "display_name": "Чек-листы: редактирование всех",
        "description": "Редактирование любых чек-листов компании, включая чужие.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "payroll.advance.delete",
        "display_name": "Авансы: удаление",
        "description": "Удаление заявок на аванс.",
        "responsibility_zone": "Зарплата",
    },
    {
        "code": "staff_employees.restore",
        "display_name": "Сотрудники: восстановление",
        "description": "Восстановление уволенных сотрудников в активный статус.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "iiko.view",
        "display_name": "iiko: просмотр",
        "description": "Просмотр данных интеграции iiko.",
        "responsibility_zone": "Продажи",
    },
    {
        "code": "iiko.manage",
        "display_name": "iiko: управление",
        "description": "Управление интеграцией iiko.",
        "responsibility_zone": "Продажи",
    },
    {
        "code": "iiko.catalog.sync",
        "display_name": "iiko: синхронизация справочника",
        "description": "Запуск и управление синхронизацией справочников iiko.",
        "responsibility_zone": "Продажи",
    },
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
        "responsibility_zone": "Продажи",
    },
    {
        "code": "restaurants.settings.manage",
        "display_name": "Рестораны: настройки синхронизации (управление)",
        "description": "Редактирование настроек синхронизации продаж ресторана.",
        "responsibility_zone": "Продажи",
    },
]

LEGACY_PERMISSION_REMAP = {
    "iiko_products.read": "sales.dishes.view",
    "iiko_olap_read.view": "sales.report.view_qty",
    "iiko_olap_product.manage": "iiko.catalog.sync",
}

DEPRECATED_PERMISSION_CODES = {
    "inventory.bot.access",
    *LEGACY_PERMISSION_REMAP.keys(),
}


def _permission_id(bind, code: str) -> int | None:
    return bind.execute(
        sa.select(permissions_table.c.id).where(permissions_table.c.code == code)
    ).scalar()


def _upsert_permission(bind, payload: dict[str, str]) -> None:
    code = payload["code"]
    values = {
        "name": payload["display_name"],
        "display_name": payload["display_name"],
        "description": payload["description"],
        "responsibility_zone": payload["responsibility_zone"],
    }
    permission_id = _permission_id(bind, code)
    if permission_id is None:
        bind.execute(permissions_table.insert().values(code=code, **values))
    else:
        bind.execute(
            sa.update(permissions_table)
            .where(permissions_table.c.id == permission_id)
            .values(**values)
        )


def _copy_links(bind, table, owner_column, source_permission_id: int, target_permission_id: int) -> None:
    owner_ids = bind.execute(
        sa.select(owner_column).where(table.c.permission_id == source_permission_id)
    ).all()
    for (owner_id,) in owner_ids:
        exists = bind.execute(
            sa.select(table.c.id).where(
                owner_column == owner_id,
                table.c.permission_id == target_permission_id,
            )
        ).first()
        if exists:
            continue
        bind.execute(
            table.insert().values(
                **{
                    owner_column.key: owner_id,
                    "permission_id": target_permission_id,
                }
            )
        )


def _relink_permission(bind, source_code: str, target_code: str) -> None:
    source_permission_id = _permission_id(bind, source_code)
    target_permission_id = _permission_id(bind, target_code)
    if source_permission_id is None or target_permission_id is None:
        return
    if source_permission_id == target_permission_id:
        return

    _copy_links(bind, role_permissions_table, role_permissions_table.c.role_id, source_permission_id, target_permission_id)
    _copy_links(
        bind,
        position_permissions_table,
        position_permissions_table.c.position_id,
        source_permission_id,
        target_permission_id,
    )
    _copy_links(bind, user_permissions_table, user_permissions_table.c.user_id, source_permission_id, target_permission_id)


def _delete_permission(bind, code: str) -> None:
    permission_id = _permission_id(bind, code)
    if permission_id is None:
        return

    bind.execute(sa.delete(role_permissions_table).where(role_permissions_table.c.permission_id == permission_id))
    bind.execute(sa.delete(position_permissions_table).where(position_permissions_table.c.permission_id == permission_id))
    bind.execute(sa.delete(user_permissions_table).where(user_permissions_table.c.permission_id == permission_id))
    bind.execute(sa.delete(permissions_table).where(permissions_table.c.id == permission_id))


def _normalize_responsibility_zones(bind) -> None:
    bind.execute(
        sa.update(permissions_table)
        .where(
            sa.or_(
                permissions_table.c.code.like("system.%"),
                permissions_table.c.code.like("access_control.%"),
                permissions_table.c.code.like("roles.%"),
                permissions_table.c.code.like("positions.%"),
                permissions_table.c.code.like("users.%"),
                permissions_table.c.code.like("companies.%"),
                permissions_table.c.code.in_(("restaurants.view", "restaurants.manage")),
            )
        )
        .values(responsibility_zone="Администрирование")
    )
    bind.execute(
        sa.update(permissions_table)
        .where(
            sa.or_(
                permissions_table.c.code.like("staff.%"),
                permissions_table.c.code.like("staff_%"),
                permissions_table.c.code.like("employees_card.%"),
                permissions_table.c.code.like("employee_changes.%"),
                permissions_table.c.code.like("checklists.%"),
            )
        )
        .values(responsibility_zone="Сотрудники")
    )
    bind.execute(
        sa.update(permissions_table)
        .where(permissions_table.c.code.like("payroll.%"))
        .values(responsibility_zone="Зарплата")
    )
    bind.execute(
        sa.update(permissions_table)
        .where(permissions_table.c.code.like("timesheet.%"))
        .values(responsibility_zone="Табель смен")
    )
    bind.execute(
        sa.update(permissions_table)
        .where(permissions_table.c.code.like("inventory.%"))
        .values(responsibility_zone="Склад")
    )
    bind.execute(
        sa.update(permissions_table)
        .where(permissions_table.c.code.like("kpi.%"))
        .values(responsibility_zone="KPI")
    )
    bind.execute(
        sa.update(permissions_table)
        .where(permissions_table.c.code.like("training.%"))
        .values(responsibility_zone="Обучение")
    )
    bind.execute(
        sa.update(permissions_table)
        .where(permissions_table.c.code.like("accounting.%"))
        .values(responsibility_zone="Бухгалтерия")
    )
    bind.execute(
        sa.update(permissions_table)
        .where(
            sa.or_(
                permissions_table.c.code.like("medical_checks.%"),
                permissions_table.c.code.like("cis_documents.%"),
            )
        )
        .values(responsibility_zone="Кадры")
    )
    bind.execute(
        sa.update(permissions_table)
        .where(
            sa.or_(
                permissions_table.c.code.like("sales.%"),
                permissions_table.c.code.like("iiko.%"),
                permissions_table.c.code.like("restaurants.settings.%"),
            )
        )
        .values(responsibility_zone="Продажи")
    )
    bind.execute(
        sa.update(permissions_table)
        .where(permissions_table.c.code.like("labor.summary.%"))
        .values(responsibility_zone="Сводка по труду")
    )


def upgrade() -> None:
    bind = op.get_bind()

    for payload in PERMISSION_UPSERTS:
        _upsert_permission(bind, payload)

    for source_code, target_code in LEGACY_PERMISSION_REMAP.items():
        _relink_permission(bind, source_code, target_code)

    for deprecated_code in DEPRECATED_PERMISSION_CODES:
        _delete_permission(bind, deprecated_code)

    _normalize_responsibility_zones(bind)


def downgrade() -> None:
    # Irreversible cleanup migration.
    pass
