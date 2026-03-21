from __future__ import annotations

import hashlib
import re
from datetime import date
from typing import Optional

_SPACE_RE = re.compile(r"\s+")


def _normalize_name(value: Optional[str]) -> str:
    if not value:
        return ""
    return _SPACE_RE.sub(" ", value.strip().lower())


def build_employee_row_id(
    *,
    last_name: Optional[str],
    first_name: Optional[str],
    middle_name: Optional[str],
    birth_date: Optional[date],
) -> Optional[str]:
    if not last_name or not first_name or not birth_date:
        return None
    base = "|".join(
        [
            _normalize_name(last_name),
            _normalize_name(first_name),
            _normalize_name(middle_name),
            birth_date.isoformat(),
        ]
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()
