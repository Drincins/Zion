from __future__ import annotations

import calendar
import json
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
import traceback
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from backend.bd.database import get_db
from backend.services.reference_cache import cached_reference_data, invalidate_reference_scope
from backend.services.payroll_export import (
    build_payroll_report,
    build_payroll_report_from_statement,
    resolve_payroll_export_bounds,
)
from backend.bd.models import (
    Attendance,
    Position,
    PayrollAdjustment,
    PayrollAdjustmentType,
    PayrollSalaryResult,
    PayrollAdvanceStatement,
    User,
    Restaurant,
)
from backend.schemas import (
    PayrollAdjustmentCreate,
    PayrollAdjustmentBulkCreate,
    PayrollAdjustmentBulkResponse,
    PayrollAdjustmentBulkResultItem,
    PayrollAdjustmentListResponse,
    PayrollAdjustmentPublic,
    PayrollAdjustmentTypeCreate,
    PayrollAdjustmentTypeListResponse,
    PayrollAdjustmentTypePublic,
    PayrollAdjustmentTypeUpdate,
    PayrollAdjustmentUpdate,
    PayrollSalaryResultPublic,
    PayrollSalaryResultListResponse,
    PayrollSalaryRecalcRequest,
)
from fastapi.responses import StreamingResponse

try:  # pragma: no cover - shared dependency
    from backend.utils import get_current_user, users_share_restaurant, get_user_restaurant_ids
    from backend.services.permissions import (
        PermissionCode,
        ensure_permissions,
        has_permission,
        has_global_access,
        can_manage_user,
        ensure_can_manage_user,
        can_view_rate,
    )
except Exception as exc:  # pragma: no cover
    raise RuntimeError("Failed to import shared auth dependencies in payroll router") from exc


router = APIRouter(prefix="/payroll", tags=["Payroll"])
PAYROLL_ADJUSTMENT_TYPES_CACHE_SCOPE = "payroll:adjustment_types"
PAYROLL_ADJUSTMENT_TYPES_CACHE_TTL_SECONDS = 60


def _has_payroll_view(user: User) -> bool:
    return (
        has_global_access(user)
        or has_permission(user, PermissionCode.PAYROLL_VIEW)
        or has_permission(user, PermissionCode.PAYROLL_MANAGE)
        or has_permission(user, PermissionCode.PAYROLL_RESULTS_VIEW)
        or has_permission(user, PermissionCode.PAYROLL_RESULTS_MANAGE)
    )


def _has_payroll_manage(user: User) -> bool:
    return (
        has_global_access(user)
        or has_permission(user, PermissionCode.PAYROLL_MANAGE)
        or has_permission(user, PermissionCode.PAYROLL_RESULTS_MANAGE)
    )


def _has_payroll_export(user: User) -> bool:
    return (
        has_global_access(user)
        or has_permission(user, PermissionCode.PAYROLL_EXPORT)
        or has_permission(user, PermissionCode.PAYROLL_ADVANCE_DOWNLOAD)
    )


