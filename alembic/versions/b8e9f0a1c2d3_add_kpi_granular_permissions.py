"""Add granular KPI permissions.

Revision ID: b8e9f0a1c2d3
Revises: e7c4a1b2d3f9
Create Date: 2026-03-10 20:30:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b8e9f0a1c2d3"
down_revision: Union[str, Sequence[str], None] = "e7c4a1b2d3f9"
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


KPI_PERMISSION_DEFINITIONS = [
    {
        "code": "kpi.metrics.view",
        "name": "KPI: показатели (просмотр)",
        "display_name": "KPI: показатели (просмотр)",
        "description": "Просмотр списка KPI-показателей.",
        "responsibility_zone": "KPI",
    },
    {
        "code": "kpi.metrics.manage",
        "name": "KPI: показатели (редактирование)",
        "display_name": "KPI: показатели (редактирование)",
        "description": "Создание, изменение и удаление KPI-показателей.",
        "responsibility_zone": "KPI",
    },
    {
        "code": "kpi.metric_groups.view",
        "name": "KPI: группы показателей (просмотр)",
        "display_name": "KPI: группы показателей (просмотр)",
        "description": "Просмотр групп KPI-показателей.",
        "responsibility_zone": "KPI",
    },
    {
        "code": "kpi.metric_groups.manage",
        "name": "KPI: группы показателей (редактирование)",
        "display_name": "KPI: группы показателей (редактирование)",
        "description": "Создание, изменение и удаление групп KPI-показателей.",
        "responsibility_zone": "KPI",
    },
    {
        "code": "kpi.rules.assign",
        "name": "KPI: назначение правил",
        "display_name": "KPI: назначение правил",
        "description": "Назначение и редактирование правил KPI для показателей и групп.",
        "responsibility_zone": "KPI",
    },
    {
        "code": "kpi.facts.view",
        "name": "KPI: фактические результаты (просмотр)",
        "display_name": "KPI: фактические результаты (просмотр)",
        "description": "Просмотр фактических результатов KPI.",
        "responsibility_zone": "KPI",
    },
    {
        "code": "kpi.facts.manage",
        "name": "KPI: фактические результаты (редактирование)",
        "display_name": "KPI: фактические результаты (редактирование)",
        "description": "Редактирование фактических результатов KPI.",
        "responsibility_zone": "KPI",
    },
    {
        "code": "kpi.results.view",
        "name": "KPI: результаты (просмотр)",
        "display_name": "KPI: результаты (просмотр)",
        "description": "Просмотр результатов KPI.",
        "responsibility_zone": "KPI",
    },
    {
        "code": "kpi.payouts.view",
        "name": "KPI: выплаты (просмотр)",
        "display_name": "KPI: выплаты (просмотр)",
        "description": "Просмотр истории и деталей KPI-выплат.",
        "responsibility_zone": "KPI",
    },
    {
        "code": "kpi.payouts.manage",
        "name": "KPI: выплаты (формирование)",
        "display_name": "KPI: выплаты (формирование)",
        "description": "Формирование, редактирование и проведение KPI-выплат.",
        "responsibility_zone": "KPI",
    },
]


def upgrade() -> None:
    bind = op.get_bind()
    existing_codes = {
        row.code for row in bind.execute(sa.select(permissions_table.c.code))
    }

    for item in KPI_PERMISSION_DEFINITIONS:
        values = {
            "name": item["name"],
            "display_name": item["display_name"],
            "description": item["description"],
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
    bind = op.get_bind()
    bind.execute(
        permissions_table.delete().where(
            permissions_table.c.code.in_([item["code"] for item in KPI_PERMISSION_DEFINITIONS])
        )
    )
