"""Update permission display names and add granular staff/position permissions.

Revision ID: f7a8b9c0d1e2
Revises: f6a7b8c9d0e1
Create Date: 2025-01-10 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
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
        "display_name": "Системный администратор",
        "description": "Полный доступ ко всем разделам и настройкам.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "access_control.read",
        "display_name": "Права доступа: просмотр",
        "description": "Просмотр ролей, должностей и прав.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "access_control.manage",
        "display_name": "Права доступа: управление",
        "description": "Редактирование ролей, должностей и прав.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "roles.manage",
        "display_name": "Управление ролями",
        "description": "Создание и редактирование ролей.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "positions.manage",
        "display_name": "Управление должностями (полный доступ)",
        "description": "Создание, удаление и изменение структуры должностей.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "positions.edit",
        "display_name": "Редактирование данных должности",
        "description": "Изменение названия, кода и настроек должности.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "positions.rate.manage",
        "display_name": "Редактирование ставки должности",
        "description": "Изменение ставки в карточке должности.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "users.view",
        "display_name": "Просмотр пользователей",
        "description": "Просмотр данных пользователей.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "users.manage",
        "display_name": "Управление пользователями",
        "description": "Создание и редактирование пользователей.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "companies.view",
        "display_name": "Просмотр компаний",
        "description": "Просмотр компаний.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "companies.manage",
        "display_name": "Управление компаниями",
        "description": "Создание и редактирование компаний.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "restaurants.view",
        "display_name": "Просмотр ресторанов",
        "description": "Просмотр ресторанов и подразделений.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "restaurants.manage",
        "display_name": "Управление ресторанами",
        "description": "Создание и редактирование ресторанов.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "staff.view_sensitive",
        "display_name": "Просмотр данных сотрудников",
        "description": "Доступ к карточкам и персональным данным сотрудников.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff.manage_all",
        "display_name": "Управление сотрудниками (все)",
        "description": "Создание, редактирование и увольнение сотрудников во всех подразделениях.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff.manage_subordinates",
        "display_name": "Управление сотрудниками (подчиненные)",
        "description": "Редактирование сотрудников с учетом уровней ролей.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff_employees.view",
        "display_name": "Список сотрудников",
        "description": "Просмотр списка сотрудников.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff_employees.manage",
        "display_name": "Редактирование сотрудников (по доступным ресторанам)",
        "description": "Редактирование сотрудников, которые находятся в доступных ресторанах.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "employees_card.view",
        "display_name": "Карточка сотрудника",
        "description": "Просмотр HR-карточки сотрудника.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "employees_card.manage",
        "display_name": "Редактирование карточки сотрудника",
        "description": "Редактирование HR-карточки сотрудника при наличии доступа к ресторану.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff.roles.assign",
        "display_name": "Назначение ролей сотрудникам",
        "description": "Изменение роли сотрудника в карточке.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff.rate.manage",
        "display_name": "Редактирование ставки сотрудника",
        "description": "Изменение ставки и индивидуальной ставки сотрудника.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff_portal.access",
        "display_name": "Доступ в портал сотрудников",
        "description": "Доступ к порталу сотрудников.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "payroll.view",
        "display_name": "Зарплата: просмотр",
        "description": "Просмотр табелей и расчетов.",
        "responsibility_zone": "Зарплата",
    },
    {
        "code": "payroll.manage",
        "display_name": "Зарплата: управление",
        "description": "Редактирование табелей и расчетов.",
        "responsibility_zone": "Зарплата",
    },
    {
        "code": "payroll.export",
        "display_name": "Зарплата: выгрузка",
        "description": "Выгрузка расчетов и табелей.",
        "responsibility_zone": "Зарплата",
    },
    {
        "code": "payroll.results.view",
        "display_name": "Зарплата: результаты (просмотр)",
        "description": "Просмотр итогов расчетов.",
        "responsibility_zone": "Зарплата",
    },
    {
        "code": "payroll.results.manage",
        "display_name": "Зарплата: результаты (управление)",
        "description": "Редактирование итогов расчетов.",
        "responsibility_zone": "Зарплата",
    },
    {
        "code": "inventory.view",
        "display_name": "Склад: просмотр",
        "description": "Просмотр справочников и остатков склада.",
        "responsibility_zone": "Склад",
    },
    {
        "code": "inventory.manage",
        "display_name": "Склад: управление",
        "description": "Создание и редактирование складских данных.",
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
        "description": "Создание и редактирование KPI.",
        "responsibility_zone": "KPI",
    },
    {
        "code": "training.view",
        "display_name": "Обучение: просмотр",
        "description": "Просмотр обучений и требований.",
        "responsibility_zone": "Обучение",
    },
    {
        "code": "training.manage",
        "display_name": "Обучение: управление",
        "description": "Создание и редактирование обучений.",
        "responsibility_zone": "Обучение",
    },
    {
        "code": "iiko.view",
        "display_name": "iiko: просмотр",
        "description": "Просмотр данных iiko.",
        "responsibility_zone": "iiko",
    },
    {
        "code": "iiko.manage",
        "display_name": "iiko: управление",
        "description": "Запуск синхронизаций и настройка iiko.",
        "responsibility_zone": "iiko",
    },
    {
        "code": "iiko_products.read",
        "display_name": "iiko: товары (просмотр)",
        "description": "Просмотр товаров iiko.",
        "responsibility_zone": "iiko",
    },
    {
        "code": "iiko_olap_read.view",
        "display_name": "iiko OLAP: просмотр",
        "description": "Просмотр выгрузок OLAP.",
        "responsibility_zone": "iiko",
    },
    {
        "code": "iiko_olap_product.manage",
        "display_name": "iiko OLAP: управление",
        "description": "Запуск и управление выгрузками OLAP.",
        "responsibility_zone": "iiko",
    },
    {
        "code": "medical_checks.view",
        "display_name": "Медкнижки: просмотр",
        "description": "Просмотр медкнижек сотрудников.",
        "responsibility_zone": "Документы",
    },
    {
        "code": "medical_checks.manage",
        "display_name": "Медкнижки: управление",
        "description": "Редактирование медкнижек сотрудников.",
        "responsibility_zone": "Документы",
    },
    {
        "code": "cis_documents.view",
        "display_name": "Документы СНГ: просмотр",
        "description": "Просмотр документов СНГ.",
        "responsibility_zone": "Документы",
    },
    {
        "code": "cis_documents.manage",
        "display_name": "Документы СНГ: управление",
        "description": "Редактирование документов СНГ.",
        "responsibility_zone": "Документы",
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
    # No-op: keep updated labels to avoid losing human-friendly descriptions.
    pass
