"""Reseed medical check type catalog from the agreed list.

Revision ID: d2c4e8a7b1f0
Revises: b1c2d3e4f5a6
Create Date: 2025-12-22 12:30:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d2c4e8a7b1f0"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

medical_check_types_table = sa.table(
    "medical_check_types",
    sa.column("code", sa.String(length=32)),
    sa.column("name", sa.String(length=255)),
    sa.column("validity_months", sa.Integer),
    sa.column("notice_days", sa.Integer),
    sa.column("is_active", sa.Boolean),
    sa.column("comment", sa.Text),
)

MEDICAL_CHECK_TYPES = [
    {"code": "1", "name": "Аттестация", "validity_months": 12, "notice_days": 30, "is_active": True, "comment": None},
    {"code": "6", "name": "Брюшной тиф (при устройстве на работу)", "validity_months": 12, "notice_days": 30, "is_active": True, "comment": None},
    {"code": "8", "name": "Дерматовенеролог", "validity_months": 12, "notice_days": 30, "is_active": True, "comment": None},
    {"code": "7", "name": "Кишечные инфекции ВКИ (при устройстве на работу)", "validity_months": 12, "notice_days": 30, "is_active": True, "comment": None},
    {"code": "4", "name": "Лор (Оториноларинголог)", "validity_months": 12, "notice_days": 30, "is_active": True, "comment": None},
    {"code": "12", "name": "Прививка дифтерия", "validity_months": 120, "notice_days": 60, "is_active": True, "comment": None},
    {"code": "11", "name": "Прививка корь", "validity_months": None, "notice_days": 0, "is_active": True, "comment": "Единоразовая прививка"},
    {"code": "13", "name": "Сифилис", "validity_months": 12, "notice_days": 30, "is_active": True, "comment": None},
    {"code": "10", "name": "Стафилокок (при устройстве на работу)", "validity_months": 12, "notice_days": 30, "is_active": True, "comment": None},
    {"code": "3", "name": "Стоматолог", "validity_months": 12, "notice_days": 30, "is_active": True, "comment": None},
    {"code": "2", "name": "Терапевт", "validity_months": 12, "notice_days": 30, "is_active": True, "comment": None},
    {"code": "5", "name": "Флюорография", "validity_months": 12, "notice_days": 30, "is_active": True, "comment": None},
    {"code": "9", "name": "Я/глист (гельминты и энтеробиоз)", "validity_months": 12, "notice_days": 30, "is_active": True, "comment": None},
]


def upgrade() -> None:
    bind = op.get_bind()
    # Разблокируем swap кодов 11/13 (корь/сифилис), чтобы не ловить уникальные коллизии.
    bind.execute(
        sa.update(medical_check_types_table)
        .values(code=None)
        .where(medical_check_types_table.c.code.in_(["11", "13"]))
    )

    code_by_name = {"Прививка корь": "11", "Сифилис": "13"}
    for name, code in code_by_name.items():
        bind.execute(
            sa.update(medical_check_types_table)
            .values(code=code)
            .where(medical_check_types_table.c.name == name)
        )

    # Обновляем поля по коду.
    for row in MEDICAL_CHECK_TYPES:
        bind.execute(
            sa.update(medical_check_types_table)
            .values(
                name=row["name"],
                validity_months=row["validity_months"],
                notice_days=row["notice_days"],
                is_active=row["is_active"],
                comment=row["comment"],
            )
            .where(medical_check_types_table.c.code == row["code"])
        )

    # Добавляем отсутствующие (по коду и имени).
    existing_rows = list(bind.execute(sa.select(medical_check_types_table.c.code, medical_check_types_table.c.name)))
    existing_codes = {r.code for r in existing_rows if r.code}
    existing_names = {r.name for r in existing_rows if r.name}
    rows_to_insert = [
        row for row in MEDICAL_CHECK_TYPES if row["code"] not in existing_codes and row["name"] not in existing_names
    ]
    if rows_to_insert:
        op.bulk_insert(medical_check_types_table, rows_to_insert)


def downgrade() -> None:
    pass
