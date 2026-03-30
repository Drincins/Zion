from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from . import common as c

router = APIRouter()


def _parse_month_range(month: str | None) -> tuple[datetime.date, datetime.date] | None:
    if not month:
        return None
    try:
        start = datetime.strptime(month, "%Y-%m").date().replace(day=1)
    except ValueError:
        return None
    next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    end = next_month - timedelta(days=1)
    return start, end


def _consolidated_to_public(
    stmt: c.PayrollAdvanceConsolidatedStatement,
) -> c.PayrollAdvanceConsolidatedPublic:
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
    return c.PayrollAdvanceConsolidatedPublic(
        id=stmt.id,
        title=stmt.title,
        date_from=stmt.date_from,
        date_to=stmt.date_to,
        statement_ids=ordered_ids,
        created_by_id=stmt.created_by_id,
        created_at=stmt.created_at,
        updated_at=stmt.updated_at,
    )


@router.get("/consolidated", response_model=c.PayrollAdvanceConsolidatedListResponse)
def list_consolidated(
    restaurant_id: int | None = None,
    month: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=24, ge=1, le=100),
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    c._ensure_download(current_user)
    q = db.query(c.PayrollAdvanceConsolidatedStatement).order_by(
        c.PayrollAdvanceConsolidatedStatement.created_at.desc()
    )
    if not c.has_global_access(current_user) and not c.has_permission(
        current_user, c.PermissionCode.PAYROLL_ADVANCE_DELETE
    ):
        q = q.filter(c.PayrollAdvanceConsolidatedStatement.created_by_id == current_user.id)
    items = q.all()

    month_range = _parse_month_range(month)
    if month_range:
        start, end = month_range
        items = [
            item
            for item in items
            if item.date_from <= end and item.date_to >= start
        ]

    if restaurant_id is not None:
        statement_ids: set[int] = set()
        for item in items:
            for raw_id in item.statement_ids or []:
                try:
                    stmt_id = int(raw_id)
                except (TypeError, ValueError):
                    continue
                statement_ids.add(stmt_id)

        statement_restaurants: dict[int, int | None] = {}
        if statement_ids:
            rows = (
                db.query(c.PayrollAdvanceStatement.id, c.PayrollAdvanceStatement.restaurant_id)
                .filter(c.PayrollAdvanceStatement.id.in_(statement_ids))
                .all()
            )
            statement_restaurants = {
                int(row.id): row.restaurant_id
                for row in rows
                if row.id is not None
            }

        items = [
            item
            for item in items
            if any(
                statement_restaurants.get(stmt_id) == restaurant_id
                for stmt_id in _consolidated_to_public(item).statement_ids
            )
        ]

    total = len(items)
    paginated_items = items[offset:offset + limit]
    next_offset = offset + len(paginated_items)
    has_more = next_offset < total

    return c.PayrollAdvanceConsolidatedListResponse(
        items=[_consolidated_to_public(item) for item in paginated_items],
        total=total,
        offset=offset,
        limit=limit,
        next_offset=next_offset if has_more else None,
        has_more=has_more,
    )


