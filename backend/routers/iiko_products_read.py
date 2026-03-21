# backend/routers/iiko_products_read.py
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.bd.database import get_db
from backend.bd.iiko_catalog import IikoProduct, IikoProductRestaurant, IikoProductSetting
from backend.bd.models import Restaurant, User
from backend.schemas import IikoProductRead
from backend.services.permissions import (
    PermissionCode,
    ensure_permissions,
    has_global_access,
    has_permission,
)
from backend.utils import get_current_user

router = APIRouter(prefix="/iiko-products", tags=["iiko-products-read"])

SALES_DISHES_VIEW_PERMISSIONS = (
    PermissionCode.SALES_DISHES_VIEW,
    PermissionCode.SALES_DISHES_MANAGE,
    PermissionCode.IIKO_VIEW,
    PermissionCode.IIKO_MANAGE,
)
SALES_DISHES_MANAGE_PERMISSIONS = (
    PermissionCode.SALES_DISHES_MANAGE,
    PermissionCode.IIKO_MANAGE,
)


def ensure_user_access_to_restaurant(db: Session, current_user: User, restaurant_id: int) -> Restaurant:
    if has_global_access(current_user) or has_permission(current_user, PermissionCode.IIKO_MANAGE):
        restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    else:
        restaurant = (
            db.query(Restaurant)
            .filter(Restaurant.id == restaurant_id, Restaurant.users.contains(current_user))
            .first()
        )
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or unavailable")
    return restaurant


def _to_float(value):
    if value is None:
        return None
    return float(value)


def _to_decimal(value: Optional[float]) -> Optional[Decimal]:
    if value is None:
        return None
    return Decimal(str(value))


def _to_nullable_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    clean = str(value).strip()
    return clean or None


def _effective_group_expr():
    return sa.func.coalesce(
        sa.nullif(IikoProductSetting.custom_product_group_type, ""),
        IikoProduct.product_group_type,
    )


def _effective_category_expr():
    return sa.func.coalesce(
        sa.nullif(IikoProductSetting.custom_product_category, ""),
        IikoProduct.product_category,
    )


def _serialize_product(
    product: IikoProduct,
    settings: Optional[IikoProductSetting] = None,
) -> dict:
    custom_group = getattr(settings, "custom_product_group_type", None)
    custom_category = getattr(settings, "custom_product_category", None)
    product_group_type = custom_group if custom_group not in (None, "") else product.product_group_type
    product_category = custom_category if custom_category not in (None, "") else product.product_category

    return {
        "id": product.id,
        "company_id": product.company_id,
        "source_restaurant_id": product.source_restaurant_id,
        "parent_id": product.parent_id,
        "num": product.num,
        "code": product.code,
        "name": product.name,
        "product_type": product.product_type,
        "product_group_type": product_group_type,
        "iiko_product_group_type": product.product_group_type,
        "custom_product_group_type": custom_group,
        "cooking_place_type": product.cooking_place_type,
        "main_unit": product.main_unit,
        "product_category": product_category,
        "iiko_product_category": product.product_category,
        "custom_product_category": custom_category,
        "containers": product.containers,
        "barcodes": product.barcodes,
        "default_sale_price": _to_float(product.default_sale_price),
        "estimated_cost": _to_float(product.estimated_cost),
        "tech_card_id": product.tech_card_id,
        "tech_card_date_from": product.tech_card_date_from,
        "tech_card_date_to": product.tech_card_date_to,
        "tech_card_payload": product.tech_card_payload,
        "raw_v2_payload": product.raw_v2_payload,
        "raw_payload": product.raw_payload,
        "raw_xml": product.raw_xml,
        "portion_coef_kitchen": _to_float(getattr(settings, "portion_coef_kitchen", None)),
        "portion_coef_hall": _to_float(getattr(settings, "portion_coef_hall", None)),
        "created_at": product.created_at,
        "updated_at": product.updated_at,
        "last_seen_at": product.last_seen_at,
    }


class ProductSettingsUpdateRequest(BaseModel):
    portion_coef_kitchen: Optional[float] = None
    portion_coef_hall: Optional[float] = None
    product_group_type: Optional[str] = None
    product_category: Optional[str] = None


