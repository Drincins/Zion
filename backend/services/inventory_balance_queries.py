from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.bd.models import InvItem, InvItemRecord, InvItemStock, Restaurant, User
from backend.schemas import InventoryBalance, InventoryBalanceItem
from backend.services.inventory_domain import _ensure_restaurant_allowed
from backend.utils import get_user_restaurant_ids


def list_inventory_balances(
    *,
    db: Session,
    current_user: User,
    restaurant_id: int | None = None,
) -> list[InventoryBalance]:
    allowed_restaurants = get_user_restaurant_ids(db, current_user)

    if restaurant_id is not None:
        _ensure_restaurant_allowed(allowed_restaurants, restaurant_id)
        restaurant_ids = [restaurant_id]
    else:
        if allowed_restaurants is None:
            restaurant_ids = [row[0] for row in db.query(Restaurant.id).order_by(Restaurant.id.asc()).all()]
        else:
            restaurant_ids = sorted(allowed_restaurants)

    if not restaurant_ids:
        return []

    rows = (
        db.query(
            InvItemStock.restaurant_id.label("restaurant_id"),
            InvItemStock.item_id.label("item_id"),
            InvItem.name.label("item_name"),
            InvItemStock.quantity.label("quantity"),
            InvItemStock.avg_cost.label("avg_cost"),
        )
        .join(InvItem, InvItem.id == InvItemStock.item_id)
        .filter(InvItemStock.restaurant_id.in_(restaurant_ids))
        .order_by(InvItemStock.restaurant_id.asc(), InvItem.name.asc())
        .all()
    )

    count_rows = (
        db.query(
            InvItemRecord.restaurant_id.label("restaurant_id"),
            InvItemRecord.item_id.label("item_id"),
            func.count(InvItemRecord.id).label("record_count"),
        )
        .filter(InvItemRecord.restaurant_id.in_(restaurant_ids))
        .group_by(InvItemRecord.restaurant_id, InvItemRecord.item_id)
        .all()
    )

    record_count_map: dict[tuple[int, int], int] = {
        (int(row.restaurant_id), int(row.item_id)): int(row.record_count or 0) for row in count_rows
    }

    result_map: dict[int, InventoryBalance] = {
        rest_id: InventoryBalance(
            restaurant_id=rest_id,
            total_quantity=0,
            total_cost=Decimal("0"),
            record_count=0,
            items=[],
        )
        for rest_id in restaurant_ids
    }

    for row in rows:
        rest_id = int(row.restaurant_id)
        item_quantity = int(row.quantity or 0)
        avg_cost = Decimal(row.avg_cost or 0)
        item_total_cost = avg_cost * item_quantity
        record_count = record_count_map.get((rest_id, int(row.item_id)), 0)

        entry = result_map[rest_id]
        entry.items.append(
            InventoryBalanceItem(
                item_id=int(row.item_id),
                item_name=str(row.item_name),
                total_quantity=item_quantity,
                total_cost=item_total_cost,
                record_count=record_count,
            )
        )
        entry.total_quantity += item_quantity
        entry.total_cost += item_total_cost
        entry.record_count += record_count

    return [result_map[rest_id] for rest_id in restaurant_ids]


def get_restaurant_balance(
    *,
    db: Session,
    current_user: User,
    restaurant_id: int,
) -> InventoryBalance:
    balances = list_inventory_balances(db=db, current_user=current_user, restaurant_id=restaurant_id)
    return balances[0] if balances else InventoryBalance(
        restaurant_id=restaurant_id,
        total_quantity=0,
        total_cost=Decimal("0"),
        record_count=0,
        items=[],
    )
