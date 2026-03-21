"""Add folder access rules for knowledge base.

Revision ID: 9f1a2b3c4d5e
Revises: f3e4d5c6b7a8
Create Date: 2026-03-17 13:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f1a2b3c4d5e"
down_revision: Union[str, Sequence[str], None] = "f3e4d5c6b7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_base_folder_access_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("folder_id", sa.Integer(), nullable=False),
        sa.Column(
            "scope_type",
            sa.Enum("role", "position", "user", "restaurant", name="knowledge_base_access_scope_type"),
            nullable=False,
        ),
        sa.Column("scope_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["folder_id"], ["knowledge_base_folders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("folder_id", "scope_type", "scope_id", name="uq_kb_folder_access_rule"),
    )
    op.create_index(
        op.f("ix_knowledge_base_folder_access_rules_folder_id"),
        "knowledge_base_folder_access_rules",
        ["folder_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_base_folder_access_rules_scope_id"),
        "knowledge_base_folder_access_rules",
        ["scope_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_base_folder_access_rules_created_by_user_id"),
        "knowledge_base_folder_access_rules",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_kb_folder_access_scope",
        "knowledge_base_folder_access_rules",
        ["scope_type", "scope_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_kb_folder_access_scope", table_name="knowledge_base_folder_access_rules")
    op.drop_index(
        op.f("ix_knowledge_base_folder_access_rules_created_by_user_id"),
        table_name="knowledge_base_folder_access_rules",
    )
    op.drop_index(op.f("ix_knowledge_base_folder_access_rules_scope_id"), table_name="knowledge_base_folder_access_rules")
    op.drop_index(op.f("ix_knowledge_base_folder_access_rules_folder_id"), table_name="knowledge_base_folder_access_rules")
    op.drop_table("knowledge_base_folder_access_rules")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS knowledge_base_access_scope_type")
