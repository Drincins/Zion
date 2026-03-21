"""Add section/tab access permissions and seed role/position/user links.

Revision ID: f2e3d4c5b6a7
Revises: f1d2e3c4b5a6
Create Date: 2026-02-24 00:35:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert


# revision identifiers, used by Alembic.
revision: str = "f2e3d4c5b6a7"
down_revision: Union[str, Sequence[str], None] = "f1d2e3c4b5a6"
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


SECTION_PERMISSION_DEFINITIONS = [
    {
        "code": "sections.staff.employees",
        "display_name": "Разделы: Сотрудники",
        "description": "Доступ к вкладке «Сотрудники».",
    },
    {
        "code": "sections.staff.positions",
        "display_name": "Разделы: Должности",
        "description": "Доступ к вкладке «Должности».",
    },
    {
        "code": "sections.staff.permissions",
        "display_name": "Разделы: Права доступа",
        "description": "Доступ к вкладке «Права доступа».",
    },
    {
        "code": "sections.settings.trainings",
        "display_name": "Разделы: Обучения",
        "description": "Доступ к вкладке «Обучения».",
    },
    {
        "code": "sections.settings.payroll_types",
        "display_name": "Разделы: Виды выплат",
        "description": "Доступ к вкладке «Виды выплат».",
    },
    {
        "code": "sections.settings.subdivisions",
        "display_name": "Разделы: Подразделения",
        "description": "Доступ к вкладке «Подразделения».",
    },
    {
        "code": "sections.settings.restaurants",
        "display_name": "Разделы: Рестораны",
        "description": "Доступ к вкладке «Рестораны».",
    },
    {
        "code": "sections.inventory.nomenclature",
        "display_name": "Разделы: Склад / Номенклатура",
        "description": "Доступ к подвкладкам номенклатуры в разделе «Склад».",
    },
    {
        "code": "sections.inventory.movements",
        "display_name": "Разделы: Склад / Движение товаров",
        "description": "Доступ к подвкладке «Движение товаров».",
    },
    {
        "code": "sections.inventory.tagged_items",
        "display_name": "Разделы: Склад / Товары по тегам",
        "description": "Доступ к подвкладке «Товары по тегам».",
    },
    {
        "code": "sections.control.checklists",
        "display_name": "Разделы: Контроль / Чек-листы",
        "description": "Доступ к разделу «Контроль» и чек-листам.",
    },
    {
        "code": "sections.accounting.invoices",
        "display_name": "Разделы: Бухгалтерия / Счета",
        "description": "Доступ к подвкладке «Счета».",
    },
    {
        "code": "sections.accounting.advances",
        "display_name": "Разделы: Бухгалтерия / Ведомости",
        "description": "Доступ к подвкладке «Ведомости».",
    },
    {
        "code": "sections.kpi.metrics",
        "display_name": "Разделы: KPI / Показатели",
        "description": "Доступ к подвкладке KPI «Показатели».",
    },
    {
        "code": "sections.kpi.plan_fact",
        "display_name": "Разделы: KPI / Результаты",
        "description": "Доступ к подвкладке KPI «Результаты».",
    },
    {
        "code": "sections.kpi.facts",
        "display_name": "Разделы: KPI / Факт KPI",
        "description": "Доступ к подвкладке KPI «Факт KPI».",
    },
    {
        "code": "sections.kpi.payouts",
        "display_name": "Разделы: KPI / Выплаты",
        "description": "Доступ к подвкладке KPI «Выплаты».",
    },
    {
        "code": "sections.sales.report",
        "display_name": "Разделы: Продажи / Продажи",
        "description": "Доступ к вкладке «Продажи».",
    },
    {
        "code": "sections.sales.revenue",
        "display_name": "Разделы: Продажи / Выручка",
        "description": "Доступ к вкладке «Выручка».",
    },
    {
        "code": "sections.sales.settings",
        "display_name": "Разделы: Продажи / Настройки",
        "description": "Доступ к вкладке «Настройки» в разделе «Продажи».",
    },
    {
        "code": "sections.sales.settings.nomenclature",
        "display_name": "Разделы: Продажи / Настройки / Номенклатура",
        "description": "Доступ к подвкладке «Номенклатура».",
    },
    {
        "code": "sections.sales.settings.tables",
        "display_name": "Разделы: Продажи / Настройки / Столы",
        "description": "Доступ к подвкладке «Столы».",
    },
    {
        "code": "sections.sales.settings.payment_types",
        "display_name": "Разделы: Продажи / Настройки / Типы оплат",
        "description": "Доступ к подвкладке «Типы оплат».",
    },
    {
        "code": "sections.sales.settings.report_fields",
        "display_name": "Разделы: Продажи / Настройки / Поля отчетов",
        "description": "Доступ к подвкладке «Поля отчетов».",
    },
    {
        "code": "sections.sales.settings.sales_accounting",
        "display_name": "Разделы: Продажи / Настройки / Учет продаж",
        "description": "Доступ к подвкладке «Настройки учета продаж».",
    },
    {
        "code": "sections.sales.settings.non_cash_limits",
        "display_name": "Разделы: Продажи / Настройки / Лимиты безнала",
        "description": "Доступ к подвкладке «Лимиты безнала».",
    },
    {
        "code": "sections.dashboard.labor_fund",
        "display_name": "Разделы: Дашборд / ФОТ",
        "description": "Доступ к вкладке «Фонд оплаты труда».",
    },
    {
        "code": "sections.activity.log",
        "display_name": "Разделы: Журнал / Действия",
        "description": "Доступ к вкладке «Действия».",
    },
]

SECTION_PERMISSION_SOURCES = {
    "sections.staff.employees": [
        "staff.view_sensitive",
        "staff.manage_subordinates",
        "staff.manage_all",
        "staff_employees.view",
        "employees_card.view",
    ],
    "sections.staff.positions": ["positions.manage", "positions.edit", "positions.rate.manage"],
    "sections.staff.permissions": ["roles.manage", "positions.manage", "access_control.read", "access_control.manage"],
    "sections.settings.trainings": ["training.view", "training.manage"],
    "sections.settings.payroll_types": ["payroll.view", "payroll.manage"],
    "sections.settings.subdivisions": ["positions.manage"],
    "sections.settings.restaurants": [
        "restaurants.manage",
        "restaurants.view",
        "restaurants.settings.view",
        "restaurants.settings.manage",
    ],
    "sections.inventory.nomenclature": [
        "inventory.view",
        "inventory.manage",
        "inventory.nomenclature.view",
        "inventory.nomenclature.manage",
    ],
    "sections.inventory.movements": [
        "inventory.view",
        "inventory.manage",
        "inventory.movements.view",
        "inventory.movements.manage",
    ],
    "sections.inventory.tagged_items": [
        "inventory.view",
        "inventory.manage",
        "inventory.nomenclature.view",
        "inventory.nomenclature.manage",
    ],
    "sections.control.checklists": ["system.admin", "checklists.edit_all", "staff.manage_all"],
    "sections.accounting.invoices": [
        "accounting.invoices.view",
        "accounting.invoices.create",
        "accounting.invoices.edit",
        "accounting.invoices.status",
    ],
    "sections.accounting.advances": [
        "payroll.view",
        "payroll.manage",
        "payroll.advance.view",
        "payroll.advance.create",
        "payroll.advance.edit",
        "payroll.advance.status.review",
        "payroll.advance.status.confirm",
        "payroll.advance.status.ready",
        "payroll.advance.status.all",
        "payroll.advance.download",
        "payroll.advance.post",
        "payroll.advance.delete",
    ],
    "sections.kpi.metrics": ["system.admin", "kpi.view", "kpi.manage"],
    "sections.kpi.plan_fact": ["system.admin", "kpi.view", "kpi.manage"],
    "sections.kpi.facts": ["system.admin", "kpi.view", "kpi.manage"],
    "sections.kpi.payouts": ["system.admin", "kpi.view", "kpi.manage"],
    "sections.sales.report": ["sales.report.view_qty", "sales.report.view_money", "iiko.view", "iiko.manage"],
    "sections.sales.revenue": ["sales.report.view_money", "iiko.view", "iiko.manage"],
    "sections.sales.settings": [
        "sales.dishes.view",
        "sales.dishes.manage",
        "sales.tables.view",
        "sales.tables.manage",
        "iiko.view",
        "iiko.manage",
    ],
    "sections.sales.settings.nomenclature": ["sales.dishes.view", "sales.dishes.manage", "iiko.view", "iiko.manage"],
    "sections.sales.settings.tables": ["sales.tables.view", "sales.tables.manage", "iiko.view", "iiko.manage"],
    "sections.sales.settings.payment_types": ["iiko.view", "iiko.manage"],
    "sections.sales.settings.report_fields": ["iiko.view", "iiko.manage"],
    "sections.sales.settings.sales_accounting": ["iiko.view", "iiko.manage"],
    "sections.sales.settings.non_cash_limits": ["iiko.view", "iiko.manage"],
    "sections.dashboard.labor_fund": ["labor.summary.dashboard.view", "labor.summary.view"],
    "sections.activity.log": ["system.admin"],
}


def _permission_ids(bind) -> dict[str, int]:
    rows = bind.execute(sa.select(permissions_table.c.code, permissions_table.c.id)).all()
    return {str(code): int(permission_id) for code, permission_id in rows if code is not None and permission_id is not None}


def _upsert_permissions(bind) -> None:
    for payload in SECTION_PERMISSION_DEFINITIONS:
        code = payload["code"]
        values = {
            "name": payload["display_name"],
            "display_name": payload["display_name"],
            "description": payload["description"],
            "responsibility_zone": "Доступ к разделам",
        }
        stmt = pg_insert(permissions_table).values(code=code, **values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[permissions_table.c.code],
            set_=values,
        )
        bind.execute(stmt)


def _copy_permission_links(bind, table, owner_column, source_permission_ids: list[int], target_permission_id: int) -> None:
    if not source_permission_ids:
        return
    owner_rows = bind.execute(
        sa.select(owner_column).where(table.c.permission_id.in_(source_permission_ids))
    ).all()
    owner_ids = sorted({int(owner_id) for (owner_id,) in owner_rows if owner_id is not None})
    for owner_id in owner_ids:
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


def _seed_assignments(bind) -> None:
    ids = _permission_ids(bind)
    for section_code, source_codes in SECTION_PERMISSION_SOURCES.items():
        target_permission_id = ids.get(section_code)
        if target_permission_id is None:
            continue
        source_permission_ids = [ids[code] for code in source_codes if code in ids]
        if not source_permission_ids:
            continue
        _copy_permission_links(
            bind,
            role_permissions_table,
            role_permissions_table.c.role_id,
            source_permission_ids,
            target_permission_id,
        )
        _copy_permission_links(
            bind,
            position_permissions_table,
            position_permissions_table.c.position_id,
            source_permission_ids,
            target_permission_id,
        )
        _copy_permission_links(
            bind,
            user_permissions_table,
            user_permissions_table.c.user_id,
            source_permission_ids,
            target_permission_id,
        )


def upgrade() -> None:
    bind = op.get_bind()
    _upsert_permissions(bind)
    _seed_assignments(bind)


def downgrade() -> None:
    # Keep section permissions on downgrade to avoid dropping active access links.
    pass
