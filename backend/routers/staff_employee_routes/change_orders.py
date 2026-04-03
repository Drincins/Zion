from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import joinedload

from . import common as c
from backend.bd.models import EmployeeChangeOrder
from backend.schemas import (
    EmployeeChangeOrderCreate,
    EmployeeChangeOrderListResponse,
    EmployeeChangeOrderPublic,
)
from backend.services.employee_change_orders import apply_employee_change_order
from backend.utils import now_local, today_local

router = APIRouter()


def _ensure_employee_change_orders_manage(
    db: c.Session,
    current_user: c.User,
    target_user: c.User,
) -> None:
    c.ensure_permissions(current_user, c.PermissionCode.STAFF_EMPLOYEE_ORDERS_MANAGE)
    c._ensure_can_edit_user(db, current_user, target_user)


def _normalize_optional_fk(value: int | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid identifier") from exc
    return parsed if parsed > 0 else None


def _load_order(
    db: c.Session,
    *,
    user_id: int,
    order_id: int,
) -> EmployeeChangeOrder:
    order = (
        db.query(EmployeeChangeOrder)
        .options(
            joinedload(EmployeeChangeOrder.created_by),
            joinedload(EmployeeChangeOrder.cancelled_by),
            joinedload(EmployeeChangeOrder.position_new),
            joinedload(EmployeeChangeOrder.workplace_restaurant_new),
        )
        .filter(EmployeeChangeOrder.id == order_id, EmployeeChangeOrder.user_id == user_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee change order not found")
    return order


@router.get(
    "/{user_id}/change-orders",
    response_model=EmployeeChangeOrderListResponse,
    response_model_exclude_none=True,
)
def list_employee_change_orders(
    user_id: int,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
) -> EmployeeChangeOrderListResponse:
    target_user = db.query(c.User).filter(c.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    _ensure_employee_change_orders_manage(db, current_user, target_user)

    items = (
        db.query(EmployeeChangeOrder)
        .options(
            joinedload(EmployeeChangeOrder.created_by),
            joinedload(EmployeeChangeOrder.cancelled_by),
            joinedload(EmployeeChangeOrder.position_new),
            joinedload(EmployeeChangeOrder.workplace_restaurant_new),
        )
        .filter(EmployeeChangeOrder.user_id == user_id)
        .order_by(
            EmployeeChangeOrder.effective_date.desc(),
            EmployeeChangeOrder.created_at.desc(),
            EmployeeChangeOrder.id.desc(),
        )
        .all()
    )
    return EmployeeChangeOrderListResponse(
        items=[EmployeeChangeOrderPublic.model_validate(item) for item in items]
    )


@router.post(
    "/{user_id}/change-orders",
    response_model=EmployeeChangeOrderPublic,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def create_employee_change_order(
    user_id: int,
    payload: EmployeeChangeOrderCreate,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
) -> EmployeeChangeOrderPublic:
    target_user = (
        db.query(c.User)
        .options(
            joinedload(c.User.position).joinedload(c.Position.payment_format),
            joinedload(c.User.workplace_restaurant),
        )
        .filter(c.User.id == user_id)
        .first()
    )
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    _ensure_employee_change_orders_manage(db, current_user, target_user)

    if payload.effective_date < today_local():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Effective date must be today or in the future",
        )

    has_changes = any(
        [
            payload.change_position,
            payload.change_workplace_restaurant,
            payload.change_individual_rate,
        ]
    )
    if not has_changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нужно выбрать хотя бы одно кадровое изменение",
        )

    if (
        not payload.change_position and payload.position_id_new is not None
    ) or (
        not payload.change_workplace_restaurant and payload.workplace_restaurant_id_new is not None
    ) or (
        not payload.change_individual_rate and payload.individual_rate_new is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Values can be provided only for the selected change fields",
        )

    if payload.change_rate or payload.rate_new is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Direct rate change is not supported. Use individual rate or position change.",
        )

    rate_change_requested = payload.change_individual_rate
    if rate_change_requested and (
        not c.has_permission(current_user, c.PermissionCode.STAFF_RATE_MANAGE)
        or not c.can_view_rate(current_user, target_user)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: insufficient permissions to manage rates",
        )

    position_id_new = _normalize_optional_fk(payload.position_id_new)
    workplace_restaurant_id_new = _normalize_optional_fk(payload.workplace_restaurant_id_new)

    if payload.change_position and position_id_new is not None:
        position = (
            db.query(c.Position)
            .options(joinedload(c.Position.payment_format))
            .filter(c.Position.id == position_id_new)
            .first()
        )
        if not position:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    if payload.change_workplace_restaurant and workplace_restaurant_id_new is not None:
        restaurant = db.query(c.Restaurant).filter(c.Restaurant.id == workplace_restaurant_id_new).first()
        if not restaurant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
        allowed_workplaces = c._get_allowed_workplace_ids(db, current_user)
        if allowed_workplaces is not None and workplace_restaurant_id_new not in allowed_workplaces:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to the selected workplace restaurant is not allowed",
            )

    existing_pending = (
        db.query(EmployeeChangeOrder.id)
        .filter(
            EmployeeChangeOrder.user_id == user_id,
            EmployeeChangeOrder.effective_date == payload.effective_date,
            EmployeeChangeOrder.status == "pending",
        )
        .first()
    )
    if existing_pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending кадровое изменение already exists for this date",
        )

    order = EmployeeChangeOrder(
        user_id=user_id,
        effective_date=payload.effective_date,
        change_position=bool(payload.change_position),
        position_id_new=position_id_new if payload.change_position else None,
        change_workplace_restaurant=bool(payload.change_workplace_restaurant),
        workplace_restaurant_id_new=(
            workplace_restaurant_id_new if payload.change_workplace_restaurant else None
        ),
        change_rate=False,
        rate_new=None,
        change_individual_rate=bool(payload.change_individual_rate),
        individual_rate_new=(
            payload.individual_rate_new if payload.change_individual_rate else None
        ),
        apply_to_attendances=bool(payload.apply_to_attendances),
        comment=(payload.comment or "").strip() or None,
        created_by_id=current_user.id,
    )
    db.add(order)
    db.commit()

    order = _load_order(db, user_id=user_id, order_id=order.id)
    if order.effective_date <= today_local():
        try:
            apply_employee_change_order(db, order)
            db.commit()
            order = _load_order(db, user_id=user_id, order_id=order.id)
        except Exception:
            db.rollback()
            raise
    return EmployeeChangeOrderPublic.model_validate(order)


@router.post(
    "/{user_id}/change-orders/{order_id}/cancel",
    response_model=EmployeeChangeOrderPublic,
    response_model_exclude_none=True,
)
def cancel_employee_change_order(
    user_id: int,
    order_id: int,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
) -> EmployeeChangeOrderPublic:
    target_user = db.query(c.User).filter(c.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    _ensure_employee_change_orders_manage(db, current_user, target_user)
    order = _load_order(db, user_id=user_id, order_id=order_id)
    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending кадровые изменения can be cancelled",
        )

    order.status = "cancelled"
    order.cancelled_by_id = current_user.id
    order.cancelled_at = now_local()
    order.error_message = None
    db.commit()
    order = _load_order(db, user_id=user_id, order_id=order.id)
    return EmployeeChangeOrderPublic.model_validate(order)
