from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy.exc import IntegrityError

from backend.bd.database import SessionLocal
from backend.bd.models import Company, Position, Restaurant, User
from backend.services.employee_codes import generate_unique_numeric_code
from backend.services.employee_identity import build_employee_row_id
from backend.services.iiko_staff import fetch_iiko_id_by_code, IikoIntegrationError
from backend.utils import hash_password

_SPACE_RE = re.compile(r"\s+")
_DIGITS_RE = re.compile(r"\D+")


def _normalize_key(value: Optional[str]) -> str:
    if not value:
        return ""
    return _SPACE_RE.sub(" ", str(value).strip().lower())


def _to_clean_str(value: object) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value).strip()
    value_str = str(value).strip()
    return value_str or None


def _parse_date(value: object) -> Optional[date]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return None
    return parsed.date()


def _normalize_phone(value: Optional[str]) -> Optional[str]:
    raw = _to_clean_str(value)
    if not raw:
        return None
    digits = _DIGITS_RE.sub("", raw)
    if len(digits) == 11 and digits[0] in {"7", "8"}:
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return f"+7{digits}"


def _extract_departments(value: object) -> list[str]:
    raw = _to_clean_str(value)
    if not raw:
        return []
    parts = [part.strip() for part in str(raw).split(",")]
    return [part for part in parts if part]


def _generate_unique_username(db, base: Optional[str]) -> str:
    candidate = (base or "").strip() or f"user_{uuid.uuid4().hex[:8]}"
    unique_username = candidate
    suffix = 1
    while db.query(User.id).filter(User.username == unique_username).first():
        unique_username = f"{candidate}_{suffix}"
        suffix += 1
    return unique_username


def _resolve_company_id(db, company_id: Optional[int]) -> int:
    if company_id:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError(f"Company {company_id} not found")
        return company.id
    companies = db.query(Company).order_by(Company.id.asc()).all()
    if len(companies) == 1:
        return companies[0].id
    raise ValueError("Multiple companies found, pass --company-id")


def _resolve_restaurant_name(
    restaurants_by_id,
    restaurants_by_name,
    name: str,
    restaurant_map: Optional[dict[str, object]] = None,
) -> Optional[Restaurant]:
    key = _normalize_key(name)
    target = None
    if restaurant_map and key in restaurant_map:
        target = restaurant_map[key]
    if target is None:
        target = name
    if isinstance(target, (int, float)) and not isinstance(target, bool):
        return restaurants_by_id.get(int(target))
    target_str = str(target).strip()
    if target_str.isdigit():
        return restaurants_by_id.get(int(target_str))
    return restaurants_by_name.get(_normalize_key(target_str))


def _load_restaurant_map(path: Optional[str]) -> dict[str, object]:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("restaurant map must be a JSON object")
    return {_normalize_key(str(key)): value for key, value in data.items()}


def _load_position_map(path: Optional[str]) -> dict[str, object]:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("position map must be a JSON object")
    return {_normalize_key(str(key)): value for key, value in data.items()}


def _resolve_position_name(
    positions_by_id,
    positions_by_name,
    name: Optional[str],
    position_map: Optional[dict[str, object]] = None,
) -> tuple[Optional[Position], bool]:
    if not name:
        return None, False
    key = _normalize_key(name)
    target = None
    if position_map and key in position_map:
        target = position_map[key]
        if target is None:
            return None, True
        if isinstance(target, str) and not target.strip():
            return None, True
    if target is None:
        target = name
    if isinstance(target, (int, float)) and not isinstance(target, bool):
        return positions_by_id.get(int(target)), False
    target_str = str(target).strip()
    if not target_str:
        return None, True
    if target_str.isdigit():
        return positions_by_id.get(int(target_str)), False
    return positions_by_name.get(_normalize_key(target_str)), False


