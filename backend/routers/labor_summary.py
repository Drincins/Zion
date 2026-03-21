from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from backend.bd.database import get_db
from backend.bd.iiko_catalog import IikoPaymentMethod
from backend.bd.iiko_sales import IikoSaleItem, IikoSaleOrder
from backend.bd.models import (
    Attendance,
    LaborSummarySettings,
    PaymentFormat,
    PayrollAdjustment,
    PayrollAdjustmentType,
    Position,
    Restaurant,
    RestaurantSubdivision,
    User,
)
from backend.schemas import (
    LaborSummaryOptionPosition,
    LaborSummaryOptionSubdivision,
    LaborSummaryOptionsResponse,
    LaborSummarySettingsPublic,
    LaborSummarySettingsUpdate,
    LaborSummaryPosition,
    LaborSummarySubdivision,
    LaborSummaryTotals,
    LaborSummaryResponse,
)
from backend.services.attendance_calculations import (
    combine_date_time,
    calc_night_minutes,
)
from backend.services.payroll_calculations import resolve_rate as resolve_payroll_rate
from backend.services.permissions import PermissionCode, has_permission, require_permissions
from backend.services.reference_cache import cached_reference_data
from backend.utils import get_user_restaurant_ids, today_local

router = APIRouter(prefix="/labor-summary", tags=["Labor summary"])

REVENUE_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT = "sum_without_discount"
REVENUE_AMOUNT_MODE_SUM_WITH_DISCOUNT = "sum_with_discount"
REVENUE_AMOUNT_MODE_DISCOUNT_ONLY = "discount_only"
REVENUE_AMOUNT_MODES = {
    REVENUE_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT,
    REVENUE_AMOUNT_MODE_SUM_WITH_DISCOUNT,
    REVENUE_AMOUNT_MODE_DISCOUNT_ONLY,
}


def _normalize_id_list(value) -> list[int]:
    items: list[int] = []
    if not isinstance(value, (list, tuple, set)):
        return items
    for raw in value:
        try:
            parsed = int(raw)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            items.append(parsed)
    return sorted(set(items))


def _default_labor_summary_settings(company_id: Optional[int] = None) -> dict:
    return {
        "company_id": company_id,
        "include_base_cost": True,
        "include_accrual_cost": True,
        "include_deduction_cost": True,
        "accrual_adjustment_type_ids": None,
        "deduction_adjustment_type_ids": None,
        "revenue_real_money_only": True,
        "revenue_exclude_deleted": True,
        "revenue_amount_mode": REVENUE_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT,
        "updated_by_id": None,
        "updated_at": None,
    }


def _serialize_labor_summary_settings(
    entry: Optional[LaborSummarySettings],
    *,
    company_id: Optional[int],
) -> dict:
    if not entry:
        return _default_labor_summary_settings(company_id=company_id)
    return {
        "company_id": company_id,
        "include_base_cost": bool(entry.include_base_cost),
        "include_accrual_cost": bool(entry.include_accrual_cost),
        "include_deduction_cost": bool(entry.include_deduction_cost),
        "accrual_adjustment_type_ids": (
            _normalize_id_list(entry.accrual_adjustment_type_ids)
            if entry.accrual_adjustment_type_ids is not None
            else None
        ),
        "deduction_adjustment_type_ids": (
            _normalize_id_list(entry.deduction_adjustment_type_ids)
            if entry.deduction_adjustment_type_ids is not None
            else None
        ),
        "revenue_real_money_only": bool(entry.revenue_real_money_only),
        "revenue_exclude_deleted": bool(entry.revenue_exclude_deleted),
        "revenue_amount_mode": _normalize_revenue_amount_mode(entry.revenue_amount_mode),
        "updated_by_id": entry.updated_by_id,
        "updated_at": entry.updated_at,
    }


