from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from backend.services.iiko_sales_layouts import normalize_location_token
from backend.services.iiko_sales_report_dimensions import clean_optional_text

PAYMENT_ID_NAME_FIELDS: List[tuple[str, str]] = [
    ("PayTypes.GUID", "PayTypes"),
    ("NonCashPaymentType.Id", "NonCashPaymentType"),
    ("PaymentType.Id", "PaymentType"),
]

PAYMENT_NAME_ONLY_FIELDS: List[str] = [
    "PayTypes",
    "NonCashPaymentType",
    "PaymentType",
]

DISH_WAITER_GROUP_FIELDS: List[str] = [
    "DishWaiter.Id",
    "DishWaiter.Name",
    "DishWaiter",
    "DishWaiter.Code",
    "DishSeller.Id",
    "DishSeller.Name",
    "DishSeller",
    "DishSeller.Code",
    "DishEmployee.Id",
    "DishEmployee.Name",
    "DishEmployee",
    "DishEmployee.Code",
    "Waiter.Id",
    "Waiter.Name",
    "Waiter",
    "Waiter.Code",
    "WaiterName",
]

DISH_WAITER_FIELD_SETS: List[Dict[str, Any]] = [
    {
        "source": "DishWaiter",
        "id_keys": ["DishWaiter.Id"],
        "name_keys": ["DishWaiter.Name", "DishWaiter"],
        "code_keys": ["DishWaiter.Code"],
    },
    {
        "source": "DishSeller",
        "id_keys": ["DishSeller.Id"],
        "name_keys": ["DishSeller.Name", "DishSeller"],
        "code_keys": ["DishSeller.Code"],
    },
    {
        "source": "DishEmployee",
        "id_keys": ["DishEmployee.Id"],
        "name_keys": ["DishEmployee.Name", "DishEmployee"],
        "code_keys": ["DishEmployee.Code"],
    },
    {
        "source": "Waiter",
        "id_keys": ["Waiter.Id"],
        "name_keys": ["Waiter.Name", "Waiter"],
        "code_keys": ["Waiter.Code"],
    },
    {
        "source": "WaiterName",
        "id_keys": [],
        "name_keys": ["WaiterName"],
        "code_keys": [],
    },
]

ORDER_ID_FIELD_CANDIDATES: List[str] = [
    "UniqOrderId.Id",
    "UniqOrderId",
    "OrderId.Id",
    "OrderId",
    "Order.Id",
    "OrderGUID",
    "OrderGuid",
]


def build_synthetic_payment_guid(name: str) -> str:
    digest = hashlib.sha1(name.casefold().encode("utf-8")).hexdigest()
    return f"name::{digest}"


def build_synthetic_non_cash_id(name: str) -> str:
    digest = hashlib.sha1(name.casefold().encode("utf-8")).hexdigest()
    return f"non_cash_name::{digest}"


def normalize_payment_method(raw_guid: Any, raw_name: Any) -> tuple[Optional[str], Optional[str]]:
    guid = clean_optional_text(raw_guid)
    name = clean_optional_text(raw_name)

    if guid and name:
        return guid, name
    if guid and not name:
        return guid, guid
    if name:
        return build_synthetic_payment_guid(name), name
    return None, None


def normalize_non_cash_type(raw_id: Any, raw_name: Any) -> tuple[Optional[str], Optional[str]]:
    non_cash_id = clean_optional_text(raw_id)
    non_cash_name = clean_optional_text(raw_name)

    if non_cash_id and non_cash_name:
        return non_cash_id, non_cash_name
    if non_cash_id and not non_cash_name:
        return non_cash_id, non_cash_id
    if non_cash_name:
        return build_synthetic_non_cash_id(non_cash_name), non_cash_name
    return None, None


def extract_non_cash_fields(payload: Any) -> tuple[Optional[str], Optional[str]]:
    if not isinstance(payload, dict):
        return None, None

    return normalize_non_cash_type(
        payload.get("NonCashPaymentType.Id"),
        payload.get("NonCashPaymentType"),
    )


def select_payment_group_fields(cols: Dict[str, Any]) -> List[str]:
    for guid_field, name_field in PAYMENT_ID_NAME_FIELDS:
        if cols.get(guid_field, {}).get("groupingAllowed") and cols.get(name_field, {}).get("groupingAllowed"):
            return [guid_field, name_field]

    for name_field in PAYMENT_NAME_ONLY_FIELDS:
        if cols.get(name_field, {}).get("groupingAllowed"):
            return [name_field]

    for guid_field, _name_field in PAYMENT_ID_NAME_FIELDS:
        if cols.get(guid_field, {}).get("groupingAllowed"):
            return [guid_field]

    return []


def extract_payment_method_fields(payload: Any) -> tuple[Optional[str], Optional[str]]:
    if not isinstance(payload, dict):
        return None, None

    for guid_field, name_field in PAYMENT_ID_NAME_FIELDS:
        guid, name = normalize_payment_method(payload.get(guid_field), payload.get(name_field))
        if guid or name:
            return guid, name

    for name_field in PAYMENT_NAME_ONLY_FIELDS:
        guid, name = normalize_payment_method(None, payload.get(name_field))
        if guid or name:
            return guid, name

    for guid_field, _name_field in PAYMENT_ID_NAME_FIELDS:
        guid, name = normalize_payment_method(payload.get(guid_field), None)
        if guid or name:
            return guid, name

    return None, None


def extract_payload_text(payload: Any, key: str) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    value = payload.get(key)
    if value is None:
        return None
    clean = str(value).strip()
    return clean or None


def extract_payload_text_any(payload: Any, keys: List[str]) -> Optional[str]:
    for key in keys:
        value = extract_payload_text(payload, key)
        if value:
            return value
    return None


def extract_dish_waiter_fields(payload: Any) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    if not isinstance(payload, dict):
        return None, None, None, None

    for field_set in DISH_WAITER_FIELD_SETS:
        iiko_id = extract_payload_text_any(payload, field_set.get("id_keys", []))
        name = extract_payload_text_any(payload, field_set.get("name_keys", []))
        code = extract_payload_text_any(payload, field_set.get("code_keys", []))
        if iiko_id or name or code:
            return iiko_id, name, code, str(field_set.get("source") or "")

    auth_iiko_id = extract_payload_text(payload, "AuthUser.Id")
    auth_name = extract_payload_text(payload, "AuthUser.Name")
    auth_code = extract_payload_text(payload, "AuthUser.Code")
    if auth_iiko_id or auth_name or auth_code:
        return auth_iiko_id, auth_name, auth_code, "AuthUser"

    return None, None, None, None


def extract_order_guid(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None

    for key in ORDER_ID_FIELD_CANDIDATES:
        value = clean_optional_text(payload.get(key))
        if value:
            return value

    parts = [
        clean_optional_text(payload.get("OrderNum")) or "",
        clean_optional_text(payload.get("OpenTime")) or "",
        clean_optional_text(payload.get("CloseTime")) or "",
        normalize_location_token(payload.get("Department")) or "",
        normalize_location_token(payload.get("TableNum")) or "",
        clean_optional_text(payload.get("OrderWaiter.Id")) or "",
        clean_optional_text(payload.get("OrderWaiter.Name")) or "",
        clean_optional_text(payload.get("GuestNum")) or "",
    ]
    signature = "|".join(parts)
    if not signature.strip("|"):
        return None
    digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()
    return f"synthetic::{digest}"