def _pick_column(
    column_names: list[str],
    column_map: Optional[dict[str, str]],
    key: str,
    default_index: int,
    fallback_names: list[str],
) -> str:
    if column_map:
        mapped = column_map.get(key)
        if mapped in column_names:
            return mapped
    for name in fallback_names:
        if name in column_names:
            return name
    return column_names[default_index]


def import_employees(
    *,
    file_path: Optional[Path] = None,
    sheet_name: Optional[str],
    company_id: Optional[int],
    update_existing: bool,
    sync_iiko: bool,
    limit: Optional[int],
    dry_run: bool,
    restaurant_map: Optional[dict[str, object]] = None,
    position_map: Optional[dict[str, object]] = None,
    column_map: Optional[dict[str, str]] = None,
    dataframe: Optional[pd.DataFrame] = None,
) -> dict[str, object]:
    if dataframe is not None:
        df = dataframe.copy()
    else:
        if file_path is None:
            raise ValueError("file_path is required when dataframe is not provided")
        df = pd.read_excel(file_path, sheet_name=sheet_name)
    if isinstance(df, dict):
        if not df:
            raise ValueError("Excel file has no sheets")
        first_sheet = next(iter(df))
        df = df[first_sheet]
    if limit:
        df = df.head(limit)

    column_names = list(df.columns)
    idx_department = _pick_column(
        column_names,
        column_map,
        "department",
        0,
        ["Подразделение", "Ресторан", "Рестораны"],
    )
    idx_iiko_code = _pick_column(
        column_names,
        column_map,
        "iiko_code",
        1,
        ["Табельный номер", "iiko_code", "iiko code"],
    )
    idx_first_name = _pick_column(
        column_names,
        column_map,
        "first_name",
        2,
        ["Имя", "FirstName", "first_name"],
    )
    idx_position = _pick_column(
        column_names,
        column_map,
        "position",
        3,
        ["Должность", "Должности", "Position"],
    )
    idx_last_name = _pick_column(
        column_names,
        column_map,
        "last_name",
        4,
        ["Фамилия", "LastName", "last_name"],
    )
    idx_staff_code = _pick_column(
        column_names,
        column_map,
        "staff_code",
        5,
        ["ПИН", "PIN", "staff_code", "pin"],
    )
    idx_birth_date = _pick_column(
        column_names,
        column_map,
        "birth_date",
        6,
        ["Дата рождения", "Birth date", "birth_date"],
    )
    idx_phone = _pick_column(
        column_names,
        column_map,
        "phone",
        7,
        ["Телефон", "Phone", "phone"],
    )
    idx_mobile = _pick_column(
        column_names,
        column_map,
        "mobile",
        8,
        ["Моб. телефон", "Моб телефон", "Мобильный телефон", "Mobile", "mobile"],
    )

    db = SessionLocal()
    try:
        resolved_company_id = _resolve_company_id(db, company_id)

        restaurants = db.query(Restaurant).all()
        restaurants_by_id = {r.id: r for r in restaurants}
        restaurants_by_name = {_normalize_key(r.name): r for r in restaurants if r.name}
        normalized_restaurant_map = {
            _normalize_key(str(key)): value for key, value in (restaurant_map or {}).items()
        }

        positions = db.query(Position).all()
        positions_by_id = {p.id: p for p in positions}
        positions_by_name = {_normalize_key(p.name): p for p in positions if p.name}
        normalized_position_map = {
            _normalize_key(str(key)): value for key, value in (position_map or {}).items()
        }

        created = 0
        updated = 0
        skipped = 0
        errors = 0
        missing_restaurants = set()
        missing_positions = set()
        missing_iiko = 0
        pin_conflicts = 0
        synced_iiko = 0
        missing_workplace = set()

        for _, row in df.iterrows():
            departments = _extract_departments(row[idx_department])
            if not departments:
                missing_restaurants.add("")
                skipped += 1
                continue
            workplace = _resolve_restaurant_name(
                restaurants_by_id,
                restaurants_by_name,
                departments[0],
                normalized_restaurant_map,
            )
            if workplace is None:
                missing_workplace.add(departments[0])
                missing_restaurants.add(departments[0])
                skipped += 1
                continue
            resolved_restaurants = []
            for name in departments:
                resolved = _resolve_restaurant_name(
                    restaurants_by_id,
                    restaurants_by_name,
                    name,
                    normalized_restaurant_map,
                )
                if resolved is None:
                    missing_restaurants.add(name)
                    continue
                if resolved.id not in {r.id for r in resolved_restaurants}:
                    resolved_restaurants.append(resolved)
            if workplace.id not in {r.id for r in resolved_restaurants}:
                resolved_restaurants.insert(0, workplace)

            position_name = _to_clean_str(row[idx_position])
            position, position_explicit_empty = _resolve_position_name(
                positions_by_id,
                positions_by_name,
                position_name,
                normalized_position_map,
            )
            if position_name and not position and not position_explicit_empty:
                missing_positions.add(position_name)

            first_name = _to_clean_str(row[idx_first_name])
            last_name = _to_clean_str(row[idx_last_name])
            birth_date = _parse_date(row[idx_birth_date])
            phone = _normalize_phone(row[idx_mobile]) or _normalize_phone(row[idx_phone])

            iiko_code = _to_clean_str(row[idx_iiko_code])
            staff_code = _to_clean_str(row[idx_staff_code])
            if not staff_code:
                try:
                    staff_code = generate_unique_numeric_code(db, "staff_code", max_width=5)
                except ValueError:
                    errors += 1
                    continue

            if not iiko_code:
                try:
                    iiko_code = generate_unique_numeric_code(db, "iiko_code", max_width=6)
                except ValueError:
                    errors += 1
                    continue

            row_id = build_employee_row_id(
                last_name=last_name,
                first_name=first_name,
                middle_name=None,
                birth_date=birth_date,
            )

            existing = None
            if iiko_code:
                existing = db.query(User).filter(User.iiko_code == iiko_code).first()
            if existing is None and row_id:
                existing = db.query(User).filter(User.employee_row_id == row_id).first()

            if staff_code:
                staff_owner = db.query(User).filter(User.staff_code == staff_code).first()
                if staff_owner and (existing is None or staff_owner.id != existing.id):
                    pin_conflicts += 1
                    skipped += 1
                    continue

            if existing and not update_existing:
                skipped += 1
                continue

            if not existing:
                username = _generate_unique_username(db, iiko_code)
                user = User(
                    username=username,
                    hashed_password=hash_password(uuid.uuid4().hex),
                    first_name=first_name,
                    last_name=last_name,
                    iiko_code=iiko_code,
                    staff_code=staff_code,
                    phone_number=phone,
                    birth_date=birth_date,
                    company_id=resolved_company_id,
                    position_id=position.id if position else None,
                    role_id=position.role_id if position and position.role_id else None,
                    workplace_restaurant_id=workplace.id,
                    hire_date=date.today(),
                    fired=False,
                    employee_row_id=row_id,
                )
                if position and position.rate is not None:
                    user.rate = position.rate
                user.restaurants = resolved_restaurants
                db.add(user)
                action = "create"
            else:
                user = existing
                user.first_name = first_name
                user.last_name = last_name
                user.iiko_code = iiko_code
                user.staff_code = staff_code
                user.phone_number = phone
                user.birth_date = birth_date
                user.company_id = resolved_company_id
                user.position_id = position.id if position else None
                user.role_id = position.role_id if position and position.role_id else None
                user.workplace_restaurant_id = workplace.id
                user.employee_row_id = row_id
                user.restaurants = resolved_restaurants
                if position and position.rate is not None:
                    user.rate = position.rate
                action = "update"

            if dry_run:
                if not existing:
                    created += 1
                else:
                    updated += 1
                continue

            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                errors += 1
                continue
            db.refresh(user)

            if action == "create":
                created += 1
            else:
                updated += 1

            if sync_iiko:
                if user.iiko_id:
                    continue
                if not user.iiko_code:
                    missing_iiko += 1
                    continue
                try:
                    iiko_id = fetch_iiko_id_by_code(db, user)
                except IikoIntegrationError:
                    missing_iiko += 1
                    continue
                if iiko_id:
                    user.iiko_id = iiko_id
                    db.commit()
                    synced_iiko += 1

        summary = {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
            "pin_conflicts": pin_conflicts,
            "missing_restaurants": sorted(filter(None, missing_restaurants)),
            "missing_workplace_restaurants": sorted(missing_workplace),
            "missing_positions": sorted(missing_positions),
            "iiko_id_synced": synced_iiko,
            "iiko_id_missing": missing_iiko,
        }
        return summary
    finally:
        db.close()


