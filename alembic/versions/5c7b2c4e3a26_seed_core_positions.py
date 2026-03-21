"""Seed initial employee positions linked to roles.

Revision ID: 5c7b2c4e3a26
Revises: 38e9b7e4dc1b
Create Date: 2025-10-31 14:05:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "5c7b2c4e3a26"
down_revision: Union[str, Sequence[str], None] = "38e9b7e4dc1b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

metadata = sa.MetaData()
roles_table = sa.Table(
    "roles",
    metadata,
    sa.Column("id", sa.Integer),
    sa.Column("name", sa.String),
)
employee_positions_table = sa.Table(
    "employee_positions",
    metadata,
    sa.Column("id", sa.Integer),
    sa.Column("name", sa.String),
    sa.Column("role_id", sa.Integer),
    sa.Column("hierarchy_level", sa.Integer),
)

POSITIONS = [
    ("Операционный директор", "Главный администратор", 0),
    ("Технический администратор", "Технический администратор", 0),
    ("Управляющий", "Администратор подразделения", 1),
    ("Администратор подразделений", "Младший администратор подразделения", 2),
    ("Таймконтроль", "Таймконтроль", 3),
]


def upgrade() -> None:
    bind = op.get_bind()
    role_id_by_name = {
        row.name: row.id
        for row in bind.execute(sa.select(roles_table.c.name, roles_table.c.id))
    }

    for position_name, role_name, level in POSITIONS:
        role_id = role_id_by_name.get(role_name)
        if role_id is None:
            continue
        exists = bind.execute(
            sa.select(employee_positions_table.c.id).where(employee_positions_table.c.name == position_name)
        ).first()
        if exists:
            continue
        bind.execute(
            employee_positions_table.insert().values(
                name=position_name,
                role_id=role_id,
                hierarchy_level=level,
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        employee_positions_table.delete().where(
            employee_positions_table.c.name.in_([name for name, _, _ in POSITIONS])
        )
    )
