"""Add accounting invoices tables and permissions.

Revision ID: 0a1b2c3d4e5f
Revises: fd4e5f6a7b8c
Create Date: 2026-01-20 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0a1b2c3d4e5f"
# Based on latest merged head before accounting module
down_revision: Union[str, Sequence[str], None] = "cb8a91487c6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accounting_invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("from_restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("for_restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payee", sa.String(length=255), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.Date(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("invoice_file_key", sa.Text(), nullable=False),
        sa.Column("payment_order_file_key", sa.Text(), nullable=True),
        sa.Column("include_in_expenses", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_accounting_invoices_status", "accounting_invoices", ["status"])
    op.create_index("ix_accounting_invoices_sent_at", "accounting_invoices", ["sent_at"])
    op.create_index("ix_accounting_invoices_restaurants", "accounting_invoices", ["from_restaurant_id", "for_restaurant_id"])
    op.create_index("ix_accounting_invoices_created_by", "accounting_invoices", ["created_by_user_id"])

    op.create_table(
        "accounting_invoice_closing_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("accounting_invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_key", sa.Text(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_accounting_invoice_closing_documents_invoice", "accounting_invoice_closing_documents", ["invoice_id"])

    op.create_table(
        "accounting_invoice_changes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("accounting_invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field", sa.String(length=64), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("changed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_accounting_invoice_changes_invoice", "accounting_invoice_changes", ["invoice_id"])

    op.create_table(
        "accounting_invoice_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("accounting_invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_accounting_invoice_events_invoice", "accounting_invoice_events", ["invoice_id"])

    # Seed permissions
    permissions_table = sa.table(
        "permissions",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("display_name", sa.String),
        sa.column("responsibility_zone", sa.String),
    )
    op.bulk_insert(
        permissions_table,
        [
            {
                "code": "accounting.invoices.view",
                "name": "Бухгалтерия: просмотр счетов",
                "description": "Просмотр списка счетов и истории.",
                "display_name": "Бухгалтерия: просмотр счетов",
                "responsibility_zone": "accounting",
            },
            {
                "code": "accounting.invoices.create",
                "name": "Бухгалтерия: создание счетов",
                "description": "Создание счетов и отправка в бухгалтерию.",
                "display_name": "Бухгалтерия: создание счетов",
                "responsibility_zone": "accounting",
            },
            {
                "code": "accounting.invoices.edit",
                "name": "Бухгалтерия: редактирование счетов",
                "description": "Редактирование счетов, файлов и флагов расходов.",
                "display_name": "Бухгалтерия: редактирование счетов",
                "responsibility_zone": "accounting",
            },
            {
                "code": "accounting.invoices.status",
                "name": "Бухгалтерия: смена статуса счетов",
                "description": "Изменение статусов счетов.",
                "display_name": "Бухгалтерия: смена статуса счетов",
                "responsibility_zone": "accounting",
            },
            {
                "code": "accounting.invoices.delete",
                "name": "Бухгалтерия: удаление счетов",
                "description": "Удаление счетов.",
                "display_name": "Бухгалтерия: удаление счетов",
                "responsibility_zone": "accounting",
            },
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM permissions WHERE code LIKE 'accounting.invoices.%'")
    op.drop_index("ix_accounting_invoice_events_invoice", table_name="accounting_invoice_events")
    op.drop_table("accounting_invoice_events")
    op.drop_index("ix_accounting_invoice_changes_invoice", table_name="accounting_invoice_changes")
    op.drop_table("accounting_invoice_changes")
    op.drop_index("ix_accounting_invoice_closing_documents_invoice", table_name="accounting_invoice_closing_documents")
    op.drop_table("accounting_invoice_closing_documents")
    op.drop_index("ix_accounting_invoices_created_by", table_name="accounting_invoices")
    op.drop_index("ix_accounting_invoices_restaurants", table_name="accounting_invoices")
    op.drop_index("ix_accounting_invoices_sent_at", table_name="accounting_invoices")
    op.drop_index("ix_accounting_invoices_status", table_name="accounting_invoices")
    op.drop_table("accounting_invoices")
