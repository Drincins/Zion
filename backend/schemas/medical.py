"""Schemas for medical check dictionaries and records."""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.bd.models import MedicalCheckStatus


class MedicalCheckTypeBase(BaseModel):
    code: Optional[str] = None
    name: str
    validity_months: Optional[int] = None
    notice_days: Optional[int] = None
    comment: Optional[str] = None


class MedicalCheckTypeCreate(MedicalCheckTypeBase):
    pass


class MedicalCheckTypeUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    validity_months: Optional[int] = None
    notice_days: Optional[int] = None
    comment: Optional[str] = None
    is_active: Optional[bool] = None


class MedicalCheckTypeRead(MedicalCheckTypeBase):
    id: int
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class MedicalCheckRecordBase(BaseModel):
    medical_check_type_id: int
    passed_at: date
    comment: Optional[str] = None


class MedicalCheckRecordCreate(MedicalCheckRecordBase):
    user_id: int


class MedicalCheckRecordUpdate(BaseModel):
    medical_check_type_id: Optional[int] = None
    passed_at: Optional[date] = None
    comment: Optional[str] = None


class MedicalCheckRecordPublic(BaseModel):
    id: int
    user_id: int
    # Accepts ORM attribute `check_type` but keeps public field name `medical_check_type`.
    medical_check_type: MedicalCheckTypeRead = Field(validation_alias="check_type")
    passed_at: date
    next_due_at: Optional[date] = None
    status: MedicalCheckStatus
    comment: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MedicalCheckRecordListResponse(BaseModel):
    items: List[MedicalCheckRecordPublic]
