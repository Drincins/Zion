"""Schemas for staff portal and attendance."""
from __future__ import annotations

from datetime import date, datetime, time
from typing import List, Optional, Literal

from pydantic import BaseModel, ConfigDict, Field

PHONE_PATTERN = r"^\+7\d{10}$"

from backend.schemas.permissions import PositionHierarchyNode
from backend.schemas.core import RestaurantRead, CompanyRead, RoleRead
from backend.schemas.medical import MedicalCheckRecordPublic
from backend.schemas.cis_documents import CisDocumentRecordPublic


class StaffLoginRequest(BaseModel):
    staff_code: str
    auth_method: Optional[Literal["code", "fingerprint"]] = None
    fingerprint_score: Optional[int] = None
    fingerprint_slot: Optional[int] = Field(default=None, ge=1, le=3)


class StaffRestaurantPublic(BaseModel):
    id: int
    name: str
    department_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StaffUserPublic(BaseModel):
    id: int
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    iiko_id: Optional[str] = None
    iiko_code: Optional[str] = None
    staff_code: Optional[str] = None
    phone_number: Optional[str] = Field(default=None, pattern=PHONE_PATTERN)
    email: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    position_id: Optional[int] = None
    position_name: Optional[str] = None
    position_code: Optional[str] = None
    gender: Optional[Literal["male", "female"]] = None
    rate: Optional[float] = None
    position_rate: Optional[float] = None
    hire_date: Optional[date] = None
    fire_date: Optional[date] = None
    birth_date: Optional[date] = None
    photo_key: Optional[str] = None
    fired: bool
    is_cis_employee: bool = False
    restaurants: List[StaffRestaurantPublic] = Field(default_factory=list)
    restaurant_ids: List[int] = Field(default_factory=list)
    restaurant_department_codes: List[str] = Field(default_factory=list)
    workplace_restaurant_id: Optional[int] = None
    individual_rate: Optional[float] = None
    has_full_restaurant_access: bool = False
    confidential_data_consent: bool = False
    has_fingerprint: bool = False
    rate_hidden: bool = False
    is_formalized: bool = False
    restaurant_subdivision_id: Optional[int] = None
    restaurant_subdivision_name: Optional[str] = None
    restaurant_subdivision_is_multi: bool = False

    model_config = ConfigDict(from_attributes=True)


class StaffUserListPublic(BaseModel):
    id: int
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    iiko_id: Optional[str] = None
    iiko_code: Optional[str] = None
    staff_code: Optional[str] = None
    phone_number: Optional[str] = Field(default=None, pattern=PHONE_PATTERN)
    company_name: Optional[str] = None
    role_id: Optional[int] = None
    position_id: Optional[int] = None
    position_name: Optional[str] = None
    position_code: Optional[str] = None
    position_rate: Optional[float] = None
    gender: Optional[Literal["male", "female"]] = None
    hire_date: Optional[date] = None
    fire_date: Optional[date] = None
    birth_date: Optional[date] = None
    fired: bool
    is_cis_employee: bool = False
    is_formalized: bool = False
    restaurants: List[StaffRestaurantPublic] = Field(default_factory=list)
    restaurant_ids: List[int] = Field(default_factory=list)
    workplace_restaurant_id: Optional[int] = None
    rate_hidden: bool = False

    model_config = ConfigDict(from_attributes=True)


class StaffLoginResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: str = "bearer"
    user: StaffUserPublic


class StaffEmployeeListResponse(BaseModel):
    items: List[StaffUserPublic]
    offset: int = 0
    limit: int = 0
    has_more: bool = False
    next_offset: Optional[int] = None


class StaffEmployeeListCompactResponse(BaseModel):
    items: List[StaffUserListPublic]
    offset: int = 0
    limit: int = 0
    has_more: bool = False
    next_offset: Optional[int] = None


