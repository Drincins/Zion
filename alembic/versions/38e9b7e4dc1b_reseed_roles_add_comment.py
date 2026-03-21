"""Add comment to roles and reseed predefined roles.

Revision ID: 38e9b7e4dc1b
Revises: f20a2f8c1f5f
Create Date: 2025-10-31 13:15:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "38e9b7e4dc1b"
down_revision: Union[str, Sequence[str], None] = "f20a2f8c1f5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

metadata = sa.MetaData()
roles_table = sa.Table(
    "roles",
    metadata,
    sa.Column("id", sa.Integer),
    sa.Column("name", sa.String),
    sa.Column("level", sa.Integer),
    sa.Column("comment", sa.String),
)
role_permissions_table = sa.Table(
    "role_permissions",
    metadata,
    sa.Column("role_id", sa.Integer),
    sa.Column("permission_id", sa.Integer),
)
users_table = sa.Table(
    "users",
    metadata,
    sa.Column("id", sa.Integer),
    sa.Column("role_id", sa.Integer),
)
employee_positions_table = sa.Table(
    "employee_positions",
    metadata,
    sa.Column("id", sa.Integer),
    sa.Column("role_id", sa.Integer),
)

NEW_ROLES = [
    {"name": "Технический администратор", "level": 0, "comment": "Полный технический доступ ко всем подсистемам."},
    {"name": "Главный администратор", "level": 1, "comment": "Общий административный доступ без технических задач."},
    {"name": "Администратор подразделения", "level": 2, "comment": "Управление конкретным подразделением/рестораном."},
    {"name": "Младший администратор подразделения", "level": 3, "comment": "Помощник администратора подразделения."},
    {"name": "Пользователь", "level": 4, "comment": "Обычный пользователь с базовыми правами."},
    {"name": "Таймконтроль", "level": 5, "comment": "Доступ только к функциям контроля времени/табелей."},
]


def upgrade() -> None:
    op.add_column("roles", sa.Column("comment", sa.String(), nullable=True))
    op.alter_column("employee_positions", "role_id", existing_type=sa.Integer(), nullable=True)

    bind = op.get_bind()

    # Очистить зависимые записи и подготовить таблицы
    bind.execute(role_permissions_table.delete())
    bind.execute(sa.update(employee_positions_table).values(role_id=None))
    bind.execute(sa.update(users_table).values(role_id=None))
    bind.execute(sa.delete(roles_table))

    name_to_id: dict[str, int] = {}
    for role in NEW_ROLES:
        result = bind.execute(
            roles_table.insert()
            .values(name=role["name"], level=role["level"], comment=role["comment"])
            .returning(roles_table.c.id)
        )
        name_to_id[role["name"]] = result.scalar_one()

    default_role_id = name_to_id["Пользователь"]
    bind.execute(sa.update(users_table).values(role_id=default_role_id))
    bind.execute(sa.update(employee_positions_table).values(role_id=default_role_id))

    op.alter_column("employee_positions", "role_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    # Невозможно восстановить исходные роли; оставляем новые записи.
    op.drop_column("roles", "comment")
