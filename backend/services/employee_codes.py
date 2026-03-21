from __future__ import annotations

import re
from typing import Optional

from sqlalchemy.orm import Session

from backend.bd.models import User

_NUMERIC_RE = re.compile(r"^\d+$")


def _extract_numeric_stats(values: list[Optional[str]], *, width_limit: Optional[int] = None) -> tuple[int, int]:
    max_value = 0
    max_seen_width = 0
    for raw in values:
        if raw is None:
            continue
        value = str(raw).strip()
        if not value or not _NUMERIC_RE.match(value):
            continue
        if width_limit is not None and len(value) > width_limit:
            continue
        number = int(value)
        if number > max_value:
            max_value = number
        if len(value) > max_seen_width:
            max_seen_width = len(value)
    return max_value, max_seen_width


def generate_unique_numeric_code(
    db: Session,
    field_name: str,
    *,
    min_value: int = 1,
    pad_width: Optional[int] = None,
    max_width: Optional[int] = None,
) -> str:
    column = getattr(User, field_name)
    values = [row[0] for row in db.query(column).filter(column.isnot(None)).all()]
    max_value, max_seen_width = _extract_numeric_stats(values, width_limit=max_width)
    if max_value < min_value:
        max_value = min_value - 1
    if pad_width is None:
        if max_width is not None:
            pad_width = max_width
        else:
            pad_width = max_seen_width if max_seen_width > 0 else None

    candidate = max_value + 1
    if max_width is not None:
        max_allowed = (10 ** max_width) - 1
        if candidate > max_allowed:
            candidate = min_value
        while candidate <= max_allowed:
            candidate_str = str(candidate)
            if pad_width and len(candidate_str) < pad_width:
                candidate_str = candidate_str.zfill(pad_width)
            exists = db.query(User.id).filter(column == candidate_str).first()
            if not exists:
                return candidate_str
            candidate += 1
        raise ValueError(f"No available codes for {field_name} within {max_width} digits")

    while True:
        candidate_str = str(candidate)
        if pad_width and len(candidate_str) < pad_width:
            candidate_str = candidate_str.zfill(pad_width)
        exists = db.query(User.id).filter(column == candidate_str).first()
        if not exists:
            return candidate_str
        candidate += 1
        if pad_width and len(str(candidate)) > pad_width:
            pad_width = len(str(candidate))
