"""Update permission labels in Russian.

Revision ID: f9a0b1c2d3e4
Revises: f8d9e0f1a2b3
Create Date: 2026-01-10 00:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f9a0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "f8d9e0f1a2b3"
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
        "code": "system.admin",
        "display_name": "Система: полный доступ",
        "description": "Полный доступ ко всем разделам и настройкам.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "access_control.read",
        "display_name": "Права доступа: просмотр",
        "description": "Просмотр списка прав, ролей и назначений.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "access_control.manage",
        "display_name": "Права доступа: управление",
        "description": "Создание и редактирование прав, ролей и назначений.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "roles.manage",
        "display_name": "Роли: управление",
        "description": "Создание и редактирование ролей.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "positions.manage",
        "display_name": "Должности: управление",
        "description": "Создание, удаление и управление должностями.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "positions.edit",
        "display_name": "Должности: редактирование",
        "description": "Редактирование названия и параметров должности.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "positions.rate.manage",
        "display_name": "Должности: ставки",
        "description": "Изменение ставок должностей.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "users.view",
        "display_name": "Пользователи: просмотр",
        "description": "Просмотр пользователей системы.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "users.manage",
        "display_name": "Пользователи: управление",
        "description": "Создание и редактирование пользователей.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "companies.view",
        "display_name": "Компании: просмотр",
        "description": "Просмотр компаний.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "companies.manage",
        "display_name": "Компании: управление",
        "description": "Создание и редактирование компаний.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "restaurants.view",
        "display_name": "Рестораны: просмотр",
        "description": "Просмотр ресторанов.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "restaurants.manage",
        "display_name": "Рестораны: управление",
        "description": "Создание и редактирование ресторанов.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "staff.view_sensitive",
        "display_name": "Сотрудники: персональные данные",
        "description": "Доступ к персональным данным сотрудников.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff.manage_all",
        "display_name": "Сотрудники: полный доступ",
        "description": "Полный доступ к сотрудникам без ограничений.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff.manage_subordinates",
        "display_name": "Сотрудники: управление подчиненными",
        "description": "Управление подчиненными сотрудниками.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff_employees.view",
        "display_name": "Сотрудники: список",
        "description": "Просмотр списка сотрудников.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff_employees.manage",
        "display_name": "Сотрудники: управление",
        "description": "Создание и редактирование сотрудников.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "employees_card.view",
        "display_name": "HR-карточка: просмотр",
        "description": "Просмотр HR-карточки сотрудника.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "employees_card.manage",
        "display_name": "HR-карточка: редактирование",
        "description": "Редактирование HR-карточки сотрудника.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff.roles.assign",
        "display_name": "Сотрудники: назначение должности",
        "description": "Назначение должности или роли сотруднику.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff.rate.manage",
        "display_name": "Сотрудники: индивидуальная ставка",
        "description": "Назначение индивидуальной ставки сотруднику.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff_portal.access",
        "display_name": "Портал сотрудника: доступ",
        "description": "Доступ к порталу сотрудника.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "employee_changes.view",
        "display_name": "История изменений: просмотр",
        "description": "Просмотр истории изменений сотрудника.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "employee_changes.manage",
        "display_name": "История изменений: редактирование",
        "description": "Редактирование истории изменений сотрудника.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "employee_changes.delete",
        "display_name": "История изменений: удаление",
        "description": "Удаление записей истории изменений сотрудника.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "payroll.view",
        "display_name": "Зарплата: просмотр",
        "description": "Просмотр данных по зарплате.",
        "responsibility_zone": "Зарплата",
    },
    {
        "code": "payroll.manage",
        "display_name": "Зарплата: управление",
        "description": "Управление данными по зарплате.",
        "responsibility_zone": "Зарплата",
    },
    {
        "code": "payroll.export",
        "display_name": "Зарплата: выгрузка",
        "description": "Выгрузка данных по зарплате.",
        "responsibility_zone": "Зарплата",
    },
    {
        "code": "payroll.results.view",
        "display_name": "Зарплата: результаты (просмотр)",
        "description": "Просмотр итогов расчета зарплаты.",
        "responsibility_zone": "Зарплата",
    },
    {
        "code": "payroll.results.manage",
        "display_name": "Зарплата: результаты (пересчет)",
        "description": "Пересчет итогов расчета зарплаты.",
        "responsibility_zone": "Зарплата",
    },
    {
        "code": "timesheet.export",
        "display_name": "Табель смен: выгрузка",
        "description": "Выгрузка табеля смен.",
        "responsibility_zone": "Табель смен",
    },
    {
        "code": "inventory.view",
        "display_name": "Склад: просмотр",
        "description": "Просмотр складских данных.",
        "responsibility_zone": "Склад",
    },
    {
        "code": "inventory.manage",
        "display_name": "Склад: управление",
        "description": "Управление складскими данными.",
        "responsibility_zone": "Склад",
    },
    {
        "code": "kpi.view",
        "display_name": "KPI: просмотр",
        "description": "Просмотр KPI.",
        "responsibility_zone": "KPI",
    },
    {
        "code": "kpi.manage",
        "display_name": "KPI: управление",
        "description": "Управление KPI.",
        "responsibility_zone": "KPI",
    },
    {
        "code": "training.view",
        "display_name": "Обучение: просмотр",
        "description": "Просмотр обучающих мероприятий.",
        "responsibility_zone": "Обучение",
    },
    {
        "code": "training.manage",
        "display_name": "Обучение: управление",
        "description": "Управление обучающими мероприятиями.",
        "responsibility_zone": "Обучение",
    },
    {
        "code": "iiko.view",
        "display_name": "iiko: просмотр",
        "description": "Просмотр данных интеграции iiko.",
        "responsibility_zone": "iiko",
    },
    {
        "code": "iiko.manage",
        "display_name": "iiko: управление",
        "description": "Управление интеграцией iiko.",
        "responsibility_zone": "iiko",
    },
    {
        "code": "iiko_products.read",
        "display_name": "iiko: товары (просмотр)",
        "description": "Просмотр справочника товаров iiko.",
        "responsibility_zone": "iiko",
    },
    {
        "code": "iiko_olap_read.view",
        "display_name": "iiko OLAP: просмотр",
        "description": "Просмотр отчетов iiko OLAP.",
        "responsibility_zone": "iiko",
    },
    {
        "code": "iiko_olap_product.manage",
        "display_name": "iiko OLAP: синхронизация",
        "description": "Синхронизация данных iiko OLAP.",
        "responsibility_zone": "iiko",
    },
    {
        "code": "medical_checks.view",
        "display_name": "Кадры: медосмотры (просмотр)",
        "description": "Просмотр медосмотров сотрудников.",
        "responsibility_zone": "Кадры",
    },
    {
        "code": "medical_checks.manage",
        "display_name": "Кадры: медосмотры (управление)",
        "description": "Управление медосмотрами сотрудников.",
        "responsibility_zone": "Кадры",
    },
    {
        "code": "cis_documents.view",
        "display_name": "Кадры: CIS-документы (просмотр)",
        "description": "Просмотр CIS-документов.",
        "responsibility_zone": "Кадры",
    },
    {
        "code": "cis_documents.manage",
        "display_name": "Кадры: CIS-документы (управление)",
        "description": "Управление CIS-документами.",
        "responsibility_zone": "Кадры",
    },
    {
        "code": "labor.summary.view",
        "display_name": "Сводка по труду: просмотр",
        "description": "Просмотр сводки по труду (часы).",
        "responsibility_zone": "Сводка по труду",
    },
    {
        "code": "labor.summary.view_cost",
        "display_name": "Сводка по труду: просмотр сумм",
        "description": "Просмотр сводки по труду с суммами.",
        "responsibility_zone": "Сводка по труду",
    },
    {
        "code": "labor.summary.dashboard.view",
        "display_name": "Сводка по труду: дашборд",
        "description": "Просмотр дашборда сводки по труду.",
        "responsibility_zone": "Сводка по труду",
    },
]


def upgrade() -> None:
    bind = op.get_bind()
    existing_codes = {
        row.code for row in bind.execute(sa.select(permissions_table.c.code))
    }
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
            bind.execute(
                permissions_table.insert().values(code=item["code"], **values)
            )


def downgrade() -> None:
    # Keep Russian labels on downgrade to avoid reintroducing unreadable text.
    pass
