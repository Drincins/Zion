"""Add statement kind to payroll advance statements.

Revision ID: b3c4d5e6f7b8
Revises: a7d8e9f0b1c2
Create Date: 2026-03-05 22:40:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7b8"
down_revision: Union[str, Sequence[str], None] = "a7d8e9f0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PAYROLL_STATEMENT_KIND = sa.Enum("advance", "salary", name="payroll_statement_kind")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("payroll_advance_statements")}

    PAYROLL_STATEMENT_KIND.create(bind, checkfirst=True)

    if "statement_kind" not in columns:
        op.add_column(
            "payroll_advance_statements",
            sa.Column(
                "statement_kind",
                PAYROLL_STATEMENT_KIND,
                nullable=False,
                server_default="advance",
            ),
        )
        op.execute(
            "UPDATE payroll_advance_statements SET statement_kind = 'advance' WHERE statement_kind IS NULL"
        )
        op.alter_column("payroll_advance_statements", "statement_kind", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("payroll_advance_statements")}

    if "statement_kind" in columns:
        op.drop_column("payroll_advance_statements", "statement_kind")

    PAYROLL_STATEMENT_KIND.drop(bind, checkfirst=True)