def _format_items(items: list[str], limit: int = 10) -> str:
    if not items:
        return ""
    if len(items) <= limit:
        return ", ".join(items)
    remaining = len(items) - limit
    return f"{', '.join(items[:limit])} и еще {remaining}"


def format_summary(summary: dict[str, object], *, sync_iiko: bool) -> str:
    created = summary.get("created", 0)
    updated = summary.get("updated", 0)
    skipped = summary.get("skipped", 0)
    errors = summary.get("errors", 0)
    pin_conflicts = summary.get("pin_conflicts", 0)
    missing_restaurants = summary.get("missing_restaurants", [])
    missing_workplace = summary.get("missing_workplace_restaurants", [])
    missing_positions = summary.get("missing_positions", [])
    lines = [
        f"Готово. Создано: {created}, обновлено: {updated}, пропущено: {skipped}, ошибок: {errors}.",
    ]
    if pin_conflicts:
        lines.append(
            f"PIN-конфликты: {pin_conflicts}. Эти строки пропущены, проверьте дубликаты PIN."
        )
    if missing_restaurants:
        lines.append(
            "Не найдены рестораны: "
            f"{_format_items(missing_restaurants)}. Проверьте маппинг ресторанов."
        )
    if missing_workplace:
        lines.append(
            "Не найдено место работы (первое подразделение): "
            f"{_format_items(missing_workplace)}."
        )
    if missing_positions:
        lines.append(
            "Не найдены должности: "
            f"{_format_items(missing_positions)}. Проверьте маппинг должностей."
        )
    if sync_iiko:
        lines.append(
            f"iiko GUID: синхронизировано {summary.get('iiko_id_synced', 0)}, "
            f"не найдено {summary.get('iiko_id_missing', 0)}."
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import employees from Excel file")
    parser.add_argument("--file", default="pers.xlsx", help="Path to Excel file")
    parser.add_argument("--sheet", default=None, help="Sheet name (default: first)")
    parser.add_argument("--company-id", type=int, default=None, help="Company id for all employees")
    parser.add_argument("--restaurant-map", default=None, help="JSON file with restaurant name mappings")
    parser.add_argument("--position-map", default=None, help="JSON file with position name mappings")
    parser.add_argument("--update-existing", action="store_true", help="Update existing employees")
    parser.add_argument("--sync-iiko", action="store_true", help="Fetch iiko_id for imported employees")
    parser.add_argument("--limit", type=int, default=None, help="Import only first N rows")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to DB")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return 1
    restaurant_map = _load_restaurant_map(args.restaurant_map)
    position_map = _load_position_map(args.position_map)
    summary = import_employees(
        file_path=file_path,
        sheet_name=args.sheet,
        company_id=args.company_id,
        update_existing=args.update_existing,
        sync_iiko=args.sync_iiko,
        limit=args.limit,
        dry_run=args.dry_run,
        restaurant_map=restaurant_map,
        position_map=position_map,
    )
    print(format_summary(summary, sync_iiko=args.sync_iiko))
    return 0


if __name__ == "__main__":
    sys.exit(main())
