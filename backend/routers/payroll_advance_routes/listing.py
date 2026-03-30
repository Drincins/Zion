from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException, status

from . import common as c

router = APIRouter()


@router.get("/options")
def list_advance_options(
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    c._ensure_view(current_user)
    query = db.query(c.Restaurant).order_by(
        c.func.lower(c.Restaurant.name).nullslast(),
        c.Restaurant.id.asc(),
    )
    allowed = c._allowed_restaurant_ids(db, current_user)
    if allowed is not None:
        if allowed:
            query = query.filter(c.Restaurant.id.in_(allowed))
        else:
            query = query.filter(False)
    restaurants = query.all()
    return {
        "restaurants": [
            {"id": item.id, "name": item.name or f"Restaurant #{item.id}"}
            for item in restaurants
            if item.id is not None
        ]
    }


@router.get("/", response_model=c.PayrollAdvanceListResponse)
def list_statements(
    restaurant_id: int | None = Query(default=None),
    month: str | None = Query(default=None),
    statuses: list[str] = Query(default_factory=list),
    sort_by: str = Query(default="created_at"),
    sort_direction: str = Query(default="desc"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=24, ge=1, le=100),
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    c._ensure_view(current_user)
    if restaurant_id is not None:
        c._ensure_restaurant_access(db, current_user, restaurant_id)

    q = (
        db.query(c.PayrollAdvanceStatement)
        .options(
            c.joinedload(c.PayrollAdvanceStatement.restaurant),
            c.joinedload(c.PayrollAdvanceStatement.subdivision),
        )
    )
    allowed = c._allowed_restaurant_ids(db, current_user)
    if allowed is not None:
        if allowed:
            q = q.filter(c.PayrollAdvanceStatement.restaurant_id.in_(allowed))
        else:
            q = q.filter(False)

    if restaurant_id is not None:
        q = q.filter(c.PayrollAdvanceStatement.restaurant_id == restaurant_id)

    normalized_statuses = sorted({str(value).strip().lower() for value in statuses if str(value).strip()})
    status_expr = c.func.lower(c.cast(c.PayrollAdvanceStatement.status, c.String))
    if normalized_statuses:
        q = q.filter(status_expr.in_(normalized_statuses))

    if month:
        try:
            year_raw, month_raw = str(month).split("-", 1)
            year = int(year_raw)
            month_number = int(month_raw)
            month_start = date(year, month_number, 1)
            if month_number == 12:
                next_month = date(year + 1, 1, 1)
            else:
                next_month = date(year, month_number + 1, 1)
            month_end = next_month - timedelta(days=1)
            q = q.filter(
                c.PayrollAdvanceStatement.date_from <= month_end,
                c.PayrollAdvanceStatement.date_to >= month_start,
            )
        except (TypeError, ValueError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid month format")

    normalized_sort_by = str(sort_by or "created_at").strip().lower()
    normalized_sort_direction = str(sort_direction or "desc").strip().lower()
    if normalized_sort_direction not in {"asc", "desc"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid sort direction")

    total = q.order_by(None).count()

    if normalized_sort_by == "restaurant_name":
        q = q.outerjoin(c.Restaurant, c.Restaurant.id == c.PayrollAdvanceStatement.restaurant_id)
        order_column = c.func.lower(c.Restaurant.name)
    elif normalized_sort_by == "date_from":
        order_column = c.PayrollAdvanceStatement.date_from
    elif normalized_sort_by == "date_to":
        order_column = c.PayrollAdvanceStatement.date_to
    elif normalized_sort_by == "status":
        order_column = status_expr
    else:
        order_column = c.PayrollAdvanceStatement.created_at

    if normalized_sort_direction == "asc":
        q = q.order_by(order_column.asc().nullslast(), c.PayrollAdvanceStatement.id.asc())
    else:
        q = q.order_by(order_column.desc().nullslast(), c.PayrollAdvanceStatement.id.desc())

    statements = q.offset(offset).limit(limit).all()
    next_offset = offset + len(statements)
    has_more = next_offset < total
    return c.PayrollAdvanceListResponse(
        items=[
            c._statement_to_public(db, s, include_items=False, include_adjustment_summaries=False)
            for s in statements
        ],
        total=total,
        offset=offset,
        limit=limit,
        next_offset=next_offset if has_more else None,
        has_more=has_more,
    )


@router.get("/lookup", response_model=c.PayrollAdvanceListResponse)
def lookup_statements(
    ids: list[int] = Query(default_factory=list),
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    c._ensure_view(current_user)

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
        return c.PayrollAdvanceListResponse(items=[], total=0, offset=0, limit=0, next_offset=None, has_more=False)
    if len(ordered_ids) > 500:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Too many statement ids")

    q = (
        db.query(c.PayrollAdvanceStatement)
        .options(
            c.joinedload(c.PayrollAdvanceStatement.restaurant),
            c.joinedload(c.PayrollAdvanceStatement.subdivision),
        )
        .filter(c.PayrollAdvanceStatement.id.in_(ordered_ids))
    )
    allowed = c._allowed_restaurant_ids(db, current_user)
    if allowed is not None:
        if allowed:
            q = q.filter(c.PayrollAdvanceStatement.restaurant_id.in_(allowed))
        else:
            q = q.filter(False)

    statements = q.all()
    by_id = {int(statement.id): statement for statement in statements if statement.id is not None}
    items = [
        c._statement_to_public(db, by_id[statement_id], include_items=False, include_adjustment_summaries=False)
        for statement_id in ordered_ids
        if statement_id in by_id
    ]
    total = len(items)
    return c.PayrollAdvanceListResponse(
        items=items,
        total=total,
        offset=0,
        limit=total,
        next_offset=None,
        has_more=False,
    )


@router.get("/totals", response_model=c.PayrollAdvanceStatementTotalsResponse)
def get_statement_totals(
    ids: list[int] = Query(default_factory=list),
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
) -> c.PayrollAdvanceStatementTotalsResponse:
    c._ensure_view(current_user)

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
        return c.PayrollAdvanceStatementTotalsResponse(items=[], missing_ids=[])
    if len(ordered_ids) > 500:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Too many statement ids")

    statements_q = db.query(c.PayrollAdvanceStatement.id).filter(c.PayrollAdvanceStatement.id.in_(ordered_ids))
    allowed = c._allowed_restaurant_ids(db, current_user)
    if allowed is not None:
        if allowed:
            statements_q = statements_q.filter(c.PayrollAdvanceStatement.restaurant_id.in_(allowed))
        else:
            statements_q = statements_q.filter(False)

    accessible_ids = {int(row.id) for row in statements_q.all() if row.id is not None}
    if not accessible_ids:
        return c.PayrollAdvanceStatementTotalsResponse(items=[], missing_ids=ordered_ids)

    totals_rows = (
        db.query(
            c.PayrollAdvanceItem.statement_id.label("statement_id"),
            c.func.count(c.PayrollAdvanceItem.id).label("row_count"),
            c.func.coalesce(c.func.sum(c.PayrollAdvanceItem.accrual_amount), 0).label("accrual_total"),
            c.func.coalesce(c.func.sum(c.PayrollAdvanceItem.deduction_amount), 0).label("deduction_total"),
            c.func.coalesce(c.func.sum(c.PayrollAdvanceItem.final_amount), 0).label("final_total"),
            c.func.coalesce(
                c.func.sum(c.case((c.PayrollAdvanceItem.accrual_amount > 0, 1), else_=0)),
                0,
            ).label("accrual_rows_count"),
            c.func.coalesce(
                c.func.sum(c.case((c.PayrollAdvanceItem.deduction_amount > 0, 1), else_=0)),
                0,
            ).label("deduction_rows_count"),
        )
        .filter(c.PayrollAdvanceItem.statement_id.in_(accessible_ids))
        .group_by(c.PayrollAdvanceItem.statement_id)
        .all()
    )

    totals_by_statement_id = {
        int(row.statement_id): row
        for row in totals_rows
        if getattr(row, "statement_id", None) is not None
    }

    items: list[c.PayrollAdvanceStatementTotalsPublic] = []
    for statement_id in ordered_ids:
        if statement_id not in accessible_ids:
            continue
        row = totals_by_statement_id.get(statement_id)
        if not row:
            items.append(
                c.PayrollAdvanceStatementTotalsPublic(
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
            c.PayrollAdvanceStatementTotalsPublic(
                statement_id=statement_id,
                row_count=int(getattr(row, "row_count", 0) or 0),
                accrual_total=float(c._quantize_money(c._decimal(getattr(row, "accrual_total", 0)))),
                deduction_total=float(c._quantize_money(c._decimal(getattr(row, "deduction_total", 0)))),
                final_total=float(c._quantize_money(c._decimal(getattr(row, "final_total", 0)))),
                accrual_rows_count=int(getattr(row, "accrual_rows_count", 0) or 0),
                deduction_rows_count=int(getattr(row, "deduction_rows_count", 0) or 0),
            )
        )

    missing_ids = [statement_id for statement_id in ordered_ids if statement_id not in accessible_ids]
    return c.PayrollAdvanceStatementTotalsResponse(items=items, missing_ids=missing_ids)
