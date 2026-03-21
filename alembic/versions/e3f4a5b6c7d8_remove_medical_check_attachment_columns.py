"""Remove medical check attachment fields.

Revision ID: e3f4a5b6c7d8
Revises: d0e1f2a3b4c6
Create Date: 2026-01-04 20:30:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a3b4c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("medical_check_records") as batch_op:
        batch_op.drop_column("issuer")
        batch_op.drop_column("attachment_url")


def downgrade() -> None:
    with op.batch_alter_table("medical_check_records") as batch_op:
        batch_op.add_column(sa.Column("issuer", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("attachment_url", sa.Text(), nullable=True))
