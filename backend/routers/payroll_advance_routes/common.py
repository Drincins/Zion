from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import re
from typing import Optional
from urllib.parse import quote

from fastapi import Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import String, case, cast, func
from sqlalchemy.orm import Session, joinedload

from backend.bd.database import get_db
from backend.bd.models import (
    PayrollAdjustment,
    PayrollAdjustmentType,
    PayrollAdvanceConsolidatedStatement,
    PayrollAdvanceItem,
    PayrollAdvanceStatement,
    Position,
    Restaurant,
    RestaurantSubdivision,
    User,
)
from backend.schemas import (
    PayrollAdvanceConsolidatedCreateRequest,
    PayrollAdvanceConsolidatedDownloadRequest,
    PayrollAdvanceConsolidatedHistogramResponse,
    PayrollAdvanceConsolidatedListResponse,
    PayrollAdvanceConsolidatedPublic,
    PayrollAdvanceCreateRequest,
    PayrollAdvanceHistogramPositionPublic,
    PayrollAdvanceHistogramSubdivisionPublic,
    PayrollAdvanceItemBulkUpdateItem,
    PayrollAdvanceItemPatchResponse,
    PayrollAdvanceItemsBulkPatchResponse,
    PayrollAdvanceItemsBulkUpdateRequest,
    PayrollAdvanceItemPublic,
    PayrollAdvanceItemUpdateRequest,
    PayrollAdvanceListResponse,
    PayrollAdvancePostRequest,
    PayrollAdvanceStatementAdjustmentSummaryPublic,
    PayrollAdvanceStatementPublic,
    PayrollAdvanceStatementTotalsPublic,
    PayrollAdvanceStatementTotalsResponse,
    PayrollAdvanceStatusUpdate,
    PayrollAdjustmentBulkResponse,
    PayrollAdjustmentBulkResultItem,
    PayrollAdjustmentBulkStatusItem,
)
from backend.services.payroll_advances import (
    _merge_fire_comment,
    calculate_advance_rows,
    payroll_row_to_item_payload,
)
from backend.services.payroll_export import (
    build_consolidated_payroll_report_from_statements,
    build_payroll_report_from_statement,
)

try:  # pragma: no cover - shared dependency
    from backend.services.permissions import (
        PermissionCode,
        ensure_permissions,
        has_global_access,
        has_permission,
    )
    from backend.utils import get_current_user, get_user_restaurant_ids
except Exception as exc:  # pragma: no cover
    raise RuntimeError("Failed to import shared auth dependencies in payroll advances router") from exc


EDITABLE_STATUSES = {"draft", "review"}
LOCKED_STATUSES = {"ready", "posted"}
ALLOWED_TRANSITIONS = {
    "draft": {"review", "confirmed"},
    "review": {"draft", "confirmed"},
    "confirmed": {"review", "draft", "ready"},
    "ready": {"confirmed"},
    "posted": {"ready"},
}
STATUS_PERMISSIONS = {
    "review": PermissionCode.PAYROLL_ADVANCE_STATUS_REVIEW,
    "confirmed": PermissionCode.PAYROLL_ADVANCE_STATUS_CONFIRM,
    "ready": PermissionCode.PAYROLL_ADVANCE_STATUS_READY,
    "posted": PermissionCode.PAYROLL_ADVANCE_POST,
}
MONEY_QUANT = Decimal("0.01")


def _ensure_view(user: User) -> None:
    ensure_permissions(user, PermissionCode.PAYROLL_ADVANCE_VIEW)


def _ensure_create(user: User) -> None:
    ensure_permissions(user, PermissionCode.PAYROLL_ADVANCE_VIEW, PermissionCode.PAYROLL_ADVANCE_CREATE)


def _ensure_edit(user: User) -> None:
    ensure_permissions(user, PermissionCode.PAYROLL_ADVANCE_EDIT)


def _ensure_download(user: User) -> None:
    ensure_permissions(user, PermissionCode.PAYROLL_ADVANCE_DOWNLOAD)


def _ensure_delete(user: User, *, status: str) -> None:
    if has_global_access(user) or has_permission(user, PermissionCode.PAYROLL_ADVANCE_DELETE):
        return
    if status == "posted":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    ensure_permissions(user, PermissionCode.PAYROLL_ADVANCE_EDIT)


def _ensure_status(user: User, target_status: str) -> None:
    if target_status == "draft":
        ensure_permissions(user, PermissionCode.PAYROLL_ADVANCE_EDIT)
        return
    if has_global_access(user) or has_permission(user, PermissionCode.PAYROLL_ADVANCE_STATUS_ALL):
        return
    code = STATUS_PERMISSIONS.get(target_status)
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported status transition")
    ensure_permissions(user, code)


