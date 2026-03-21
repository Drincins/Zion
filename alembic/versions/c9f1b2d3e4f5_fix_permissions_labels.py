"""Fix permission labels and add timesheet export permission.

Revision ID: c9f1b2d3e4f5
Revises: a8c9d0e1f2a3
Create Date: 2025-02-01 00:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c9f1b2d3e4f5"
down_revision: Union[str, Sequence[str], None] = "a8c9d0e1f2a3"
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
        "responsibility_zone": "Система",
    },
    {
        "code": "access_control.read",
        "display_name": "Доступ: просмотр прав",
        "description": "Просмотр ролей, должностей и назначенных прав.",
        "responsibility_zone": "Доступ",
    },
    {
        "code": "access_control.manage",
        "display_name": "Доступ: управление правами",
        "description": "Создание и редактирование ролей, должностей и назначений прав.",
        "responsibility_zone": "Доступ",
    },
    {
        "code": "roles.manage",
        "display_name": "Администрирование: роли",
        "description": "Создание и редактирование ролей.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "positions.manage",
        "display_name": "Администрирование: должности",
        "description": "Создание и редактирование должностей.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "positions.edit",
        "display_name": "Администрирование: редактирование должностей",
        "description": "Редактирование структуры и параметров должностей.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "positions.rate.manage",
        "display_name": "Администрирование: ставки должностей",
        "description": "Настройка ставок для должностей.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "users.view",
        "display_name": "Администрирование: просмотр пользователей",
        "description": "Просмотр учетных записей пользователей.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "users.manage",
        "display_name": "Администрирование: управление пользователями",
        "description": "Создание и редактирование учетных записей пользователей.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "companies.view",
        "display_name": "Администрирование: просмотр компаний",
        "description": "Просмотр компаний и их реквизитов.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "companies.manage",
        "display_name": "Администрирование: управление компаниями",
        "description": "Создание и редактирование компаний.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "restaurants.view",
        "display_name": "Администрирование: просмотр ресторанов",
        "description": "Просмотр ресторанов и их настроек.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "restaurants.manage",
        "display_name": "Администрирование: управление ресторанами",
        "description": "Создание и редактирование ресторанов.",
        "responsibility_zone": "Администрирование",
    },
    {
        "code": "staff.view_sensitive",
        "display_name": "Сотрудники: персональные данные",
        "description": "Просмотр чувствительных персональных данных сотрудников.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff.manage_all",
        "display_name": "Сотрудники: управление всеми",
        "description": "Полное управление карточками всех сотрудников.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff.manage_subordinates",
        "display_name": "Сотрудники: управление подчиненными",
        "description": "Управление карточками подчиненных сотрудников.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff_employees.view",
        "display_name": "Сотрудники: просмотр списка",
        "description": "Просмотр списка сотрудников.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff_employees.manage",
        "display_name": "Сотрудники: управление списком",
        "description": "Создание и редактирование сотрудников.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "employees_card.view",
        "display_name": "Сотрудники: HR-карточки (просмотр)",
        "description": "Просмотр HR-карточек сотрудников.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "employees_card.manage",
        "display_name": "Сотрудники: HR-карточки (редактирование)",
        "description": "Редактирование HR-карточек сотрудников.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff.roles.assign",
        "display_name": "Сотрудники: назначение ролей",
        "description": "Назначение ролей сотрудникам.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff.rate.manage",
        "display_name": "Сотрудники: индивидуальные ставки",
        "description": "Изменение индивидуальной ставки сотрудника.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff_portal.access",
        "display_name": "Сотрудники: доступ в портал",
        "description": "Доступ к порталу сотрудника.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "payroll.view",
        "display_name": "Зарплата: просмотр",
        "description": "Просмотр расчетов и данных по зарплате.",
        "responsibility_zone": "Зарплата",
    },
    {
        "code": "payroll.manage",
        "display_name": "Зарплата: редактирование",
        "description": "Редактирование расчетов и данных по зарплате.",
        "responsibility_zone": "Зарплата",
    },
    {
        "code": "payroll.export",
        "display_name": "Зарплата: выгрузка",
        "description": "Скачивание зарплатных отчетов.",
        "responsibility_zone": "Зарплата",
    },
    {
        "code": "payroll.results.view",
        "display_name": "Начисления/удержания: просмотр",
        "description": "Просмотр начислений и удержаний.",
        "responsibility_zone": "Зарплата",
    },
    {
        "code": "payroll.results.manage",
        "display_name": "Начисления/удержания: редактирование",
        "description": "Редактирование начислений и удержаний.",
        "responsibility_zone": "Зарплата",
    },
    {
        "code": "timesheet.export",
        "display_name": "Табель смен: выгрузка",
        "description": "Скачивание табеля смен.",
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
        "description": "Управление складскими операциями.",
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
        "description": "Настройка и управление KPI.",
        "responsibility_zone": "KPI",
    },
    {
        "code": "training.view",
        "display_name": "Обучение: просмотр",
        "description": "Просмотр обучения и материалов.",
        "responsibility_zone": "Обучение",
    },
    {
        "code": "training.manage",
        "display_name": "Обучение: управление",
        "description": "Создание и управление обучением.",
        "responsibility_zone": "Обучение",
    },
    {
        "code": "iiko.view",
        "display_name": "iiko: просмотр",
        "description": "Просмотр интеграции iiko.",
        "responsibility_zone": "iiko",
    },
    {
        "code": "iiko.manage",
        "display_name": "iiko: управление",
        "description": "Настройка интеграции iiko.",
        "responsibility_zone": "iiko",
    },
    {
        "code": "iiko_products.read",
        "display_name": "iiko: справочники (просмотр)",
        "description": "Просмотр справочников iiko.",
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
        "display_name": "iiko OLAP: управление",
        "description": "Управление отчетами iiko OLAP.",
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
    # Keep updated labels to avoid reintroducing garbled text.
    pass
