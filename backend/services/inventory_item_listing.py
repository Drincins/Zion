from __future__ import annotations

from backend.routers.inventory_routes.common import (
    InvItem,
    InvItemInstance,
    InvItemLocationSummary,
    InvItemRead,
    InvStoragePlace,
    Optional,
    Restaurant,
    RestaurantSubdivision,
    Session,
    User,
    and_,
    func,
    get_user_restaurant_ids,
    or_,
    _ensure_inventory_lookup_access,
    _item_schema,
)


def list_inventory_items(
    *,
    db: Session,
    current_user: User,
    item_ids: Optional[list[int]] = None,
    item_ids_bracket: Optional[list[int]] = None,
    group_id: Optional[int] = None,
    category_id: Optional[int] = None,
    kind_id: Optional[int] = None,
    restaurant_ids: Optional[list[int]] = None,
    restaurant_ids_bracket: Optional[list[int]] = None,
    storage_place_ids: Optional[list[int]] = None,
    storage_place_ids_bracket: Optional[list[int]] = None,
    subdivision_ids: Optional[list[int]] = None,
    subdivision_ids_bracket: Optional[list[int]] = None,
    include_warehouse: bool = False,
    only_in_locations: bool = False,
    include_locations: bool = True,
) -> list[InvItemRead]:
    _ensure_inventory_lookup_access(current_user)
    query = db.query(InvItem)
    normalized_item_ids = sorted({int(item_id) for item_id in (item_ids or []) + (item_ids_bracket or [])})
    if normalized_item_ids:
        query = query.filter(InvItem.id.in_(normalized_item_ids))
    if group_id is not None:
        query = query.filter(InvItem.group_id == group_id)
    if category_id is not None:
        query = query.filter(InvItem.category_id == category_id)
    if kind_id is not None:
        query = query.filter(InvItem.kind_id == kind_id)

    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    raw_restaurant_ids = sorted({int(rid) for rid in (restaurant_ids or []) + (restaurant_ids_bracket or [])})
    normalized_restaurant_ids: list[int] = []
    if raw_restaurant_ids:
        if allowed_restaurants is None:
            normalized_restaurant_ids = raw_restaurant_ids
        else:
            normalized_restaurant_ids = sorted({int(rid) for rid in raw_restaurant_ids if int(rid) in allowed_restaurants})

    normalized_subdivision_ids = sorted({int(sid) for sid in (subdivision_ids or []) + (subdivision_ids_bracket or [])})
    normalized_storage_place_ids = sorted({int(place_id) for place_id in (storage_place_ids or []) + (storage_place_ids_bracket or [])})

    location_conditions = []
    if include_warehouse:
        location_conditions.append(InvItemInstance.location_kind == "warehouse")
    if normalized_restaurant_ids:
        restaurant_condition = and_(
            InvItemInstance.location_kind == "restaurant",
            InvItemInstance.restaurant_id.in_(normalized_restaurant_ids),
        )
        if normalized_storage_place_ids:
            restaurant_condition = and_(
                restaurant_condition,
                InvItemInstance.storage_place_id.in_(normalized_storage_place_ids),
            )
        location_conditions.append(restaurant_condition)
    if normalized_subdivision_ids:
        location_conditions.append(
            and_(
                InvItemInstance.location_kind == "subdivision",
                InvItemInstance.subdivision_id.in_(normalized_subdivision_ids),
            )
        )

    should_filter_by_locations = bool(location_conditions) or only_in_locations
    if should_filter_by_locations:
        if not location_conditions:
            return []
        query = (
            query.join(InvItemInstance, InvItemInstance.item_id == InvItem.id)
            .filter(or_(*location_conditions))
            .distinct()
        )

    items = query.order_by(InvItem.name.asc()).all()
    if not items:
        return []

    if not include_locations:
        return [_item_schema(item) for item in items]

    item_ids_list = [item.id for item in items]
    summaries_query = (
        db.query(
            InvItemInstance.item_id.label("item_id"),
            InvItemInstance.location_kind.label("location_kind"),
            InvItemInstance.restaurant_id.label("restaurant_id"),
            InvItemInstance.storage_place_id.label("storage_place_id"),
            InvItemInstance.subdivision_id.label("subdivision_id"),
            func.count(InvItemInstance.id).label("quantity"),
            func.avg(
                func.coalesce(
                    InvItemInstance.purchase_cost,
                    InvItem.default_cost,
                    InvItem.cost,
                )
            ).label("avg_cost"),
            func.max(InvItemInstance.arrived_at).label("last_arrival_at"),
        )
        .join(InvItem, InvItem.id == InvItemInstance.item_id)
        .filter(InvItemInstance.item_id.in_(item_ids_list))
    )
    if should_filter_by_locations and location_conditions:
        summaries_query = summaries_query.filter(or_(*location_conditions))
    elif allowed_restaurants is not None:
        summaries_query = summaries_query.filter(
            or_(
                InvItemInstance.location_kind != "restaurant",
                InvItemInstance.restaurant_id.in_(allowed_restaurants),
            )
        )
    summary_rows = (
        summaries_query
        .group_by(
            InvItemInstance.item_id,
            InvItemInstance.location_kind,
            InvItemInstance.restaurant_id,
            InvItemInstance.storage_place_id,
            InvItemInstance.subdivision_id,
        )
        .all()
    )

    restaurant_names = {row.id: row.name for row in db.query(Restaurant.id, Restaurant.name).all()}
    storage_place_names = {row.id: row.name for row in db.query(InvStoragePlace.id, InvStoragePlace.name).all()}
    subdivision_names = {row.id: row.name for row in db.query(RestaurantSubdivision.id, RestaurantSubdivision.name).all()}

    item_location_map: dict[int, list[InvItemLocationSummary]] = {}
    total_qty_map: dict[int, int] = {}
    warehouse_qty_map: dict[int, int] = {}

    for row in summary_rows:
        item_id = int(row.item_id)
        location_kind = str(row.location_kind)
        quantity = int(row.quantity or 0)
        if quantity <= 0:
            continue
        if location_kind == "warehouse":
            location_name = "Склад"
            warehouse_qty_map[item_id] = warehouse_qty_map.get(item_id, 0) + quantity
        elif location_kind == "restaurant":
            restaurant_name = restaurant_names.get(int(row.restaurant_id), f"Ресторан #{row.restaurant_id}")
            if row.storage_place_id is not None:
                storage_place_name = storage_place_names.get(int(row.storage_place_id), f"Место #{row.storage_place_id}")
                location_name = f"{restaurant_name} · {storage_place_name}"
            else:
                location_name = f"{restaurant_name} · Без места хранения"
        else:
            location_name = subdivision_names.get(int(row.subdivision_id), f"Подразделение #{row.subdivision_id}")

        item_location_map.setdefault(item_id, []).append(
            InvItemLocationSummary(
                location_kind=location_kind,  # type: ignore[arg-type]
                restaurant_id=int(row.restaurant_id) if row.restaurant_id is not None else None,
                storage_place_id=int(row.storage_place_id) if row.storage_place_id is not None else None,
                storage_place_name=storage_place_names.get(int(row.storage_place_id)) if row.storage_place_id is not None else None,
                subdivision_id=int(row.subdivision_id) if row.subdivision_id is not None else None,
                location_name=location_name,
                quantity=quantity,
                avg_cost=row.avg_cost,
                last_arrival_at=row.last_arrival_at,
            )
        )
        total_qty_map[item_id] = total_qty_map.get(item_id, 0) + quantity

    return [
        _item_schema(
            item,
            location_totals=item_location_map.get(item.id, []),
            total_quantity=total_qty_map.get(item.id, 0),
            warehouse_quantity=warehouse_qty_map.get(item.id, 0),
        )
        for item in items
    ]
