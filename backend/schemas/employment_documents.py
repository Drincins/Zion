"""Schemas for formalized employee documents."""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from backend.bd.models import EmploymentDocumentKind


class EmploymentDocumentRecordBase(BaseModel):
    document_kind: EmploymentDocumentKind
    issued_at: Optional[date] = None
    comment: Optional[str] = None
    attachment_url: Optional[str] = None


class EmploymentDocumentRecordCreate(EmploymentDocumentRecordBase):
    user_id: int


class EmploymentDocumentRecordUpdate(BaseModel):
    issued_at: Optional[date] = None
    comment: Optional[str] = None
    attachment_url: Optional[str] = None


class EmploymentDocumentRecordPublic(BaseModel):
    id: int
    user_id: int
    document_kind: EmploymentDocumentKind
    document_name: str
    issued_at: Optional[date] = None
    comment: Optional[str] = None
    attachment_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EmploymentDocumentRecordListResponse(BaseModel):
    items: List[EmploymentDocumentRecordPublic]