class StaffEmployeesReferencePayload(BaseModel):
    restaurants: List[RestaurantRead] = Field(default_factory=list)
    companies: List[CompanyRead] = Field(default_factory=list)
    roles: List[RoleRead] = Field(default_factory=list)
    positions: List[PositionHierarchyNode] = Field(default_factory=list)


class StaffEmployeesBootstrapResponse(BaseModel):
    items: List[StaffUserPublic] = Field(default_factory=list)
    references: StaffEmployeesReferencePayload = Field(default_factory=StaffEmployeesReferencePayload)
    offset: int = 0
    limit: int = 0
    has_more: bool = False
    next_offset: Optional[int] = None


class AttendancePublic(BaseModel):
    id: int
    user_id: int
    position_id: Optional[int] = None
    position_name: Optional[str] = None
    restaurant_id: Optional[int] = None
    restaurant_name: Optional[str] = None
    rate: Optional[float] = None
    pay_amount: Optional[float] = None
    open_date: date
    open_time: time
    close_date: Optional[date] = None
    close_time: Optional[time] = None
    duration_minutes: Optional[int] = None
    night_minutes: int


class StaffEmployeeDetailResponse(BaseModel):
    user: StaffUserPublic
    attendances: List[AttendancePublic]
    date_from: date
    date_to: date


class AttendanceListResponse(BaseModel):
    items: List[AttendancePublic]
    year: int
    month: int


class AttendanceOpenRequest(BaseModel):
    restaurant_id: Optional[int] = None
    position_id: Optional[int] = None


class AttendanceCloseRequest(BaseModel):
    close_date: Optional[date] = None
    close_time: Optional[time] = None


class StaffPositionOption(BaseModel):
    id: int
    name: str
    restaurant_subdivision_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class AttendanceManualCreate(BaseModel):
    open_date: date
    open_time: time
    close_date: Optional[date] = None
    close_time: Optional[time] = None
    restaurant_id: Optional[int] = None
    position_id: Optional[int] = None
    rate: Optional[float] = None

    
class AttendanceManualUpdate(BaseModel):
    open_date: Optional[date] = None
    open_time: Optional[time] = None
    close_date: Optional[date] = None
    close_time: Optional[time] = None
    restaurant_id: Optional[int] = None
    position_id: Optional[int] = None
    rate: Optional[float] = None


