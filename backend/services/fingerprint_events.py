"""Helpers for fingerprint event logging."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from backend.bd.models import FingerprintEvent, User


def log_fingerprint_event(
    db: Session,
    *,
    staff_code: str,
    action: str,
    ok: bool = True,
    source: Optional[str] = None,
    slot: Optional[int] = None,
    score: Optional[int] = None,
    error_code: Optional[str] = None,
) -> Optional[FingerprintEvent]:
    code = (staff_code or "").strip()
    if not code:
        return None

    user = db.query(User).filter(User.staff_code == code).first()
    event = FingerprintEvent(
        user_id=user.id if user else None,
        staff_code=code,
        action=(action or "").strip().lower(),
        source=(source or "").strip().lower() or None,
        slot=slot,
        score=score,
        ok=bool(ok),
        error_code=(error_code or "").strip() or None,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
