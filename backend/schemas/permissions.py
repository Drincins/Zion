"""Schemas for access control (permissions, roles, positions)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PermissionBase(BaseModel):
    code: str = Field(..., description="Unique permission identifier, e.g. 'system.admin'.")
    name: str = Field(..., description="Human readable name.")
    description: Optional[str] = Field(default=None, description="Detailed description for UI.")
    display_name: Optional[str] = Field(default=None, description="Localized display name (e.g. Russian).")
    responsibility_zone: Optional[str] = Field(
        default=None,
        description="High-level grouping (e.g. 'Сотрудники', 'Склад') to simplify navigation.",
    )


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    display_name: Optional[str] = None
    responsibility_zone: Optional[str] = None


class PermissionRead(PermissionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class RolePermissionsBase(BaseModel):
    name: str
    level: Optional[int] = None
    comment: Optional[str] = None


class RolePermissionsCreate(RolePermissionsBase):
    pass


class RolePermissionsUpdate(BaseModel):
    name: Optional[str] = None
    level: Optional[int] = None
    comment: Optional[str] = None


class RoleWithPermissions(BaseModel):
    id: int
    name: str
    level: int
    comment: Optional[str] = None


class PositionHierarchyCreate(BaseModel):
    name: str
    code: Optional[str] = None
    role_id: int
    parent_id: Optional[int] = None
    hierarchy_level: Optional[int] = None
    rate: Optional[Decimal] = None
    payment_format_id: Optional[int] = None
    hours_per_shift: Optional[Decimal] = None
    monthly_shift_norm: Optional[Decimal] = None
    restaurant_subdivision_id: Optional[int] = None
    night_bonus_enabled: bool = False
    night_bonus_percent: Optional[Decimal] = None


class PositionHierarchyUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    role_id: Optional[int] = None
    parent_id: Optional[int] = None
    hierarchy_level: Optional[int] = None
    rate: Optional[Decimal] = None
    payment_format_id: Optional[int] = None
    hours_per_shift: Optional[Decimal] = None
    monthly_shift_norm: Optional[Decimal] = None
    restaurant_subdivision_id: Optional[int] = None
    night_bonus_enabled: Optional[bool] = None
    night_bonus_percent: Optional[Decimal] = None


class PositionHierarchyNode(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    role_id: Optional[int]
    role_name: Optional[str] = None
    parent_id: Optional[int] = None
    hierarchy_level: int
    rate: Optional[Decimal] = None
    payment_format_id: Optional[int] = None
    payment_format_name: Optional[str] = None
    hours_per_shift: Optional[Decimal] = None
    monthly_shift_norm: Optional[Decimal] = None
    restaurant_subdivision_id: Optional[int] = None
    restaurant_subdivision_name: Optional[str] = None
    night_bonus_enabled: bool = False
    night_bonus_percent: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)


class PositionChangeOrderCreate(BaseModel):
    effective_date: date
    rate_new: Decimal
    comment: Optional[str] = None


class PositionChangeOrderPublic(BaseModel):
    id: int
    position_id: int
    position_name: Optional[str] = None
    effective_date: date
    status: str
    rate_new: Decimal
    comment: Optional[str] = None
    error_message: Optional[str] = None
    created_by_id: Optional[int] = None
    created_by_name: Optional[str] = None
    cancelled_by_id: Optional[int] = None
    cancelled_by_name: Optional[str] = None
    created_at: datetime
    applied_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PositionChangeOrderListResponse(BaseModel):
    items: List[PositionChangeOrderPublic] = Field(default_factory=list)


class PermissionRouteInfo(BaseModel):
    method: str
    path: str
    name: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    permission_codes: List[str] = Field(default_factory=list)
    include_in_schema: bool = True


class PermissionRouteListResponse(BaseModel):
    routes: List[PermissionRouteInfo] = Field(default_factory=list)


class PermissionCodeList(BaseModel):
    permission_codes: List[str] = Field(default_factory=list)


class PermissionCodeSingle(BaseModel):
    permission_code: str
