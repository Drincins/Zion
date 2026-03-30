from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from . import common as c

router = APIRouter()


@router.post("/{statement_id}/status", response_model=c.PayrollAdvanceStatementPublic)
def change_status(
    statement_id: int,
    payload: c.PayrollAdvanceStatusUpdate,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    c._ensure_view(current_user)
    statement = c._load_statement(db, statement_id)
    c._ensure_restaurant_access(db, current_user, statement.restaurant_id)

    target = payload.status
    current = statement.status
    if target == current:
        return c._statement_to_public(db, statement)

    if target not in c.ALLOWED_TRANSITIONS.get(current, set()) and not c.has_permission(
        current_user, c.PermissionCode.PAYROLL_ADVANCE_STATUS_ALL
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transition is not allowed")

    c._ensure_status(current_user, target)

    statement.status = target
    if target == "posted":
        statement.posted_at = datetime.utcnow()
    statement.updated_at = datetime.utcnow()
    statement.updated_by_id = current_user.id
    db.commit()
    db.refresh(statement)
    return c._statement_to_public(db, statement)


@router.post("/{statement_id}/post", response_model=c.PayrollAdjustmentBulkResponse)
def post_statement(
    statement_id: int,
    payload: c.PayrollAdvancePostRequest,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    c._ensure_status(current_user, "posted")
    statement = c._load_statement(db, statement_id)
    c._ensure_restaurant_access(db, current_user, statement.restaurant_id)
    if statement.status not in {"ready", "confirmed"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Statement must be ready or confirmed")

    adj_type = db.query(c.PayrollAdjustmentType).get(payload.adjustment_type_id)
    if not adj_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adjustment type not found")

    rows = []
    for item in statement.items:
        code = (item.staff_code or "").strip()
        if not code:
            continue
        raw_amount = c._quantize_money(c._decimal(item.final_amount))
        if raw_amount == 0:
            continue
        rows.append(
            {
                "staff_code": code,
                "amount": c._normalize_amount(raw_amount, adj_type.kind),
                "raw_amount": raw_amount,
            }
        )

    skipped: list[c.PayrollAdjustmentBulkResultItem] = []
    errors: list[c.PayrollAdjustmentBulkResultItem] = []
    results: list[c.PayrollAdjustmentBulkStatusItem] = []
    created: list[c.PayrollAdjustment] = []
    created_total = c.Decimal("0")

    users = (
        db.query(c.User)
        .filter(c.User.staff_code.in_([r["staff_code"] for r in rows]))
        .all()
    )
    staff_to_user = {row.staff_code: row for row in users if row.staff_code}

    target_restaurant_id = statement.restaurant_id or payload.restaurant_id

    existing_q = (
        db.query(c.PayrollAdjustment.user_id)
        .filter(c.PayrollAdjustment.restaurant_id == target_restaurant_id)
        .filter(c.PayrollAdjustment.adjustment_type_id == payload.adjustment_type_id)
        .filter(c.PayrollAdjustment.date == payload.date)
    )
    existing_map = {row.user_id for row in existing_q.all()}

    for row in rows:
        code = row["staff_code"]
        user = staff_to_user.get(code)
        if not user:
            reason = "Сотрудник не найден"
            errors.append(c.PayrollAdjustmentBulkResultItem(staff_code=code, reason=reason))
            results.append(c.PayrollAdjustmentBulkStatusItem(staff_code=code, status="error", reason=reason))
            continue
        user_id = user.id
        full_name = c._full_name(user)
        if user_id in existing_map:
            reason = "Запись уже существует"
            skipped.append(
                c.PayrollAdjustmentBulkResultItem(
                    staff_code=code,
                    user_id=user_id,
                    full_name=full_name,
                    reason=reason,
                )
            )
            results.append(
                c.PayrollAdjustmentBulkStatusItem(
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
            c.PayrollAdjustment(
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
            c.PayrollAdjustmentBulkStatusItem(
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

    return c.PayrollAdjustmentBulkResponse(
        created_count=created_count,
        created_total=float(c._quantize_money(created_total)),
        skipped=skipped,
        errors=errors,
        results=results,
    )


@router.get("/{statement_id}/download")
def download_statement(
    statement_id: int,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    c._ensure_download(current_user)
    statement = c._load_statement(db, statement_id)
    c._ensure_restaurant_access(db, current_user, statement.restaurant_id)
    stream = c.build_payroll_report_from_statement(db, statement)
    filename = c._statement_filename(statement)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": c._content_disposition(filename, fallback="advance_statement.xlsx")},
    )


@router.delete("/{statement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_statement(
    statement_id: int,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    statement = c._load_statement(db, statement_id)
    c._ensure_restaurant_access(db, current_user, statement.restaurant_id)
    c._ensure_delete(current_user, status=statement.status)

    db.delete(statement)
    db.commit()

