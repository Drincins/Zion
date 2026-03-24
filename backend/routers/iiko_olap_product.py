# backend/routers/iiko_olap_product.py
import json
import hashlib
import uuid
import requests
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
from datetime import date as date_cls
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Dict, Any

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.bd.database import get_db
from backend.bd.models import User, Restaurant
from backend.bd.iiko_catalog import IikoProduct, IikoProductNameHistory, IikoProductRestaurant
from backend.bd.iiko_olap import IikoOlapRow, IikoOlapRawRow
from backend.utils import get_current_user, get_user_company_ids, now_local
from backend.services.iiko_http import get_iiko_tls_verify
from backend.services.permissions import ensure_permissions, PermissionCode, has_global_access, has_permission

router = APIRouter(prefix="/iiko-olap-product", tags=["iiko-olap-product"])


# ==========================
#   ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================

def get_token(server: str, login: str, password_sha1: str) -> str:
    url = f"{server}/resto/api/auth"
    r = requests.get(url, params={"login": login, "pass": password_sha1}, verify=get_iiko_tls_verify(), timeout=60)
    r.raise_for_status()
    return r.text.strip()


def get_olap_columns(server: str, token: str, report_type: str = "SALES") -> dict:
    url = f"{server}/resto/api/v2/reports/olap/columns"
    r = requests.get(url, params={"key": token, "reportType": report_type}, verify=get_iiko_tls_verify(), timeout=60)
    r.raise_for_status()
    return r.json()


def to_iso_date(ddmmyyyy_or_iso: str) -> str:
    """
    Принимает 'DD.MM.YYYY' или 'YYYY-MM-DD' и возвращает 'YYYY-MM-DD'
    (для OpenDate.Typed -> DateRange)
    """
    s = ddmmyyyy_or_iso.strip()
    if len(s) == 10 and s[4] == '-' and s[7] == '-':
        return s
    return datetime.strptime(s, "%d.%m.%Y").strftime("%Y-%m-%d")


def to_iso_dt_start(ddmmyyyy_or_iso: str) -> str:
    """
    Для OpenDate (не Typed) -> DateTimeRange from
    """
    s = ddmmyyyy_or_iso.strip()
    if len(s) == 10 and s[4] == '-' and s[7] == '-':
        dt = datetime.strptime(s, "%Y-%m-%d")
    else:
        dt = datetime.strptime(s, "%d.%m.%Y")
    return dt.strftime("%Y-%m-%dT00:00:00.000")


def to_iso_dt_end(ddmmyyyy_or_iso: str) -> str:
    """
    Для OpenDate (не Typed) -> DateTimeRange to
    """
    s = ddmmyyyy_or_iso.strip()
    if len(s) == 10 and s[4] == '-' and s[7] == '-':
        dt = datetime.strptime(s, "%Y-%m-%d")
    else:
        dt = datetime.strptime(s, "%d.%m.%Y")
    return dt.strftime("%Y-%m-%dT23:59:59.999")


def post_olap_sales(server: str, token: str, groups: List[str], date_field: str,
                    aggregates: List[str], from_date: str, to_date: str):
    """
    Универсальный постер OLAP с корректным фильтром по дате.
    НИКАКИХ переименований — возвращаем как есть.
    """
    url = f"{server}/resto/api/v2/reports/olap"
    if date_field.endswith(".Typed"):
        filt = {
            "filterType": "DateRange",
            "periodType": "CUSTOM",
            "from": to_iso_date(from_date),
            "to": to_iso_date(to_date),
            "includeLow": True,
            "includeHigh": True
        }
    else:
        filt = {
            "filterType": "DateTimeRange",
            "periodType": "CUSTOM",
            "from": to_iso_dt_start(from_date),
            "to": to_iso_dt_end(to_date),
            "includeLow": True,
            "includeHigh": True
        }
    payload = {
        "reportType": "SALES",
        "buildSummary": False,
        "groupByRowFields": groups,
        "groupByColFields": [],
        "aggregateFields": aggregates,
        "filters": {date_field: filt}
    }
    r = requests.post(url, params={"key": token}, json=payload, verify=get_iiko_tls_verify(), timeout=180)
    return r


def fetch_products_xml(server: str, token: str, include_deleted: bool = False, revision_from: int = -1) -> ET.Element:
    url = f"{server}/resto/api/products"
    params = {"key": token, "includeDeleted": str(include_deleted).lower(), "revisionFrom": revision_from}
    r = requests.get(url, params=params, verify=get_iiko_tls_verify(), timeout=180)
    r.raise_for_status()
    return ET.fromstring(r.content)


def _extract_list_payload(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []

    for key in ("products", "data", "entities", "result", "items", "rows"):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]

    # Some endpoints can return a single object.
    if payload:
        return [payload]
    return []


def fetch_products_v2(
    server: str,
    token: str,
    *,
    include_deleted: bool = False,
    revision_from: int = -1,
) -> List[Dict[str, Any]]:
    """
    Fetch nomenclature from v2 entities endpoint.

    We try GET first and fallback to POST form for installations where only
    x-www-form-urlencoded is enabled for this method.
    """
    url = f"{server.rstrip('/')}/resto/api/v2/entities/products/list"
    query = {"includeDeleted": str(include_deleted).lower()}
    if revision_from is not None:
        query["revisionFrom"] = int(revision_from)

    response = requests.get(
        url,
        params={"key": token, **query},
        verify=get_iiko_tls_verify(),
        timeout=180,
    )
    if response.status_code in (404, 405, 415):
        response = requests.post(
            url,
            params={"key": token},
            data=query,
            verify=get_iiko_tls_verify(),
            timeout=180,
        )
    response.raise_for_status()
    return _extract_list_payload(response.json())


