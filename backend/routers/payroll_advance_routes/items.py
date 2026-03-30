from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from . import common as c

router = APIRouter()


@router.patch("/{statement_id}/items/{item_id}", response_model=c.PayrollAdvanceStatementPublic)
def update_item(
    statement_id: int,
    item_id: int,
    payload: c.PayrollAdvanceItemUpdateRequest,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    c._ensure_edit(current_user)
    statement = c._load_statement(db, statement_id)
    c._ensure_restaurant_access(db, current_user, statement.restaurant_id)
    if statement.status not in c.EDITABLE_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Statement is not editable in this status")

    item = next((i for i in statement.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    item.final_amount = payload.final_amount
    item.manual = True
    item.comment = payload.comment
    if item.user and item.user.fired:
        item.comment = c._merge_fire_comment(item.comment, item.user.fire_date)
    statement.updated_at = datetime.utcnow()
    statement.updated_by_id = current_user.id
    db.commit()
    db.refresh(statement)
    return c._statement_to_public(db, statement)


@router.patch("/{statement_id}/items/{item_id}/compact", response_model=c.PayrollAdvanceItemPatchResponse)
def update_item_compact(
    statement_id: int,
    item_id: int,
    payload: c.PayrollAdvanceItemUpdateRequest,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
) -> c.PayrollAdvanceItemPatchResponse:
    c._ensure_edit(current_user)
    statement = (
        db.query(c.PayrollAdvanceStatement)
        .filter(c.PayrollAdvanceStatement.id == statement_id)
        .first()
    )
    if not statement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Statement not found")
    c._ensure_restaurant_access(db, current_user, statement.restaurant_id)
    if statement.status not in c.EDITABLE_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Statement is not editable in this status")

    item = (
        db.query(c.PayrollAdvanceItem)
        .options(
            c.joinedload(c.PayrollAdvanceItem.restaurant),
            c.joinedload(c.PayrollAdvanceItem.user),
            c.joinedload(c.PayrollAdvanceItem.position).joinedload(c.Position.restaurant_subdivision),
        )
        .filter(
            c.PayrollAdvanceItem.statement_id == statement_id,
            c.PayrollAdvanceItem.id == item_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    item.final_amount = payload.final_amount
    item.manual = True
    item.comment = payload.comment
    if item.user and item.user.fired:
        item.comment = c._merge_fire_comment(item.comment, item.user.fire_date)

    statement.updated_at = datetime.utcnow()
    statement.updated_by_id = current_user.id
    db.commit()

    refreshed_item = (
        db.query(c.PayrollAdvanceItem)
        .options(
            c.joinedload(c.PayrollAdvanceItem.restaurant),
            c.joinedload(c.PayrollAdvanceItem.user),
            c.joinedload(c.PayrollAdvanceItem.position).joinedload(c.Position.restaurant_subdivision),
        )
        .filter(
            c.PayrollAdvanceItem.statement_id == statement_id,
            c.PayrollAdvanceItem.id == item_id,
        )
        .first()
    )
    if not refreshed_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    return c.PayrollAdvanceItemPatchResponse(
        statement_id=statement_id,
        item=c._item_to_public(refreshed_item),
        updated_at=statement.updated_at,
        updated_by_id=statement.updated_by_id,
    )


@router.patch("/{statement_id}/items/bulk/update", response_model=c.PayrollAdvanceItemsBulkPatchResponse)
def update_items_bulk_compact(
    statement_id: int,
    payload: c.PayrollAdvanceItemsBulkUpdateRequest,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
) -> c.PayrollAdvanceItemsBulkPatchResponse:
    c._ensure_edit(current_user)
    statement = (
        db.query(c.PayrollAdvanceStatement)
        .filter(c.PayrollAdvanceStatement.id == statement_id)
        .first()
    )
    if not statement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Statement not found")
    c._ensure_restaurant_access(db, current_user, statement.restaurant_id)
    if statement.status not in c.EDITABLE_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Statement is not editable in this status")

    raw_items = payload.items or []
    if not raw_items:
        return c.PayrollAdvanceItemsBulkPatchResponse(
            statement_id=statement_id,
            items=[],
            updated_at=statement.updated_at,
            updated_by_id=statement.updated_by_id,
        )

    normalized_items: list[c.PayrollAdvanceItemBulkUpdateItem] = []
    seen_ids: set[int] = set()
    for row in raw_items:
        item_id = int(row.item_id)
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)
        normalized_items.append(row)

    target_ids = [int(row.item_id) for row in normalized_items]
    db_items = (
        db.query(c.PayrollAdvanceItem)
        .options(
            c.joinedload(c.PayrollAdvanceItem.restaurant),
            c.joinedload(c.PayrollAdvanceItem.user),
            c.joinedload(c.PayrollAdvanceItem.position).joinedload(c.Position.restaurant_subdivision),
        )
        .filter(
            c.PayrollAdvanceItem.statement_id == statement_id,
            c.PayrollAdvanceItem.id.in_(target_ids),
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
            item.comment = c._merge_fire_comment(item.comment, item.user.fire_date)

    statement.updated_at = datetime.utcnow()
    statement.updated_by_id = current_user.id
    db.commit()

    refreshed_items = (
        db.query(c.PayrollAdvanceItem)
        .options(
            c.joinedload(c.PayrollAdvanceItem.restaurant),
            c.joinedload(c.PayrollAdvanceItem.user),
            c.joinedload(c.PayrollAdvanceItem.position).joinedload(c.Position.restaurant_subdivision),
        )
        .filter(
            c.PayrollAdvanceItem.statement_id == statement_id,
            c.PayrollAdvanceItem.id.in_(target_ids),
        )
        .all()
    )
    refreshed_by_id = {int(item.id): item for item in refreshed_items}
    ordered_payload = [
        c._item_to_public(refreshed_by_id[int(row.item_id)])
        for row in normalized_items
        if int(row.item_id) in refreshed_by_id
    ]

    return c.PayrollAdvanceItemsBulkPatchResponse(
        statement_id=statement_id,
        items=ordered_payload,
        updated_at=statement.updated_at,
        updated_by_id=statement.updated_by_id,
    )

