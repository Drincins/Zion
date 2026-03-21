"""Extend payment formats and add salary results table.

Revision ID: 6fb1c9986191
Revises: 3c9d5a27c2f1
Create Date: 2025-11-22 12:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import table, column


# revision identifiers, used by Alembic.
revision: str = "6fb1c9986191"
down_revision: Union[str, Sequence[str], None] = "3c9d5a27c2f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


payment_calc_enum = sa.Enum("hourly", "fixed", "shift_norm", name="payment_calculation_mode")


def upgrade() -> None:
    bind = op.get_bind()
    payment_calc_enum.create(bind, checkfirst=True)

    op.add_column("payment_formats", sa.Column("code", sa.String(), nullable=True))
    op.add_column("payment_formats", sa.Column("calculation_mode", payment_calc_enum, nullable=True))
    op.create_unique_constraint("uq_payment_formats_code", "payment_formats", ["code"])

    payment_formats = table(
        "payment_formats",
        column("id", sa.Integer()),
        column("name", sa.String()),
        column("code", sa.String()),
        column("calculation_mode", sa.String()),
    )

    rows = list(bind.execute(sa.select(payment_formats.c.id, payment_formats.c.name)))
    if rows:
        for row in rows:
            name = row.name or f"format_{row.id}"
            code = name.lower().replace(" ", "_")
            bind.execute(
                payment_formats.update()
                .where(payment_formats.c.id == row.id)
                .values(code=code, calculation_mode="hourly")
            )
    else:
        op.bulk_insert(
            payment_formats,
            [
                {
                    "name": "Почасовая оплата",
                    "code": "hourly",
                    "calculation_mode": "hourly",
                },
                {
                    "name": "Фиксированный оклад",
                    "code": "fixed",
                    "calculation_mode": "fixed",
                },
                {
                    "name": "Оклад за норму смен",
                    "code": "shift_norm",
                    "calculation_mode": "shift_norm",
                },
            ],
        )

    op.alter_column("payment_formats", "code", nullable=False)
    op.alter_column("payment_formats", "calculation_mode", nullable=False)

    op.add_column("positions", sa.Column("hours_per_shift", sa.Numeric(6, 2), nullable=True))
    op.add_column("positions", sa.Column("monthly_shift_norm", sa.Numeric(6, 2), nullable=True))

    op.create_table(
        "payroll_salary_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("base_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("adjustments_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("gross_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("calculated_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_unique_constraint(
        "uq_payroll_salary_result_user_period",
        "payroll_salary_results",
        ["user_id", "period_start", "period_end"],
    )
    op.create_index(
        "ix_payroll_salary_results_user_id",
        "payroll_salary_results",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_payroll_salary_results_calculated_by_id",
        "payroll_salary_results",
        ["calculated_by_id"],
        unique=False,
    )

    permissions_table = table(
        "permissions",
        column("code", sa.String()),
        column("name", sa.String()),
        column("description", sa.String()),
        column("display_name", sa.String()),
        column("responsibility_zone", sa.String()),
    )
    existing_permission_codes = {
        row.code for row in bind.execute(sa.select(permissions_table.c.code))
    }
    new_permissions = [
        {
            "code": "payroll.results.view",
            "name": "Просмотр итогов зарплаты",
            "display_name": "Просмотр итогов зарплаты",
            "description": "Доступ на чтение рассчитанных зарплатных ведомостей и деталей расчёта.",
            "responsibility_zone": "Финансы",
        },
        {
            "code": "payroll.results.manage",
            "name": "Пересчёт итогов зарплаты",
            "display_name": "Пересчёт итогов зарплаты",
            "description": "Пересчёт итоговых сумм по сотрудникам и обновление ведомостей.",
            "responsibility_zone": "Финансы",
        },
    ]
    rows_to_insert = [row for row in new_permissions if row["code"] not in existing_permission_codes]
    if rows_to_insert:
        op.bulk_insert(permissions_table, rows_to_insert)


def downgrade() -> None:
    op.execute(
        "DELETE FROM permissions WHERE code IN ('payroll.results.view', 'payroll.results.manage')"
    )

    op.drop_index("ix_payroll_salary_results_calculated_by_id", table_name="payroll_salary_results")
    op.drop_index("ix_payroll_salary_results_user_id", table_name="payroll_salary_results")
    op.drop_constraint("uq_payroll_salary_result_user_period", "payroll_salary_results", type_="unique")
    op.drop_table("payroll_salary_results")

    op.drop_column("positions", "monthly_shift_norm")
    op.drop_column("positions", "hours_per_shift")

    op.drop_constraint("uq_payment_formats_code", "payment_formats", type_="unique")
    op.drop_column("payment_formats", "calculation_mode")
    op.drop_column("payment_formats", "code")
    payment_calc_enum.drop(op.get_bind(), checkfirst=True)
