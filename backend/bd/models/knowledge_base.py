"""Knowledge base domain models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.bd.database import Base


KNOWLEDGE_BASE_DOCUMENT_TYPE = Enum("text", "file", name="knowledge_base_document_type")
KNOWLEDGE_BASE_AUDIT_ENTITY_TYPE = Enum(
    "folder",
    "document",
    "document_version",
    name="knowledge_base_audit_entity_type",
)
KNOWLEDGE_BASE_ACCESS_SCOPE_TYPE = Enum(
    "role",
    "position",
    "user",
    "restaurant",
    name="knowledge_base_access_scope_type",
)


class KnowledgeBaseFolder(Base):
    __tablename__ = "knowledge_base_folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("knowledge_base_folders.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    style_key: Mapped[str] = mapped_column(String(64), nullable=False, server_default="amber")
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    updated_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    parent: Mapped["KnowledgeBaseFolder | None"] = relationship(
        "KnowledgeBaseFolder",
        remote_side=[id],
        back_populates="children",
    )
    children: Mapped[list["KnowledgeBaseFolder"]] = relationship(
        "KnowledgeBaseFolder",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    documents: Mapped[list["KnowledgeBaseDocument"]] = relationship(
        "KnowledgeBaseDocument",
        back_populates="folder",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    access_rules: Mapped[list["KnowledgeBaseFolderAccessRule"]] = relationship(
        "KnowledgeBaseFolderAccessRule",
        back_populates="folder",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("parent_id", "name", name="uq_kb_folders_parent_name"),
        Index("ix_kb_folders_parent_updated", "parent_id", "updated_at"),
    )


class KnowledgeBaseDocument(Base):
    __tablename__ = "knowledge_base_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folder_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("knowledge_base_folders.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(KNOWLEDGE_BASE_DOCUMENT_TYPE, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extension: Mapped[str | None] = mapped_column(String(32), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    updated_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    folder: Mapped["KnowledgeBaseFolder | None"] = relationship(
        "KnowledgeBaseFolder",
        back_populates="documents",
    )
    versions: Mapped[list["KnowledgeBaseDocumentVersion"]] = relationship(
        "KnowledgeBaseDocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("folder_id", "name", name="uq_kb_documents_folder_name"),
        Index("ix_kb_documents_folder_updated", "folder_id", "updated_at"),
    )


class KnowledgeBaseDocumentVersion(Base):
    __tablename__ = "knowledge_base_document_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("knowledge_base_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    document_type: Mapped[str] = mapped_column(KNOWLEDGE_BASE_DOCUMENT_TYPE, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extension: Mapped[str | None] = mapped_column(String(32), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped["KnowledgeBaseDocument"] = relationship(
        "KnowledgeBaseDocument",
        back_populates="versions",
    )

    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_kb_document_version_number"),
        Index("ix_kb_document_versions_document_created", "document_id", "created_at"),
    )


class KnowledgeBaseAuditLog(Base):
    __tablename__ = "knowledge_base_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(KNOWLEDGE_BASE_AUDIT_ENTITY_TYPE, nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_kb_audit_entity_created", "entity_type", "entity_id", "created_at"),
    )


class KnowledgeBaseFolderAccessRule(Base):
    __tablename__ = "knowledge_base_folder_access_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folder_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("knowledge_base_folders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope_type: Mapped[str] = mapped_column(KNOWLEDGE_BASE_ACCESS_SCOPE_TYPE, nullable=False)
    scope_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    folder: Mapped["KnowledgeBaseFolder"] = relationship(
        "KnowledgeBaseFolder",
        back_populates="access_rules",
    )

    __table_args__ = (
        UniqueConstraint("folder_id", "scope_type", "scope_id", name="uq_kb_folder_access_rule"),
        Index("ix_kb_folder_access_scope", "scope_type", "scope_id"),
    )
