"""Rename labor summary cost permission label to fact-cost wording.

Revision ID: d1f2e3a4b5c6
Revises: c9d8e7f6a5b4
Create Date: 2026-03-11 20:55:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d1f2e3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c9d8e7f6a5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


metadata = sa.MetaData()
permissions_table = sa.Table(
    "permissions",
    metadata,
    sa.Column("code", sa.String),
    sa.Column("name", sa.String),
    sa.Column("display_name", sa.String),
    sa.Column("description", sa.String),
)

PERMISSION_CODE = "labor.summary.view_cost"

NEXT_VALUES = {
    "name": "ФОТ: просмотр факта затрат",
    "display_name": "ФОТ: просмотр факта затрат",
    "description": "Просмотр денежных метрик ФОТ и факта затрат.",
}

PREV_VALUES = {
    "name": "Сводка по труду: просмотр сумм",
    "display_name": "Сводка по труду: просмотр сумм",
    "description": "Просмотр сводки по труду с суммами.",
}


def _update_permission(values: dict[str, str]) -> None:
    bind = op.get_bind()
    bind.execute(
        sa.update(permissions_table)
        .where(permissions_table.c.code == PERMISSION_CODE)
        .values(**values)
    )


def upgrade() -> None:
    _update_permission(NEXT_VALUES)


def downgrade() -> None:
    _update_permission(PREV_VALUES)

