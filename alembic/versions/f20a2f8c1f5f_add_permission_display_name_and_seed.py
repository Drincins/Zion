"""Add display_name to permissions and seed default entries.

Revision ID: f20a2f8c1f5f
Revises: d21f0a1c8f0f
Create Date: 2025-10-31 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f20a2f8c1f5f"
down_revision: Union[str, Sequence[str], None] = "d21f0a1c8f0f"
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
)

PERMISSION_DEFINITIONS = [
    {
        "code": "system.admin",
        "name": "Суперадминистратор",
        "display_name": "Суперадминистратор",
        "description": "Полный доступ ко всем разделам и операциям без ограничений.",
        "responsibility_zone": "Системные",
    },
    {
        "code": "staff.manage_all",
        "name": "Управление всеми сотрудниками",
        "display_name": "Управление всеми сотрудниками",
        "description": "Полный доступ к данным сотрудников независимо от ресторана или должности.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff.manage_subordinates",
        "name": "Управление подчинёнными",
        "display_name": "Управление подчинёнными",
        "description": "Работа только со своими подчинёнными в рамках доступных ресторанов.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff.view_sensitive",
        "name": "Просмотр чувствительных данных",
        "display_name": "Просмотр чувствительных данных",
        "description": "Просмотр зарплат, контактов и других чувствительных полей сотрудников.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "roles.manage",
        "name": "Управление ролями",
        "display_name": "Управление ролями",
        "description": "Создание и редактирование ролей и наборов прав.",
        "responsibility_zone": "Системные",
    },
    {
        "code": "positions.manage",
        "name": "Управление должностями",
        "display_name": "Управление должностями",
        "description": "Настройка дерева должностей и связей с ролями и ставками.",
        "responsibility_zone": "Системные",
    },
    {
        "code": "users.view",
        "name": "Просмотр пользователей",
        "display_name": "Просмотр пользователей",
        "description": "Чтение списка пользователей админ-панели.",
        "responsibility_zone": "Пользователи",
    },
    {
        "code": "users.manage",
        "name": "Управление пользователями",
        "display_name": "Управление пользователями",
        "description": "Создание, редактирование и удаление пользователей, сброс паролей.",
        "responsibility_zone": "Пользователи",
    },
    {
        "code": "companies.view",
        "name": "Просмотр компаний",
        "display_name": "Просмотр компаний",
        "description": "Просмотр справочника юридических лиц и реквизитов.",
        "responsibility_zone": "Справочники",
    },
    {
        "code": "companies.manage",
        "name": "Управление компаниями",
        "display_name": "Управление компаниями",
        "description": "Создание и редактирование компаний и связанных данных.",
        "responsibility_zone": "Справочники",
    },
    {
        "code": "restaurants.view",
        "name": "Просмотр ресторанов",
        "display_name": "Просмотр ресторанов",
        "description": "Просмотр списка ресторанов и их настроек.",
        "responsibility_zone": "Справочники",
    },
    {
        "code": "restaurants.manage",
        "name": "Управление ресторанами",
        "display_name": "Управление ресторанами",
        "description": "Создание и редактирование ресторанов, управление доступами.",
        "responsibility_zone": "Справочники",
    },
    {
        "code": "inventory.view",
        "name": "Просмотр складского учёта",
        "display_name": "Просмотр складского учёта",
        "description": "Чтение справочников и отчётов по инвентаризации.",
        "responsibility_zone": "Склад",
    },
    {
        "code": "inventory.manage",
        "name": "Управление складским учётом",
        "display_name": "Управление складским учётом",
        "description": "Изменение номенклатуры, категорий и документов инвентаризации.",
        "responsibility_zone": "Склад",
    },
    {
        "code": "payroll.view",
        "name": "Просмотр выплат",
        "display_name": "Просмотр выплат",
        "description": "Просмотр выплат, корректировок и показателей расчёта.",
        "responsibility_zone": "Финансы",
    },
    {
        "code": "payroll.manage",
        "name": "Управление выплатами",
        "display_name": "Управление выплатами",
        "description": "Создание и утверждение выплат и корректировок.",
        "responsibility_zone": "Финансы",
    },
    {
        "code": "training.view",
        "name": "Просмотр тренингов",
        "display_name": "Просмотр тренингов",
        "description": "Просмотр типов тренингов и истории прохождений.",
        "responsibility_zone": "Тренинги",
    },
    {
        "code": "training.manage",
        "name": "Управление тренингами",
        "display_name": "Управление тренингами",
        "description": "Управление справочником тренингов и регистрацией результатов.",
        "responsibility_zone": "Тренинги",
    },
    {
        "code": "iiko.view",
        "name": "Просмотр интеграций iiko",
        "display_name": "Просмотр интеграций iiko",
        "description": "Просмотр настроек интеграций и состояния обмена с iiko.",
        "responsibility_zone": "Интеграции iiko",
    },
    {
        "code": "iiko.manage",
        "name": "Управление интеграциями iiko",
        "display_name": "Управление интеграциями iiko",
        "description": "Настройка подключений, учётных данных и расписаний синхронизации.",
        "responsibility_zone": "Интеграции iiko",
    },
    {
        "code": "iiko_products.read",
        "name": "Чтение справочника блюд iiko",
        "display_name": "Чтение справочника блюд iiko",
        "description": "Импорт и просмотр продуктовой матрицы из iiko.",
        "responsibility_zone": "Интеграции iiko",
    },
    {
        "code": "iiko_olap_read.view",
        "name": "Просмотр отчётов iiko OLAP",
        "display_name": "Просмотр отчётов iiko OLAP",
        "description": "Доступ к отчётам iiko OLAP (выручка, продажи и т.д.).",
        "responsibility_zone": "Интеграции iiko",
    },
    {
        "code": "iiko_olap_product.manage",
        "name": "Управление выгрузками iiko OLAP",
        "display_name": "Управление выгрузками iiko OLAP",
        "description": "Настройка задач выгрузки товарных показателей из iiko OLAP.",
        "responsibility_zone": "Интеграции iiko",
    },
    {
        "code": "staff_portal.access",
        "name": "Доступ к тайм-контролю",
        "display_name": "Доступ к тайм-контролю",
        "description": "Авторизация по staff-коду в терминале и мобильном тайм-контроле.",
        "responsibility_zone": "Тайм-контроль",
    },
    {
        "code": "staff_employees.view",
        "name": "Просмотр раздела “Сотрудники”",
        "display_name": "Просмотр раздела “Сотрудники”",
        "description": "Просмотр списка сотрудников, карточек и графиков смен.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "staff_employees.manage",
        "name": "Управление разделом “Сотрудники”",
        "display_name": "Управление разделом “Сотрудники”",
        "description": "Редактирование данных сотрудников и операций со сменами.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "employees_card.view",
        "name": "Просмотр HR-карточки",
        "display_name": "Просмотр HR-карточки",
        "description": "Просмотр полной кадровой карточки сотрудника.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "employees_card.manage",
        "name": "Управление HR-карточкой",
        "display_name": "Управление HR-карточкой",
        "description": "Редактирование кадровых данных и документов сотрудника.",
        "responsibility_zone": "Сотрудники",
    },
    {
        "code": "access_control.read",
        "name": "Просмотр каталога прав",
        "display_name": "Просмотр каталога прав",
        "description": "Просмотр прав, ролей и должностей.",
        "responsibility_zone": "Системные",
    },
    {
        "code": "access_control.manage",
        "name": "Управление каталогом прав",
        "display_name": "Управление каталогом прав",
        "description": "Создание и редактирование прав, ролей и связей с должностями.",
        "responsibility_zone": "Системные",
    },
]

def upgrade() -> None:
    op.add_column("permissions", sa.Column("display_name", sa.String(), nullable=True))

    bind = op.get_bind()
    existing_codes = {
        row.code for row in bind.execute(sa.select(permissions_table.c.code))
    }

    for item in PERMISSION_DEFINITIONS:
        values = {
            "name": item["name"],
            "description": item["description"],
            "display_name": item["display_name"],
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
    op.drop_column("permissions", "display_name")