def _ensure_payroll_view(user: User) -> None:
    if not _has_payroll_view(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")


def _ensure_payroll_export(user: User) -> None:
    if not _has_payroll_export(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")


def _effective_user(db: Session, viewer: User, requested_user_id: Optional[int]) -> Optional[int]:
    if requested_user_id is None:
        return None if _has_payroll_view(viewer) else viewer.id
    if requested_user_id == viewer.id:
        return requested_user_id
    if not users_share_restaurant(db, viewer, requested_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to the selected restaurants is not allowed",
        )
    if _has_payroll_view(viewer):
        return requested_user_id
    if has_permission(viewer, PermissionCode.STAFF_MANAGE_SUBORDINATES):
        target = (
            db.query(User)
            .options(
                joinedload(User.position).joinedload(Position.payment_format),
                joinedload(User.position).joinedload(Position.restaurant_subdivision),
            )
            .filter(User.id == requested_user_id)
            .first()
        )
        if target and can_manage_user(viewer, target):
            return requested_user_id
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")


def _ensure_payroll_manage(user: User) -> None:
    if not _has_payroll_manage(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")


def _load_user_with_position(db: Session, user_id: int) -> Optional[User]:
    return (
        db.query(User)
        .options(
            joinedload(User.position).joinedload(Position.payment_format),
            joinedload(User.position).joinedload(Position.restaurant_subdivision),
            joinedload(User.restaurants),
        )
        .filter(User.id == user_id)
        .first()
    )


def _ensure_adjustment_restaurant_access(
    db: Session, target_user: User, restaurant_id: Optional[int], current_user: User
) -> None:
    if restaurant_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="restaurant_id is required")

    user_restaurant_ids = {
        r.id for r in (getattr(target_user, "restaurants", None) or []) if r and r.id is not None
    }
    can_override_employee_restaurants = _has_payroll_manage(current_user) or has_permission(
        current_user, PermissionCode.STAFF_MANAGE_ALL
    ) or has_permission(current_user, PermissionCode.STAFF_MANAGE_SUBORDINATES)
    if restaurant_id not in user_restaurant_ids and not can_override_employee_restaurants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ресторан не закреплен за сотрудником",
        )

    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    if allowed_restaurants is not None and restaurant_id not in allowed_restaurants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ к выбранному ресторану запрещен",
        )


DEFAULT_SHIFT_HOURS = Decimal("8")
MONEY_QUANT = Decimal("0.01")


def _quantize_money(amount: Decimal) -> Decimal:
    return amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _resolve_period_bounds(
    period_start: Optional[date],
    period_end: Optional[date],
) -> tuple[date, date]:
    if period_start and not period_end:
        period_end = period_start
    if period_end and not period_start:
        period_start = period_end
    if not period_start or not period_end:
        today = date.today()
        first_day = today.replace(day=1)
        last_day = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
        period_start = period_start or first_day
        period_end = period_end or last_day
    if period_end < period_start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period_end must be >= period_start")
    return period_start, period_end