def _month_bounds(day: date) -> tuple[date, date]:
    start = date(day.year, day.month, 1)
    if day.month == 12:
        end = date(day.year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(day.year, day.month + 1, 1) - timedelta(days=1)
    return start, end


def _minutes_to_hours(minutes: int) -> Decimal:
    if minutes <= 0:
        return Decimal("0.00")
    return (Decimal(minutes) / Decimal("60")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _clean_optional_text(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _is_not_deleted_expr(field_expr):
    normalized = func.upper(func.trim(func.coalesce(field_expr, "")))
    return or_(normalized == "", normalized == "NOT_DELETED")


def _normalize_revenue_amount_mode(value: Optional[str]) -> str:
    clean = str(value or "").strip().lower()
    aliases = {
        "": REVENUE_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT,
        "sum": REVENUE_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT,
        "gross": REVENUE_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT,
        REVENUE_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT: REVENUE_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT,
        REVENUE_AMOUNT_MODE_SUM_WITH_DISCOUNT: REVENUE_AMOUNT_MODE_SUM_WITH_DISCOUNT,
        "net": REVENUE_AMOUNT_MODE_SUM_WITH_DISCOUNT,
        REVENUE_AMOUNT_MODE_DISCOUNT_ONLY: REVENUE_AMOUNT_MODE_DISCOUNT_ONLY,
        "discount": REVENUE_AMOUNT_MODE_DISCOUNT_ONLY,
    }
    return aliases.get(clean, clean)


def _resolve_revenue_sum_expr(amount_mode: str):
    discount_abs_expr = func.abs(func.coalesce(IikoSaleItem.discount_sum, 0))
    if amount_mode == REVENUE_AMOUNT_MODE_DISCOUNT_ONLY:
        return discount_abs_expr
    if amount_mode == REVENUE_AMOUNT_MODE_SUM_WITH_DISCOUNT:
        return func.coalesce(IikoSaleItem.sum, 0) - discount_abs_expr
    return func.coalesce(IikoSaleItem.sum, 0)


def _load_real_money_payment_method_maps(
    db: Session,
    *,
    company_id: Optional[int],
) -> tuple[set[str], dict[str, str], int]:
    query = db.query(
        IikoPaymentMethod.guid,
        IikoPaymentMethod.name,
        IikoPaymentMethod.category,
        IikoPaymentMethod.is_active,
    )
    if company_id is not None:
        query = query.filter(
            or_(
                IikoPaymentMethod.company_id == company_id,
                IikoPaymentMethod.company_id.is_(None),
            )
        )
    rows = query.all()

    real_money_guids: set[str] = set()
    guid_by_name: dict[str, str] = {}
    categorized_count = 0
    for guid, name, category, is_active in rows:
        clean_guid = _clean_optional_text(guid)
        clean_name = _clean_optional_text(name)
        clean_category = (_clean_optional_text(category) or "").casefold()
        if not clean_guid:
            continue
        clean_guid_norm = clean_guid.casefold()
        if clean_name:
            guid_by_name.setdefault(clean_name.casefold(), clean_guid_norm)
        if clean_category:
            categorized_count += 1
        if is_active is False:
            continue
        if clean_category == "real_money":
            real_money_guids.add(clean_guid_norm)
    return real_money_guids, guid_by_name, categorized_count


def _calc_revenue_amount(
    db: Session,
    *,
    company_id: Optional[int],
    restaurant_ids: list[int],
    date_from: date,
    date_to: date,
    exclude_deleted_orders: bool,
    real_money_only: bool,
    amount_mode: str,
) -> Decimal:
    normalized_restaurant_ids: set[int] = set()
    for raw in restaurant_ids or []:
        try:
            parsed = int(raw)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            normalized_restaurant_ids.add(parsed)
    normalized_restaurant_ids = sorted(normalized_restaurant_ids)
    if not normalized_restaurant_ids:
        return Decimal("0")

    amount_expr = _resolve_revenue_sum_expr(amount_mode)
    base_q = (
        db.query(IikoSaleItem)
        .join(IikoSaleOrder, IikoSaleOrder.id == IikoSaleItem.order_id)
        .filter(IikoSaleOrder.restaurant_id.in_(normalized_restaurant_ids))
        .filter(IikoSaleOrder.open_date >= date_from, IikoSaleOrder.open_date <= date_to)
    )
    if exclude_deleted_orders:
        is_not_deleted = _is_not_deleted_expr(
            func.coalesce(
                IikoSaleItem.raw_payload["OrderDeleted"].astext,
                IikoSaleOrder.raw_payload["OrderDeleted"].astext,
            )
        ) & _is_not_deleted_expr(
            func.coalesce(
                IikoSaleItem.raw_payload["DeletedWithWriteoff"].astext,
                IikoSaleOrder.raw_payload["DeletedWithWriteoff"].astext,
            )
        )
        base_q = base_q.filter(is_not_deleted)

    if not real_money_only:
        value = base_q.with_entities(func.coalesce(func.sum(amount_expr), 0)).scalar()
        return _dec(value)

    non_cash_id_expr = func.trim(func.coalesce(IikoSaleItem.raw_payload["NonCashPaymentType.Id"].astext, ""))
    non_cash_name_expr = func.trim(func.coalesce(IikoSaleItem.raw_payload["NonCashPaymentType"].astext, ""))
    base_q = base_q.filter(non_cash_id_expr == "").filter(non_cash_name_expr == "")

    payment_guid_expr = func.coalesce(
        IikoSaleItem.raw_payload["PayTypes.GUID"].astext,
        IikoSaleItem.raw_payload["PaymentType.Id"].astext,
        IikoSaleItem.raw_payload["NonCashPaymentType.Id"].astext,
    )
    payment_guid_expr_norm = func.lower(func.trim(func.coalesce(payment_guid_expr, "")))
    payment_name_expr = func.coalesce(
        IikoSaleItem.raw_payload["PayTypes"].astext,
        IikoSaleItem.raw_payload["PaymentType"].astext,
        IikoSaleItem.raw_payload["NonCashPaymentType"].astext,
    )

    grouped_rows = (
        base_q.with_entities(
            payment_guid_expr_norm.label("payment_guid_norm"),
            payment_name_expr.label("payment_name"),
            func.coalesce(func.sum(amount_expr), 0).label("amount"),
        )
        .group_by(payment_guid_expr_norm, payment_name_expr)
        .all()
    )
    if not grouped_rows:
        return Decimal("0")

    real_money_guids, guid_by_name, categorized_count = _load_real_money_payment_method_maps(
        db,
        company_id=company_id,
    )

    if real_money_guids:
        total = Decimal("0")
        for row in grouped_rows:
            raw_guid_norm = _clean_optional_text(getattr(row, "payment_guid_norm", None))
            raw_name = _clean_optional_text(getattr(row, "payment_name", None))
            resolved_guid_norm = raw_guid_norm.casefold() if raw_guid_norm else None
            if not resolved_guid_norm and raw_name:
                resolved_guid_norm = guid_by_name.get(raw_name.casefold())
            if not resolved_guid_norm or resolved_guid_norm not in real_money_guids:
                continue
            total += _dec(getattr(row, "amount", 0))
        return total

    if categorized_count > 0:
        return Decimal("0")

    total = Decimal("0")
    for row in grouped_rows:
        total += _dec(getattr(row, "amount", 0))
    return total


def _calc_variable_amount(
    *,
    rate: Decimal,
    payment_mode: Optional[str],
    minutes: int,
    night_minutes: int,
    hours_per_shift,
    monthly_shift_norm,
    night_bonus_enabled: bool,
    night_bonus_percent,
) -> Decimal:
    if minutes <= 0 or rate <= 0:
        return Decimal("0")
    fact_hours = _dec(minutes) / Decimal("60")
    night_hours = _dec(night_minutes) / Decimal("60") if night_minutes else Decimal("0")

    base_amount = Decimal("0")
    if payment_mode == "hourly":
        base_amount = rate * fact_hours
    elif payment_mode == "shift_norm":
        hps = _dec(hours_per_shift)
        norm = _dec(monthly_shift_norm)
        if hps > 0 and norm > 0:
            fact_shifts = fact_hours / hps
            worked_ratio = min(fact_shifts, norm) / norm
            base_amount = rate * worked_ratio
    base_amount = base_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    night_bonus = Decimal("0")
    night_percent = _dec(night_bonus_percent)
    if night_bonus_enabled and night_percent > 0 and night_hours > 0:
        if payment_mode == "shift_norm":
            hps = _dec(hours_per_shift)
            norm = _dec(monthly_shift_norm)
            if hps > 0 and norm > 0:
                hourly_rate = rate / norm / hps
                night_bonus = hourly_rate * night_hours * (night_percent / Decimal("100"))
        elif payment_mode == "hourly":
            night_bonus = rate * night_hours * (night_percent / Decimal("100"))
        night_bonus = night_bonus.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return base_amount + night_bonus


def _load_labor_summary_options_payload(db: Session) -> dict[str, list[dict]]:
    positions = (
        db.query(Position)
        .order_by(Position.name.asc().nullslast(), Position.id.asc())
        .all()
    )
    subdivisions = (
        db.query(RestaurantSubdivision)
        .order_by(RestaurantSubdivision.name.asc())
        .all()
    )

    return {
        "subdivisions": [
            {
                "id": item.id,
                "name": item.name or f"Subdivision #{item.id}",
            }
            for item in subdivisions
            if item and item.id is not None
        ],
        "positions": [
            {
                "id": item.id,
                "name": item.name or f"Position #{item.id}",
                "restaurant_id": getattr(item, "restaurant_id", None),
                "restaurant_subdivision_id": getattr(item, "restaurant_subdivision_id", None),
            }
            for item in positions
            if item and item.id is not None
        ],
    }


def _resolve_restaurant_with_access(*, db: Session, restaurant_id: int, current_user) -> Restaurant:
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")

    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    if allowed_restaurants is not None and restaurant_id not in allowed_restaurants:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return restaurant


def _resolve_company_restaurant_ids_for_user(
    *,
    db: Session,
    company_id: Optional[int],
    current_user,
) -> list[int]:
    if company_id is None:
        return []

    query = db.query(Restaurant.id).filter(Restaurant.company_id == company_id)
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    if allowed_restaurants is not None:
        if not allowed_restaurants:
            return []
        query = query.filter(Restaurant.id.in_(sorted(allowed_restaurants)))

    return [int(item[0]) for item in query.all() if item and item[0] is not None]


@router.get("/options", response_model=LaborSummaryOptionsResponse)
def get_labor_summary_options(
    restaurant_id: list[int] = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permissions(
            PermissionCode.LABOR_SUMMARY_VIEW,
            PermissionCode.LABOR_SUMMARY_DASHBOARD_VIEW,
        )
    ),
) -> LaborSummaryOptionsResponse:
    restaurant_ids = sorted({int(item) for item in (restaurant_id or []) if item is not None})
    if not restaurant_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="restaurant_id is required")

    existing_restaurant_ids = {
        item[0]
        for item in (
            db.query(Restaurant.id)
            .filter(Restaurant.id.in_(restaurant_ids))
            .all()
        )
        if item and item[0] is not None
    }
    if len(existing_restaurant_ids) != len(restaurant_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")

    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    if allowed_restaurants is not None and any(item not in allowed_restaurants for item in restaurant_ids):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Positions/Subdivisions are shared across restaurants in this schema.
    # We still require restaurant_id(s) for access checking, but the option lists
    # are global and used only for filtering the labor summary request.
    payload = cached_reference_data(
        "labor-summary-options",
        key="global",
        loader=lambda: _load_labor_summary_options_payload(db),
        ttl_seconds=120,
    )
    return LaborSummaryOptionsResponse(
        subdivisions=[LaborSummaryOptionSubdivision(**item) for item in payload["subdivisions"]],
        positions=[LaborSummaryOptionPosition(**item) for item in payload["positions"]],
    )


@router.get("/settings", response_model=LaborSummarySettingsPublic)
def get_labor_summary_settings(
    restaurant_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permissions(
            PermissionCode.LABOR_SUMMARY_VIEW,
            PermissionCode.LABOR_SUMMARY_DASHBOARD_VIEW,
        )
    ),
) -> LaborSummarySettingsPublic:
    restaurant = _resolve_restaurant_with_access(db=db, restaurant_id=restaurant_id, current_user=current_user)
    company_id = getattr(restaurant, "company_id", None)
    settings_entry = None
    if company_id is not None:
        settings_entry = (
            db.query(LaborSummarySettings)
            .filter(LaborSummarySettings.company_id == company_id)
            .first()
        )
    payload = _serialize_labor_summary_settings(settings_entry, company_id=company_id)
    return LaborSummarySettingsPublic(**payload)


@router.put("/settings", response_model=LaborSummarySettingsPublic)
def upsert_labor_summary_settings(
    payload: LaborSummarySettingsUpdate,
    restaurant_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(PermissionCode.LABOR_SUMMARY_SETTINGS_MANAGE)),
) -> LaborSummarySettingsPublic:
    restaurant = _resolve_restaurant_with_access(db=db, restaurant_id=restaurant_id, current_user=current_user)
    company_id = getattr(restaurant, "company_id", None)
    if company_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Restaurant must be linked to company",
        )

    normalized_revenue_amount_mode = _normalize_revenue_amount_mode(payload.revenue_amount_mode)
    if normalized_revenue_amount_mode not in REVENUE_AMOUNT_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported revenue_amount_mode: {payload.revenue_amount_mode}",
        )

    normalized_accrual_adjustment_type_ids = (
        None
        if payload.accrual_adjustment_type_ids is None
        else _normalize_id_list(payload.accrual_adjustment_type_ids)
    )
    normalized_deduction_adjustment_type_ids = (
        None
        if payload.deduction_adjustment_type_ids is None
        else _normalize_id_list(payload.deduction_adjustment_type_ids)
    )
    requested_adjustment_type_ids = set(normalized_accrual_adjustment_type_ids or []) | set(
        normalized_deduction_adjustment_type_ids or []
    )

    if requested_adjustment_type_ids:
        kind_by_type_id = {
            int(type_id): str(kind)
            for type_id, kind in (
                db.query(PayrollAdjustmentType.id, PayrollAdjustmentType.kind)
                .filter(PayrollAdjustmentType.id.in_(sorted(requested_adjustment_type_ids)))
                .all()
            )
        }
        missing_type_ids = sorted(requested_adjustment_type_ids - set(kind_by_type_id.keys()))
        if missing_type_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown adjustment type ids: {', '.join(str(item) for item in missing_type_ids)}",
            )
        invalid_accrual_type_ids = [
            type_id
            for type_id in (normalized_accrual_adjustment_type_ids or [])
            if kind_by_type_id.get(type_id) != "accrual"
        ]
        if invalid_accrual_type_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "accrual_adjustment_type_ids must reference accrual types: "
                    + ", ".join(str(item) for item in invalid_accrual_type_ids)
                ),
            )
        invalid_deduction_type_ids = [
            type_id
            for type_id in (normalized_deduction_adjustment_type_ids or [])
            if kind_by_type_id.get(type_id) != "deduction"
        ]
        if invalid_deduction_type_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "deduction_adjustment_type_ids must reference deduction types: "
                    + ", ".join(str(item) for item in invalid_deduction_type_ids)
                ),
            )

    settings_entry = (
        db.query(LaborSummarySettings)
        .filter(LaborSummarySettings.company_id == company_id)
        .first()
    )
    if not settings_entry:
        settings_entry = LaborSummarySettings(company_id=company_id)
        db.add(settings_entry)

    settings_entry.include_base_cost = payload.include_base_cost
    settings_entry.include_accrual_cost = payload.include_accrual_cost
    settings_entry.include_deduction_cost = payload.include_deduction_cost
    settings_entry.accrual_adjustment_type_ids = normalized_accrual_adjustment_type_ids
    settings_entry.deduction_adjustment_type_ids = normalized_deduction_adjustment_type_ids
    settings_entry.revenue_real_money_only = payload.revenue_real_money_only
    settings_entry.revenue_exclude_deleted = payload.revenue_exclude_deleted
    settings_entry.revenue_amount_mode = normalized_revenue_amount_mode
    settings_entry.updated_by_id = getattr(current_user, "id", None)

    db.commit()
    db.refresh(settings_entry)

    response_payload = _serialize_labor_summary_settings(settings_entry, company_id=company_id)
    return LaborSummarySettingsPublic(**response_payload)


