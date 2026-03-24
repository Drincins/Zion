from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, Optional
import xml.etree.ElementTree as ET
from urllib.parse import quote, urlparse

import requests
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.bd.models import User, Restaurant
from backend.services.iiko_http import get_iiko_tls_verify

logger = logging.getLogger(__name__)


class IikoIntegrationError(HTTPException):
    """HTTP 400 wrapper for iiko integration validation issues."""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


IIKO_EMPTY_TOKENS = {"-", "—", "none", "null", "n/a", "na"}


def _normalize_iiko_token(value: Optional[str]) -> str:
    text = str(value or "").strip()
    if text.casefold() in IIKO_EMPTY_TOKENS:
        return ""
    return text


def _normalize_iiko_server(server_raw: Optional[str], *, restaurant: Optional[Restaurant] = None) -> str:
    server = _normalize_iiko_token(server_raw)
    if not server:
        return ""

    candidate = server
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        restaurant_name = getattr(restaurant, "name", None) or f"ID {getattr(restaurant, 'id', '?')}"
        raise IikoIntegrationError(
            f'Некорректный адрес iiko-сервера у ресторана "{restaurant_name}": "{server}". '
            "Укажите полный URL, например https://example.iiko.it"
        )

    return candidate.rstrip("/")


def _restaurant_iiko_credentials(restaurant: Restaurant) -> tuple[str, str, str]:
    server = _normalize_iiko_server(getattr(restaurant, "server", None), restaurant=restaurant)
    login = _normalize_iiko_token(getattr(restaurant, "iiko_login", None))
    password_sha1 = _normalize_iiko_token(getattr(restaurant, "iiko_password_sha1", None))
    if server and login and password_sha1:
        return server, login, password_sha1

    restaurant_name = getattr(restaurant, "name", None) or f"ID {getattr(restaurant, 'id', '?')}"
    raise IikoIntegrationError(
        f'Не заполнены настройки iiko у ресторана "{restaurant_name}" (server/login/password).'
    )


def _pick_restaurant(db: Session, user: User) -> Restaurant:
    if getattr(user, "workplace_restaurant_id", None):
        restaurant = (
            user.workplace_restaurant
            or db.query(Restaurant)
            .filter(Restaurant.id == user.workplace_restaurant_id)
            .first()
        )
        if not restaurant:
            raise IikoIntegrationError("Workplace restaurant not found")
        return restaurant
    restaurants = [r for r in (user.restaurants or []) if r]
    if not restaurants:
        raise IikoIntegrationError("Cannot add to iiko: workplace restaurant is required")
    if len(restaurants) > 1:
        raise IikoIntegrationError("Cannot add to iiko: workplace restaurant is required")
    return restaurants[0]


def _build_employee_xml(data: Dict[str, Any]) -> str:
    def _render_tag(tag: str, value: Optional[str], *, allow_empty: bool = False) -> str:
        if value is None:
            return ""
        if value == "" and not allow_empty:
            return ""
        return f"<{tag}>{value}</{tag}>"

    role_codes = data.get("roleCodes") or []
    if isinstance(role_codes, str):
        role_codes = [role_codes]
    role_nodes = "".join(f"<roleCodes>{c}</roleCodes>" for c in role_codes if c)
    name = data.get("name") or " ".join(
        x for x in [data.get("lastName"), data.get("firstName"), data.get("middleName")] if x
    )
    dept_nodes = "".join(f"<departmentCodes>{c}</departmentCodes>" for c in data.get("departmentCodes", []) or [])
    resp_nodes = "".join(
        f"<responsibilityDepartmentCodes>{c}</responsibilityDepartmentCodes>"
        for c in data.get("responsibilityDepartmentCodes", []) or []
    )
    login_node = _render_tag("login", data.get("login", ""), allow_empty=True)
    phone_node = _render_tag("phone", data.get("phone"))
    first_name_node = _render_tag("firstName", data.get("firstName"))
    middle_name_node = _render_tag("middleName", data.get("middleName"))
    last_name_node = _render_tag("lastName", data.get("lastName"))
    birthday_node = _render_tag("birthday", data.get("birthday"))
    email_node = _render_tag("email", data.get("email"))
    card_number_node = _render_tag("cardNumber", data.get("cardNumber"))
    pin_code_node = _render_tag("pinCode", data.get("pinCode"))
    hire_date_node = _render_tag("hireDate", data.get("hireDate"))
    fire_date_node = _render_tag("fireDate", data.get("fireDate"))
    preferred_department_node = _render_tag("preferredDepartmentCode", data.get("preferredDepartmentCode"))
    xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<employee>
    <code>{data.get("code","")}</code>
    <name>{name}</name>
    {login_node}
    <mainRoleCode>{data.get("mainRoleCode","")}</mainRoleCode>
    {role_nodes or "<roleCodes></roleCodes>"}
    {phone_node}
    {first_name_node}
    {middle_name_node}
    {last_name_node}
    {birthday_node}
    {email_node}
    {card_number_node}
    {pin_code_node}
    {hire_date_node}
    {fire_date_node}
    <employee>{str(data.get("employee", True)).lower()}</employee>
    <client>{str(data.get("client", False)).lower()}</client>
    <supplier>{str(data.get("supplier", False)).lower()}</supplier>
    {dept_nodes}
    {preferred_department_node}
    {resp_nodes}