def fetch_assembly_charts_all(
    server: str,
    token: str,
    *,
    date_from: str,
    date_to: Optional[str] = None,
    include_deleted_products: bool = True,
    include_prepared_charts: bool = False,
) -> Dict[str, Any]:
    """
    Fetch technology cards snapshot for the requested interval.
    """
    url = f"{server.rstrip('/')}/resto/api/v2/assemblyCharts/getAll"
    params: Dict[str, Any] = {
        "key": token,
        "dateFrom": date_from,
        "includeDeletedProducts": str(include_deleted_products).lower(),
        "includePreparedCharts": str(include_prepared_charts).lower(),
    }
    if date_to:
        params["dateTo"] = date_to
    response = requests.get(url, params=params, verify=get_iiko_tls_verify(), timeout=180)
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, dict) else {}


def fetch_prices_v2(
    server: str,
    token: str,
    *,
    date_from: str,
    date_to: Optional[str] = None,
    department_id: Optional[str] = None,
    include_out_of_sale: bool = False,
    price_type: str = "BASE",
    revision_from: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Fetch prices from iiko price API.

    Expected response shape:
    {
      "result": "SUCCESS",
      "errors": [...],
      "response": [ProductPriceDto...],
      "revision": <int>
    }
    """
    url = f"{server.rstrip('/')}/resto/api/v2/price"
    params: Dict[str, Any] = {
        "key": token,
        "dateFrom": date_from,
        "includeOutOfSale": str(include_out_of_sale).lower(),
        "type": price_type,
    }
    if date_to:
        params["dateTo"] = date_to
    if department_id:
        params["departmentId"] = department_id
    if revision_from is not None:
        params["revisionFrom"] = int(revision_from)

    response = requests.get(url, params=params, verify=get_iiko_tls_verify(), timeout=180)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        return {"rows": [], "revision": None, "errors": []}
    rows = payload.get("response")
    if not isinstance(rows, list):
        rows = []
    errors = payload.get("errors")
    if not isinstance(errors, list):
        errors = []
    return {"rows": rows, "revision": payload.get("revision"), "errors": errors}


def _extract_price_from_price_item(price_item: Dict[str, Any]) -> Optional[Decimal]:
    direct = _to_decimal(price_item.get("price"))
    if direct is not None:
        return direct

    # Sometimes price is category-specific.
    per_categories = price_item.get("pricesForCategories")
    if not isinstance(per_categories, list):
        return None

    candidate: Optional[Decimal] = None
    for row in per_categories:
        if not isinstance(row, dict):
            continue
        value = _to_decimal(row.get("price"))
        if value is None:
            continue
        if candidate is None or value > candidate:
            candidate = value
    return candidate


def _select_effective_price_for_row(
    row: Dict[str, Any],
    *,
    as_of: date_cls,
) -> tuple[Optional[Decimal], bool]:
    """
    Returns (price, from_size_variant).
    from_size_variant=True means value came from row with productSizeId != null.
    """
    prices = row.get("prices")
    if not isinstance(prices, list):
        return None, bool(row.get("productSizeId"))

    candidates: List[tuple[date_cls, Decimal]] = []
    for item in prices:
        if not isinstance(item, dict):
            continue

        start = _parse_chart_date(item.get("dateFrom")) or date_cls.min
        end = _parse_chart_date(item.get("dateTo")) or date_cls.max
        if not (start <= as_of < end):
            continue

        if item.get("included") is False:
            continue

        price = _extract_price_from_price_item(item)
        if price is None:
            continue

        candidates.append((start, price))

    if not candidates:
        return None, bool(row.get("productSizeId"))

    candidates.sort(key=lambda pair: pair[0], reverse=True)
    return candidates[0][1], bool(row.get("productSizeId"))


def _build_price_map(
    price_rows: List[Dict[str, Any]],
    *,
    as_of: date_cls,
) -> Dict[str, Decimal]:
    """
    Build product_id -> best effective price.
    Prefer:
    1) non-zero over zero
    2) product-level price over size-level price
    """
    by_product: Dict[str, tuple[Decimal, bool]] = {}
    for row in price_rows:
        if not isinstance(row, dict):
            continue
        product_id = _first_non_empty_value(row, ["productId"])
        if product_id is None:
            continue
        product_id = str(product_id)

        price, from_size_variant = _select_effective_price_for_row(row, as_of=as_of)
        if price is None:
            continue

        existing = by_product.get(product_id)
        if existing is None:
            by_product[product_id] = (price, from_size_variant)
            continue

        current_price, current_from_size = existing
        current_non_zero = current_price != 0
        new_non_zero = price != 0

        should_replace = False
        if not current_non_zero and new_non_zero:
            should_replace = True
        elif current_non_zero == new_non_zero:
            # If both are either zero or non-zero, prefer product-level over size-level.
            if current_from_size and not from_size_variant:
                should_replace = True

        if should_replace:
            by_product[product_id] = (price, from_size_variant)

    return {product_id: value[0] for product_id, value in by_product.items()}


def _first_non_empty_value(payload: Optional[Dict[str, Any]], keys: List[str]) -> Optional[Any]:
    if not isinstance(payload, dict):
        return None
    for key in keys:
        if key in payload:
            value = payload.get(key)
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
    return None


def _is_uuid_text(value: Optional[str]) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    if not text:
        return False
    try:
        uuid.UUID(text)
        return True
    except Exception:
        return False


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError, TypeError):
        return None


def _find_first_numeric_by_key_fragment(
    payload: Any,
    *,
    fragments: List[str],
    max_depth: int = 5,
) -> Optional[Decimal]:
    queue: List[tuple[Any, int]] = [(payload, 0)]
    normalized = [f.lower() for f in fragments if f]
    while queue:
        node, depth = queue.pop(0)
        if depth > max_depth:
            continue
        if isinstance(node, dict):
            for key, value in node.items():
                key_lower = str(key).lower()
                if any(fragment in key_lower for fragment in normalized):
                    parsed = _to_decimal(value)
                    if parsed is not None:
                        return parsed
                if isinstance(value, (dict, list)):
                    queue.append((value, depth + 1))
        elif isinstance(node, list):
            for value in node:
                if isinstance(value, (dict, list)):
                    queue.append((value, depth + 1))
    return None


def _parse_chart_date(value: Any) -> Optional[date_cls]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _select_chart_for_date(charts: List[Dict[str, Any]], as_of: date_cls) -> Optional[Dict[str, Any]]:
    if not charts:
        return None

    active: List[Dict[str, Any]] = []
    future: List[Dict[str, Any]] = []
    past: List[Dict[str, Any]] = []

    for chart in charts:
        start = _parse_chart_date(chart.get("dateFrom"))
        end = _parse_chart_date(chart.get("dateTo"))
        if start and start > as_of:
            future.append(chart)
            continue
        if start and start <= as_of and (end is None or end > as_of):
            active.append(chart)
            continue
        past.append(chart)

    if active:
        active.sort(key=lambda row: _parse_chart_date(row.get("dateFrom")) or date_cls.min, reverse=True)
        return active[0]
    if future:
        future.sort(key=lambda row: _parse_chart_date(row.get("dateFrom")) or date_cls.max)
        return future[0]
    if past:
        past.sort(key=lambda row: _parse_chart_date(row.get("dateFrom")) or date_cls.min, reverse=True)
        return past[0]
    return charts[0]


def _build_tech_card_map(chart_result: Dict[str, Any], as_of: date_cls) -> Dict[str, Dict[str, Any]]:
    rows = chart_result.get("assemblyCharts")
    if not isinstance(rows, list):
        return {}

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        product_id = _first_non_empty_value(row, ["assembledProductId", "productId"])
        if product_id is None:
            continue
        key = str(product_id)
        grouped.setdefault(key, []).append(row)

    selected: Dict[str, Dict[str, Any]] = {}
    for product_id, charts in grouped.items():
        chart = _select_chart_for_date(charts, as_of)
        if chart is not None:
            selected[product_id] = chart
    return selected


def parse_products_xml(root: ET.Element) -> List[Dict[str, Any]]:
    """
    Возвращает список dict «как есть» (имена полей — как в наших моделях).
    """
    rows: List[Dict[str, Any]] = []

    def txt(el: ET.Element, tag: str) -> Optional[str]:
        t = el.find(tag)
        return t.text if t is not None else None

    for p in root.findall(".//productDto"):
        row: Dict[str, Any] = {
            "id": txt(p, "id"),
            "parent_id": txt(p, "parentId"),
            "num": txt(p, "num"),
            "code": txt(p, "code"),
            "name": txt(p, "name"),
            "product_type": txt(p, "productType"),
            "product_group_type": txt(p, "productGroupType"),
            "cooking_place_type": txt(p, "cookingPlaceType"),
            "main_unit": txt(p, "mainUnit"),
            "product_category": txt(p, "productCategory"),
        }

        # containers -> строка + структурированный payload
        container_rows: List[Dict[str, Any]] = []
        containers = []
        for c in p.findall("./containers/container"):
            item: Dict[str, Any] = {}
            parts = []
            for tag in (
                "id",
                "num",
                "name",
                "count",
                "minContainerWeight",
                "maxContainerWeight",
                "containerWeight",
                "fullContainerWeight",
                "density",
                "backwardRecalculation",
                "deleted",
                "useInFront",
            ):
                val = c.findtext(tag)
                if val is not None:
                    item[tag] = val
                    parts.append(f"{tag}={val}")
            if item:
                container_rows.append(item)
            containers.append(";".join(parts))
        row["containers"] = " | ".join(containers) if containers else None

        # barcodes -> строка + структурированный payload
        barcode_rows: List[Dict[str, Any]] = []
        barcodes = []
        for b in p.findall("./barcodes/barcodeContainer"):
            item: Dict[str, Any] = {}
            parts = []
            for tag in ("barcode", "containerName"):
                val = b.findtext(tag)
                if val is not None:
                    item[tag] = val
                    parts.append(f"{tag}={val}")
            if item:
                barcode_rows.append(item)
            barcodes.append(";".join(parts))
        row["barcodes"] = " | ".join(barcodes) if barcodes else None

        row["raw_payload"] = {
            "source": "products_xml_v1",
            "product": {
                "id": row["id"],
                "parent_id": row["parent_id"],
                "num": row["num"],
                "code": row["code"],
                "name": row["name"],
                "product_type": row["product_type"],
                "product_group_type": row["product_group_type"],
                "cooking_place_type": row["cooking_place_type"],
                "main_unit": row["main_unit"],
                "product_category": row["product_category"],
                "containers": container_rows,
                "barcodes": barcode_rows,
            },
        }
        row["raw_xml"] = ET.tostring(p, encoding="unicode")

        rows.append(row)

    return rows


def _parse_open_date_value(value: Optional[str]) -> Optional[date_cls]:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _build_full_olap_fields(cols: Dict[str, Any]) -> tuple[str, List[str], List[str]]:
    date_group = "OpenDate.Typed" if "OpenDate.Typed" in cols else "OpenDate"
    group_fields = [name for name, meta in cols.items() if meta.get("groupingAllowed")]
    if date_group not in group_fields and cols.get(date_group, {}).get("groupingAllowed"):
        group_fields.append(date_group)
    agg_fields = [name for name, meta in cols.items() if meta.get("aggregationAllowed")]
    return date_group, group_fields, agg_fields


def _resolve_date_range(from_date: str, to_date: str) -> tuple[date_cls, date_cls]:
    start = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date()
    end = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date()
    return start, end


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))


def _hash_payload(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _chunked(items: List[str], size: int = 1000) -> List[List[str]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def _build_processed_rows(
    db: Session,
    restaurant_id: int,
    data: List[Dict[str, Any]],
    date_group: str,
) -> List[IikoOlapRow]:
    codes = {row.get("DishCode") for row in data if row.get("DishCode")}
    product_name_by_code: Dict[str, Optional[str]] = {}
    if codes:
        # DishCode in OLAP matches `num` (article) from /products, not the quick `code`.
        q = db.query(IikoProduct.num, IikoProduct.name).filter(IikoProduct.num.in_(list(codes))).all()
        for num, name in q:
            product_name_by_code[num] = name

    seen_keys = set()
    to_insert = []
    for row in data:
        dedup_key = (row.get(date_group), row.get("Department"), row.get("DishCode"))
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        name_value = (
            row.get("DishFullName")
            or row.get("DishName")
            or row.get("DishForeignName")
        )
        if not name_value:
            code = row.get("DishCode")
            if code:
                name_value = product_name_by_code.get(code)

        rec = IikoOlapRow(
            restaurant_id=restaurant_id,
            open_date=_parse_open_date_value(row.get(date_group)),
            department=row.get("Department"),
            dish_code=row.get("DishCode"),
            dish_measure_unit=row.get("DishMeasureUnit"),
            dish_group=row.get("DishGroup"),
            cooking_place=row.get("CookingPlace"),
            non_cash_payment_type=row.get("NonCashPaymentType"),
            pay_types=row.get("PayTypes"),
            dish_amount_int=row.get("DishAmountInt"),
            dish_sum_int=row.get("DishSumInt"),
            discount_sum=row.get("DiscountSum"),
            raw_row=row,
        )

        if hasattr(rec, "dish_full_name"):
            setattr(rec, "dish_full_name", name_value)
        elif hasattr(rec, "dishfulname"):
            setattr(rec, "dishfulname", name_value)

        to_insert.append(rec)

    return to_insert


def _upsert_raw_rows(
    db: Session,
    restaurant_id: int,
    data: List[Dict[str, Any]],
    date_group: str,
    group_fields: List[str],
) -> Dict[str, int]:
    group_fields_sorted = sorted(group_fields)
    prepared = []
    row_keys: List[str] = []
    for row in data:
        key_payload = {field: row.get(field) for field in group_fields_sorted}
        row_key = _hash_payload(key_payload)
        row_keys.append(row_key)
        prepared.append(
            (
                row_key,
                _hash_payload(row),
                _parse_open_date_value(row.get(date_group)),
                row,
            )
        )

    existing: Dict[str, IikoOlapRawRow] = {}
    for chunk in _chunked(row_keys):
        if not chunk:
            continue
        rows = (
            db.query(IikoOlapRawRow)
            .filter(IikoOlapRawRow.restaurant_id == restaurant_id, IikoOlapRawRow.row_key.in_(chunk))
            .all()
        )
        for row in rows:
            existing[row.row_key] = row

    inserted = 0
    updated = 0
    skipped = 0
    now = now_local()
    for row_key, payload_hash, open_date, payload in prepared:
        current = existing.get(row_key)
        if current is None:
            current = IikoOlapRawRow(
                restaurant_id=restaurant_id,
                open_date=open_date,
                row_key=row_key,
                payload_hash=payload_hash,
                payload=payload,
                updated_at=now,
            )
            db.add(current)
            existing[row_key] = current
            inserted += 1
            continue
        if current.payload_hash == payload_hash:
            skipped += 1
            continue
        current.payload = payload
        current.payload_hash = payload_hash
        current.open_date = open_date
        current.updated_at = now
        updated += 1

    return {"inserted": inserted, "updated": updated, "skipped": skipped}


def ensure_user_access_to_restaurant(db: Session, current_user: User, restaurant_id: int) -> Restaurant:
    query = db.query(Restaurant).filter(Restaurant.id == restaurant_id)
    if not has_global_access(current_user):
        company_ids = sorted(get_user_company_ids(db, current_user) or [])
        if company_ids:
            query = query.filter(Restaurant.company_id.in_(company_ids))
            if not (
                has_permission(current_user, PermissionCode.IIKO_MANAGE)
                or has_permission(current_user, PermissionCode.IIKO_CATALOG_SYNC)
            ):
                query = query.filter(Restaurant.users.contains(current_user))
        else:
            query = query.filter(Restaurant.users.contains(current_user))
    restaurant = query.first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or unavailable")
    return restaurant


def ensure_iiko_credentials(restaurant: Restaurant) -> None:
    if not restaurant.server or not restaurant.iiko_login or not restaurant.iiko_password_sha1:
        raise HTTPException(status_code=400, detail="Restaurant has no iiko credentials configured")


# ==========================
#         СХЕМЫ
# ==========================

from pydantic import BaseModel

class SyncOlapRequest(BaseModel):
    restaurant_id: int
    from_date: str  # 'DD.MM.YYYY' или 'YYYY-MM-DD' — как удобно
    to_date: str    # 'DD.MM.YYYY' или 'YYYY-MM-DD'


class SyncProductsRequest(BaseModel):
    restaurant_id: int
    include_deleted: bool = False
    revision_from: int = -1


# ==========================
#        ЭНДПОИНТЫ
# ==========================

@router.post("/sync-olap")
def sync_olap(
    payload: SyncOlapRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Тянем OLAP SALES «как есть» и сохраняем в iiko_olap_rows.
    Теперь дата включена в группировки и сохраняется в open_date.
    """
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    restaurant = ensure_user_access_to_restaurant(db, current_user, payload.restaurant_id)

    token = get_token(restaurant.server, restaurant.iiko_login, restaurant.iiko_password_sha1)
    cols = get_olap_columns(restaurant.server, token, report_type="SALES")

    # дата: используем и как фильтр, и как поле группировки
    date_group = "OpenDate.Typed" if "OpenDate.Typed" in cols else "OpenDate"
    date_field = date_group

    wanted_groups = [
        date_group,               # дата обязательно в группах
        "Department",
        "DishCode",
        "DishFullName",
        "DishName",               # <- добавлено
        "DishMeasureUnit",
        "DishGroup",
        "CookingPlace",
        "NonCashPaymentType",
        "PayTypes",
    ]
    group_fields = [g for g in wanted_groups if cols.get(g, {}).get("groupingAllowed")]

    wanted_aggs = ["DishSumInt", "DiscountSum", "DishAmountInt"]
    agg_fields = [a for a in wanted_aggs if cols.get(a, {}).get("aggregationAllowed")]

    if not agg_fields:
        raise HTTPException(status_code=400, detail="Нет разрешённых агрегатов в OLAP.")

    r = post_olap_sales(
        restaurant.server, token, group_fields, date_field, agg_fields,
        payload.from_date, payload.to_date
    )
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text[:400])

    data = r.json().get("data", [])
    if not data:
        return {"status": "ok", "inserted": 0, "message": "No OLAP data returned", "groups": group_fields, "aggregates": agg_fields}

    to_insert = _build_processed_rows(db, payload.restaurant_id, data, date_group)
    if to_insert:
        db.add_all(to_insert)
        db.commit()

    return {
        "status": "ok",
        "restaurant": restaurant.name,
        "groups": group_fields,
        "aggregates": agg_fields,
        "inserted": len(to_insert),
        "from_date": payload.from_date,
        "to_date": payload.to_date,
    }


