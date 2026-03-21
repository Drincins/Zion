"""Utilities for CIS document validity calculations."""
from __future__ import annotations

import calendar
from datetime import date

from backend.bd.models import CisDocumentRecord, CisDocumentStatus, CisDocumentType

DEFAULT_NOTICE_DAYS = 30


def add_months(value: date, months: int) -> date:
    month_index = (value.month - 1) + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(value.day, last_day)
    return date(year, month, day)


def calculate_expiry(issued_at: date | None, validity_months: int | None) -> date | None:
    if issued_at is None or validity_months is None or validity_months <= 0:
        return None
    return add_months(issued_at, validity_months)


def calculate_status(
    *,
    expires_at: date | None,
    notice_days: int | None,
    today: date | None = None,
) -> CisDocumentStatus:
    if expires_at is None:
        return CisDocumentStatus.OK
    today = today or date.today()
    delta = (expires_at - today).days
    if delta < 0:
        return CisDocumentStatus.EXPIRED
    threshold = notice_days if notice_days is not None else DEFAULT_NOTICE_DAYS
    if delta <= threshold:
        return CisDocumentStatus.EXPIRING
    return CisDocumentStatus.OK


def refresh_document_state(record: CisDocumentRecord, *, today: date | None = None) -> CisDocumentRecord:
    doc_type: CisDocumentType | None = getattr(record, "document_type", None)
    validity_months = doc_type.validity_months if doc_type else None
    notice_days = doc_type.notice_days if doc_type else DEFAULT_NOTICE_DAYS
    record.expires_at = calculate_expiry(record.issued_at, validity_months) if record.expires_at is None else record.expires_at
    record.status = calculate_status(expires_at=record.expires_at, notice_days=notice_days, today=today)
    return record
