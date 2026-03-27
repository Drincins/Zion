from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import re
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

from backend.bd.database import get_db
from backend.bd.models import (
    PayrollAdvanceItem,
    PayrollAdvanceConsolidatedStatement,
    PayrollAdvanceStatement,
    Position,
    User,
)
from backend.schemas import (
    PayrollAdvanceCreateRequest,
    PayrollAdvanceConsolidatedDownloadRequest,
    PayrollAdvanceConsolidatedCreateRequest,
    PayrollAdvanceConsolidatedListResponse,
    PayrollAdvanceConsolidatedPublic,
    PayrollAdvanceItemBulkUpdateItem,
    PayrollAdvanceItemsBulkUpdateRequest,
    PayrollAdvanceItemPublic,
    PayrollAdvanceItemPatchResponse,
    PayrollAdvanceItemsBulkPatchResponse,
    PayrollAdvanceItemUpdateRequest,
    PayrollAdvanceListResponse,
    PayrollAdvanceStatementAdjustmentSummaryPublic,
    PayrollAdvanceStatementTotalsPublic,
    PayrollAdvanceStatementTotalsResponse,
    PayrollAdvanceStatementPublic,
    PayrollAdvanceStatusUpdate,
    PayrollAdvancePostRequest,
    PayrollAdjustmentBulkResponse,
    PayrollAdjustmentBulkResultItem,
    PayrollAdjustmentBulkStatusItem,
)
from backend.services.payroll_advances import (
    calculate_advance_rows,
    payroll_row_to_item_payload,
    _merge_fire_comment,
)
from backend.services.payroll_export import (
    build_consolidated_payroll_report_from_statements,
    build_payroll_report_from_statement,
)
from backend.bd.models import PayrollAdjustment, PayrollAdjustmentType

try:  # pragma: no cover - shared dependency
    from backend.utils import get_current_user, get_user_restaurant_ids
    from backend.services.permissions import (
        PermissionCode,
        ensure_permissions,
        has_permission,
        has_global_access,
    )
except Exception as exc:  # pragma: no cover
    raise RuntimeError("Failed to import shared auth dependencies in payroll advances router") from exc


router = APIRouter(prefix="/payroll/advances", tags=["Payroll advances"])

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
        # Возврат в черновик разрешаем при праве на редактирование
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
    return set(int(rid) for rid in allowed)


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
    if date_from == date_to:
        date_part = date_from
    else:
        date_part = f"{date_from}_{date_to}"
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
    restaurant_name = None
    if item.restaurant:
        restaurant_name = item.restaurant.name
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


@router.get("", response_model=PayrollAdvanceListResponse)
def list_statements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_view(current_user)
    q = (
        db.query(PayrollAdvanceStatement)
        .options(
            joinedload(PayrollAdvanceStatement.restaurant),
            joinedload(PayrollAdvanceStatement.subdivision),
        )
        .order_by(PayrollAdvanceStatement.created_at.desc())
    )
    allowed = _allowed_restaurant_ids(db, current_user)
    if allowed is not None:
        if allowed:
            q = q.filter(PayrollAdvanceStatement.restaurant_id.in_(allowed))
        else:
            q = q.filter(False)
    statements = q.all()
    return PayrollAdvanceListResponse(
        items=[
            _statement_to_public(db, s, include_items=False, include_adjustment_summaries=False)
            for s in statements
        ]
    )