@router.post(
    "/consolidated",
    response_model=c.PayrollAdvanceConsolidatedPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_consolidated(
    payload: c.PayrollAdvanceConsolidatedCreateRequest,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    c._ensure_download(current_user)

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
        db.query(c.PayrollAdvanceStatement)
        .options(
            c.joinedload(c.PayrollAdvanceStatement.restaurant),
            c.joinedload(c.PayrollAdvanceStatement.items),
        )
        .filter(c.PayrollAdvanceStatement.id.in_(ordered_ids))
        .all()
    )
    statement_map = {stmt.id: stmt for stmt in statements}
    missing_ids = [stmt_id for stmt_id in ordered_ids if stmt_id not in statement_map]
    if missing_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Statements not found: {missing_ids}")

    ordered_statements: list[c.PayrollAdvanceStatement] = []
    for stmt_id in ordered_ids:
        stmt = statement_map[stmt_id]
        c._ensure_restaurant_access(db, current_user, stmt.restaurant_id)
        ordered_statements.append(stmt)

    date_from = min(s.date_from for s in ordered_statements)
    date_to = max(s.date_to for s in ordered_statements)
    title = (payload.title or "").strip() or None

    consolidated = c.PayrollAdvanceConsolidatedStatement(
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


@router.get("/consolidated/{consolidated_id}", response_model=c.PayrollAdvanceConsolidatedPublic)
def get_consolidated(
    consolidated_id: int,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    c._ensure_download(current_user)
    consolidated = db.query(c.PayrollAdvanceConsolidatedStatement).get(consolidated_id)
    if not consolidated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consolidated statement not found")
    if (
        not c.has_global_access(current_user)
        and consolidated.created_by_id != current_user.id
        and not c.has_permission(current_user, c.PermissionCode.PAYROLL_ADVANCE_DELETE)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return _consolidated_to_public(consolidated)


@router.get(
    "/consolidated/{consolidated_id}/histogram",
    response_model=c.PayrollAdvanceConsolidatedHistogramResponse,
)
def get_consolidated_histogram(
    consolidated_id: int,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    c._ensure_download(current_user)
    consolidated = db.query(c.PayrollAdvanceConsolidatedStatement).get(consolidated_id)
    if not consolidated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consolidated statement not found")
    if (
        not c.has_global_access(current_user)
        and consolidated.created_by_id != current_user.id
        and not c.has_permission(current_user, c.PermissionCode.PAYROLL_ADVANCE_DELETE)
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
        return c.PayrollAdvanceConsolidatedHistogramResponse(items=[])

    statements = (
        db.query(c.PayrollAdvanceStatement.id, c.PayrollAdvanceStatement.restaurant_id)
        .filter(c.PayrollAdvanceStatement.id.in_(ordered_ids))
        .all()
    )
    statement_restaurants = {int(row.id): row.restaurant_id for row in statements if row.id is not None}
    missing_ids = [stmt_id for stmt_id in ordered_ids if stmt_id not in statement_restaurants]
    if missing_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Statements not found: {missing_ids}")
    for stmt_id in ordered_ids:
        c._ensure_restaurant_access(db, current_user, statement_restaurants.get(stmt_id))

    statement_kind_expr = c.func.lower(
        c.cast(c.PayrollAdvanceStatement.statement_kind, c.String)
    )
    total_cost_expr = c.case(
        (
            statement_kind_expr == "salary",
            c.func.coalesce(c.PayrollAdvanceItem.final_amount, 0)
            + c.func.coalesce(c.PayrollAdvanceItem.deduction_amount, 0),
        ),
        else_=c.func.coalesce(c.PayrollAdvanceItem.final_amount, 0),
    )

    subdivision_name_expr = c.func.coalesce(c.RestaurantSubdivision.name, "Без подразделения")

    rows = (
        db.query(
            subdivision_name_expr.label("subdivision_name"),
            c.PayrollAdvanceItem.position_name.label("position_name"),
            c.func.count(c.PayrollAdvanceItem.id).label("row_count"),
            c.func.coalesce(c.func.sum(c.PayrollAdvanceItem.fact_hours), 0).label("hours"),
            c.func.coalesce(c.func.sum(c.PayrollAdvanceItem.night_hours), 0).label("night_hours"),
            c.func.coalesce(c.func.sum(c.PayrollAdvanceItem.accrual_amount), 0).label("accrual_amount"),
            c.func.coalesce(c.func.sum(c.PayrollAdvanceItem.deduction_amount), 0).label("deduction_amount"),
            c.func.coalesce(c.func.sum(total_cost_expr), 0).label("total_cost"),
        )
        .join(c.PayrollAdvanceStatement, c.PayrollAdvanceStatement.id == c.PayrollAdvanceItem.statement_id)
        .outerjoin(c.Position, c.Position.id == c.PayrollAdvanceItem.position_id)
        .outerjoin(c.RestaurantSubdivision, c.RestaurantSubdivision.id == c.Position.restaurant_subdivision_id)
        .filter(c.PayrollAdvanceItem.statement_id.in_(ordered_ids))
        .group_by(subdivision_name_expr, c.PayrollAdvanceItem.position_name)
        .all()
    )

    subdivisions: dict[str, dict] = {}
    for row in rows:
        subdivision_name = (getattr(row, "subdivision_name", None) or "").strip() or "Без подразделения"
        position_name = (getattr(row, "position_name", None) or "").strip() or "Без должности"
        subdivision = subdivisions.setdefault(
            subdivision_name,
            {
                "subdivision_name": subdivision_name,
                "hours": 0.0,
                "night_hours": 0.0,
                "accrual_amount": 0.0,
                "deduction_amount": 0.0,
                "total_cost": 0.0,
                "row_count": 0,
                "positions": [],
            },
        )
        position = c.PayrollAdvanceHistogramPositionPublic(
            position_name=position_name,
            hours=float(c._quantize_money(c._decimal(getattr(row, "hours", 0)))),
            night_hours=float(c._quantize_money(c._decimal(getattr(row, "night_hours", 0)))),
            accrual_amount=float(c._quantize_money(c._decimal(getattr(row, "accrual_amount", 0)))),
            deduction_amount=float(c._quantize_money(c._decimal(getattr(row, "deduction_amount", 0)))),
            total_cost=float(c._quantize_money(c._decimal(getattr(row, "total_cost", 0)))),
            row_count=int(getattr(row, "row_count", 0) or 0),
        )
        subdivision["hours"] += position.hours
        subdivision["night_hours"] += position.night_hours
        subdivision["accrual_amount"] += position.accrual_amount
        subdivision["deduction_amount"] += position.deduction_amount
        subdivision["total_cost"] += position.total_cost
        subdivision["row_count"] += position.row_count
        subdivision["positions"].append(position)

    items = [
        c.PayrollAdvanceHistogramSubdivisionPublic(
            subdivision_name=entry["subdivision_name"],
            hours=float(c._quantize_money(c._decimal(entry["hours"]))),
            night_hours=float(c._quantize_money(c._decimal(entry["night_hours"]))),
            accrual_amount=float(c._quantize_money(c._decimal(entry["accrual_amount"]))),
            deduction_amount=float(c._quantize_money(c._decimal(entry["deduction_amount"]))),
            total_cost=float(c._quantize_money(c._decimal(entry["total_cost"]))),
            row_count=int(entry["row_count"]),
            positions=sorted(entry["positions"], key=lambda item: item.total_cost, reverse=True),
        )
        for entry in subdivisions.values()
    ]
    items.sort(key=lambda item: item.total_cost, reverse=True)
    return c.PayrollAdvanceConsolidatedHistogramResponse(items=items)


@router.get("/consolidated/{consolidated_id}/download")
def download_consolidated_by_id(
    consolidated_id: int,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    c._ensure_download(current_user)
    consolidated = db.query(c.PayrollAdvanceConsolidatedStatement).get(consolidated_id)
    if not consolidated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consolidated statement not found")
    if (
        not c.has_global_access(current_user)
        and consolidated.created_by_id != current_user.id
        and not c.has_permission(current_user, c.PermissionCode.PAYROLL_ADVANCE_DELETE)
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
        db.query(c.PayrollAdvanceStatement)
        .options(
            c.joinedload(c.PayrollAdvanceStatement.restaurant),
            c.joinedload(c.PayrollAdvanceStatement.items),
        )
        .filter(c.PayrollAdvanceStatement.id.in_(ordered_ids))
        .all()
    )
    statement_map = {stmt.id: stmt for stmt in statements}
    missing_ids = [stmt_id for stmt_id in ordered_ids if stmt_id not in statement_map]
    if missing_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Statements not found: {missing_ids}")

    ordered_statements: list[c.PayrollAdvanceStatement] = []
    for stmt_id in ordered_ids:
        stmt = statement_map[stmt_id]
        c._ensure_restaurant_access(db, current_user, stmt.restaurant_id)
        ordered_statements.append(stmt)

    stream = c.build_consolidated_payroll_report_from_statements(db, ordered_statements)
    filename = f"advance_consolidated_{consolidated.id}_{datetime.utcnow().date().isoformat()}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": c._content_disposition(filename, fallback="advance_consolidated.xlsx")},
    )


@router.post("/consolidated/download")
def download_consolidated(
    payload: c.PayrollAdvanceConsolidatedDownloadRequest,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    c._ensure_download(current_user)

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
        db.query(c.PayrollAdvanceStatement)
        .options(
            c.joinedload(c.PayrollAdvanceStatement.restaurant),
            c.joinedload(c.PayrollAdvanceStatement.items),
        )
        .filter(c.PayrollAdvanceStatement.id.in_(ordered_ids))
        .all()
    )
    statement_map = {stmt.id: stmt for stmt in statements}
    missing_ids = [stmt_id for stmt_id in ordered_ids if stmt_id not in statement_map]
    if missing_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Statements not found: {missing_ids}")

    ordered_statements: list[c.PayrollAdvanceStatement] = []
    for stmt_id in ordered_ids:
        stmt = statement_map[stmt_id]
        c._ensure_restaurant_access(db, current_user, stmt.restaurant_id)
        ordered_statements.append(stmt)

    stream = c.build_consolidated_payroll_report_from_statements(db, ordered_statements)
    filename = f"advance_consolidated_{datetime.utcnow().date().isoformat()}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": c._content_disposition(filename, fallback="advance_consolidated.xlsx")},
    )


@router.delete("/consolidated/{consolidated_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_consolidated(
    consolidated_id: int,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    c._ensure_download(current_user)
    consolidated = db.query(c.PayrollAdvanceConsolidatedStatement).get(consolidated_id)
    if not consolidated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consolidated statement not found")
    if (
        not c.has_global_access(current_user)
        and consolidated.created_by_id != current_user.id
        and not c.has_permission(current_user, c.PermissionCode.PAYROLL_ADVANCE_DELETE)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    db.delete(consolidated)
    db.commit()
