"""Add CIS document tracking tables and permissions.

Revision ID: c4b8d9a1c7fe
Revises: b14c3b9f2a61
Create Date: 2025-11-13 03:45:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c4b8d9a1c7fe"
down_revision: Union[str, Sequence[str], None] = "b14c3b9f2a61"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


cis_document_status_enum = postgresql.ENUM(
    "ok",
    "expiring",
    "expired",
    name="cis_document_status",
    create_type=False,
)

cis_document_types_table = sa.table(
    "cis_document_types",
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
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'cis_document_status') "
        "THEN CREATE TYPE cis_document_status AS ENUM ('ok', 'expiring', 'expired'); "
        "END IF; END $$;"
    )

    op.create_table(
        "cis_document_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=True, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("validity_months", sa.Integer(), nullable=True),
        sa.Column("notice_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("comment", sa.Text(), nullable=True),
    )
    op.create_index("ix_cis_document_types_name", "cis_document_types", ["name"], unique=False)

    op.create_table(
        "cis_document_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "cis_document_type_id",
            sa.Integer(),
            sa.ForeignKey("cis_document_types.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("number", sa.String(length=128), nullable=True),
        sa.Column("issued_at", sa.Date(), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("status", cis_document_status_enum, nullable=False, server_default="ok"),
        sa.Column("issuer", sa.String(length=255), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("attachment_url", sa.Text(), nullable=True),
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
            "cis_document_type_id",
            "number",
            name="uq_cis_document_record_user_type_number",
        ),
    )
    op.create_index(
        "ix_cis_document_records_user_type",
        "cis_document_records",
        ["user_id", "cis_document_type_id"],
        unique=False,
    )
    op.create_index(
        "ix_cis_document_records_expires_at",
        "cis_document_records",
        ["expires_at"],
        unique=False,
    )

    op.bulk_insert(
        cis_document_types_table,
        [
            {"code": "patent", "name": "Патент", "validity_months": 12, "notice_days": 30, "is_active": True},
            {
                "code": "stay_period",
                "name": "Срок пребывания",
                "validity_months": 6,
                "notice_days": 30,
                "is_active": True,
            },
            {
                "code": "personal_id",
                "name": "Личный документ сотрудника",
                "validity_months": None,
                "notice_days": 0,
                "is_active": True,
                "comment": "Серия/номер паспорта, внутренний документ",
            },
            {
                "code": "employment_notice",
                "name": "Уведомление о трудовой деятельности",
                "validity_months": 1,
                "notice_days": 15,
                "is_active": True,
            },
        ],
    )

    op.alter_column("cis_document_types", "notice_days", server_default=None)
    op.alter_column("cis_document_types", "is_active", server_default=None)

    existing_codes = {
        row.code for row in bind.execute(sa.select(permissions_table.c.code))
    }
    permission_rows = [
        {
            "code": "cis_documents.view",
            "name": "Просмотр документов СНГ",
            "display_name": "Документы СНГ: просмотр",
            "description": "Просмотр статусов патента, срока пребывания и прочих документов сотрудников.",
            "responsibility_zone": "HR",
        },
        {
            "code": "cis_documents.manage",
            "name": "Управление документами СНГ",
            "display_name": "Документы СНГ: управление",
            "description": "Создание и редактирование записей по документам иностранных сотрудников.",
            "responsibility_zone": "HR",
        },
    ]
    rows_to_insert = [row for row in permission_rows if row["code"] not in existing_codes]
    if rows_to_insert:
        op.bulk_insert(permissions_table, rows_to_insert)


def downgrade() -> None:
    op.execute(
        permissions_table.delete().where(
            permissions_table.c.code.in_(["cis_documents.view", "cis_documents.manage"])
        )
    )

    op.drop_index("ix_cis_document_records_expires_at", table_name="cis_document_records")
    op.drop_index("ix_cis_document_records_user_type", table_name="cis_document_records")
    op.drop_table("cis_document_records")

    op.drop_index("ix_cis_document_types_name", table_name="cis_document_types")
    op.drop_table("cis_document_types")

    op.execute("DROP TYPE IF EXISTS cis_document_status")
