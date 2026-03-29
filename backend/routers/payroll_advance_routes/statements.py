from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, status

from . import common as c

router = APIRouter()


@router.get("/{statement_id}", response_model=c.PayrollAdvanceStatementPublic)
def get_statement(
    statement_id: int,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    c._ensure_view(current_user)
    statement = c._load_statement(db, statement_id)
    c._ensure_restaurant_access(db, current_user, statement.restaurant_id)
    return c._statement_to_public(db, statement)


@router.post("/", response_model=c.PayrollAdvanceStatementPublic, status_code=status.HTTP_201_CREATED)
def create_statement(
    payload: c.PayrollAdvanceCreateRequest,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    c._ensure_create(current_user)
    if payload.date_to < payload.date_from:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="date_to must be >= date_from")
    c._ensure_restaurant_access(db, current_user, payload.restaurant_id)

    statement_kind = payload.statement_kind or "advance"
    default_salary_percent = 100 if statement_kind == "salary" else 50
    salary_percent = payload.salary_percent if payload.salary_percent is not None else default_salary_percent
    calc = c.calculate_advance_rows(
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

    statement = c.PayrollAdvanceStatement(
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
        statement.items.append(c.PayrollAdvanceItem(**c.payroll_row_to_item_payload(row)))

    db.add(statement)
    db.commit()
    db.refresh(statement)
    return c._statement_to_public(db, statement)


@router.post("/{statement_id}/refresh", response_model=c.PayrollAdvanceStatementPublic)
def refresh_statement(
    statement_id: int,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    c._ensure_edit(current_user)
    statement = c._load_statement(db, statement_id)
    c._ensure_restaurant_access(db, current_user, statement.restaurant_id)
    if statement.status in c.LOCKED_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Statement is locked for editing")

    filters = statement.filters or {}
    calc = c.calculate_advance_rows(
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
            return str(raw.quantize(c.MONEY_QUANT, rounding=ROUND_HALF_UP))
        except Exception:
            return str(value)

    def _item_key(item: c.PayrollAdvanceItem) -> tuple[int, int | None, str | None]:
        return (item.user_id, item.position_id, _rate_key(item.rate))

    def _payload_key(payload: dict) -> tuple[int, int | None, str | None]:
        return (int(payload["user_id"]), payload.get("position_id"), _rate_key(payload.get("rate")))

    existing_by_key: dict[tuple[int, int | None, str | None], list[c.PayrollAdvanceItem]] = {}
    for item in statement.items:
        existing_by_key.setdefault(_item_key(item), []).append(item)

    for row in calc.rows:
        payload = c.payroll_row_to_item_payload(row)
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
                item.comment = c._merge_fire_comment(item.comment, row.user.fire_date)
            if not item.manual:
                item.final_amount = payload["calculated_amount"]
        else:
            statement.items.append(c.PayrollAdvanceItem(**payload))

    for items in existing_by_key.values():
        for item in items:
            db.delete(item)

    statement.updated_at = datetime.utcnow()
    statement.updated_by_id = current_user.id
    db.commit()
    db.refresh(statement)
    return c._statement_to_public(db, statement)