@router.get("/rows", response_model=List[IikoProductRead])
def list_product_rows(
    restaurant_id: Optional[int] = Query(None),
    code: Optional[str] = Query(None, description="search by code (LIKE)"),
    name: Optional[str] = Query(None, description="search by name (LIKE)"),
    product_type: Optional[str] = Query(None, description="GOODS/DISH/PREPARED/..."),
    product_group_type: Optional[str] = Query(None, description="PRODUCTS/MODIFIERS"),
    product_category: Optional[str] = Query(None, description="product category"),
    main_unit: Optional[str] = Query(None),
    only_present: bool = Query(False),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_DISHES_VIEW_PERMISSIONS)

    if restaurant_id is not None:
        ensure_user_access_to_restaurant(db, current_user, restaurant_id)

    q = (
        db.query(
            IikoProduct,
            IikoProductSetting,
        )
        .outerjoin(IikoProductSetting, IikoProductSetting.product_id == IikoProduct.id)
    )

    if getattr(current_user, "company_id", None) is not None:
        q = q.filter(IikoProduct.company_id == current_user.company_id)

    if restaurant_id is not None and only_present:
        q = (
            q.join(IikoProductRestaurant, IikoProductRestaurant.product_id == IikoProduct.id)
            .filter(IikoProductRestaurant.restaurant_id == restaurant_id)
        )

    if code:
        q = q.filter(IikoProduct.code.ilike(f"%{code}%"))
    if name:
        q = q.filter(IikoProduct.name.ilike(f"%{name}%"))
    if product_type:
        q = q.filter(IikoProduct.product_type == product_type)
    if product_group_type:
        q = q.filter(_effective_group_expr() == product_group_type)
    if product_category:
        q = q.filter(_effective_category_expr() == product_category)
    if main_unit:
        q = q.filter(IikoProduct.main_unit.ilike(f"%{main_unit}%"))

    q = q.order_by(IikoProduct.name.asc().nullslast())

    rows = q.offset(offset).limit(limit).all()
    return [_serialize_product(product, settings=settings) for product, settings in rows]


@router.get("/distinct")
def product_distincts(
    field: str = Query(..., description="one of: product_type, product_group_type, product_category, main_unit"),
    restaurant_id: Optional[int] = Query(None),
    only_present: bool = Query(False, description="If true, only values present in the selected restaurant catalog"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_DISHES_VIEW_PERMISSIONS)

    if restaurant_id is not None:
        ensure_user_access_to_restaurant(db, current_user, restaurant_id)

    q = db.query(IikoProduct.id).select_from(IikoProduct)

    if field == "product_type":
        col = IikoProduct.product_type
    elif field == "product_group_type":
        col = _effective_group_expr().label("product_group_type")
        q = q.outerjoin(IikoProductSetting, IikoProductSetting.product_id == IikoProduct.id)
    elif field == "product_category":
        col = _effective_category_expr().label("product_category")
        q = q.outerjoin(IikoProductSetting, IikoProductSetting.product_id == IikoProduct.id)
    elif field == "main_unit":
        col = IikoProduct.main_unit
    else:
        raise HTTPException(status_code=400, detail=f"Invalid field '{field}'")
    q = q.with_entities(col)

    if getattr(current_user, "company_id", None) is not None:
        q = q.filter(IikoProduct.company_id == current_user.company_id)

    if only_present:
        if restaurant_id is None:
            raise HTTPException(status_code=400, detail="restaurant_id is required when only_present=true")
        q = (
            q.join(IikoProductRestaurant, IikoProductRestaurant.product_id == IikoProduct.id)
            .filter(IikoProductRestaurant.restaurant_id == restaurant_id)
        )

    values = q.filter(col.isnot(None)).distinct().order_by(col.asc()).all()
    return [v[0] for v in values]


@router.patch("/rows/{product_id}/settings", response_model=IikoProductRead)
def update_product_settings(
    product_id: str,
    payload: ProductSettingsUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_DISHES_MANAGE_PERMISSIONS)

    q = db.query(IikoProduct).filter(IikoProduct.id == product_id)
    if getattr(current_user, "company_id", None) is not None:
        q = q.filter(IikoProduct.company_id == current_user.company_id)
    product = q.first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    setting = db.query(IikoProductSetting).filter(IikoProductSetting.product_id == product.id).first()
    if not setting:
        setting = IikoProductSetting(product_id=product.id)
        db.add(setting)

    fields_set = payload.model_fields_set
    if "portion_coef_kitchen" in fields_set:
        setting.portion_coef_kitchen = _to_decimal(payload.portion_coef_kitchen)
    if "portion_coef_hall" in fields_set:
        setting.portion_coef_hall = _to_decimal(payload.portion_coef_hall)
    if "product_group_type" in fields_set:
        setting.custom_product_group_type = _to_nullable_text(payload.product_group_type)
    if "product_category" in fields_set:
        setting.custom_product_category = _to_nullable_text(payload.product_category)

    db.commit()

    return _serialize_product(product, settings=setting)
