"""Schemas for CIS document dictionary and records."""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.bd.models import CisDocumentStatus


class CisDocumentTypeBase(BaseModel):
    code: Optional[str] = None
    name: str
    validity_months: Optional[int] = None
    notice_days: Optional[int] = None
    comment: Optional[str] = None


class CisDocumentTypeCreate(CisDocumentTypeBase):
    pass


class CisDocumentTypeUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    validity_months: Optional[int] = None
    notice_days: Optional[int] = None
    comment: Optional[str] = None
    is_active: Optional[bool] = None


class CisDocumentTypeRead(CisDocumentTypeBase):
    id: int
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class CisDocumentRecordBase(BaseModel):
    cis_document_type_id: int
    number: Optional[str] = None
    issued_at: Optional[date] = None
    expires_at: Optional[date] = None
    issuer: Optional[str] = None
    comment: Optional[str] = None
    attachment_url: Optional[str] = None


class CisDocumentRecordCreate(CisDocumentRecordBase):
    user_id: int


class CisDocumentRecordUpdate(BaseModel):
    cis_document_type_id: Optional[int] = None
    number: Optional[str] = None
    issued_at: Optional[date] = None
    expires_at: Optional[date] = None
    issuer: Optional[str] = None
    comment: Optional[str] = None
    attachment_url: Optional[str] = None


class CisDocumentRecordPublic(BaseModel):
    id: int
    user_id: int
    # Accepts ORM attribute `document_type` but keeps public field name `cis_document_type`.
    cis_document_type: CisDocumentTypeRead = Field(validation_alias="document_type")
    number: Optional[str] = None
    issued_at: Optional[date] = None
    expires_at: Optional[date] = None
    status: CisDocumentStatus
    issuer: Optional[str] = None
    comment: Optional[str] = None
    attachment_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CisDocumentRecordListResponse(BaseModel):
    items: List[CisDocumentRecordPublic]
