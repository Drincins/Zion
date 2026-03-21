"""Add medical check reference tables and seed default data.

Revision ID: b14c3b9f2a61
Revises: 4a8ba5b0bdb7
Create Date: 2025-11-13 02:30:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b14c3b9f2a61"
down_revision: Union[str, Sequence[str], None] = "4a8ba5b0bdb7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


medical_check_status_enum = postgresql.ENUM(
    "ok",
    "expiring",
    "expired",
    name="medical_check_status",
    create_type=False,
)

medical_check_types_table = sa.table(
    "medical_check_types",
    sa.column("code", sa.String(length=32)),
    sa.column("name", sa.String(length=255)),
    sa.column("validity_months", sa.Integer),
    sa.column("notice_days", sa.Integer),
    sa.column("is_active", sa.Boolean),
    sa.column("comment", sa.Text),
)

permissions_table = sa.table(
    "permissions",
    sa.column("code", sa.String(length=255)),
    sa.column("name", sa.String(length=255)),
    sa.column("description", sa.Text()),
    sa.column("display_name", sa.String(length=255)),
    sa.column("responsibility_zone", sa.String(length=255)),
)


def upgrade() -> None:
    bind = op.get_bind()
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'medical_check_status') "
        "THEN CREATE TYPE medical_check_status AS ENUM ('ok', 'expiring', 'expired'); "
        "END IF; END $$;"
    )
    status_enum_column = medical_check_status_enum

    op.create_table(
        "medical_check_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=True, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("validity_months", sa.Integer(), nullable=True),
        sa.Column("notice_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("comment", sa.Text(), nullable=True),
    )
    op.create_index("ix_medical_check_types_name", "medical_check_types", ["name"], unique=False)

    op.create_table(
        "medical_check_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "medical_check_type_id",
            sa.Integer(),
            sa.ForeignKey("medical_check_types.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("passed_at", sa.Date(), nullable=False),
        sa.Column("next_due_at", sa.Date(), nullable=True),
        # use copy so SQLAlchemy will not try to re-create the type at table creation
        sa.Column("status", status_enum_column, nullable=False, server_default="ok"),
        sa.Column("issuer", sa.String(length=255), nullable=True),
        sa.Column("attachment_url", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "user_id",
            "medical_check_type_id",
            "passed_at",
            name="uq_medical_check_records_user_type_date",
        ),
    )
    op.create_index(
        "ix_medical_check_records_user_type",
        "medical_check_records",
        ["user_id", "medical_check_type_id"],
        unique=False,
    )
    op.create_index(
        "ix_medical_check_records_next_due",
        "medical_check_records",
        ["next_due_at"],
        unique=False,
    )

    op.bulk_insert(
        medical_check_types_table,
        [
            {"code": "1", "name": "Аттестация", "validity_months": 12, "notice_days": 30, "is_active": True},
            {"code": "6", "name": "Брюшной тиф (при устройстве на работу)", "validity_months": 12, "notice_days": 30, "is_active": True},
            {"code": "8", "name": "Дерматовенеролог", "validity_months": 12, "notice_days": 30, "is_active": True},
            {"code": "7", "name": "Кишечные инфекции ВКИ (при устройстве на работу)", "validity_months": 12, "notice_days": 30, "is_active": True},
            {"code": "4", "name": "ЛОР (отоларинголог)", "validity_months": 12, "notice_days": 30, "is_active": True},
            {"code": "12", "name": "Прививка дифтерия", "validity_months": 120, "notice_days": 60, "is_active": True},
            {"code": "13", "name": "Прививка корь", "validity_months": None, "notice_days": 0, "is_active": True, "comment": "Единоразовая прививка"},
            {"code": "11", "name": "Сифилис", "validity_months": 12, "notice_days": 30, "is_active": True},
            {"code": "10", "name": "Стафилокок (при устройстве на работу)", "validity_months": 12, "notice_days": 30, "is_active": True},
            {"code": "3", "name": "Стоматолог", "validity_months": 12, "notice_days": 30, "is_active": True},
            {"code": "2", "name": "Терапевт", "validity_months": 12, "notice_days": 30, "is_active": True},
            {"code": "5", "name": "Флюорография", "validity_months": 12, "notice_days": 30, "is_active": True},
            {"code": "9", "name": "Я/лист (гельминты и энтеробиоз)", "validity_months": 12, "notice_days": 30, "is_active": True},
        ],
    )

    op.alter_column("medical_check_types", "notice_days", server_default=None)
    op.alter_column("medical_check_types", "is_active", server_default=None)

    existing_codes = {
        row.code for row in bind.execute(sa.select(permissions_table.c.code))
    }
    permission_rows = [
        {
            "code": "medical_checks.view",
            "name": "Просмотр медкнижек сотрудников",
            "display_name": "Медкнижки: просмотр",
            "description": "Доступ к перечню медицинских осмотров сотрудников.",
            "responsibility_zone": "HR",
        },
        {
            "code": "medical_checks.manage",
            "name": "Управление медкнижками сотрудников",
            "display_name": "Медкнижки: управление",
            "description": "Создание, редактирование и удаление записей медицинских осмотров.",
            "responsibility_zone": "HR",
        },
    ]
    rows_to_insert = [row for row in permission_rows if row["code"] not in existing_codes]
    if rows_to_insert:
        op.bulk_insert(permissions_table, rows_to_insert)


def downgrade() -> None:
    op.drop_index("ix_medical_check_records_next_due", table_name="medical_check_records")
    op.drop_index("ix_medical_check_records_user_type", table_name="medical_check_records")
    op.drop_table("medical_check_records")

    op.drop_index("ix_medical_check_types_name", table_name="medical_check_types")
    op.drop_table("medical_check_types")

    bind = op.get_bind()
    op.execute("DROP TYPE IF EXISTS medical_check_status")

    op.execute(
        permissions_table.delete().where(
            permissions_table.c.code.in_(["medical_checks.view", "medical_checks.manage"])
        )
    )