def _attendance_minutes(attendance: Attendance) -> int:
    if attendance.duration_minutes is not None:
        return attendance.duration_minutes
    if (
        attendance.open_date
        and attendance.open_time
        and attendance.close_date
        and attendance.close_time
    ):
        opened = datetime.combine(attendance.open_date, attendance.open_time)
        closed = datetime.combine(attendance.close_date, attendance.close_time)
        delta = closed - opened
        return max(int(delta.total_seconds() // 60), 0)
    return 0


def _deserialize_details(raw: Optional[str]) -> Optional[dict]:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _calculate_salary_components(
    db: Session,
    user: User,
    period_start: date,
    period_end: date,
) -> tuple[Decimal, Decimal, Decimal, dict]:
    position = getattr(user, "position", None)
    payment_format = getattr(position, "payment_format", None) if position else None
    rate = Decimal(position.rate) if position and position.rate is not None else Decimal("0")

    attendances = (
        db.query(Attendance)
        .filter(Attendance.user_id == user.id)
        .filter(Attendance.close_date.isnot(None))
        # Все часы относим к дате открытия смены, даже если закрылась в другой день
        .filter(Attendance.open_date >= period_start)
        .filter(Attendance.open_date <= period_end)
        .all()
    )
    total_minutes = sum(_attendance_minutes(item) for item in attendances)
    fact_hours = Decimal(total_minutes) / Decimal(60) if total_minutes else Decimal("0")

    details: dict = {
        "payment_format_code": getattr(payment_format, "code", None),
        "payment_format_name": getattr(payment_format, "name", None),
        "rate": float(rate),
        "fact_minutes": total_minutes,
        "fact_hours": float(fact_hours),
        "attendances_count": len(attendances),
    }

    base_amount = Decimal("0")
    fact_shifts: Optional[Decimal] = None

    if payment_format and position:
        mode = payment_format.calculation_mode
        if mode == "hourly":
            base_amount = rate * fact_hours
        elif mode == "fixed":
            base_amount = rate
        elif mode == "shift_norm":
            hours_per_shift = Decimal(position.hours_per_shift) if position.hours_per_shift else DEFAULT_SHIFT_HOURS
            monthly_shift_norm = Decimal(position.monthly_shift_norm) if position.monthly_shift_norm else Decimal("0")
            details["hours_per_shift"] = float(hours_per_shift)
            details["monthly_shift_norm"] = float(monthly_shift_norm)
            if hours_per_shift > 0 and monthly_shift_norm > 0:
                fact_shifts = fact_hours / hours_per_shift if hours_per_shift > 0 else Decimal("0")
                details["fact_shifts"] = float(fact_shifts)
                worked_ratio = min(fact_shifts, monthly_shift_norm) / monthly_shift_norm
                base_amount = rate * worked_ratio
        else:
            base_amount = Decimal("0")

    base_amount = _quantize_money(base_amount)

    adjustment_rows = (
        db.query(PayrollAdjustment, PayrollAdjustmentType)
        .join(PayrollAdjustmentType, PayrollAdjustment.adjustment_type_id == PayrollAdjustmentType.id)
        .filter(PayrollAdjustment.user_id == user.id)
        .filter(PayrollAdjustment.date >= period_start)
        .filter(PayrollAdjustment.date <= period_end)
        .order_by(PayrollAdjustment.date.asc())
        .all()
    )
    adjustments_amount = Decimal("0")
    adjustment_details = []
    for adjustment, adjustment_type in adjustment_rows:
        amount = Decimal(adjustment.amount or 0)
        signed_amount = amount if adjustment_type.kind == "accrual" else amount * Decimal("-1")
        adjustments_amount += signed_amount
        adjustment_details.append(
            {
                "id": adjustment.id,
                "type_id": adjustment_type.id,
                "type_name": adjustment_type.name,
                "kind": adjustment_type.kind,
                "amount": float(amount),
                "signed_amount": float(signed_amount),
                "date": adjustment.date.isoformat(),
                "comment": adjustment.comment,
            }
        )

    adjustments_amount = _quantize_money(adjustments_amount)
    gross_amount = _quantize_money(base_amount + adjustments_amount)

    details["fact_shifts"] = details.get("fact_shifts")
    details["adjustments"] = adjustment_details
    details["base_amount"] = float(base_amount)
    details["adjustments_amount"] = float(adjustments_amount)
    details["gross_amount"] = float(gross_amount)

    return base_amount, adjustments_amount, gross_amount, details


def _salary_result_public(result: PayrollSalaryResult) -> PayrollSalaryResultPublic:
    return PayrollSalaryResultPublic(
        id=result.id,
        user_id=result.user_id,
        period_start=result.period_start,
        period_end=result.period_end,
        base_amount=float(result.base_amount or 0),
        adjustments_amount=float(result.adjustments_amount or 0),
        gross_amount=float(result.gross_amount or 0),
        details=_deserialize_details(result.details),
        calculated_at=result.calculated_at,
        calculated_by_id=result.calculated_by_id,
    )


def _recalculate_salary_for_user(
    db: Session,
    user: User,
    period_start: date,
    period_end: date,
    calculated_by_id: Optional[int],
) -> PayrollSalaryResult:
    base_amount, adjustments_amount, gross_amount, details = _calculate_salary_components(
        db, user, period_start, period_end
    )
    record = (
        db.query(PayrollSalaryResult)
        .filter(
            PayrollSalaryResult.user_id == user.id,
            PayrollSalaryResult.period_start == period_start,
            PayrollSalaryResult.period_end == period_end,
        )
        .first()
    )
    if not record:
        record = PayrollSalaryResult(
            user_id=user.id,
            period_start=period_start,
            period_end=period_end,
        )
        db.add(record)

    record.base_amount = base_amount
    record.adjustments_amount = adjustments_amount
    record.gross_amount = gross_amount
    record.details = json.dumps(details, ensure_ascii=False)
    record.calculated_at = datetime.utcnow()
    record.calculated_by_id = calculated_by_id

    db.flush()
    db.refresh(record)
    return record


@router.get("/salary-results", response_model=PayrollSalaryResultListResponse)
def list_salary_results(
    user_id: Optional[int] = Query(None),
    period_from: Optional[date] = Query(None),
    period_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PayrollSalaryResultListResponse:
    _ensure_payroll_view(current_user)
    effective_user_id = _effective_user(db, current_user, user_id)
    query = db.query(PayrollSalaryResult)
    if effective_user_id is not None:
        query = query.filter(PayrollSalaryResult.user_id == effective_user_id)
    if period_from:
        query = query.filter(PayrollSalaryResult.period_end >= period_from)
    if period_to:
        query = query.filter(PayrollSalaryResult.period_start <= period_to)
    items = (
        query.order_by(PayrollSalaryResult.period_start.desc(), PayrollSalaryResult.user_id.asc()).all()
    )
    return PayrollSalaryResultListResponse(items=[_salary_result_public(item) for item in items])


@router.post(
    "/salary-results/recalculate",
    response_model=PayrollSalaryResultListResponse,
    status_code=status.HTTP_201_CREATED,
)
def recalculate_salary_results(
    payload: PayrollSalaryRecalcRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PayrollSalaryResultListResponse:
    _ensure_payroll_manage(current_user)
    period_start, period_end = _resolve_period_bounds(payload.period_start, payload.period_end)

    target_ids = payload.user_ids or [current_user.id]
    unique_user_ids: List[int] = []
    seen: set[int] = set()
    for user_id in target_ids:
        if user_id not in seen:
            unique_user_ids.append(user_id)
            seen.add(user_id)

    if not unique_user_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_ids cannot be empty")

    results: List[PayrollSalaryResult] = []
    for user_id in unique_user_ids:
        target_user_id = _effective_user(db, current_user, user_id)
        if target_user_id is None:
            continue
        user = _load_user_with_position(db, target_user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {target_user_id} not found")
        result = _recalculate_salary_for_user(db, user, period_start, period_end, current_user.id)
        results.append(result)

    db.commit()
    return PayrollSalaryResultListResponse(items=[_salary_result_public(item) for item in results])


@router.get("/export")
def export_payroll_register(
    period: Optional[str] = Query(None, description="Период YYYY-MM"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    company_id: Optional[int] = Query(None),
    restaurant_id: Optional[int] = Query(None),
    restaurant_subdivision_id: Optional[int] = Query(None),
    user_ids: Optional[List[int]] = Query(None),
    salary_percent: Optional[float] = Query(
        None,
        ge=0,
        le=100,
        description="Доля оклада для включения в ведомость, % (0-100). Применяется только к формату оплаты fixed.",
    ),
    advance_statement_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        _ensure_payroll_export(current_user)
        snapshot_stream = None
        if advance_statement_id:
            statement = (
                db.query(PayrollAdvanceStatement)
                .options(joinedload(PayrollAdvanceStatement.items))
                .filter(PayrollAdvanceStatement.id == advance_statement_id)
                .first()
            )
            if not statement:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Statement not found")

            allowed_restaurants = get_user_restaurant_ids(db, current_user)
            if (
                allowed_restaurants is not None
                and statement.restaurant_id is not None
                and statement.restaurant_id not in allowed_restaurants
            ):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for this restaurant")

            period = None
            date_from = statement.date_from
            date_to = statement.date_to
            if statement.restaurant_id is not None:
                restaurant_id = statement.restaurant_id
            if statement.subdivision_id is not None:
                restaurant_subdivision_id = statement.subdivision_id
            if statement.salary_percent is not None:
                salary_percent = float(statement.salary_percent)
            statement_user_ids = [item.user_id for item in statement.items if item.user_id is not None]
            user_ids = list({int(uid) for uid in statement_user_ids}) if statement_user_ids else None
            # Export statement files from the saved document state instead of
            # rebuilding them through user_id-based overrides. This preserves
            # multiple rows for one employee and keeps Excel aligned with the
            # exact statement values, including manual edits.
            snapshot_stream = build_payroll_report_from_statement(db, statement)
        start, end = resolve_payroll_export_bounds(period=period, date_from=date_from, date_to=date_to)
        if snapshot_stream is not None:
            stream = snapshot_stream
        else:
            stream = build_payroll_report(
                db,
                period=period,
                date_from=date_from,
                date_to=date_to,
                company_id=company_id,
                restaurant_id=restaurant_id,
                subdivision_id=restaurant_subdivision_id,
                user_ids=user_ids,
                salary_percent=salary_percent,
            )
        if date_from or date_to or not period:
            label = start.isoformat() if start == end else f"{start.isoformat()}_{end.isoformat()}"
        else:
            label = period
        filename = f"payroll_{label}.xlsx"
        return StreamingResponse(
            stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store, max-age=0",
                "Pragma": "no-cache",
            },
        )
    except ValueError as exc:
        return Response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        tb = traceback.format_exc()
        message = f"{exc.__class__.__name__}: {exc}\\n{tb}"
        print(message)
        return Response(
            content="Internal Server Error",
            media_type="text/plain",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

def _to_type_public(obj: PayrollAdjustmentType) -> PayrollAdjustmentTypePublic:
    return PayrollAdjustmentTypePublic(
        id=obj.id,
        name=obj.name,
        kind=obj.kind,
        show_in_report=bool(getattr(obj, "show_in_report", False)),
        is_advance=bool(getattr(obj, "is_advance", False)),
    )


def _full_name(user: Optional[User]) -> Optional[str]:
    if not user:
        return None
    parts = [user.last_name or "", user.first_name or ""]
    name = " ".join(p for p in parts if p).strip()
    if name:
        return name
    return user.username


def _to_adjustment_public(
    obj: PayrollAdjustment,
    *,
    can_view_amount: bool = True,
) -> PayrollAdjustmentPublic:
    amount = float(obj.amount) if can_view_amount and obj.amount is not None else None
    return PayrollAdjustmentPublic(
        id=obj.id,
        user_id=obj.user_id,
        adjustment_type_id=obj.adjustment_type_id,
        amount=amount,
        date=obj.date,
        restaurant_id=getattr(obj, "restaurant_id", None),
        responsible_id=obj.responsible_id,
        responsible_name=_full_name(getattr(obj, "responsible", None)),
        comment=obj.comment,
        adjustment_type=_to_type_public(obj.adjustment_type) if obj.adjustment_type else None,
        restaurant_name=getattr(getattr(obj, "restaurant", None), "name", None),
    )


def _to_decimal(value) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _normalize_amount(value, kind: str) -> Optional[Decimal]:
    amount = _to_decimal(value)
    if amount is None:
        return None
    amount = abs(amount)
    return -amount if kind == 'deduction' else amount


@router.get("/adjustment-types", response_model=PayrollAdjustmentTypeListResponse)
def list_adjustment_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PayrollAdjustmentTypeListResponse:
    ensure_permissions(current_user, PermissionCode.PAYROLL_VIEW, PermissionCode.PAYROLL_MANAGE)
    def _load_adjustment_types() -> list[dict]:
        rows = db.query(PayrollAdjustmentType).order_by(PayrollAdjustmentType.name.asc()).all()
        return [_to_type_public(item).model_dump(mode="json") for item in rows]

    payload = cached_reference_data(
        PAYROLL_ADJUSTMENT_TYPES_CACHE_SCOPE,
        "all",
        _load_adjustment_types,
        ttl_seconds=PAYROLL_ADJUSTMENT_TYPES_CACHE_TTL_SECONDS,
    )
    items = [PayrollAdjustmentTypePublic.model_validate(item) for item in payload]
    return PayrollAdjustmentTypeListResponse(items=items)


@router.post("/adjustment-types", response_model=PayrollAdjustmentTypePublic, status_code=status.HTTP_201_CREATED)
def create_adjustment_type(
    payload: PayrollAdjustmentTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PayrollAdjustmentTypePublic:
    _ensure_payroll_manage(current_user)
    normalized = func.lower(PayrollAdjustmentType.name)
    duplicate = (
        db.query(PayrollAdjustmentType)
        .filter(normalized == payload.name.lower())
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Adjustment type already exists")
    if payload.is_advance and payload.kind != "deduction":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Авансовым может быть только удержание",
        )

    obj = PayrollAdjustmentType(
        name=payload.name,
        kind=payload.kind,
        show_in_report=bool(payload.show_in_report),
        is_advance=bool(payload.is_advance),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    invalidate_reference_scope(PAYROLL_ADJUSTMENT_TYPES_CACHE_SCOPE)
    return _to_type_public(obj)


@router.put("/adjustment-types/{type_id}", response_model=PayrollAdjustmentTypePublic)
def update_adjustment_type(
    type_id: int,
    payload: PayrollAdjustmentTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PayrollAdjustmentTypePublic:
    _ensure_payroll_manage(current_user)
    obj = db.query(PayrollAdjustmentType).get(type_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adjustment type not found")

    data = payload.model_dump(exclude_unset=True)
    next_kind = data.get("kind", obj.kind)
    next_is_advance = bool(data.get("is_advance", obj.is_advance))
    if next_is_advance and next_kind != "deduction":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Авансовым может быть только удержание",
        )

    if "name" in data:
        normalized = func.lower(PayrollAdjustmentType.name)
        duplicate = (
            db.query(PayrollAdjustmentType)
            .filter(normalized == data["name"].lower(), PayrollAdjustmentType.id != type_id)
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Adjustment type already exists")
        obj.name = data["name"]
    if "kind" in data:
        new_kind = data["kind"]
        obj.kind = new_kind
        for adjustment in obj.adjustments:
            if adjustment.amount is not None:
                adjustment.amount = _normalize_amount(adjustment.amount, new_kind)
    if "show_in_report" in data:
        obj.show_in_report = bool(data["show_in_report"])
    if "is_advance" in data:
        obj.is_advance = bool(data["is_advance"])

    db.commit()
    db.refresh(obj)
    invalidate_reference_scope(PAYROLL_ADJUSTMENT_TYPES_CACHE_SCOPE)
    return _to_type_public(obj)


@router.delete("/adjustment-types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_adjustment_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _ensure_payroll_manage(current_user)
    obj = db.query(PayrollAdjustmentType).get(type_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adjustment type not found")
    db.delete(obj)
    db.commit()
    invalidate_reference_scope(PAYROLL_ADJUSTMENT_TYPES_CACHE_SCOPE)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/adjustments", response_model=PayrollAdjustmentListResponse)
def list_adjustments(
    user_id: Optional[int] = Query(None),
    responsible_id: Optional[int] = Query(None),
    adjustment_type_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PayrollAdjustmentListResponse:
    _ensure_payroll_view(current_user)
    effective_user_id = _effective_user(db, current_user, user_id)
    allowed_restaurants = get_user_restaurant_ids(db, current_user)

    qry = (
        db.query(PayrollAdjustment)
        .options(
            joinedload(PayrollAdjustment.adjustment_type),
            joinedload(PayrollAdjustment.restaurant),
            joinedload(PayrollAdjustment.responsible),
            joinedload(PayrollAdjustment.user).joinedload(User.role),
            joinedload(PayrollAdjustment.user).joinedload(User.position).joinedload(Position.role),
        )
        .join(PayrollAdjustment.user)
    )
    if effective_user_id is not None:
        qry = qry.filter(PayrollAdjustment.user_id == effective_user_id)
    if responsible_id is not None:
        qry = qry.filter(PayrollAdjustment.responsible_id == responsible_id)
    if adjustment_type_id is not None:
        qry = qry.filter(PayrollAdjustment.adjustment_type_id == adjustment_type_id)
    if date_from is not None:
        qry = qry.filter(PayrollAdjustment.date >= date_from)
    if date_to is not None:
        qry = qry.filter(PayrollAdjustment.date <= date_to)
    if allowed_restaurants is not None:
        if not allowed_restaurants:
            qry = qry.filter(PayrollAdjustment.user_id == current_user.id)
        else:
            qry = qry.filter(
                or_(
                    PayrollAdjustment.user_id == current_user.id,
                    PayrollAdjustment.restaurant_id.in_(allowed_restaurants),
                )
            )

    rows = (
        qry.order_by(PayrollAdjustment.date.desc(), PayrollAdjustment.id.desc())
        .limit(limit)
        .distinct()
        .all()
    )

    items = [
        _to_adjustment_public(a, can_view_amount=can_view_rate(current_user, a.user))
        for a in rows
    ]
    return PayrollAdjustmentListResponse(items=items)


@router.post("/adjustments", response_model=PayrollAdjustmentPublic, status_code=status.HTTP_201_CREATED)
def create_adjustment(
    payload: PayrollAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PayrollAdjustmentPublic:
    ensure_permissions(
        current_user,
        PermissionCode.PAYROLL_MANAGE,
        PermissionCode.STAFF_MANAGE_ALL,
        PermissionCode.STAFF_MANAGE_SUBORDINATES,
    )

    target_user = None
    if payload.user_id != current_user.id:
        target_user = _load_user_with_position(db, payload.user_id)
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not users_share_restaurant(db, current_user, payload.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to the selected restaurants is not allowed",
            )
        ensure_can_manage_user(current_user, target_user)
    elif not has_permission(current_user, PermissionCode.PAYROLL_MANAGE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: payroll management permission required",
        )
    if target_user is None:
        target_user = _load_user_with_position(db, payload.user_id)
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    adjustment_type = db.query(PayrollAdjustmentType).get(payload.adjustment_type_id)
    if not adjustment_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adjustment type not found")

    _ensure_adjustment_restaurant_access(db, target_user, payload.restaurant_id, current_user)

    amount = _normalize_amount(payload.amount, adjustment_type.kind)

    obj = PayrollAdjustment(
        user_id=payload.user_id,
        adjustment_type_id=payload.adjustment_type_id,
        restaurant_id=payload.restaurant_id,
        amount=amount,
        date=payload.date,
        responsible_id=payload.responsible_id,
        comment=payload.comment,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_adjustment_public(obj, can_view_amount=can_view_rate(current_user, target_user))


@router.post("/adjustments/bulk", response_model=PayrollAdjustmentBulkResponse, status_code=status.HTTP_201_CREATED)
def create_adjustments_bulk(
    payload: PayrollAdjustmentBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PayrollAdjustmentBulkResponse:
    # временно только для админов/управления пейроллом
    ensure_permissions(current_user, PermissionCode.SYSTEM_ADMIN, PermissionCode.PAYROLL_MANAGE, PermissionCode.PAYROLL_RESULTS_MANAGE)

    adjustment_type = db.query(PayrollAdjustmentType).get(payload.adjustment_type_id)
    if not adjustment_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adjustment type not found")

    restaurant = db.query(Restaurant).get(payload.restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")

    if payload.period_from > payload.period_to:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period_from must be <= period_to")

    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    if allowed_restaurants is not None and payload.restaurant_id not in allowed_restaurants:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access to the selected restaurants is not allowed")

    staff_codes = [r.staff_code.strip() for r in payload.rows if r.staff_code and str(r.staff_code).strip()]
    if not staff_codes:
        return PayrollAdjustmentBulkResponse(created_count=0)

    users_by_staff = {
        u.staff_code: u
        for u in db.query(User).filter(User.staff_code.in_(staff_codes)).all()
        if u.staff_code
    }

    existing_q = (
        db.query(PayrollAdjustment.user_id)
        .filter(PayrollAdjustment.restaurant_id == payload.restaurant_id)
        .filter(PayrollAdjustment.adjustment_type_id == payload.adjustment_type_id)
        .filter(PayrollAdjustment.date == payload.date)
    )
    existing_map = {row.user_id for row in existing_q.all()}

    skipped: list[PayrollAdjustmentBulkResultItem] = []
    errors: list[PayrollAdjustmentBulkResultItem] = []
    to_create: list[PayrollAdjustment] = []

    for row in payload.rows:
        staff_code = (row.staff_code or "").strip()
        if not staff_code:
            errors.append(PayrollAdjustmentBulkResultItem(staff_code="", reason="Пустой табельный код"))
            continue

        user = users_by_staff.get(staff_code)
        if not user:
            errors.append(PayrollAdjustmentBulkResultItem(staff_code=staff_code, reason="Сотрудник не найден"))
            continue

        try:
            _ensure_adjustment_restaurant_access(db, user, payload.restaurant_id, current_user)
        except HTTPException as exc:
            errors.append(PayrollAdjustmentBulkResultItem(staff_code=staff_code, user_id=user.id, reason=f"Нет доступа: {exc.detail}"))
            continue

        if user.id in existing_map:
            skipped.append(PayrollAdjustmentBulkResultItem(staff_code=staff_code, user_id=user.id, reason="Уже существует запись на эту дату/тип/ресторан"))
            continue
        amount = _normalize_amount(row.amount, adjustment_type.kind)
        to_create.append(
            PayrollAdjustment(
                user_id=user.id,
                adjustment_type_id=payload.adjustment_type_id,
                restaurant_id=payload.restaurant_id,
                amount=amount,
                date=payload.date,
                responsible_id=current_user.id,
                comment=payload.comment,
            )
        )

    created_count = 0
    if to_create and not payload.dry_run:
        db.bulk_save_objects(to_create)
        db.commit()
        created_count = len(to_create)
    elif payload.dry_run:
        created_count = len(to_create)

    return PayrollAdjustmentBulkResponse(
        created_count=created_count,
        skipped=skipped,
        errors=errors,
    )


@router.put("/adjustments/{adjustment_id}", response_model=PayrollAdjustmentPublic)
def update_adjustment(
    adjustment_id: int,
    payload: PayrollAdjustmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PayrollAdjustmentPublic:
    obj = db.query(PayrollAdjustment).get(adjustment_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adjustment not found")

    ensure_permissions(
        current_user,
        PermissionCode.PAYROLL_MANAGE,
        PermissionCode.STAFF_MANAGE_ALL,
        PermissionCode.STAFF_MANAGE_SUBORDINATES,
    )

    target_user = _load_user_with_position(db, obj.user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if obj.user_id != current_user.id:
        if not users_share_restaurant(db, current_user, obj.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to the selected restaurants is not allowed",
            )
        ensure_can_manage_user(current_user, target_user)
    elif not has_permission(current_user, PermissionCode.PAYROLL_MANAGE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: payroll management permission required",
        )

    data = payload.model_dump(exclude_unset=True)
    new_type = None
    if "adjustment_type_id" in data:
        new_type = db.query(PayrollAdjustmentType).get(data["adjustment_type_id"])
        if not new_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adjustment type not found")
        obj.adjustment_type_id = data["adjustment_type_id"]
        obj.adjustment_type = new_type

    target_type = new_type or obj.adjustment_type
    if target_type is None:
        target_type = db.query(PayrollAdjustmentType).get(obj.adjustment_type_id)
        if not target_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adjustment type not found")
        obj.adjustment_type = target_type

    if "amount" in data:
        obj.amount = _normalize_amount(data["amount"], target_type.kind)
    elif new_type is not None:
        obj.amount = _normalize_amount(obj.amount, target_type.kind)
    if "restaurant_id" in data:
        _ensure_adjustment_restaurant_access(db, target_user, data["restaurant_id"], current_user)
        obj.restaurant_id = data["restaurant_id"]
    elif obj.restaurant_id is not None:
        _ensure_adjustment_restaurant_access(db, target_user, obj.restaurant_id, current_user)
    if "date" in data:
        obj.date = data["date"]
    if "responsible_id" in data:
        obj.responsible_id = data["responsible_id"]
    if "comment" in data:
        obj.comment = data["comment"]

    db.commit()
    db.refresh(obj)
    return _to_adjustment_public(obj, can_view_amount=can_view_rate(current_user, target_user))


@router.delete("/adjustments/{adjustment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_adjustment(
    adjustment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    obj = db.query(PayrollAdjustment).get(adjustment_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adjustment not found")

    ensure_permissions(
        current_user,
        PermissionCode.PAYROLL_MANAGE,
        PermissionCode.STAFF_MANAGE_ALL,
        PermissionCode.STAFF_MANAGE_SUBORDINATES,
    )

    target_user = _load_user_with_position(db, obj.user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if obj.user_id != current_user.id:
        if not users_share_restaurant(db, current_user, obj.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to the selected restaurants is not allowed",
            )
        ensure_can_manage_user(current_user, target_user)
    elif not has_permission(current_user, PermissionCode.PAYROLL_MANAGE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: payroll management permission required",
        )

    if obj.restaurant_id is not None:
        _ensure_adjustment_restaurant_access(db, target_user, obj.restaurant_id, current_user)

    db.delete(obj)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