</employee>
""".strip()
    return xml


def _fetch_key(server: str, login: str, password_sha1: str) -> str:
    url = f"{server.rstrip('/')}/resto/api/auth"
    try:
        resp = requests.get(url, params={"login": login, "pass": password_sha1}, verify=get_iiko_tls_verify(), timeout=30)
    except requests.RequestException as exc:  # pragma: no cover - network failures
        raise IikoIntegrationError(f"iiko auth failed: {exc}") from exc
    if resp.status_code != 200:
        raise IikoIntegrationError(f"iiko auth failed: {resp.status_code} {resp.text}")
    key = (resp.text or "").strip()
    if not key:
        raise IikoIntegrationError("iiko auth returned empty key")
    return key


def _normalize_match_value(value: Optional[str]) -> str:
    return " ".join((value or "").strip().lower().split())


def _xml_text(node: ET.Element, tag: str) -> str:
    child = node.find(tag)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def _find_employee_node(root: ET.Element) -> Optional[ET.Element]:
    if root.tag == "employee":
        return root
    for node in root.findall(".//employee"):
        if node.find("code") is not None or node.find("id") is not None:
            return node
    return None


def _parse_iiko_employee_payload(xml_text: str) -> dict[str, Any]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise IikoIntegrationError(f"iiko employee parse failed: {exc}") from exc

    node = _find_employee_node(root)
    if node is None:
        raise IikoIntegrationError("iiko employee parse failed: employee node is missing")

    department_codes: list[str] = []
    for dept_node in node.findall("departmentCodes"):
        if dept_node.text and dept_node.text.strip():
            department_codes.append(dept_node.text.strip())
    preferred_department_code = _xml_text(node, "preferredDepartmentCode")
    if preferred_department_code and preferred_department_code not in department_codes:
        department_codes.insert(0, preferred_department_code)
    department_code = preferred_department_code or (department_codes[0] if department_codes else "")

    role_codes: list[str] = []
    for role_node in node.findall("roleCodes"):
        if role_node.text and role_node.text.strip():
            role_codes.append(role_node.text.strip())
    main_role_code = _xml_text(node, "mainRoleCode")
    if main_role_code and main_role_code not in role_codes:
        role_codes.insert(0, main_role_code)

    return {
        "id": _xml_text(node, "id"),
        "code": _xml_text(node, "code"),
        "first_name": _xml_text(node, "firstName"),
        "middle_name": _xml_text(node, "middleName"),
        "last_name": _xml_text(node, "lastName"),
        "main_role_code": main_role_code,
        "role_codes": role_codes,
        "pin_code": _xml_text(node, "pinCode"),
        "department_code": department_code,
        "department_codes": department_codes,
    }


def _parse_iiko_employee_snapshots(xml_text: str) -> list[dict[str, str]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise IikoIntegrationError(f"iiko employees parse failed: {exc}") from exc

    if root.tag == "employee":
        nodes = [root]
    else:
        nodes = []
        for node in root.findall(".//employee"):
            # Filter out scalar <employee>true</employee> child nodes.
            if node.find("code") is None and node.find("id") is None and node.find("pinCode") is None:
                continue
            nodes.append(node)

    snapshots: list[dict[str, str]] = []
    for node in nodes:
        snapshots.append(
            {
                "id": _xml_text(node, "id"),
                "code": _xml_text(node, "code"),
                "first_name": _xml_text(node, "firstName"),
                "last_name": _xml_text(node, "lastName"),
                "pin_code": _xml_text(node, "pinCode"),
            }
        )
    return snapshots


def _fetch_iiko_employee_snapshots(server: str, key: str) -> list[dict[str, str]]:
    url = f"{server.rstrip('/')}/resto/api/employees"
    try:
        resp = requests.get(url, params={"key": key}, verify=get_iiko_tls_verify(), timeout=30)
    except requests.RequestException as exc:  # pragma: no cover - network failures
        raise IikoIntegrationError(f"iiko employees lookup failed: {exc}") from exc
    if resp.status_code in (404, 405):
        logger.warning("iiko employees list endpoint is unavailable (%s), duplicate check skipped", resp.status_code)
        return []
    if resp.status_code != 200:
        raise IikoIntegrationError(f"iiko employees lookup failed: {resp.status_code} {resp.text}")
    return _parse_iiko_employee_snapshots(resp.text)


def _fetch_iiko_employee_snapshot(
    server: str,
    key: str,
    *,
    iiko_code: Optional[str],
    iiko_id: Optional[str],
) -> Optional[dict[str, Any]]:
    lookup_paths: list[tuple[str, str]] = []
    if iiko_code:
        lookup_paths.append(("code", f"/resto/api/employees/byCode/{quote(iiko_code)}"))
    if iiko_id:
        lookup_paths.append(("id", f"/resto/api/employees/byId/{quote(iiko_id)}"))

    for lookup_kind, path in lookup_paths:
        url = f"{server.rstrip('/')}{path}"
        try:
            resp = requests.get(url, params={"key": key}, verify=get_iiko_tls_verify(), timeout=30)
        except requests.RequestException as exc:  # pragma: no cover - network failures
            raise IikoIntegrationError(
                f"iiko employee lookup by {lookup_kind} failed: {exc}"
            ) from exc
        if resp.status_code == 200:
            return _parse_iiko_employee_payload(resp.text)
        if resp.status_code == 404:
            continue
        raise IikoIntegrationError(
            f"iiko employee lookup by {lookup_kind} failed: {resp.status_code} {resp.text}"
        )
    return None


def _find_iiko_employee_by_name_and_staff(
    server: str,
    key: str,
    user: User,
    *,
    exclude_code: Optional[str] = None,
    exclude_iiko_id: Optional[str] = None,
) -> Optional[dict[str, str]]:
    first_name = _normalize_match_value(user.first_name)
    last_name = _normalize_match_value(user.last_name)
    staff_code = _normalize_match_value(user.staff_code)
    if not first_name or not last_name or not staff_code:
        return None

    normalized_exclude_code = _normalize_match_value(exclude_code)
    normalized_exclude_iiko_id = _normalize_match_value(exclude_iiko_id)
    matches: list[dict[str, str]] = []

    for snapshot in _fetch_iiko_employee_snapshots(server, key):
        snapshot_code = _normalize_match_value(snapshot.get("code"))
        snapshot_iiko_id = _normalize_match_value(snapshot.get("id"))
        same_record = bool(
            (normalized_exclude_iiko_id and snapshot_iiko_id and normalized_exclude_iiko_id == snapshot_iiko_id)
            or (normalized_exclude_code and snapshot_code and normalized_exclude_code == snapshot_code)
        )
        if same_record:
            continue

        snapshot_first_name = _normalize_match_value(snapshot.get("first_name"))
        snapshot_last_name = _normalize_match_value(snapshot.get("last_name"))
        snapshot_staff_code = _normalize_match_value(snapshot.get("pin_code"))

        same_name = snapshot_first_name == first_name and snapshot_last_name == last_name
        same_staff_code = snapshot_staff_code == staff_code
        if not (same_name and same_staff_code):
            continue

        matches.append(snapshot)

    if not matches:
        return None

    if len(matches) > 1:
        conflict_labels: list[str] = []
        for snapshot in matches:
            code = (snapshot.get("code") or "").strip()
            iiko_id = (snapshot.get("id") or "").strip()
            label_parts: list[str] = []
            if code:
                label_parts.append(f"код {code}")
            if iiko_id:
                label_parts.append(f"id {iiko_id}")
            if label_parts:
                conflict_labels.append(", ".join(label_parts))
        suffix = f": {'; '.join(conflict_labels)}" if conflict_labels else ""
        raise IikoIntegrationError(
            "В iiko найдено несколько сотрудников с таким ФИО и табельным номером"
            f"{suffix}. Уточните код iiko вручную."
        )

    return matches[0]


def _ensure_no_iiko_employee_duplicates(
    server: str,
    key: str,
    user: User,
    *,
    current_code: Optional[str] = None,
    current_iiko_id: Optional[str] = None,
) -> None:
    snapshot = _find_iiko_employee_by_name_and_staff(
        server,
        key,
        user,
        exclude_code=current_code,
        exclude_iiko_id=current_iiko_id,
    )
    if not snapshot:
        return

    snapshot_code = (snapshot.get("code") or "").strip()
    snapshot_iiko_id = (snapshot.get("id") or "").strip()
    if not snapshot_code and not snapshot_iiko_id:
        raise IikoIntegrationError(
            "Сотрудник с таким ФИО и табельным номером уже существует в iiko. "
            "Проверьте код iiko перед синхронизацией."
        )

    if snapshot_code and not current_code:
        # We can safely reuse the existing iiko employee by code.
        return

    if snapshot_iiko_id and not current_iiko_id:
        # Existing employee can be reused by id once code is resolved.
        return

    if snapshot_code and current_code and snapshot_code.casefold() == current_code.casefold():
        return

    if snapshot_iiko_id and current_iiko_id and snapshot_iiko_id.casefold() == current_iiko_id.casefold():
        return

    conflict_parts = []
    if snapshot.get("code"):
        conflict_parts.append(f"код iiko: {snapshot['code']}")
    if snapshot.get("id"):
        conflict_parts.append(f"id: {snapshot['id']}")
    conflict_hint = f" ({', '.join(conflict_parts)})" if conflict_parts else ""
    raise IikoIntegrationError(
        "Сотрудник с таким ФИО и табельным номером уже существует в iiko"
        f"{conflict_hint}. Проверьте код iiko перед синхронизацией."
    )


def _resolve_iiko_identity_for_sync(server: str, key: str, user: User) -> tuple[str, Optional[str]]:
    resolved_code = _normalize_iiko_token(getattr(user, "iiko_code", None))
    resolved_iiko_id = _normalize_iiko_token(getattr(user, "iiko_id", None))

    # Prefer explicit code/id on the employee card.
    snapshot = _fetch_iiko_employee_snapshot(
        server,
        key,
        iiko_code=resolved_code or None,
        iiko_id=resolved_iiko_id or None,
    )
    if snapshot:
        resolved_code = _normalize_iiko_token(snapshot.get("code")) or resolved_code
        resolved_iiko_id = _normalize_iiko_token(snapshot.get("id")) or resolved_iiko_id

    # Legacy employees may have mismatched/missing iiko_code; match by full name + staff code.
    if not snapshot or not resolved_code:
        matched = _find_iiko_employee_by_name_and_staff(
            server,
            key,
            user,
            exclude_code=resolved_code or None,
            exclude_iiko_id=resolved_iiko_id or None,
        )
        if matched:
            matched_code = _normalize_iiko_token(matched.get("code"))
            if matched_code:
                resolved_code = matched_code
            resolved_iiko_id = _normalize_iiko_token(matched.get("id")) or resolved_iiko_id

    if not resolved_code:
        raise IikoIntegrationError(
            "Не удалось определить код iiko для сотрудника. "
            "Укажите 'Код iiko' вручную или выберите данные из iiko в окне синхронизации."
        )

    _ensure_no_iiko_employee_duplicates(
        server,
        key,
        user,
        current_code=resolved_code,
        current_iiko_id=resolved_iiko_id or None,
    )

    return resolved_code, resolved_iiko_id or None


def _sync_user_iiko_identity(user: User, *, code: Optional[str], iiko_id: Optional[str]) -> None:
    normalized_code = _normalize_iiko_token(code)
    normalized_id = _normalize_iiko_token(iiko_id)

    if normalized_code:
        current_code = _normalize_iiko_token(getattr(user, "iiko_code", None))
        if current_code != normalized_code:
            user.iiko_code = normalized_code

    if normalized_id:
        current_iiko_id = _normalize_iiko_token(getattr(user, "iiko_id", None))
        if current_iiko_id != normalized_id:
            user.iiko_id = normalized_id


def _resolve_sync_restaurant(db: Session, user: User, sync_restaurant_id: Optional[int]) -> Restaurant:
    if sync_restaurant_id is None:
        return _pick_restaurant(db, user)

    restaurant = db.query(Restaurant).filter(Restaurant.id == sync_restaurant_id).first()
    if not restaurant:
        raise IikoIntegrationError("Sync restaurant not found")
    return restaurant


def _resolve_department_restaurants(
    db: Session,
    user: User,
    *,
    requested_ids: Optional[list[int]],
    fallback_restaurant: Restaurant,
) -> list[Restaurant]:
    if requested_ids is not None:
        normalized_ids: list[int] = []
        seen_ids: set[int] = set()
        for raw in requested_ids:
            try:
                rid = int(raw)
            except Exception:
                continue
            if rid <= 0 or rid in seen_ids:
                continue
            seen_ids.add(rid)
            normalized_ids.append(rid)
        if not normalized_ids:
            raise IikoIntegrationError("Выберите хотя бы один ресторан для доступа в iiko")

        rows = db.query(Restaurant).filter(Restaurant.id.in_(normalized_ids)).all()
        by_id = {row.id: row for row in rows if row and row.id is not None}
        missing_ids = [rid for rid in normalized_ids if rid not in by_id]
        if missing_ids:
            raise IikoIntegrationError(f"Не найдены рестораны для доступа в iiko: {', '.join(map(str, missing_ids))}")
        return [by_id[rid] for rid in normalized_ids]

    restaurants: list[Restaurant] = []
    seen_ids: set[int] = set()
    if getattr(user, "workplace_restaurant", None) is not None and getattr(user.workplace_restaurant, "id", None):
        rid = int(user.workplace_restaurant.id)
        restaurants.append(user.workplace_restaurant)
        seen_ids.add(rid)
    for row in (user.restaurants or []):
        if not row or row.id is None:
            continue
        rid = int(row.id)
        if rid in seen_ids:
            continue
        restaurants.append(row)
        seen_ids.add(rid)
    if fallback_restaurant.id is not None and int(fallback_restaurant.id) not in seen_ids:
        restaurants.append(fallback_restaurant)
    return restaurants


def fetch_iiko_employee_snapshot(
    db: Session,
    user: User,
    *,
    sync_restaurant_id: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    restaurant = _resolve_sync_restaurant(db, user, sync_restaurant_id)
    server, login, password_sha1 = _restaurant_iiko_credentials(restaurant)

    iiko_code = (getattr(user, "iiko_code", None) or "").strip() or None
    iiko_id = (getattr(user, "iiko_id", None) or "").strip() or None
    if not iiko_code and not iiko_id:
        return None

    key = _fetch_key(server, login, password_sha1)
    return _fetch_iiko_employee_snapshot(
        server,
        key,
        iiko_code=iiko_code,
        iiko_id=iiko_id,
    )


def add_user_to_iiko(
    db: Session,
    user: User,
    *,
    sync_restaurant_id: Optional[int] = None,
    department_restaurant_ids: Optional[list[int]] = None,
) -> Optional[str]:
    """
    Trigger employee creation/update in iiko via PUT /employees/byCode/{code}.
    """
    position = getattr(user, "position", None)
    if not position or not getattr(position, "code", None):
        raise IikoIntegrationError("Position with a code is required to add employee to iiko")

    sync_restaurant = _resolve_sync_restaurant(db, user, sync_restaurant_id)
    server, login, password_sha1 = _restaurant_iiko_credentials(sync_restaurant)
    department_restaurants = _resolve_department_restaurants(
        db,
        user,
        requested_ids=department_restaurant_ids,
        fallback_restaurant=sync_restaurant,
    )
    department_codes: list[str] = []
    seen_codes: set[str] = set()
    for row in department_restaurants:
        code = _normalize_iiko_token(getattr(row, "department_code", None))
        if not code:
            continue
        code_key = code.casefold()
        if code_key in seen_codes:
            continue
        seen_codes.add(code_key)
        department_codes.append(code)
    if not department_codes:
        raise IikoIntegrationError("У выбранных ресторанов отсутствуют department_code для синхронизации в iiko")

    preferred_department_code = _normalize_iiko_token(getattr(getattr(user, "workplace_restaurant", None), "department_code", None))
    if not preferred_department_code:
        preferred_department_code = _normalize_iiko_token(getattr(sync_restaurant, "department_code", None))
    if preferred_department_code and preferred_department_code.casefold() not in {item.casefold() for item in department_codes}:
        department_codes.insert(0, preferred_department_code)
    if not preferred_department_code:
        preferred_department_code = department_codes[0]

    key = _fetch_key(server, login, password_sha1)
    resolved_iiko_code, resolved_iiko_id = _resolve_iiko_identity_for_sync(server, key, user)
    _sync_user_iiko_identity(user, code=resolved_iiko_code, iiko_id=resolved_iiko_id)

    fire_date = None
    if user.fire_date:
        fire_date = user.fire_date
    elif getattr(user, "fired", False):
        fire_date = date.today()
    birthday_value = None
    if user.birth_date:
        birthday_value = f"{user.birth_date.isoformat()}T00:00:00"
    payload = {
        "code": resolved_iiko_code,
        "login": user.username or resolved_iiko_code,
        "mainRoleCode": position.code,
        "roleCodes": [position.code],
        "firstName": user.first_name or "",
        "middleName": user.middle_name or "",
        "lastName": user.last_name or "",
        "phone": user.phone_number or "",
        "hireDate": (user.hire_date or date.today()).isoformat(),
        "fireDate": fire_date.isoformat() if fire_date else "",
        "birthday": birthday_value,
        "pinCode": user.staff_code or "",
        "departmentCodes": department_codes,
        "preferredDepartmentCode": preferred_department_code,
        "responsibilityDepartmentCodes": department_codes,
        "employee": True,
        "client": False,
        "supplier": False,
    }
    xml_body = _build_employee_xml(payload)
    url = f"{server.rstrip('/')}/resto/api/employees/byCode/{quote(resolved_iiko_code)}"
    try:
        resp = requests.put(
            url,
            params={"key": key},
            data=xml_body.encode("utf-8"),
            headers={"Content-Type": "application/xml"},
            verify=get_iiko_tls_verify(),
            timeout=30,
        )
    except requests.RequestException as exc:  # pragma: no cover - network failures
        raise IikoIntegrationError(f"iiko request failed: {exc}") from exc

    if resp.status_code not in (200, 201):
        raise IikoIntegrationError(f"iiko responded {resp.status_code}: {resp.text}")

    # Fetch assigned iiko GUID by code
    id_url = f"{server.rstrip('/')}/resto/api/employees/byCode/{quote(resolved_iiko_code)}"
    try:
        resp_id = requests.get(id_url, params={"key": key}, verify=get_iiko_tls_verify(), timeout=30)
    except requests.RequestException as exc:  # pragma: no cover
        raise IikoIntegrationError(f"iiko id lookup failed: {exc}") from exc
    if resp_id.status_code != 200:
        raise IikoIntegrationError(f"iiko id lookup failed: {resp_id.status_code} {resp_id.text}")
    iiko_id = _extract_employee_id(resp_id.text) or resolved_iiko_id
    _sync_user_iiko_identity(user, code=resolved_iiko_code, iiko_id=iiko_id)

    logger.info(
        "Added/updated user %s in iiko (code=%s, dept=%s, iiko_id=%s)",
        user.id,
        resolved_iiko_code,
        preferred_department_code,
        iiko_id,
    )
    return iiko_id


def _extract_employee_id(xml_text: str) -> Optional[str]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None
    node = root.find(".//id") if root.tag != "id" else root
    if node is None or not (node.text or "").strip():
        return None
    return node.text.strip()


def fire_user_in_iiko(db: Session, user: User) -> None:
    """
    Mark employee as fired in iiko by setting deleted=true via POST /employees/byId/{id}.
    """
    if not getattr(user, "iiko_id", None):
        raise IikoIntegrationError("iiko_id is required to fire employee in iiko")

    restaurant = _pick_restaurant(db, user)
    server, login, password_sha1 = _restaurant_iiko_credentials(restaurant)

    key = _fetch_key(server, login, password_sha1)
    url = f"{server.rstrip('/')}/resto/api/employees/byId/{user.iiko_id}"
    fire_date = user.fire_date or date.today()
    payload = {
        "deleted": "true",
        "fireDate": fire_date.isoformat(),
    }
    try:
        resp = requests.post(
            url,
            params={"key": key},
            data=payload,
            verify=get_iiko_tls_verify(),
            timeout=30,
        )
    except requests.RequestException as exc:  # pragma: no cover
        raise IikoIntegrationError(f"iiko fire failed: {exc}") from exc
    if resp.status_code not in (200, 201):
        raise IikoIntegrationError(f"iiko fire responded {resp.status_code}: {resp.text}")
    logger.info("Fired user %s in iiko (iiko_id=%s)", user.id, user.iiko_id)
    return None


def delete_user_from_iiko(db: Session, user: User) -> None:
    """
    Delete employee in iiko by iiko_id via DELETE /employees/byId/{id}.
    """
    if not getattr(user, "iiko_id", None):
        raise IikoIntegrationError("iiko_id is required to delete employee in iiko")

    restaurant = _pick_restaurant(db, user)
    server, login, password_sha1 = _restaurant_iiko_credentials(restaurant)

    key = _fetch_key(server, login, password_sha1)
    url = f"{server.rstrip('/')}/resto/api/employees/byId/{user.iiko_id}"
    try:
        resp = requests.delete(url, params={"key": key}, verify=get_iiko_tls_verify(), timeout=30)
    except requests.RequestException as exc:  # pragma: no cover
        raise IikoIntegrationError(f"iiko delete failed: {exc}") from exc
    if resp.status_code not in (200, 202, 204):
        raise IikoIntegrationError(f"iiko delete responded {resp.status_code}: {resp.text}")
    logger.info("Deleted user %s from iiko (iiko_id=%s)", user.id, user.iiko_id)
    return None


def fetch_iiko_id_by_code(db: Session, user: User) -> Optional[str]:
    """
    Fetch iiko GUID by employee code without modifying the employee in iiko.
    """
    if not getattr(user, "iiko_code", None):
        raise IikoIntegrationError("iiko_code is required to fetch employee id in iiko")

    restaurant = _pick_restaurant(db, user)
    server, login, password_sha1 = _restaurant_iiko_credentials(restaurant)

    key = _fetch_key(server, login, password_sha1)
    url = f"{server.rstrip('/')}/resto/api/employees/byCode/{user.iiko_code}"
    try:
        resp = requests.get(url, params={"key": key}, verify=get_iiko_tls_verify(), timeout=30)
    except requests.RequestException as exc:  # pragma: no cover
        raise IikoIntegrationError(f"iiko id lookup failed: {exc}") from exc
    if resp.status_code != 200:
        raise IikoIntegrationError(f"iiko id lookup failed: {resp.status_code} {resp.text}")
    return _extract_employee_id(resp.text)