@router.get("/totals", response_model=PayrollAdvanceStatementTotalsResponse)
def get_statement_totals(
    ids: list[int] = Query(default_factory=list),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PayrollAdvanceStatementTotalsResponse:
    _ensure_view(current_user)

    ordered_ids: list[int] = []
    seen_ids: set[int] = set()
    for raw_id in ids or []:
        try:
            statement_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if statement_id <= 0 or statement_id in seen_ids:
            continue
        seen_ids.add(statement_id)
        ordered_ids.append(statement_id)

    if not ordered_ids:
        return PayrollAdvanceStatementTotalsResponse(items=[], missing_ids=[])
    if len(ordered_ids) > 500:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Too many statement ids")

    statements_q = db.query(PayrollAdvanceStatement.id).filter(PayrollAdvanceStatement.id.in_(ordered_ids))
    allowed = _allowed_restaurant_ids(db, current_user)
    if allowed is not None:
        if allowed:
            statements_q = statements_q.filter(PayrollAdvanceStatement.restaurant_id.in_(allowed))
        else:
            statements_q = statements_q.filter(False)

    accessible_ids = {int(row.id) for row in statements_q.all() if row.id is not None}
    if not accessible_ids:
        return PayrollAdvanceStatementTotalsResponse(items=[], missing_ids=ordered_ids)

    totals_rows = (
        db.query(
            PayrollAdvanceItem.statement_id.label("statement_id"),
            func.count(PayrollAdvanceItem.id).label("row_count"),
            func.coalesce(func.sum(PayrollAdvanceItem.accrual_amount), 0).label("accrual_total"),
            func.coalesce(func.sum(PayrollAdvanceItem.deduction_amount), 0).label("deduction_total"),
            func.coalesce(func.sum(PayrollAdvanceItem.final_amount), 0).label("final_total"),
            func.coalesce(
                func.sum(
                    case((PayrollAdvanceItem.accrual_amount > 0, 1), else_=0)
                ),
                0,
            ).label("accrual_rows_count"),
            func.coalesce(
                func.sum(
                    case((PayrollAdvanceItem.deduction_amount > 0, 1), else_=0)
                ),
                0,
            ).label("deduction_rows_count"),
        )
        .filter(PayrollAdvanceItem.statement_id.in_(accessible_ids))
        .group_by(PayrollAdvanceItem.statement_id)
        .all()
    )

    totals_by_statement_id = {
        int(row.statement_id): row
        for row in totals_rows
        if getattr(row, "statement_id", None) is not None
    }

    items: list[PayrollAdvanceStatementTotalsPublic] = []
    for statement_id in ordered_ids:
        if statement_id not in accessible_ids:
            continue
        row = totals_by_statement_id.get(statement_id)
        if not row:
            items.append(
                PayrollAdvanceStatementTotalsPublic(
                    statement_id=statement_id,
                    row_count=0,
                    accrual_total=0,
                    deduction_total=0,
                    final_total=0,
                    accrual_rows_count=0,
                    deduction_rows_count=0,
                )
            )
            continue
        items.append(
            PayrollAdvanceStatementTotalsPublic(
                statement_id=statement_id,
                row_count=int(getattr(row, "row_count", 0) or 0),
                accrual_total=float(_quantize_money(_decimal(getattr(row, "accrual_total", 0)))),
                deduction_total=float(_quantize_money(_decimal(getattr(row, "deduction_total", 0)))),
                final_total=float(_quantize_money(_decimal(getattr(row, "final_total", 0)))),
                accrual_rows_count=int(getattr(row, "accrual_rows_count", 0) or 0),
                deduction_rows_count=int(getattr(row, "deduction_rows_count", 0) or 0),
            )
        )

    missing_ids = [statement_id for statement_id in ordered_ids if statement_id not in accessible_ids]
    return PayrollAdvanceStatementTotalsResponse(items=items, missing_ids=missing_ids)


def _consolidated_to_public(
    stmt: PayrollAdvanceConsolidatedStatement,
) -> PayrollAdvanceConsolidatedPublic:
    raw_ids = stmt.statement_ids or []
    ordered_ids: list[int] = []
    seen: set[int] = set()
    for raw_id in raw_ids:
        try:
            stmt_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if stmt_id in seen:
            continue
        seen.add(stmt_id)
        ordered_ids.append(stmt_id)
    return PayrollAdvanceConsolidatedPublic(
        id=stmt.id,
        title=stmt.title,
        date_from=stmt.date_from,
        date_to=stmt.date_to,
        statement_ids=ordered_ids,
        created_by_id=stmt.created_by_id,
        created_at=stmt.created_at,
        updated_at=stmt.updated_at,
    )


@router.get("/consolidated", response_model=PayrollAdvanceConsolidatedListResponse)
def list_consolidated(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_download(current_user)
    q = db.query(PayrollAdvanceConsolidatedStatement).order_by(
        PayrollAdvanceConsolidatedStatement.created_at.desc()
    )
    if not has_global_access(current_user) and not has_permission(
        current_user, PermissionCode.PAYROLL_ADVANCE_DELETE
    ):
        q = q.filter(PayrollAdvanceConsolidatedStatement.created_by_id == current_user.id)
    items = q.all()
    return PayrollAdvanceConsolidatedListResponse(
        items=[_consolidated_to_public(item) for item in items]
    )


@router.post(
    "/consolidated",
    response_model=PayrollAdvanceConsolidatedPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_consolidated(
    payload: PayrollAdvanceConsolidatedCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_download(current_user)

    ordered_ids: list[int] = []
    seen: set[int] = set()
    for raw_id in payload.statement_ids:
        try:
            stmt_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if stmt_id in seen:
            continue
        seen.add(stmt_id)
        ordered_ids.append(stmt_id)
    if not ordered_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No statements selected")

    statements = (
        db.query(PayrollAdvanceStatement)
        .options(
            joinedload(PayrollAdvanceStatement.restaurant),
            joinedload(PayrollAdvanceStatement.items),
        )
        .filter(PayrollAdvanceStatement.id.in_(ordered_ids))
        .all()
    )
    statement_map = {stmt.id: stmt for stmt in statements}
    missing_ids = [stmt_id for stmt_id in ordered_ids if stmt_id not in statement_map]
    if missing_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Statements not found: {missing_ids}")

    ordered_statements: list[PayrollAdvanceStatement] = []
    for stmt_id in ordered_ids:
        stmt = statement_map[stmt_id]
        _ensure_restaurant_access(db, current_user, stmt.restaurant_id)
        ordered_statements.append(stmt)

    date_from = min(s.date_from for s in ordered_statements)
    date_to = max(s.date_to for s in ordered_statements)
    title = (payload.title or "").strip() or None

    consolidated = PayrollAdvanceConsolidatedStatement(
        title=title,
        statement_ids=ordered_ids,
        date_from=date_from,
        date_to=date_to,
        created_by_id=current_user.id,
    )
    db.add(consolidated)
    db.commit()
    db.refresh(consolidated)
    return _consolidated_to_public(consolidated)


@router.get("/consolidated/{consolidated_id}", response_model=PayrollAdvanceConsolidatedPublic)
def get_consolidated(
    consolidated_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_download(current_user)
    consolidated = db.query(PayrollAdvanceConsolidatedStatement).get(consolidated_id)
    if not consolidated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consolidated statement not found")
    if (
        not has_global_access(current_user)
        and consolidated.created_by_id != current_user.id
        and not has_permission(current_user, PermissionCode.PAYROLL_ADVANCE_DELETE)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return _consolidated_to_public(consolidated)


@router.get("/consolidated/{consolidated_id}/download")
def download_consolidated_by_id(
    consolidated_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_download(current_user)
    consolidated = db.query(PayrollAdvanceConsolidatedStatement).get(consolidated_id)
    if not consolidated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consolidated statement not found")
    if (
        not has_global_access(current_user)
        and consolidated.created_by_id != current_user.id
        and not has_permission(current_user, PermissionCode.PAYROLL_ADVANCE_DELETE)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    ordered_ids: list[int] = []
    seen: set[int] = set()
    for raw_id in (consolidated.statement_ids or []):
        try:
            stmt_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if stmt_id in seen:
            continue
        seen.add(stmt_id)
        ordered_ids.append(stmt_id)
    if not ordered_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No statements selected")

    statements = (
        db.query(PayrollAdvanceStatement)
        .options(
            joinedload(PayrollAdvanceStatement.restaurant),
            joinedload(PayrollAdvanceStatement.items),
        )
        .filter(PayrollAdvanceStatement.id.in_(ordered_ids))
        .all()
    )
    statement_map = {stmt.id: stmt for stmt in statements}
    missing_ids = [stmt_id for stmt_id in ordered_ids if stmt_id not in statement_map]
    if missing_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Statements not found: {missing_ids}")

    ordered_statements: list[PayrollAdvanceStatement] = []
    for stmt_id in ordered_ids:
        stmt = statement_map[stmt_id]
        _ensure_restaurant_access(db, current_user, stmt.restaurant_id)
        ordered_statements.append(stmt)

    stream = build_consolidated_payroll_report_from_statements(db, ordered_statements)
    filename = f"advance_consolidated_{consolidated.id}_{datetime.utcnow().date().isoformat()}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": _content_disposition(filename, fallback="advance_consolidated.xlsx")},
    )


@router.delete("/consolidated/{consolidated_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_consolidated(
    consolidated_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_download(current_user)
    consolidated = db.query(PayrollAdvanceConsolidatedStatement).get(consolidated_id)
    if not consolidated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consolidated statement not found")
    if (
        not has_global_access(current_user)
        and consolidated.created_by_id != current_user.id
        and not has_permission(current_user, PermissionCode.PAYROLL_ADVANCE_DELETE)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    db.delete(consolidated)
    db.commit()


@router.get("/{statement_id}", response_model=PayrollAdvanceStatementPublic)
def get_statement(
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_view(current_user)
    statement = _load_statement(db, statement_id)
    _ensure_restaurant_access(db, current_user, statement.restaurant_id)
    return _statement_to_public(db, statement)


@router.post("", response_model=PayrollAdvanceStatementPublic, status_code=status.HTTP_201_CREATED)
def create_statement(
    payload: PayrollAdvanceCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_create(current_user)
    if payload.date_to < payload.date_from:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="date_to must be >= date_from")
    _ensure_restaurant_access(db, current_user, payload.restaurant_id)

    statement_kind = payload.statement_kind or "advance"
    default_salary_percent = 100 if statement_kind == "salary" else 50
    salary_percent = payload.salary_percent if payload.salary_percent is not None else default_salary_percent
    calc = calculate_advance_rows(
        db,
        date_from=payload.date_from,
        date_to=payload.date_to,
        company_id=None,
        restaurant_id=payload.restaurant_id,
        subdivision_id=payload.subdivision_id,
        user_ids=payload.user_ids,
        salary_percent=salary_percent,
        fixed_only=False,
    )
    if not calc.rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No employees matched the filters")

    filters = {}
    if payload.user_ids:
        filters["user_ids"] = payload.user_ids

    statement = PayrollAdvanceStatement(
        title=payload.title,
        status="draft",
        statement_kind=statement_kind,
        date_from=payload.date_from,
        date_to=payload.date_to,
        restaurant_id=payload.restaurant_id,
        subdivision_id=payload.subdivision_id,
        salary_percent=salary_percent,
        fixed_only=False,
        filters=filters or None,
        adjustments_snapshot=calc.adjustments_snapshot,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    for row in calc.rows:
        statement.items.append(PayrollAdvanceItem(**payroll_row_to_item_payload(row)))

    db.add(statement)
    db.commit()
    db.refresh(statement)
    return _statement_to_public(db, statement)


@router.post("/{statement_id}/refresh", response_model=PayrollAdvanceStatementPublic)
def refresh_statement(
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_edit(current_user)
    statement = _load_statement(db, statement_id)
    _ensure_restaurant_access(db, current_user, statement.restaurant_id)
    if statement.status in LOCKED_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Statement is locked for editing")

    filters = statement.filters or {}
    calc = calculate_advance_rows(
        db,
        date_from=statement.date_from,
        date_to=statement.date_to,
        company_id=None,
        restaurant_id=statement.restaurant_id,
        subdivision_id=statement.subdivision_id,
        user_ids=filters.get("user_ids"),
        salary_percent=float(statement.salary_percent) if statement.salary_percent is not None else None,
        fixed_only=False,
    )
    statement.adjustments_snapshot = calc.adjustments_snapshot

    def _rate_key(value: object | None) -> str | None:
        if value is None:
            return None
        try:
            raw = value if isinstance(value, Decimal) else Decimal(str(value))
            return str(raw.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))
        except Exception:
            return str(value)

    def _item_key(item: PayrollAdvanceItem) -> tuple[int, int | None, str | None]:
        return (item.user_id, item.position_id, _rate_key(item.rate))

    def _payload_key(payload: dict) -> tuple[int, int | None, str | None]:
        return (int(payload["user_id"]), payload.get("position_id"), _rate_key(payload.get("rate")))

    # One statement can legitimately contain multiple rows for the same employee
    # (e.g. different positions/rates within the period). Refresh must reconcile
    # rows without collapsing them by user_id.
    existing_by_key: dict[tuple[int, int | None, str | None], list[PayrollAdvanceItem]] = {}
    for item in statement.items:
        existing_by_key.setdefault(_item_key(item), []).append(item)

    for row in calc.rows:
        payload = payroll_row_to_item_payload(row)
        key = _payload_key(payload)
        items = existing_by_key.get(key) or []
        if items:
            item = items.pop(0)
            item.restaurant_id = payload["restaurant_id"]
            item.position_id = payload["position_id"]
            item.position_name = payload["position_name"]
            item.staff_code = payload["staff_code"]
            item.full_name = payload["full_name"]
            item.calculated_amount = payload["calculated_amount"]
            item.fact_hours = payload["fact_hours"]
            item.night_hours = payload["night_hours"]
            item.rate = payload["rate"]
            item.accrual_amount = payload["accrual_amount"]
            item.deduction_amount = payload["deduction_amount"]
            item.calc_snapshot = payload["calc_snapshot"]
            if row.user.fired:
                item.comment = _merge_fire_comment(item.comment, row.user.fire_date)
            if not item.manual:
                item.final_amount = payload["calculated_amount"]
        else:
            statement.items.append(PayrollAdvanceItem(**payload))

    for items in existing_by_key.values():
        for item in items:
            db.delete(item)

    statement.updated_at = datetime.utcnow()
    statement.updated_by_id = current_user.id
    db.commit()
    db.refresh(statement)
    return _statement_to_public(db, statement)


@router.patch("/{statement_id}/items/{item_id}", response_model=PayrollAdvanceStatementPublic)
def update_item(
    statement_id: int,
    item_id: int,
    payload: PayrollAdvanceItemUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_edit(current_user)
    statement = _load_statement(db, statement_id)
    _ensure_restaurant_access(db, current_user, statement.restaurant_id)
    if statement.status not in EDITABLE_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Statement is not editable in this status")

    item = next((i for i in statement.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    item.final_amount = payload.final_amount
    item.manual = True
    item.comment = payload.comment
    if item.user and item.user.fired:
        item.comment = _merge_fire_comment(item.comment, item.user.fire_date)
    statement.updated_at = datetime.utcnow()
    statement.updated_by_id = current_user.id
    db.commit()
    db.refresh(statement)
    return _statement_to_public(db, statement)


@router.patch("/{statement_id}/items/{item_id}/compact", response_model=PayrollAdvanceItemPatchResponse)
def update_item_compact(
    statement_id: int,
    item_id: int,
    payload: PayrollAdvanceItemUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PayrollAdvanceItemPatchResponse:
    _ensure_edit(current_user)
    statement = (
        db.query(PayrollAdvanceStatement)
        .filter(PayrollAdvanceStatement.id == statement_id)
        .first()
    )
    if not statement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Statement not found")
    _ensure_restaurant_access(db, current_user, statement.restaurant_id)
    if statement.status not in EDITABLE_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Statement is not editable in this status")

    item = (
        db.query(PayrollAdvanceItem)
        .options(
            joinedload(PayrollAdvanceItem.restaurant),
            joinedload(PayrollAdvanceItem.user),
            joinedload(PayrollAdvanceItem.position).joinedload(Position.restaurant_subdivision),
        )
        .filter(
            PayrollAdvanceItem.statement_id == statement_id,
            PayrollAdvanceItem.id == item_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    item.final_amount = payload.final_amount
    item.manual = True
    item.comment = payload.comment
    if item.user and item.user.fired:
        item.comment = _merge_fire_comment(item.comment, item.user.fire_date)

    statement.updated_at = datetime.utcnow()
    statement.updated_by_id = current_user.id
    db.commit()

    refreshed_item = (
        db.query(PayrollAdvanceItem)
        .options(
            joinedload(PayrollAdvanceItem.restaurant),
            joinedload(PayrollAdvanceItem.user),
            joinedload(PayrollAdvanceItem.position).joinedload(Position.restaurant_subdivision),
        )
        .filter(
            PayrollAdvanceItem.statement_id == statement_id,
            PayrollAdvanceItem.id == item_id,
        )
        .first()
    )
    if not refreshed_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    return PayrollAdvanceItemPatchResponse(
        statement_id=statement_id,
        item=_item_to_public(refreshed_item),
        updated_at=statement.updated_at,
        updated_by_id=statement.updated_by_id,
    )


@router.patch("/{statement_id}/items/bulk/update", response_model=PayrollAdvanceItemsBulkPatchResponse)
def update_items_bulk_compact(
    statement_id: int,
    payload: PayrollAdvanceItemsBulkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PayrollAdvanceItemsBulkPatchResponse:
    _ensure_edit(current_user)
    statement = (
        db.query(PayrollAdvanceStatement)
        .filter(PayrollAdvanceStatement.id == statement_id)
        .first()
    )
    if not statement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Statement not found")
    _ensure_restaurant_access(db, current_user, statement.restaurant_id)
    if statement.status not in EDITABLE_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Statement is not editable in this status")

    raw_items = payload.items or []
    if not raw_items:
        return PayrollAdvanceItemsBulkPatchResponse(
            statement_id=statement_id,
            items=[],
            updated_at=statement.updated_at,
            updated_by_id=statement.updated_by_id,
        )

    normalized_items: list[PayrollAdvanceItemBulkUpdateItem] = []
    seen_ids: set[int] = set()
    for row in raw_items:
        item_id = int(row.item_id)
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)
        normalized_items.append(row)

    target_ids = [int(row.item_id) for row in normalized_items]
    db_items = (
        db.query(PayrollAdvanceItem)
        .options(
            joinedload(PayrollAdvanceItem.restaurant),
            joinedload(PayrollAdvanceItem.user),
            joinedload(PayrollAdvanceItem.position).joinedload(Position.restaurant_subdivision),
        )
        .filter(
            PayrollAdvanceItem.statement_id == statement_id,
            PayrollAdvanceItem.id.in_(target_ids),
        )
        .all()
    )
    items_by_id = {int(item.id): item for item in db_items}
    missing_ids = [item_id for item_id in target_ids if item_id not in items_by_id]
    if missing_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Items not found: {missing_ids[:10]}")

    for row in normalized_items:
        item = items_by_id[int(row.item_id)]
        item.final_amount = row.final_amount
        item.manual = True
        item.comment = row.comment
        if item.user and item.user.fired:
            item.comment = _merge_fire_comment(item.comment, item.user.fire_date)

    statement.updated_at = datetime.utcnow()
    statement.updated_by_id = current_user.id
    db.commit()

    refreshed_items = (
        db.query(PayrollAdvanceItem)
        .options(
            joinedload(PayrollAdvanceItem.restaurant),
            joinedload(PayrollAdvanceItem.user),
            joinedload(PayrollAdvanceItem.position).joinedload(Position.restaurant_subdivision),
        )
        .filter(
            PayrollAdvanceItem.statement_id == statement_id,
            PayrollAdvanceItem.id.in_(target_ids),
        )
        .all()
    )
    refreshed_by_id = {int(item.id): item for item in refreshed_items}
    ordered_payload = [
        _item_to_public(refreshed_by_id[int(row.item_id)])
        for row in normalized_items
        if int(row.item_id) in refreshed_by_id
    ]

    return PayrollAdvanceItemsBulkPatchResponse(
        statement_id=statement_id,
        items=ordered_payload,
        updated_at=statement.updated_at,
        updated_by_id=statement.updated_by_id,
    )


@router.post("/{statement_id}/status", response_model=PayrollAdvanceStatementPublic)
def change_status(
    statement_id: int,
    payload: PayrollAdvanceStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_view(current_user)
    statement = _load_statement(db, statement_id)
    _ensure_restaurant_access(db, current_user, statement.restaurant_id)

    target = payload.status
    current = statement.status
    if target == current:
        return _statement_to_public(db, statement)

    if target not in ALLOWED_TRANSITIONS.get(current, set()) and not has_permission(
        current_user, PermissionCode.PAYROLL_ADVANCE_STATUS_ALL
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transition is not allowed")

    _ensure_status(current_user, target)

    statement.status = target
    if target == "posted":
        statement.posted_at = datetime.utcnow()
    statement.updated_at = datetime.utcnow()
    statement.updated_by_id = current_user.id
    db.commit()
    db.refresh(statement)
    return _statement_to_public(db, statement)


def _normalize_amount(value, kind: Optional[str]) -> float:
    amount = _decimal(value)
    if kind == "deduction" and amount > 0:
        amount = -amount
    return _quantize_money(amount)


MONEY_QUANT = Decimal("0.01")


def _decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _quantize_money(amount: Decimal) -> Decimal:
    return amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


@router.post("/{statement_id}/post", response_model=PayrollAdjustmentBulkResponse)
def post_statement(
    statement_id: int,
    payload: PayrollAdvancePostRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_status(current_user, "posted")
    statement = _load_statement(db, statement_id)
    _ensure_restaurant_access(db, current_user, statement.restaurant_id)
    if statement.status not in {"ready", "confirmed"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Statement must be ready or confirmed")

    adj_type = db.query(PayrollAdjustmentType).get(payload.adjustment_type_id)
    if not adj_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adjustment type not found")

    rows = []
    for item in statement.items:
        code = (item.staff_code or "").strip()
        if not code:
            continue
        raw_amount = _quantize_money(_decimal(item.final_amount))
        if raw_amount == 0:
            continue
        rows.append(
            {
                "staff_code": code,
                "amount": _normalize_amount(raw_amount, adj_type.kind),
                "raw_amount": raw_amount,
            }
        )

    skipped: list[PayrollAdjustmentBulkResultItem] = []
    errors: list[PayrollAdjustmentBulkResultItem] = []
    results: list[PayrollAdjustmentBulkStatusItem] = []
    created: list[PayrollAdjustment] = []
    created_total = Decimal("0")

    users = (
        db.query(User)
        .filter(User.staff_code.in_([r["staff_code"] for r in rows]))
        .all()
    )
    staff_to_user = {row.staff_code: row for row in users if row.staff_code}

    target_restaurant_id = statement.restaurant_id or payload.restaurant_id

    existing_q = (
        db.query(PayrollAdjustment.user_id)
        .filter(PayrollAdjustment.restaurant_id == target_restaurant_id)
        .filter(PayrollAdjustment.adjustment_type_id == payload.adjustment_type_id)
        .filter(PayrollAdjustment.date == payload.date)
    )
    existing_map = {row.user_id for row in existing_q.all()}

    for row in rows:
        code = row["staff_code"]
        user = staff_to_user.get(code)
        if not user:
            reason = "Сотрудник не найден"
            errors.append(PayrollAdjustmentBulkResultItem(staff_code=code, reason=reason))
            results.append(PayrollAdjustmentBulkStatusItem(staff_code=code, status="error", reason=reason))
            continue
        user_id = user.id
        full_name = _full_name(user)
        if user_id in existing_map:
            reason = "Запись уже существует"
            skipped.append(
                PayrollAdjustmentBulkResultItem(
                    staff_code=code,
                    user_id=user_id,
                    full_name=full_name,
                    reason=reason,
                )
            )
            results.append(
                PayrollAdjustmentBulkStatusItem(
                    staff_code=code,
                    user_id=user_id,
                    full_name=full_name,
                    status="skipped",
                    reason=reason,
                )
            )
            continue
        created_total += abs(row["raw_amount"])
        created.append(
            PayrollAdjustment(
                user_id=user_id,
                adjustment_type_id=payload.adjustment_type_id,
                restaurant_id=target_restaurant_id,
                amount=row["amount"],
                date=payload.date,
                responsible_id=current_user.id,
                comment=payload.comment,
            )
        )
        results.append(
            PayrollAdjustmentBulkStatusItem(
                staff_code=code,
                user_id=user_id,
                full_name=full_name,
                status="created",
            )
        )

    created_count = len(created)
    if created:
        db.bulk_save_objects(created)
        statement.status = "posted"
        statement.posted_at = datetime.utcnow()
        statement.updated_at = datetime.utcnow()
        statement.updated_by_id = current_user.id
        db.commit()
        db.refresh(statement)

    return PayrollAdjustmentBulkResponse(
        created_count=created_count,
        created_total=float(_quantize_money(created_total)),
        skipped=skipped,
        errors=errors,
        results=results,
    )


@router.get("/{statement_id}/download")
def download_statement(
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_download(current_user)
    statement = _load_statement(db, statement_id)
    _ensure_restaurant_access(db, current_user, statement.restaurant_id)
    stream = build_payroll_report_from_statement(db, statement)
    filename = _statement_filename(statement)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": _content_disposition(filename, fallback="advance_statement.xlsx")},
    )


@router.post("/consolidated/download")
def download_consolidated(
    payload: PayrollAdvanceConsolidatedDownloadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_download(current_user)

    ordered_ids: list[int] = []
    seen: set[int] = set()
    for raw_id in payload.statement_ids:
        try:
            stmt_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if stmt_id in seen:
            continue
        seen.add(stmt_id)
        ordered_ids.append(stmt_id)
    if not ordered_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No statements selected")

    statements = (
        db.query(PayrollAdvanceStatement)
        .options(
            joinedload(PayrollAdvanceStatement.restaurant),
            joinedload(PayrollAdvanceStatement.items),
        )
        .filter(PayrollAdvanceStatement.id.in_(ordered_ids))
        .all()
    )
    statement_map = {stmt.id: stmt for stmt in statements}
    missing_ids = [stmt_id for stmt_id in ordered_ids if stmt_id not in statement_map]
    if missing_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Statements not found: {missing_ids}")

    ordered_statements: list[PayrollAdvanceStatement] = []
    for stmt_id in ordered_ids:
        stmt = statement_map[stmt_id]
        _ensure_restaurant_access(db, current_user, stmt.restaurant_id)
        ordered_statements.append(stmt)

    stream = build_consolidated_payroll_report_from_statements(db, ordered_statements)
    filename = f"advance_consolidated_{datetime.utcnow().date().isoformat()}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": _content_disposition(filename, fallback="advance_consolidated.xlsx")},
    )


@router.delete("/{statement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_statement(
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = _load_statement(db, statement_id)
    _ensure_restaurant_access(db, current_user, statement.restaurant_id)
    _ensure_delete(current_user, status=statement.status)

    db.delete(statement)
    db.commit()