def _allowed_restaurant_ids(db: Session, viewer: User) -> Optional[set[int]]:
    allowed = get_user_restaurant_ids(db, viewer)
    if allowed is None:
        return None
    return {int(rid) for rid in allowed}


def _ensure_restaurant_access(db: Session, viewer: User, restaurant_id: Optional[int]) -> None:
    if restaurant_id is None:
        return
    allowed = _allowed_restaurant_ids(db, viewer)
    if allowed is not None and restaurant_id not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for this restaurant")


def _safe_slug(value: Optional[str], fallback: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^\w\-]+", "", text, flags=re.UNICODE)
    text = re.sub(r"_+", "_", text).strip("_-")
    return text or fallback


def _statement_kind_code(statement: PayrollAdvanceStatement) -> str:
    raw_kind = str(getattr(statement, "statement_kind", "") or "").lower()
    return "salary" if raw_kind == "salary" else "advance"


def _statement_filename(statement: PayrollAdvanceStatement) -> str:
    restaurant_name = getattr(getattr(statement, "restaurant", None), "name", None)
    if restaurant_name:
        restaurant_part = _safe_slug(restaurant_name, "restaurant")
    elif statement.restaurant_id:
        restaurant_part = f"restaurant_{statement.restaurant_id}"
    else:
        restaurant_part = "restaurant"
    date_from = statement.date_from.isoformat() if statement.date_from else "from"
    date_to = statement.date_to.isoformat() if statement.date_to else "to"
    date_part = date_from if date_from == date_to else f"{date_from}_{date_to}"
    kind_part = _statement_kind_code(statement)
    return f"{kind_part}_{restaurant_part}_{date_part}.xlsx"


def _ascii_filename_fallback(filename: str, fallback: str = "statement.xlsx") -> str:
    raw = str(filename or "").strip()
    if not raw:
        return fallback
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", raw)
    safe = re.sub(r"_+", "_", safe).strip("._-")
    if not safe:
        return fallback
    if "." not in safe and "." in fallback:
        ext = fallback.rsplit(".", 1)[-1]
        safe = f"{safe}.{ext}"
    return safe


def _content_disposition(filename: str, fallback: str = "statement.xlsx") -> str:
    safe_name = _ascii_filename_fallback(filename, fallback)
    encoded_name = quote(str(filename or safe_name), safe="")
    return f"attachment; filename=\"{safe_name}\"; filename*=UTF-8''{encoded_name}"


def _full_name(user: Optional[User]) -> Optional[str]:
    if not user:
        return None
    last = (getattr(user, "last_name", None) or "").strip()
    first = (getattr(user, "first_name", None) or "").strip()
    full_name = " ".join(part for part in (last, first) if part).strip()
    return full_name or getattr(user, "username", None)


def _item_to_public(item: PayrollAdvanceItem) -> PayrollAdvanceItemPublic:
    restaurant_name = item.restaurant.name if item.restaurant else None
    user = getattr(item, "user", None)
    fired = bool(getattr(user, "fired", False)) if user else False
    fire_date = getattr(user, "fire_date", None) if user else None
    calc_snapshot = item.calc_snapshot if isinstance(item.calc_snapshot, dict) else {}
    subdivision_name = calc_snapshot.get("subdivision_name")
    if not subdivision_name:
        subdivision_name = getattr(getattr(getattr(item, "position", None), "restaurant_subdivision", None), "name", None)
    return PayrollAdvanceItemPublic(
        id=item.id,
        user_id=item.user_id,
        staff_code=item.staff_code,
        full_name=item.full_name,
        position_name=item.position_name,
        subdivision_name=subdivision_name,
        restaurant_id=item.restaurant_id,
        restaurant_name=restaurant_name,
        fact_hours=float(item.fact_hours or 0),
        night_hours=float(item.night_hours or 0),
        rate=float(item.rate or 0) if item.rate is not None else None,
        accrual_amount=float(item.accrual_amount or 0),
        deduction_amount=float(item.deduction_amount or 0),
        calculated_amount=float(item.calculated_amount or 0),
        final_amount=float(item.final_amount or 0),
        manual=bool(item.manual),
        fired=fired,
        fire_date=fire_date,
        comment=item.comment,
    )


