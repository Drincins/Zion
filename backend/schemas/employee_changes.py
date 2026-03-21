"""Schemas for employee change history."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Any

from pydantic import BaseModel, ConfigDict


class EmployeeChangeEventRead(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    changed_by_id: Optional[int] = None
    changed_by_name: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    field: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    old_value_json: Optional[Any] = None
    new_value_json: Optional[Any] = None
    source: Optional[str] = None
    comment: Optional[str] = None
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    restaurant_id: Optional[int] = None
    position_id: Optional[int] = None
    role_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmployeeChangeEventUpdate(BaseModel):
    field: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    source: Optional[str] = None
    comment: Optional[str] = None


class EmployeeChangeEventListResponse(BaseModel):
    items: List[EmployeeChangeEventRead]