class AttendanceRecalculateNightRequest(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class EmployeeListItem(BaseModel):
    id: int
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    staff_code: Optional[str] = None
    gender: Optional[Literal["male", "female"]] = None
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    position_id: Optional[int] = None
    position_name: Optional[str] = None
    position_rate: Optional[float] = None
    fired: bool
    middle_name: Optional[str] = None
    phone_number: Optional[str] = Field(default=None, pattern=PHONE_PATTERN)
    confidential_data_consent: bool = False
    is_formalized: bool = False


class EmployeeListResponse(BaseModel):
    items: List[EmployeeListItem]


class EmployeeCardPublic(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    iiko_code: Optional[str] = None
    iiko_id: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    position_id: Optional[int] = None
    position_name: Optional[str] = None
    rate: Optional[float] = None
    hire_date: Optional[date] = None
    fire_date: Optional[date] = None
    fired: bool
    staff_code: Optional[str] = None
    gender: Optional[Literal["male", "female"]] = None
    phone_number: Optional[str] = Field(default=None, pattern=PHONE_PATTERN)
    email: Optional[str] = None
    birth_date: Optional[date] = None
    photo_key: Optional[str] = None
    photo_url: Optional[str] = None
    is_cis_employee: bool = False
    confidential_data_consent: bool = False
    workplace_restaurant_id: Optional[int] = None
    individual_rate: Optional[float] = None
    has_fingerprint: bool = False
    medical_checks: List[MedicalCheckRecordPublic] = Field(default_factory=list)
    cis_documents: List[CisDocumentRecordPublic] = Field(default_factory=list)
    iiko_sync_error: Optional[str] = None
    rate_hidden: bool = False
    is_formalized: bool = False


class IikoSyncEmployeeSnapshot(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    position_name: Optional[str] = None
    position_code: Optional[str] = None
    staff_code: Optional[str] = None
    iiko_code: Optional[str] = None
    iiko_id: Optional[str] = None
    workplace_restaurant_id: Optional[int] = None
    workplace_restaurant_name: Optional[str] = None
    department_code: Optional[str] = None
    restaurant_ids: List[int] = Field(default_factory=list)
    restaurant_names: List[str] = Field(default_factory=list)
    department_codes: List[str] = Field(default_factory=list)


class EmployeeIikoSyncPreviewResponse(BaseModel):
    local: IikoSyncEmployeeSnapshot
    iiko: Optional[IikoSyncEmployeeSnapshot] = None
    iiko_error: Optional[str] = None


class EmployeeUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    gender: Optional[Literal["male", "female"]] = None
    staff_code: Optional[str] = None
    iiko_code: Optional[str] = None
    iiko_id: Optional[str] = None
    phone_number: Optional[str] = Field(default=None, pattern=PHONE_PATTERN)
    email: Optional[str] = None
    position_id: Optional[int] = None
    role_id: Optional[int] = None
    company_id: Optional[int] = None
    workplace_restaurant_id: Optional[int] = None
    restaurant_ids: Optional[List[int]] = None
    clear_restaurants: Optional[bool] = None
    rate: Optional[float] = None
    individual_rate: Optional[float] = None
    hire_date: Optional[date] = None
    fire_date: Optional[date] = None
    fired: Optional[bool] = None
    birth_date: Optional[date] = None
    is_cis_employee: Optional[bool] = None
    password: Optional[str] = None
    photo_key: Optional[str] = None
    confidential_data_consent: Optional[bool] = None
    is_formalized: Optional[bool] = None
    update_attendances: Optional[bool] = None
    attendance_date_from: Optional[date] = None
    attendance_date_to: Optional[date] = None
    add_to_iiko: Optional[bool] = None
    iiko_sync_restaurant_id: Optional[int] = None
    iiko_department_restaurant_ids: Optional[List[int]] = None


class EmployeeChangeOrderCreate(BaseModel):
    effective_date: date
    change_position: bool = False
    position_id_new: Optional[int] = None
    change_workplace_restaurant: bool = False
    workplace_restaurant_id_new: Optional[int] = None
    change_rate: bool = False
    rate_new: Optional[float] = None
    change_individual_rate: bool = False
    individual_rate_new: Optional[float] = None
    apply_to_attendances: bool = False
    comment: Optional[str] = None


class EmployeeChangeOrderPublic(BaseModel):
    id: int
    user_id: int
    effective_date: date
    status: str
    change_position: bool = False
    position_id_new: Optional[int] = None
    position_name_new: Optional[str] = None
    change_workplace_restaurant: bool = False
    workplace_restaurant_id_new: Optional[int] = None
    workplace_restaurant_name_new: Optional[str] = None
    change_rate: bool = False
    rate_new: Optional[float] = None
    change_individual_rate: bool = False
    individual_rate_new: Optional[float] = None
    apply_to_attendances: bool = False
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


class EmployeeChangeOrderListResponse(BaseModel):
    items: List[EmployeeChangeOrderPublic] = Field(default_factory=list)


class PhotoUploadResponse(BaseModel):
    photo_key: str
    photo_url: str


class AttendanceRangeResponse(BaseModel):
    items: List[AttendancePublic]
    date_from: date
    date_to: date


class TimesheetRestaurantOption(BaseModel):
    id: int
    name: str


class TimesheetSubdivisionOption(BaseModel):
    id: int
    name: str


class TimesheetPositionOption(BaseModel):
    id: int
    name: str
    restaurant_subdivision_id: Optional[int] = None


class TimesheetOptionsResponse(BaseModel):
    restaurants: List[TimesheetRestaurantOption]
    subdivisions: List[TimesheetSubdivisionOption]
    positions: List[TimesheetPositionOption]
