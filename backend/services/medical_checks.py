"""Utility helpers for employee medical checks."""
from __future__ import annotations

from datetime import date
import calendar

from backend.bd.models import MedicalCheckRecord, MedicalCheckStatus, MedicalCheckType

DEFAULT_NOTICE_DAYS = 30


def add_months(source: date, months: int) -> date:
    """Return date shifted by N months while keeping last day of month if needed."""
    month_index = (source.month - 1) + months
    year = source.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(source.day, last_day)
    return date(year, month, day)


def calculate_next_due(passed_at: date, validity_months: int | None) -> date | None:
    """Calculate expiration date based on validity in months."""
    if validity_months is None or validity_months <= 0:
        return None
    return add_months(passed_at, validity_months)


def calculate_status(
    *,
    next_due_at: date | None,
    notice_days: int | None,
    today: date | None = None,
) -> MedicalCheckStatus:
    """Return record status based on expiry date and notice period."""
    if next_due_at is None:
        return MedicalCheckStatus.OK
    today = today or date.today()
    delta = (next_due_at - today).days
    if delta < 0:
        return MedicalCheckStatus.EXPIRED
    threshold = notice_days if notice_days is not None else DEFAULT_NOTICE_DAYS
    if delta <= threshold:
        return MedicalCheckStatus.EXPIRING
    return MedicalCheckStatus.OK


def refresh_record_state(record: MedicalCheckRecord, *, today: date | None = None) -> MedicalCheckRecord:
    """Recalculate `next_due_at` and `status` for the given record."""
    record_type: MedicalCheckType | None = getattr(record, "check_type", None)
    validity_months = record_type.validity_months if record_type else None
    notice_days = record_type.notice_days if record_type else DEFAULT_NOTICE_DAYS
    record.next_due_at = calculate_next_due(record.passed_at, validity_months)
    record.status = calculate_status(next_due_at=record.next_due_at, notice_days=notice_days, today=today)
    return record