def sync_olap_sales_full(
    db: Session,
    restaurant: Restaurant,
    from_date: str,
    to_date: str,
) -> Dict[str, Any]:
    token = get_token(restaurant.server, restaurant.iiko_login, restaurant.iiko_password_sha1)
    cols = get_olap_columns(restaurant.server, token, report_type="SALES")
    date_group, group_fields, agg_fields = _build_full_olap_fields(cols)

    if not group_fields:
        raise HTTPException(status_code=400, detail="No OLAP grouping fields available")
    if not agg_fields:
        raise HTTPException(status_code=400, detail="No OLAP aggregation fields available")

    r = post_olap_sales(
        restaurant.server,
        token,
        group_fields,
        date_group,
        agg_fields,
        from_date,
        to_date,
    )
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text[:400])

    data = r.json().get("data", [])
    if not data:
        return {
            "status": "ok",
            "restaurant": restaurant.name,
            "groups": group_fields,
            "aggregates": agg_fields,
            "inserted_raw": 0,
            "updated_raw": 0,
            "skipped_raw": 0,
            "from_date": from_date,
            "to_date": to_date,
        }

    stats = _upsert_raw_rows(db, restaurant.id, data, date_group, group_fields)
    db.commit()

    return {
        "status": "ok",
        "restaurant": restaurant.name,
        "groups": group_fields,
        "aggregates": agg_fields,
        "inserted_raw": stats["inserted"],
        "updated_raw": stats["updated"],
        "skipped_raw": stats["skipped"],
        "from_date": from_date,
        "to_date": to_date,
    }


