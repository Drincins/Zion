"""Core schemas: company, restaurant, role, user."""
from __future__ import annotations

from datetime import date
from typing import List, Optional, Literal

from pydantic import BaseModel, ConfigDict, Field


class RestaurantBase(BaseModel):
    name: str
    server: str
    department_code: Optional[str] = None
    participates_in_sales: bool = True


class RestaurantCreate(RestaurantBase):
    iiko_login: str
    iiko_password: str


class RestaurantRead(RestaurantBase):
    id: int
    iiko_login: Optional[str] = None
    company_id: int

    model_config = ConfigDict(from_attributes=True)


class CompanyBase(BaseModel):
    name: str


class CompanyCreate(CompanyBase):
    pass


class CompanyRead(CompanyBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class RoleBase(BaseModel):
    name: str
    comment: Optional[str] = None


class RoleCreate(RoleBase):
    level: Optional[int] = None


class RoleRead(RoleBase):
    id: int
    level: int

    model_config = ConfigDict(from_attributes=True)


class PaymentFormatRead(BaseModel):
    id: int
    name: str
    code: str
    calculation_mode: str

    model_config = ConfigDict(from_attributes=True)


class RestaurantSubdivisionRead(BaseModel):
    id: int
    name: str
    is_multi: bool = False

    model_config = ConfigDict(from_attributes=True)


class RestaurantSubdivisionCreate(BaseModel):
    name: str
    is_multi: bool = False


class RestaurantSubdivisionUpdate(BaseModel):
    name: Optional[str] = None
    is_multi: Optional[bool] = None


class PositionRead(BaseModel):
    id: int
    name: str
    permission_codes: List[str] = Field(default_factory=list)
    rate: Optional[float] = None
    payment_format_id: Optional[int] = None
    payment_format: Optional[PaymentFormatRead] = None
    hours_per_shift: Optional[float] = None
    monthly_shift_norm: Optional[float] = None
    restaurant_subdivision_id: Optional[int] = None
    restaurant_subdivision: Optional[RestaurantSubdivisionRead] = None

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    iiko_code: Optional[str] = None
    gender: Optional[Literal["male", "female"]] = None
    is_cis_employee: bool = False
    is_formalized: bool = False


class UserCreate(UserBase):
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    middle_name: Optional[str] = None
    birth_date: date
    password: Optional[str] = None
    staff_code: Optional[str] = None
    phone_number: Optional[str] = None
    hire_date: Optional[date] = None
    fire_date: Optional[date] = None
    fired: Optional[bool] = None
    photo_key: Optional[str] = None
    confidential_data_consent: Optional[bool] = None
    rate: Optional[float] = None
    role_id: Optional[int] = None
    company_id: Optional[int] = None
    position_id: Optional[int] = None
    workplace_restaurant_id: Optional[int] = None
    individual_rate: Optional[float] = None
    restaurant_ids: List[int] = Field(default_factory=list)
    has_full_restaurant_access: bool = False
    add_to_iiko: bool = False
    iiko_sync_restaurant_id: Optional[int] = None
    iiko_department_restaurant_ids: Optional[List[int]] = None


class UserUpdate(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    iiko_code: Optional[str] = None
    gender: Optional[Literal["male", "female"]] = None
    password: Optional[str] = None
    role_id: Optional[int] = None
    company_id: Optional[int] = None
    position_id: Optional[int] = None
    workplace_restaurant_id: Optional[int] = None
    individual_rate: Optional[float] = None
    restaurant_ids: Optional[List[int]] = None
    clear_restaurants: Optional[bool] = None
    has_full_restaurant_access: Optional[bool] = None
    is_cis_employee: Optional[bool] = None
    is_formalized: Optional[bool] = None
    fired: Optional[bool] = None


class UserRead(UserBase):
    id: int
    company_id: Optional[int]
    company: Optional["CompanyRead"] = None
    role: Optional["RoleRead"] = None
    position: Optional["PositionRead"] = None
    workplace_restaurant_id: Optional[int] = None
    individual_rate: Optional[float] = None
    restaurants: List["RestaurantRead"] = Field(default_factory=list)
    has_full_restaurant_access: bool = False
    has_global_access: bool = False
    permission_codes: List[str] = Field(default_factory=list)
    iiko_sync_error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
