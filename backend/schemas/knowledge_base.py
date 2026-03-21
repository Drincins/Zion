"""Schemas for the knowledge base module."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


KnowledgeBaseDocumentType = Literal["text", "file"]
KnowledgeBaseItemType = Literal["folder", "document"]
KnowledgeBasePreviewType = Literal["text", "pdf", "spreadsheet", "file"]
KnowledgeBaseAuditEntityType = Literal["folder", "document", "document_version"]
KnowledgeBaseAccessScopeType = Literal["role", "position", "user", "restaurant"]


class KnowledgeBaseFolderStyle(BaseModel):
    key: str
    label: str
    accent: str


class KnowledgeBaseBootstrapResponse(BaseModel):
    folder_styles: list[KnowledgeBaseFolderStyle]
    can_view: bool
    can_manage: bool
    can_upload: bool


class KnowledgeBaseBreadcrumbItem(BaseModel):
    id: int | None = None
    name: str


class KnowledgeBaseFolderRead(BaseModel):
    id: int
    parent_id: int | None = None
    name: str
    style_key: str
    created_by_user_id: int | None = None
    created_by_name: str | None = None
    updated_by_user_id: int | None = None
    updated_by_name: str | None = None
    created_at: datetime
    updated_at: datetime
    children_count: int = 0
    documents_count: int = 0
    access: KnowledgeBaseFolderAccessSelection | None = None

    model_config = ConfigDict(from_attributes=True)


class KnowledgeBaseFolderTreeNode(BaseModel):
    id: int
    item_type: KnowledgeBaseItemType = "folder"
    parent_id: int | None = None
    name: str
    has_documents: bool = False
    style_key: str | None = None
    document_type: KnowledgeBaseDocumentType | None = None
    mime_type: str | None = None
    extension: str | None = None
    file_size: int | None = None
    preview_type: KnowledgeBasePreviewType | None = None
    children: list["KnowledgeBaseFolderTreeNode"] = Field(default_factory=list)


class KnowledgeBaseItemRead(BaseModel):
    id: int
    item_type: KnowledgeBaseItemType
    name: str
    parent_id: int | None = None
    style_key: str | None = None
    document_type: KnowledgeBaseDocumentType | None = None
    mime_type: str | None = None
    extension: str | None = None
    file_size: int | None = None
    preview_type: KnowledgeBasePreviewType | None = None
    created_by_user_id: int | None = None
    created_by_name: str | None = None
    updated_by_user_id: int | None = None
    updated_by_name: str | None = None
    created_at: datetime
    updated_at: datetime


class KnowledgeBaseListResponse(BaseModel):
    folder_id: int | None = None
    breadcrumbs: list[KnowledgeBaseBreadcrumbItem]
    items: list[KnowledgeBaseItemRead]
    total: int
    offset: int = 0
    limit: int = 0
    has_more: bool = False
    next_offset: int | None = None


class KnowledgeBaseFolderCreate(BaseModel):
    parent_id: int | None = None
    name: str
    style_key: str | None = None
    access: KnowledgeBaseFolderAccessSelection | None = None


class KnowledgeBaseFolderUpdate(BaseModel):
    parent_id: int | None = None
    name: str | None = None
    style_key: str | None = None


class KnowledgeBaseTextDocumentCreate(BaseModel):
    folder_id: int | None = None
    name: str
    content: str | None = ""


class KnowledgeBaseDocumentUpdate(BaseModel):
    folder_id: int | None = None
    name: str | None = None


class KnowledgeBaseDocumentContentUpdate(BaseModel):
    content: str
    comment: str | None = None


class KnowledgeBaseDocumentRead(BaseModel):
    id: int
    folder_id: int | None = None
    name: str
    document_type: KnowledgeBaseDocumentType
    mime_type: str | None = None
    extension: str | None = None
    file_size: int | None = None
    storage_key: str | None = None
    content_text: str | None = None
    preview_type: KnowledgeBasePreviewType
    download_url: str | None = None
    latest_version_number: int | None = None
    created_by_user_id: int | None = None
    created_by_name: str | None = None
    updated_by_user_id: int | None = None
    updated_by_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeBaseDownloadResponse(BaseModel):
    download_url: str


class KnowledgeBaseAuditLogRead(BaseModel):
    id: int
    entity_type: KnowledgeBaseAuditEntityType
    entity_id: int
    action: str
    payload: dict | None = None
    created_by_user_id: int | None = None
    created_by_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeBaseDocumentVersionRead(BaseModel):
    id: int
    document_id: int
    version_number: int
    document_type: KnowledgeBaseDocumentType
    name: str
    mime_type: str | None = None
    extension: str | None = None
    file_size: int | None = None
    storage_key: str | None = None
    content_text: str | None = None
    comment: str | None = None
    created_by_user_id: int | None = None
    created_by_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeBaseDocumentHistoryResponse(BaseModel):
    audit_logs: list[KnowledgeBaseAuditLogRead]
    versions: list[KnowledgeBaseDocumentVersionRead]


class KnowledgeBaseAccessOption(BaseModel):
    id: int
    name: str


class KnowledgeBaseAccessOptionsResponse(BaseModel):
    roles: list[KnowledgeBaseAccessOption] = Field(default_factory=list)
    positions: list[KnowledgeBaseAccessOption] = Field(default_factory=list)
    users: list[KnowledgeBaseAccessOption] = Field(default_factory=list)
    restaurants: list[KnowledgeBaseAccessOption] = Field(default_factory=list)


class KnowledgeBaseFolderAccessSelection(BaseModel):
    role_ids: list[int] = Field(default_factory=list)
    position_ids: list[int] = Field(default_factory=list)
    user_ids: list[int] = Field(default_factory=list)
    restaurant_ids: list[int] = Field(default_factory=list)


class KnowledgeBaseFolderAccessRead(KnowledgeBaseFolderAccessSelection):
    folder_id: int


KnowledgeBaseFolderRead.model_rebuild()
KnowledgeBaseFolderCreate.model_rebuild()
KnowledgeBaseFolderTreeNode.model_rebuild()
