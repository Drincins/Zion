"""Add labor summary settings table and manage permission.

Revision ID: c9d8e7f6a5b4
Revises: b8e9f0a1c2d3, 1a2b3c4d5e6f
Create Date: 2026-03-11 17:10:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, Sequence[str], None] = ("b8e9f0a1c2d3", "1a2b3c4d5e6f")
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

PERMISSION_SETTINGS_MANAGE = {
    "code": "labor.summary.settings.manage",
    "name": "ФОТ: настройки расчета (управление)",
    "display_name": "ФОТ: настройки расчета (управление)",
    "description": "Изменение постоянных настроек расчета ФОТ (затраты, типы корректировок, выручка).",
    "responsibility_zone": "ФОТ",
}


def _upsert_permission(bind, payload: dict[str, str]) -> None:
    code = payload["code"]
    values = {
        "name": payload["name"],
        "display_name": payload["display_name"],
        "description": payload["description"],
        "responsibility_zone": payload["responsibility_zone"],
    }
    permission_id = bind.execute(
        sa.select(permissions_table.c.id).where(permissions_table.c.code == code)
    ).scalar()
    if permission_id is None:
        bind.execute(permissions_table.insert().values(code=code, **values))
    else:
        bind.execute(
            sa.update(permissions_table)
            .where(permissions_table.c.id == permission_id)
            .values(**values)
        )


def upgrade() -> None:
    op.create_table(
        "labor_summary_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("include_base_cost", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("include_accrual_cost", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("include_deduction_cost", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("accrual_adjustment_type_ids", sa.JSON(), nullable=True),
        sa.Column("deduction_adjustment_type_ids", sa.JSON(), nullable=True),
        sa.Column("revenue_real_money_only", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("revenue_exclude_deleted", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "revenue_amount_mode",
            sa.String(length=32),
            nullable=False,
            server_default="sum_without_discount",
        ),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", name="uq_labor_summary_settings_company"),
    )
    op.create_index(
        op.f("ix_labor_summary_settings_company_id"),
        "labor_summary_settings",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_labor_summary_settings_updated_by_id"),
        "labor_summary_settings",
        ["updated_by_id"],
        unique=False,
    )

    bind = op.get_bind()
    _upsert_permission(bind, PERMISSION_SETTINGS_MANAGE)


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        permissions_table.delete().where(permissions_table.c.code == PERMISSION_SETTINGS_MANAGE["code"])
    )

    op.drop_index(op.f("ix_labor_summary_settings_updated_by_id"), table_name="labor_summary_settings")
    op.drop_index(op.f("ix_labor_summary_settings_company_id"), table_name="labor_summary_settings")
    op.drop_table("labor_summary_settings")