def _decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _quantize_money(amount: Decimal) -> Decimal:
    return amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _build_statement_adjustment_summaries(
    db: Session,
    statement: PayrollAdvanceStatement,
) -> list[PayrollAdvanceStatementAdjustmentSummaryPublic]:
    snapshot = statement.adjustments_snapshot or []
    parsed_rows: list[tuple[Optional[int], str, str, Decimal]] = []
    type_ids: set[int] = set()
    for entry in snapshot:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("type_name") or "").strip()
        kind = str(entry.get("kind") or "").strip().lower()
        if not name or kind not in {"accrual", "deduction"}:
            continue
        raw_type_id = entry.get("adjustment_type_id")
        try:
            type_id = int(raw_type_id) if raw_type_id is not None else None
        except (TypeError, ValueError):
            type_id = None
        if type_id is not None:
            type_ids.add(type_id)
        amount = abs(_quantize_money(_decimal(entry.get("amount"))))
        if amount <= 0:
            continue
        parsed_rows.append((type_id, name, kind, amount))

    if not parsed_rows:
        return []

    type_map: dict[int, PayrollAdjustmentType] = {}
    if type_ids:
        type_map = {
            obj.id: obj
            for obj in db.query(PayrollAdjustmentType)
            .filter(PayrollAdjustmentType.id.in_(type_ids))
            .all()
        }

    summary_map: dict[tuple[Optional[int], str, str], dict] = {}
    for type_id, snapshot_name, snapshot_kind, amount in parsed_rows:
        obj = type_map.get(type_id) if type_id is not None else None
        name = str(getattr(obj, "name", None) or snapshot_name).strip()
        kind = str(getattr(obj, "kind", None) or snapshot_kind).strip().lower()
        if kind not in {"accrual", "deduction"}:
            kind = snapshot_kind
        key = (type_id, name, kind)
        if key not in summary_map:
            summary_map[key] = {
                "adjustment_type_id": type_id,
                "name": name,
                "kind": kind,
                "show_in_report": bool(getattr(obj, "show_in_report", False)),
                "is_advance": bool(getattr(obj, "is_advance", False)),
                "amount": Decimal("0"),
            }
        summary_map[key]["amount"] += amount

    return [
        PayrollAdvanceStatementAdjustmentSummaryPublic(
            adjustment_type_id=payload["adjustment_type_id"],
            name=payload["name"],
            kind=payload["kind"],
            show_in_report=payload["show_in_report"],
            is_advance=payload["is_advance"],
            amount=float(_quantize_money(payload["amount"])),
        )
        for payload in sorted(
            summary_map.values(),
            key=lambda item: (
                0 if item["show_in_report"] else 1,
                str(item["kind"]),
                str(item["name"]).lower(),
            ),
        )
    ]


def _statement_to_public(
    db: Session,
    statement: PayrollAdvanceStatement,
    include_items: bool = True,
    include_adjustment_summaries: bool = True,
) -> PayrollAdvanceStatementPublic:
    restaurant_name = getattr(statement.restaurant, "name", None)
    subdivision_name = getattr(statement.subdivision, "name", None)
    payload = PayrollAdvanceStatementPublic(
        id=statement.id,
        status=statement.status,
        statement_kind=_statement_kind_code(statement),
        date_from=statement.date_from,
        date_to=statement.date_to,
        restaurant_id=statement.restaurant_id,
        restaurant_name=restaurant_name,
        subdivision_id=statement.subdivision_id,
        subdivision_name=subdivision_name,
        salary_percent=float(statement.salary_percent) if statement.salary_percent is not None else None,
        fixed_only=False,
        title=statement.title,
        created_by_id=statement.created_by_id,
        updated_by_id=statement.updated_by_id,
        created_at=statement.created_at,
        updated_at=statement.updated_at,
        posted_at=statement.posted_at,
        items=[],
        adjustment_summaries=(
            _build_statement_adjustment_summaries(db, statement)
            if include_adjustment_summaries
            else []
        ),
    )
    if include_items:
        payload.items = [_item_to_public(item) for item in statement.items]
    return payload


def _load_statement(db: Session, statement_id: int) -> PayrollAdvanceStatement:
    statement = (
        db.query(PayrollAdvanceStatement)
        .options(
            joinedload(PayrollAdvanceStatement.restaurant),
            joinedload(PayrollAdvanceStatement.subdivision),
            joinedload(PayrollAdvanceStatement.items).joinedload(PayrollAdvanceItem.restaurant),
            joinedload(PayrollAdvanceStatement.items).joinedload(PayrollAdvanceItem.user),
            joinedload(PayrollAdvanceStatement.items)
            .joinedload(PayrollAdvanceItem.position)
            .joinedload(Position.restaurant_subdivision),
        )
        .filter(PayrollAdvanceStatement.id == statement_id)
        .first()
    )
    if not statement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Statement not found")
    return statement


def _normalize_amount(value, kind: Optional[str]) -> float:
    amount = _decimal(value)
    if kind == "deduction" and amount > 0:
        amount = -amount
    return float(_quantize_money(amount))
