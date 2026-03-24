# backend/routers/iiko_olap_read.py
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.bd.database import get_db
from backend.bd.models import User, Restaurant
from backend.utils import get_current_user, get_user_company_ids
from backend.services.permissions import ensure_permissions, PermissionCode, has_permission, has_global_access
from backend.bd.iiko_olap import IikoOlapRow

router = APIRouter(prefix="/iiko-olap", tags=["iiko-olap"])

def _ensure_restaurant_access(db: Session, user: User, restaurant_id: int) -> None:
    query = db.query(Restaurant).filter(Restaurant.id == restaurant_id)
    if not has_global_access(user):
        company_ids = sorted(get_user_company_ids(db, user) or [])
        if company_ids:
            query = query.filter(Restaurant.company_id.in_(company_ids))
            if not has_permission(user, PermissionCode.IIKO_MANAGE):
                query = query.filter(Restaurant.users.contains(user))
        else:
            query = query.filter(Restaurant.users.contains(user))
    match = query.first()
    if not match:
        raise HTTPException(status_code=404, detail="Restaurant not found for the requested report")


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")

@router.get("/rows")
def get_rows(
    restaurant_id: int = Query(...),
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    limit: Optional[int] = Query(None, ge=1, le=10000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    ensure_permissions(current_user, PermissionCode.IIKO_VIEW, PermissionCode.IIKO_MANAGE)
    _ensure_restaurant_access(db, current_user, restaurant_id)
    try:
        from_dt = _parse_date(from_date)
        to_dt_excl = _parse_date(to_date) + timedelta(days=1)
    except ValueError:
        raise HTTPException(status_code=400, detail="from_date/to_date должны быть в формате YYYY-MM-DD")

    q = (
        db.query(IikoOlapRow)
        .filter(IikoOlapRow.restaurant_id == restaurant_id)
        .filter(IikoOlapRow.open_date >= from_dt.date())
        .filter(IikoOlapRow.open_date < to_dt_excl.date())
        .order_by(IikoOlapRow.open_date.asc())
    )
    if limit:
        q = q.limit(limit)

    rows: List[IikoOlapRow] = q.all()

    data: List[Dict[str, Any]] = []
    for r in rows:
        dish_name = r.dish_full_name or getattr(r, "dish_name", None)

        data.append({
            # наша схема
            "open_date": r.open_date.isoformat() if r.open_date else None,
            "department": r.department,
            "dish_code": r.dish_code,
            "dish_full_name": dish_name,
            "dish_name": dish_name,
            "dish_measure_unit": r.dish_measure_unit,
            "dish_group": r.dish_group,
            "cooking_place": r.cooking_place,
            "non_cash_payment_type": r.non_cash_payment_type,
            "pay_types": r.pay_types,
            "dish_amount_int": r.dish_amount_int,
            "dish_sum_int": r.dish_sum_int,
            "discount_sum": r.discount_sum,

            # совместимость с фронтом/старым кодом/iiko-названием
            "OpenDate": r.open_date.isoformat() if r.open_date else None,
            "DishCode": r.dish_code,
            "DishFullName": dish_name,
            "DishName": dish_name,
        })

    return {
        "restaurant_id": restaurant_id,
        "from_date": from_date,
        "to_date": to_date,
        "total": len(data),
        "rows": data,
    }