@router.post("/sync-olap-full")
def sync_olap_full(
    payload: SyncOlapRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    restaurant = ensure_user_access_to_restaurant(db, current_user, payload.restaurant_id)
    return sync_olap_sales_full(db, restaurant, payload.from_date, payload.to_date)


@router.post("/sync-products")
def sync_products(
    payload: SyncProductsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch /resto/api/products (XML) and sync it into the canonical catalog:
    - iiko_products (global by iiko GUID)
    - iiko_product_restaurants (presence per restaurant)
    - iiko_product_name_history (name change history)
    """
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE, PermissionCode.IIKO_CATALOG_SYNC)
    restaurant = ensure_user_access_to_restaurant(db, current_user, payload.restaurant_id)
    ensure_iiko_credentials(restaurant)

    token = get_token(restaurant.server, restaurant.iiko_login, restaurant.iiko_password_sha1)
    root = fetch_products_xml(restaurant.server, token,
                              include_deleted=payload.include_deleted,
                              revision_from=payload.revision_from)

    parsed = parse_products_xml(root)
    if not parsed:
        return {"status": "ok", "restaurant": restaurant.name, "upserted": 0, "message": "Empty /products response"}

    sync_date = now_local().date()
    v2_rows: List[Dict[str, Any]] = []
    v2_error: Optional[str] = None
    try:
        v2_rows = fetch_products_v2(
            restaurant.server,
            token,
            include_deleted=payload.include_deleted,
            revision_from=payload.revision_from,
        )
    except Exception as exc:
        # Keep XML sync working even on installations without entities/products/list support.
        v2_error = str(exc)[:400]

    v2_by_id: Dict[str, Dict[str, Any]] = {}
    for row in v2_rows:
        row_id = _first_non_empty_value(row, ["id"])
        if row_id is None:
            continue
        v2_by_id[str(row_id)] = row

    chart_payload: Dict[str, Any] = {}
    tech_cards_error: Optional[str] = None
    try:
        chart_payload = fetch_assembly_charts_all(
            restaurant.server,
            token,
            date_from=sync_date.isoformat(),
            date_to=None,
            include_deleted_products=payload.include_deleted,
            include_prepared_charts=False,
        )
    except Exception as exc:
        # Tech cards are optional enrichment for catalog sync.
        tech_cards_error = str(exc)[:400]

    tech_card_by_product_id = _build_tech_card_map(chart_payload, sync_date)

    price_rows: List[Dict[str, Any]] = []
    price_revision: Optional[int] = None
    price_errors: List[Any] = []
    price_error: Optional[str] = None
    try:
        price_payload = fetch_prices_v2(
            restaurant.server,
            token,
            date_from=sync_date.isoformat(),
            date_to=None,
            department_id=(restaurant.department_code if _is_uuid_text(restaurant.department_code) else None),
            include_out_of_sale=False,
            price_type="BASE",
            revision_from=None,
        )
        rows = price_payload.get("rows")
        if isinstance(rows, list):
            price_rows = [row for row in rows if isinstance(row, dict)]
        revision_value = price_payload.get("revision")
        if isinstance(revision_value, int):
            price_revision = revision_value
        errors_value = price_payload.get("errors")
        if isinstance(errors_value, list):
            price_errors = errors_value
    except Exception as exc:
        # Price API is optional enrichment.
        price_error = str(exc)[:400]

    price_by_product_id = _build_price_map(price_rows, as_of=sync_date)

    now = now_local()
    company_id = restaurant.company_id

    product_ids = [str(p.get("id")) for p in parsed if p.get("id")]
    existing_names: Dict[str, Optional[str]] = {}
    if product_ids:
        rows = db.query(IikoProduct.id, IikoProduct.name).filter(IikoProduct.id.in_(product_ids)).all()
        existing_names = {str(pid): name for pid, name in rows}

    name_history_rows: List[IikoProductNameHistory] = []
    products_payload: List[Dict[str, Any]] = []
    links_payload: List[Dict[str, Any]] = []

    for p in parsed:
        pid = p.get("id")
        if not pid:
            continue
        pid = str(pid)

        v2_row = v2_by_id.get(pid) or {}
        tech_card = tech_card_by_product_id.get(pid)

        # Prefer v2 payload for product master data where available.
        product_type = _first_non_empty_value(v2_row, ["type", "productType"]) or p.get("product_type")
        product_group_type = _first_non_empty_value(v2_row, ["productGroupType"]) or p.get("product_group_type")
        product_category = _first_non_empty_value(
            v2_row,
            ["productCategory", "category", "categoryName"],
        ) or p.get("product_category")
        main_unit = _first_non_empty_value(v2_row, ["mainUnit", "unit"]) or p.get("main_unit")
        code = _first_non_empty_value(v2_row, ["code"]) or p.get("code")
        num = _first_non_empty_value(v2_row, ["num"]) or p.get("num")
        parent_id = _first_non_empty_value(v2_row, ["parentId", "parent"]) or p.get("parent_id")
        tech_card_id = _first_non_empty_value(tech_card, ["id"])
        tech_card_date_from = _parse_chart_date(_first_non_empty_value(tech_card, ["dateFrom"]))
        tech_card_date_to = _parse_chart_date(_first_non_empty_value(tech_card, ["dateTo"]))

        default_sale_price = price_by_product_id.get(pid)
        if default_sale_price is None:
            default_sale_price = _to_decimal(_first_non_empty_value(v2_row, ["defaultSalePrice", "salePrice"]))
        estimated_cost = _to_decimal(
            _first_non_empty_value(
                v2_row,
                ["estimatedPurchasePrice", "estimatedCost", "estimatedPrimeCost", "primeCost", "costPrice"],
            )
        )
        if estimated_cost is None:
            estimated_cost = _find_first_numeric_by_key_fragment(
                v2_row,
                fragments=["estimated", "prime", "cost"],
            )

        merged_raw_payload: Dict[str, Any] = {}
        if isinstance(p.get("raw_payload"), dict):
            merged_raw_payload.update(p["raw_payload"])
        if v2_row:
            merged_raw_payload["v2_product"] = v2_row
        if tech_card:
            merged_raw_payload["tech_card"] = tech_card

        new_name = p.get("name")
        old_name = existing_names.get(pid)
        if old_name is not None and new_name is not None and str(old_name) != str(new_name):
            name_history_rows.append(
                IikoProductNameHistory(
                    product_id=pid,
                    restaurant_id=restaurant.id,
                    old_name=old_name,
                    new_name=str(new_name),
                )
            )

        products_payload.append(
            {
                "id": pid,
                "company_id": company_id,
                "source_restaurant_id": restaurant.id,
                "parent_id": parent_id,
                "num": num,
                "code": code,
                "name": new_name,
                "product_type": product_type,
                "product_group_type": product_group_type,
                "cooking_place_type": p.get("cooking_place_type"),
                "main_unit": main_unit,
                "product_category": product_category,
                "containers": p.get("containers"),
                "barcodes": p.get("barcodes"),
                "default_sale_price": default_sale_price,
                "estimated_cost": estimated_cost,
                "tech_card_id": str(tech_card_id) if tech_card_id is not None else None,
                "tech_card_date_from": tech_card_date_from,
                "tech_card_date_to": tech_card_date_to,
                "tech_card_payload": tech_card,
                "raw_v2_payload": v2_row or None,
                "raw_payload": merged_raw_payload or None,
                "raw_xml": p.get("raw_xml"),
                "updated_at": now,
                "last_seen_at": now,
            }
        )
        links_payload.append(
            {
                "product_id": pid,
                "restaurant_id": restaurant.id,
                "last_seen_at": now,
            }
        )

    if products_payload:
        stmt = insert(IikoProduct).values(products_payload)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "company_id": sa.func.coalesce(stmt.excluded.company_id, IikoProduct.company_id),
                "source_restaurant_id": sa.func.coalesce(IikoProduct.source_restaurant_id, stmt.excluded.source_restaurant_id),
                "parent_id": sa.func.coalesce(stmt.excluded.parent_id, IikoProduct.parent_id),
                "num": sa.func.coalesce(stmt.excluded.num, IikoProduct.num),
                "code": sa.func.coalesce(stmt.excluded.code, IikoProduct.code),
                "name": sa.func.coalesce(stmt.excluded.name, IikoProduct.name),
                "product_type": sa.func.coalesce(stmt.excluded.product_type, IikoProduct.product_type),
                "product_group_type": sa.func.coalesce(stmt.excluded.product_group_type, IikoProduct.product_group_type),
                "cooking_place_type": sa.func.coalesce(stmt.excluded.cooking_place_type, IikoProduct.cooking_place_type),
                "main_unit": sa.func.coalesce(stmt.excluded.main_unit, IikoProduct.main_unit),
                "product_category": sa.func.coalesce(stmt.excluded.product_category, IikoProduct.product_category),
                "containers": sa.func.coalesce(stmt.excluded.containers, IikoProduct.containers),
                "barcodes": sa.func.coalesce(stmt.excluded.barcodes, IikoProduct.barcodes),
                "default_sale_price": sa.case(
                    (
                        sa.and_(
                            stmt.excluded.default_sale_price.isnot(None),
                            stmt.excluded.default_sale_price != 0,
                        ),
                        stmt.excluded.default_sale_price,
                    ),
                    else_=sa.func.coalesce(IikoProduct.default_sale_price, stmt.excluded.default_sale_price),
                ),
                "estimated_cost": sa.case(
                    (
                        sa.and_(
                            stmt.excluded.estimated_cost.isnot(None),
                            stmt.excluded.estimated_cost != 0,
                        ),
                        stmt.excluded.estimated_cost,
                    ),
                    else_=sa.func.coalesce(IikoProduct.estimated_cost, stmt.excluded.estimated_cost),
                ),
                "tech_card_id": sa.func.coalesce(stmt.excluded.tech_card_id, IikoProduct.tech_card_id),
                "tech_card_date_from": sa.func.coalesce(stmt.excluded.tech_card_date_from, IikoProduct.tech_card_date_from),
                "tech_card_date_to": sa.func.coalesce(stmt.excluded.tech_card_date_to, IikoProduct.tech_card_date_to),
                "tech_card_payload": sa.func.coalesce(stmt.excluded.tech_card_payload, IikoProduct.tech_card_payload),
                "raw_v2_payload": sa.func.coalesce(stmt.excluded.raw_v2_payload, IikoProduct.raw_v2_payload),
                "raw_payload": sa.func.coalesce(stmt.excluded.raw_payload, IikoProduct.raw_payload),
                "raw_xml": sa.func.coalesce(stmt.excluded.raw_xml, IikoProduct.raw_xml),
                "updated_at": stmt.excluded.updated_at,
                "last_seen_at": stmt.excluded.last_seen_at,
            },
        )
        db.execute(stmt)

    if links_payload:
        stmt = insert(IikoProductRestaurant).values(links_payload)
        stmt = stmt.on_conflict_do_update(
            index_elements=["product_id", "restaurant_id"],
            set_={
                "last_seen_at": stmt.excluded.last_seen_at,
            },
        )
        db.execute(stmt)

    if name_history_rows:
        db.add_all(name_history_rows)

    db.commit()

    return {
        "status": "ok",
        "restaurant": restaurant.name,
        "upserted": len(products_payload),
        "product_restaurant_links": len(links_payload),
        "name_changes": len(name_history_rows),
        "v2_products": len(v2_by_id),
        "tech_cards": len(tech_card_by_product_id),
        "price_rows": len(price_rows),
        "price_products": len(price_by_product_id),
        "price_revision": price_revision,
        "price_errors_count": len(price_errors),
        "v2_error": v2_error,
        "tech_cards_error": tech_cards_error,
        "price_error": price_error,
        "include_deleted": payload.include_deleted,
        "revision_from": payload.revision_from,
    }


class SyncProductsNetworkRequest(BaseModel):
    restaurant_ids: Optional[List[int]] = None
    include_deleted: bool = False
    revision_from: int = -1
    stop_on_error: bool = False


@router.post("/sync-products-network")
def sync_products_network(
    payload: SyncProductsNetworkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sync product catalog from multiple restaurants sequentially.

    If restaurant_ids is omitted, will sync all restaurants available to the user.
    """
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE, PermissionCode.IIKO_CATALOG_SYNC)

    if payload.restaurant_ids:
        restaurants = [ensure_user_access_to_restaurant(db, current_user, rid) for rid in payload.restaurant_ids]
    else:
        q = db.query(Restaurant)
        if not has_global_access(current_user):
            company_ids = sorted(get_user_company_ids(db, current_user) or [])
            if company_ids:
                q = q.filter(Restaurant.company_id.in_(company_ids))
                if not (
                    has_permission(current_user, PermissionCode.IIKO_MANAGE)
                    or has_permission(current_user, PermissionCode.IIKO_CATALOG_SYNC)
                ):
                    q = q.filter(Restaurant.users.contains(current_user))
            else:
                q = q.filter(Restaurant.users.contains(current_user))
        restaurants = q.order_by(Restaurant.id.asc()).all()

    results: List[Dict[str, Any]] = []
    totals = {
        "restaurants": 0,
        "upserted": 0,
        "links": 0,
        "name_changes": 0,
        "v2_products": 0,
        "tech_cards": 0,
        "price_rows": 0,
        "price_products": 0,
        "skipped": 0,
        "errors": 0,
    }

    for r in restaurants:
        totals["restaurants"] += 1
        if not r.server or not r.iiko_login or not r.iiko_password_sha1:
            totals["skipped"] += 1
            results.append(
                {
                    "restaurant_id": r.id,
                    "restaurant": r.name,
                    "status": "skipped",
                    "detail": "No iiko credentials configured",
                }
            )
            continue

        try:
            res = sync_products(
                SyncProductsRequest(
                    restaurant_id=r.id,
                    include_deleted=payload.include_deleted,
                    revision_from=payload.revision_from,
                ),
                db=db,
                current_user=current_user,
            )
            results.append({"restaurant_id": r.id, "restaurant": r.name, **res})
            totals["upserted"] += int(res.get("upserted") or 0)
            totals["links"] += int(res.get("product_restaurant_links") or 0)
            totals["name_changes"] += int(res.get("name_changes") or 0)
            totals["v2_products"] += int(res.get("v2_products") or 0)
            totals["tech_cards"] += int(res.get("tech_cards") or 0)
            totals["price_rows"] += int(res.get("price_rows") or 0)
            totals["price_products"] += int(res.get("price_products") or 0)
        except HTTPException as e:
            totals["errors"] += 1
            results.append(
                {
                    "restaurant_id": r.id,
                    "restaurant": r.name,
                    "status": "error",
                    "detail": e.detail,
                }
            )
            if payload.stop_on_error:
                raise
        except Exception as e:
            totals["errors"] += 1
            results.append(
                {
                    "restaurant_id": r.id,
                    "restaurant": r.name,
                    "status": "error",
                    "detail": str(e)[:400],
                }
            )
            if payload.stop_on_error:
                raise HTTPException(status_code=500, detail=str(e)[:400])

    totals["restaurants"] = len(restaurants)
    return {"status": "ok", "totals": totals, "results": results}


class SyncBothRequest(BaseModel):
    restaurant_id: int
    from_date: str
    to_date: str
    include_deleted: bool = False
    revision_from: int = -1


@router.post("/sync-both")
def sync_both(payload: SyncBothRequest,
              db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    """
    Последовательно вызывает sync-olap и sync-products.
    """
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    # OLAP
    olap_res = sync_olap(
        SyncOlapRequest(
            restaurant_id=payload.restaurant_id,
            from_date=payload.from_date,
            to_date=payload.to_date
        ),
        db=db,
        current_user=current_user
    )

    # PRODUCTS
    prod_res = sync_products(
        SyncProductsRequest(
            restaurant_id=payload.restaurant_id,
            include_deleted=payload.include_deleted,
            revision_from=payload.revision_from
        ),
        db=db,
        current_user=current_user
    )

    return {
        "status": "ok",
        "olap": olap_res,
        "products": prod_res,
    }
