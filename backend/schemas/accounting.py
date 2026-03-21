"""Schemas for accounting invoices."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


ACCOUNTING_STATUSES = [
    "Отправлен в бухгалтерию",
    "Отправлен в оплату",
    "Оплачен",
    "Требуются закрывающие документы",
    "Счет закрыт",
]


class AccountingInvoiceBase(BaseModel):
    from_restaurant_id: int
    for_restaurant_id: int
    amount: Decimal
    payee: str
    purpose: str
    invoice_date: Optional[date] = None
    sent_at: Optional[date] = None
    comment: Optional[str] = None
    status: Optional[str] = None
    payment_order_file_key: Optional[str] = None
    include_in_expenses: bool = False
    closing_received_edo: bool = False


class AccountingInvoiceCreate(AccountingInvoiceBase):
    invoice_file_key: str
    status: Optional[str] = Field(default="Отправлен в бухгалтерию")


class AccountingInvoiceUpdate(BaseModel):
    from_restaurant_id: Optional[int] = None
    for_restaurant_id: Optional[int] = None
    amount: Optional[Decimal] = None
    payee: Optional[str] = None
    purpose: Optional[str] = None
    invoice_date: Optional[date] = None
    sent_at: Optional[date] = None
    comment: Optional[str] = None
    include_in_expenses: Optional[bool] = None
    closing_received_edo: Optional[bool] = None
    invoice_file_key: Optional[str] = None
    payment_order_file_key: Optional[str] = None


class AccountingInvoiceStatusUpdate(BaseModel):
    status: str


class AccountingInvoiceClosingDocumentRead(BaseModel):
    id: int
    invoice_id: int
    file_key: str
    file_url: Optional[str] = None
    uploaded_by_user_id: Optional[int] = None
    uploaded_at: datetime
    original_filename: Optional[str] = None
    content_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AccountingInvoiceChangeRead(BaseModel):
    id: int
    invoice_id: int
    field: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by_user_id: Optional[int] = None
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountingInvoiceEventRead(BaseModel):
    id: int
    invoice_id: int
    event_type: str
    message: Optional[str] = None
    actor_user_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountingInvoiceRead(AccountingInvoiceBase):
    id: int
    created_at: datetime
    updated_at: datetime
    created_by_user_id: Optional[int] = None
    invoice_file_key: str
    invoice_file_url: Optional[str] = None
    payment_order_file_url: Optional[str] = None
    closing_documents: List[AccountingInvoiceClosingDocumentRead] = []

    model_config = ConfigDict(from_attributes=True)


class AccountingInvoiceListResponse(BaseModel):
    items: List[AccountingInvoiceRead]
    total: int
