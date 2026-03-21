"""Add knowledge base module tables and permissions.

Revision ID: f3e4d5c6b7a8
Revises: a4b5c6d7e8f9
Create Date: 2026-03-14 18:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3e4d5c6b7a8"
down_revision: Union[str, Sequence[str], None] = "a4b5c6d7e8f9"
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

KNOWLEDGE_BASE_PERMISSIONS = [
    {
        "code": "knowledge_base.view",
        "name": "Knowledge base: view",
        "display_name": "Knowledge base: view",
        "description": "Read access to folders and documents in the knowledge base module.",
        "responsibility_zone": "Knowledge base",
    },
    {
        "code": "knowledge_base.manage",
        "name": "Knowledge base: manage",
        "display_name": "Knowledge base: manage",
        "description": "Create, edit, move and delete folders/documents in the knowledge base module.",
        "responsibility_zone": "Knowledge base",
    },
    {
        "code": "knowledge_base.upload",
        "name": "Knowledge base: upload files",
        "display_name": "Knowledge base: upload files",
        "description": "Upload file attachments to the knowledge base module.",
        "responsibility_zone": "Knowledge base",
    },
]


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
        "knowledge_base_folders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("style_key", sa.String(length=64), nullable=False, server_default="amber"),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_id"], ["knowledge_base_folders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_id", "name", name="uq_kb_folders_parent_name"),
    )
    op.create_index(op.f("ix_knowledge_base_folders_parent_id"), "knowledge_base_folders", ["parent_id"], unique=False)
    op.create_index(
        op.f("ix_knowledge_base_folders_created_by_user_id"),
        "knowledge_base_folders",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_base_folders_updated_by_user_id"),
        "knowledge_base_folders",
        ["updated_by_user_id"],
        unique=False,
    )
    op.create_index("ix_kb_folders_parent_updated", "knowledge_base_folders", ["parent_id", "updated_at"], unique=False)

    op.create_table(
        "knowledge_base_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("folder_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "document_type",
            sa.Enum("text", "file", name="knowledge_base_document_type"),
            nullable=False,
        ),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("extension", sa.String(length=32), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["folder_id"], ["knowledge_base_folders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("folder_id", "name", name="uq_kb_documents_folder_name"),
    )
    op.create_index(op.f("ix_knowledge_base_documents_folder_id"), "knowledge_base_documents", ["folder_id"], unique=False)
    op.create_index(
        op.f("ix_knowledge_base_documents_created_by_user_id"),
        "knowledge_base_documents",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_base_documents_updated_by_user_id"),
        "knowledge_base_documents",
        ["updated_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_kb_documents_folder_updated",
        "knowledge_base_documents",
        ["folder_id", "updated_at"],
        unique=False,
    )

    op.create_table(
        "knowledge_base_document_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "document_type",
            sa.Enum("text", "file", name="knowledge_base_document_type"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("extension", sa.String(length=32), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_base_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "version_number", name="uq_kb_document_version_number"),
    )
    op.create_index(
        op.f("ix_knowledge_base_document_versions_document_id"),
        "knowledge_base_document_versions",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_base_document_versions_created_by_user_id"),
        "knowledge_base_document_versions",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_kb_document_versions_document_created",
        "knowledge_base_document_versions",
        ["document_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "knowledge_base_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "entity_type",
            sa.Enum("folder", "document", "document_version", name="knowledge_base_audit_entity_type"),
            nullable=False,
        ),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_knowledge_base_audit_logs_created_by_user_id"),
        "knowledge_base_audit_logs",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_kb_audit_entity_created",
        "knowledge_base_audit_logs",
        ["entity_type", "entity_id", "created_at"],
        unique=False,
    )

    bind = op.get_bind()
    for payload in KNOWLEDGE_BASE_PERMISSIONS:
        _upsert_permission(bind, payload)


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        permissions_table.delete().where(
            permissions_table.c.code.in_([item["code"] for item in KNOWLEDGE_BASE_PERMISSIONS])
        )
    )

    op.drop_index("ix_kb_audit_entity_created", table_name="knowledge_base_audit_logs")
    op.drop_index(op.f("ix_knowledge_base_audit_logs_created_by_user_id"), table_name="knowledge_base_audit_logs")
    op.drop_table("knowledge_base_audit_logs")

    op.drop_index("ix_kb_document_versions_document_created", table_name="knowledge_base_document_versions")
    op.drop_index(
        op.f("ix_knowledge_base_document_versions_created_by_user_id"),
        table_name="knowledge_base_document_versions",
    )
    op.drop_index(op.f("ix_knowledge_base_document_versions_document_id"), table_name="knowledge_base_document_versions")
    op.drop_table("knowledge_base_document_versions")

    op.drop_index("ix_kb_documents_folder_updated", table_name="knowledge_base_documents")
    op.drop_index(op.f("ix_knowledge_base_documents_updated_by_user_id"), table_name="knowledge_base_documents")
    op.drop_index(op.f("ix_knowledge_base_documents_created_by_user_id"), table_name="knowledge_base_documents")
    op.drop_index(op.f("ix_knowledge_base_documents_folder_id"), table_name="knowledge_base_documents")
    op.drop_table("knowledge_base_documents")

    op.drop_index("ix_kb_folders_parent_updated", table_name="knowledge_base_folders")
    op.drop_index(op.f("ix_knowledge_base_folders_updated_by_user_id"), table_name="knowledge_base_folders")
    op.drop_index(op.f("ix_knowledge_base_folders_created_by_user_id"), table_name="knowledge_base_folders")
    op.drop_index(op.f("ix_knowledge_base_folders_parent_id"), table_name="knowledge_base_folders")
    op.drop_table("knowledge_base_folders")

    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS knowledge_base_audit_entity_type")
        op.execute("DROP TYPE IF EXISTS knowledge_base_document_type")