@router.get("", response_model=LaborSummaryResponse)
def get_labor_summary(
    restaurant_id: int = Query(...),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    include_positions: bool = Query(False),
    fallback_to_company_revenue_if_zero: bool = Query(False),
    restaurant_subdivision_ids: Optional[list[int]] = Query(None),
    position_ids: Optional[list[int]] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permissions(
            PermissionCode.LABOR_SUMMARY_VIEW,
            PermissionCode.LABOR_SUMMARY_DASHBOARD_VIEW,
        )
    ),
) -> LaborSummaryResponse:
    restaurant = _resolve_restaurant_with_access(db=db, restaurant_id=restaurant_id, current_user=current_user)

    if date_from is None or date_to is None:
        month_start, month_end = _month_bounds(today_local())
        date_from = date_from or month_start
        date_to = date_to or month_end
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be before or equal to date_to",
        )

    company_id = getattr(restaurant, "company_id", None)
    settings_entry = None
    if company_id is not None:
        settings_entry = (
            db.query(LaborSummarySettings)
            .filter(LaborSummarySettings.company_id == company_id)
            .first()
        )
    effective_settings = _serialize_labor_summary_settings(settings_entry, company_id=company_id)

    normalized_revenue_amount_mode = _normalize_revenue_amount_mode(effective_settings["revenue_amount_mode"])
    effective_revenue_real_money_only = bool(effective_settings["revenue_real_money_only"])
    effective_revenue_exclude_deleted = bool(effective_settings["revenue_exclude_deleted"])
    if normalized_revenue_amount_mode not in REVENUE_AMOUNT_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported revenue_amount_mode: {effective_settings['revenue_amount_mode']}",
        )

    settings_accrual_adjustment_type_ids = effective_settings["accrual_adjustment_type_ids"]
    settings_deduction_adjustment_type_ids = effective_settings["deduction_adjustment_type_ids"]
    normalized_accrual_adjustment_type_ids = (
        _normalize_id_list(settings_accrual_adjustment_type_ids)
        if settings_accrual_adjustment_type_ids is not None
        else []
    )
    normalized_deduction_adjustment_type_ids = (
        _normalize_id_list(settings_deduction_adjustment_type_ids)
        if settings_deduction_adjustment_type_ids is not None
        else []
    )
    accrual_none_selected = settings_accrual_adjustment_type_ids is not None and not normalized_accrual_adjustment_type_ids
    deduction_none_selected = (
        settings_deduction_adjustment_type_ids is not None and not normalized_deduction_adjustment_type_ids
    )
    requested_adjustment_type_ids = set(normalized_accrual_adjustment_type_ids) | set(
        normalized_deduction_adjustment_type_ids
    )
    if requested_adjustment_type_ids:
        kind_by_type_id = {
            int(type_id): str(kind)
            for type_id, kind in (
                db.query(PayrollAdjustmentType.id, PayrollAdjustmentType.kind)
                .filter(PayrollAdjustmentType.id.in_(sorted(requested_adjustment_type_ids)))
                .all()
            )
        }
        missing_type_ids = sorted(requested_adjustment_type_ids - set(kind_by_type_id.keys()))
        if missing_type_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown adjustment type ids: {', '.join(str(item) for item in missing_type_ids)}",
            )
        invalid_accrual_type_ids = [
            type_id
            for type_id in normalized_accrual_adjustment_type_ids
            if kind_by_type_id.get(type_id) != "accrual"
        ]
        if invalid_accrual_type_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "accrual_adjustment_type_ids must reference accrual types: "
                    + ", ".join(str(item) for item in invalid_accrual_type_ids)
                ),
            )
        invalid_deduction_type_ids = [
            type_id
            for type_id in normalized_deduction_adjustment_type_ids
            if kind_by_type_id.get(type_id) != "deduction"
        ]
        if invalid_deduction_type_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "deduction_adjustment_type_ids must reference deduction types: "
                    + ", ".join(str(item) for item in invalid_deduction_type_ids)
                ),
            )

    show_cost = has_permission(current_user, PermissionCode.LABOR_SUMMARY_VIEW_FACT)
    show_revenue = (
        has_permission(current_user, PermissionCode.SALES_REPORT_VIEW_MONEY)
        or has_permission(current_user, PermissionCode.IIKO_VIEW)
        or has_permission(current_user, PermissionCode.IIKO_MANAGE)
    )

    today = today_local()
    if date_to > today:
        date_to = today

    if date_from > date_to:
        totals = LaborSummaryTotals(
            hours=0.0,
            night_hours=0.0,
            amount=0.0 if show_cost else None,
            accrual_amount=0.0 if show_cost else None,
            deduction_amount=0.0 if show_cost else None,
            total_cost=0.0 if show_cost else None,
            revenue_amount=0.0 if show_revenue else None,
        )
        return LaborSummaryResponse(
            restaurant_id=restaurant_id,
            date_from=date_from,
            date_to=date_to,
            subdivisions=[],
            totals=totals,
        )

    query = (
        db.query(Attendance)
        .options(
            joinedload(Attendance.position).joinedload(Position.restaurant_subdivision),
            joinedload(Attendance.position).joinedload(Position.payment_format),
        )
        .filter(Attendance.restaurant_id == restaurant_id)
        .filter(Attendance.close_date.isnot(None))
        .filter(Attendance.close_time.isnot(None))
        # Все часы относим к дате открытия смены, как в зарплатном табеле.
        .filter(Attendance.open_date >= date_from, Attendance.open_date <= date_to)
    )

    if position_ids:
        query = query.filter(Attendance.position_id.in_(position_ids))

    if restaurant_subdivision_ids:
        query = query.filter(
            Attendance.position.has(Position.restaurant_subdivision_id.in_(restaurant_subdivision_ids))
        )

    attendances = query.all()

    groups: dict[tuple[int, Optional[int]], dict] = {}

    for attendance in attendances:
        if not attendance.open_date or not attendance.open_time:
            continue
        opened_dt = combine_date_time(attendance.open_date, attendance.open_time)
        closed_dt = combine_date_time(attendance.close_date, attendance.close_time)
        duration_minutes = attendance.duration_minutes
        if duration_minutes is None:
            duration_minutes = int((closed_dt - opened_dt).total_seconds() // 60)
        if duration_minutes <= 0:
            continue
        night_minutes = (
            attendance.night_minutes
            if attendance.night_minutes is not None
            else calc_night_minutes(opened_dt, closed_dt)
        )

        position = attendance.position
        payment_format = getattr(position, "payment_format", None) if position else None
        calc_mode = getattr(payment_format, "calculation_mode", None) if payment_format else None
        payment_mode = calc_mode or "hourly"
        group_key = (attendance.user_id, position.id if position else None)
        group = groups.setdefault(
            group_key,
            {
                "minutes": 0,
                "night_minutes": 0,
                "rate": None,
                "payment_mode": payment_mode,
                "position": position,
                "hours_per_shift": getattr(position, "hours_per_shift", None) if position else None,
                "monthly_shift_norm": getattr(position, "monthly_shift_norm", None) if position else None,
                "night_bonus_enabled": bool(getattr(position, "night_bonus_enabled", False)) if position else False,
                "night_bonus_percent": getattr(position, "night_bonus_percent", None) if position else None,
                "accrual_amount": Decimal("0"),
                "deduction_amount": Decimal("0"),
            },
        )
        group["minutes"] += duration_minutes
        group["night_minutes"] += night_minutes
        rate_value = attendance.rate if attendance.rate is not None else getattr(position, "rate", None)
        if rate_value is not None:
            group["rate"] = rate_value

    if show_cost:
        adjustment_query = (
            db.query(PayrollAdjustment)
            .options(
                joinedload(PayrollAdjustment.adjustment_type),
                joinedload(PayrollAdjustment.user)
                .joinedload(User.position)
                .joinedload(Position.restaurant_subdivision),
                joinedload(PayrollAdjustment.user)
                .joinedload(User.position)
                .joinedload(Position.payment_format),
            )
            .filter(PayrollAdjustment.date >= date_from, PayrollAdjustment.date <= date_to)
        )
        adjustment_query = adjustment_query.filter(PayrollAdjustment.restaurant_id == restaurant_id)

        joined_user_for_adjustments = False
        if position_ids:
            if not joined_user_for_adjustments:
                adjustment_query = adjustment_query.join(PayrollAdjustment.user)
                joined_user_for_adjustments = True
            adjustment_query = adjustment_query.filter(User.position_id.in_(position_ids))

        if restaurant_subdivision_ids:
            if not joined_user_for_adjustments:
                adjustment_query = adjustment_query.join(PayrollAdjustment.user)
                joined_user_for_adjustments = True
            adjustment_query = adjustment_query.join(User.position).filter(
                Position.restaurant_subdivision_id.in_(restaurant_subdivision_ids)
            )

        accrual_filter_requested = settings_accrual_adjustment_type_ids is not None
        deduction_filter_requested = settings_deduction_adjustment_type_ids is not None
        if accrual_filter_requested or deduction_filter_requested:
            type_conditions = []
            if accrual_filter_requested:
                if normalized_accrual_adjustment_type_ids:
                    type_conditions.append(
                        and_(
                            PayrollAdjustmentType.kind == "accrual",
                            PayrollAdjustment.adjustment_type_id.in_(normalized_accrual_adjustment_type_ids),
                        )
                    )
                elif not accrual_none_selected:
                    type_conditions.append(PayrollAdjustmentType.kind == "accrual")
            else:
                type_conditions.append(PayrollAdjustmentType.kind == "accrual")

            if deduction_filter_requested:
                if normalized_deduction_adjustment_type_ids:
                    type_conditions.append(
                        and_(
                            PayrollAdjustmentType.kind == "deduction",
                            PayrollAdjustment.adjustment_type_id.in_(normalized_deduction_adjustment_type_ids),
                        )
                    )
                elif not deduction_none_selected:
                    type_conditions.append(PayrollAdjustmentType.kind == "deduction")
            else:
                type_conditions.append(PayrollAdjustmentType.kind == "deduction")

            if type_conditions:
                adjustment_query = adjustment_query.join(PayrollAdjustment.adjustment_type).filter(or_(*type_conditions))
            else:
                adjustment_query = adjustment_query.filter(PayrollAdjustment.id == -1)

        adjustments = adjustment_query.all()
        for adjustment in adjustments:
            user = adjustment.user
            position = user.position if user else None
            payment_format = getattr(position, "payment_format", None) if position else None
            calc_mode = getattr(payment_format, "calculation_mode", None) if payment_format else None
            payment_mode = calc_mode or "hourly"

            group_key = (adjustment.user_id, position.id if position else None)
            group = groups.setdefault(
                group_key,
                {
                    "minutes": 0,
                    "night_minutes": 0,
                    "rate": None,
                    "payment_mode": payment_mode,
                    "position": position,
                    "hours_per_shift": getattr(position, "hours_per_shift", None) if position else None,
                    "monthly_shift_norm": getattr(position, "monthly_shift_norm", None) if position else None,
                    "night_bonus_enabled": bool(getattr(position, "night_bonus_enabled", False)) if position else False,
                    "night_bonus_percent": getattr(position, "night_bonus_percent", None) if position else None,
                    "accrual_amount": Decimal("0"),
                    "deduction_amount": Decimal("0"),
                },
            )

            adjustment_type = adjustment.adjustment_type
            signed_amount = _dec(adjustment.amount)
            # Align with payroll export logic: legacy deductions may be stored as positive.
            if adjustment_type and adjustment_type.kind == "deduction" and signed_amount > 0:
                signed_amount *= Decimal("-1")
            if signed_amount < 0:
                group["deduction_amount"] += abs(signed_amount)
            else:
                group["accrual_amount"] += signed_amount

    subdivisions: dict[tuple[Optional[int], str], dict] = {}

    for group in groups.values():
        position = group["position"]
        subdivision = position.restaurant_subdivision if position else None
        subdivision_id = subdivision.id if subdivision else None
        subdivision_name = subdivision.name if subdivision else "Unassigned"
        sub_key = (subdivision_id, subdivision_name)

        sub_entry = subdivisions.setdefault(
            sub_key,
            {
                "minutes": 0,
                "night_minutes": 0,
                "amount": Decimal("0"),
                "accrual_amount": Decimal("0"),
                "deduction_amount": Decimal("0"),
                "positions": {},
            },
        )
        sub_entry["minutes"] += group["minutes"]
        sub_entry["night_minutes"] += group["night_minutes"]

        amount = Decimal("0")
        if show_cost and group["payment_mode"] != "fixed":
            amount = _calc_variable_amount(
                rate=_dec(group["rate"]),
                payment_mode=group["payment_mode"],
                minutes=group["minutes"],
                night_minutes=group["night_minutes"],
                hours_per_shift=group["hours_per_shift"],
                monthly_shift_norm=group["monthly_shift_norm"],
                night_bonus_enabled=group["night_bonus_enabled"],
                night_bonus_percent=group["night_bonus_percent"],
            )
            sub_entry["amount"] += _dec(amount)

        if show_cost:
            sub_entry["accrual_amount"] += _dec(group.get("accrual_amount", 0))
            sub_entry["deduction_amount"] += _dec(group.get("deduction_amount", 0))

        if include_positions:
            pos_id = position.id if position else None
            pos_name = position.name if position else "Unassigned"
            pos_key = (pos_id, pos_name)
            pos_entry = sub_entry["positions"].setdefault(
                pos_key,
                {
                    "minutes": 0,
                    "night_minutes": 0,
                    "amount": Decimal("0"),
                    "accrual_amount": Decimal("0"),
                    "deduction_amount": Decimal("0"),
                },
            )
            pos_entry["minutes"] += group["minutes"]
            pos_entry["night_minutes"] += group["night_minutes"]
            if show_cost and group["payment_mode"] != "fixed":
                pos_entry["amount"] += _dec(amount)
            if show_cost:
                pos_entry["accrual_amount"] += _dec(group.get("accrual_amount", 0))
                pos_entry["deduction_amount"] += _dec(group.get("deduction_amount", 0))

    if show_cost:
        fixed_users = (
            db.query(User)
            .join(User.position)
            .join(Position.payment_format)
            .options(
                joinedload(User.position)
                .joinedload(Position.restaurant_subdivision),
                joinedload(User.position)
                .joinedload(Position.payment_format),
                selectinload(User.restaurants),
            )
            .filter(User.position_id.isnot(None))
            .filter(PaymentFormat.calculation_mode == "fixed")
            .filter(
                or_(
                    User.workplace_restaurant_id == restaurant_id,
                    User.workplace_restaurant_id.is_(None),
                )
            )
        )
        if position_ids:
            fixed_users = fixed_users.filter(User.position_id.in_(position_ids))
        if restaurant_subdivision_ids:
            fixed_users = fixed_users.filter(Position.restaurant_subdivision_id.in_(restaurant_subdivision_ids))
        fixed_users = fixed_users.all()
        for user in fixed_users:
            position = user.position
            payment_format = getattr(position, "payment_format", None) if position else None
            if not payment_format or payment_format.calculation_mode != "fixed":
                continue
            restaurant_for_user = user.workplace_restaurant_id
            if restaurant_for_user is None and user.restaurants:
                if len(user.restaurants) == 1:
                    restaurant_for_user = user.restaurants[0].id
            if restaurant_for_user != restaurant_id:
                continue
            rate = resolve_payroll_rate(
                user,
                position,
                "fixed",
                stats_rate=None,
            )
            if rate <= 0:
                continue
            # Keep fixed salary consistent with payroll statements:
            # full fixed rate for the period row, without extra date proration by hire/fire.
            fixed_amount = rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if fixed_amount <= 0:
                continue

            subdivision = position.restaurant_subdivision if position else None
            subdivision_id = subdivision.id if subdivision else None
            subdivision_name = subdivision.name if subdivision else "Unassigned"
            sub_key = (subdivision_id, subdivision_name)
            sub_entry = subdivisions.setdefault(
                sub_key,
                {
                    "minutes": 0,
                    "night_minutes": 0,
                    "amount": Decimal("0"),
                    "accrual_amount": Decimal("0"),
                    "deduction_amount": Decimal("0"),
                    "positions": {},
                },
            )
            sub_entry["amount"] += fixed_amount

            if include_positions:
                pos_id = position.id if position else None
                pos_name = position.name if position else "Unassigned"
                pos_key = (pos_id, pos_name)
                pos_entry = sub_entry["positions"].setdefault(
                    pos_key,
                    {
                        "minutes": 0,
                        "night_minutes": 0,
                        "amount": Decimal("0"),
                        "accrual_amount": Decimal("0"),
                        "deduction_amount": Decimal("0"),
                    },
                )
                pos_entry["amount"] += fixed_amount

    def _amount_or_none(value: Decimal) -> Optional[float]:
        if not show_cost:
            return None
        return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    subdivisions_items: list[LaborSummarySubdivision] = []
    total_minutes = 0
    total_night_minutes = 0
    total_amount = Decimal("0")
    total_accrual_amount = Decimal("0")
    total_deduction_amount = Decimal("0")

    for (subdivision_id, subdivision_name), data in sorted(
        subdivisions.items(), key=lambda item: (item[0][1] or "", item[0][0] or 0)
    ):
        minutes = data["minutes"]
        night_minutes = data["night_minutes"]
        amount = data["amount"]
        accrual_amount = data["accrual_amount"]
        deduction_amount = data["deduction_amount"]
        total_minutes += minutes
        total_night_minutes += night_minutes
        total_amount += amount
        total_accrual_amount += accrual_amount
        total_deduction_amount += deduction_amount

        positions_items = None
        if include_positions:
            positions_items = []
            for (pos_id, pos_name), pos_data in sorted(
                data["positions"].items(), key=lambda item: (item[0][1] or "", item[0][0] or 0)
            ):
                position_amount = pos_data["amount"]
                position_accrual = pos_data["accrual_amount"]
                position_deduction = pos_data["deduction_amount"]
                positions_items.append(
                    LaborSummaryPosition(
                        position_id=pos_id,
                        position_name=pos_name,
                        hours=float(_minutes_to_hours(pos_data["minutes"])),
                        night_hours=float(_minutes_to_hours(pos_data["night_minutes"])),
                        amount=_amount_or_none(position_amount),
                        accrual_amount=_amount_or_none(position_accrual),
                        deduction_amount=_amount_or_none(position_deduction),
                        total_cost=_amount_or_none(position_amount + position_accrual - position_deduction),
                    )
                )

        subdivisions_items.append(
            LaborSummarySubdivision(
                subdivision_id=subdivision_id,
                subdivision_name=subdivision_name,
                hours=float(_minutes_to_hours(minutes)),
                night_hours=float(_minutes_to_hours(night_minutes)),
                amount=_amount_or_none(amount),
                accrual_amount=_amount_or_none(accrual_amount),
                deduction_amount=_amount_or_none(deduction_amount),
                total_cost=_amount_or_none(amount + accrual_amount - deduction_amount),
                positions=positions_items,
            )
        )

    revenue_amount = None
    if show_revenue:
        revenue_amount = _calc_revenue_amount(
            db,
            company_id=getattr(restaurant, "company_id", None),
            restaurant_ids=[restaurant_id],
            date_from=date_from,
            date_to=date_to,
            exclude_deleted_orders=effective_revenue_exclude_deleted,
            real_money_only=effective_revenue_real_money_only,
            amount_mode=normalized_revenue_amount_mode,
        )
        if fallback_to_company_revenue_if_zero and revenue_amount <= 0:
            company_restaurant_ids = _resolve_company_restaurant_ids_for_user(
                db=db,
                company_id=getattr(restaurant, "company_id", None),
                current_user=current_user,
            )
            if company_restaurant_ids:
                company_revenue_amount = _calc_revenue_amount(
                    db,
                    company_id=getattr(restaurant, "company_id", None),
                    restaurant_ids=company_restaurant_ids,
                    date_from=date_from,
                    date_to=date_to,
                    exclude_deleted_orders=effective_revenue_exclude_deleted,
                    real_money_only=effective_revenue_real_money_only,
                    amount_mode=normalized_revenue_amount_mode,
                )
                if company_revenue_amount > 0:
                    revenue_amount = company_revenue_amount

    totals = LaborSummaryTotals(
        hours=float(_minutes_to_hours(total_minutes)),
        night_hours=float(_minutes_to_hours(total_night_minutes)),
        amount=_amount_or_none(total_amount),
        accrual_amount=_amount_or_none(total_accrual_amount),
        deduction_amount=_amount_or_none(total_deduction_amount),
        total_cost=_amount_or_none(total_amount + total_accrual_amount - total_deduction_amount),
        revenue_amount=float(revenue_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        if revenue_amount is not None
        else None,
    )

    return LaborSummaryResponse(
        restaurant_id=restaurant_id,
        date_from=date_from,
        date_to=date_to,
        subdivisions=subdivisions_items,
        totals=totals,
    )
