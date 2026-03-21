"""
Streamlit helper to preview and import employees from Excel.

Usage:
  streamlit run tools/employee_importer.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from backend.bd.database import SessionLocal
from backend.bd.models import Company, Position, Restaurant
from backend.scripts.import_employees_from_excel import format_summary, import_employees


def _normalize_key(value: Optional[str]) -> str:
    if not value:
        return ""
    return " ".join(str(value).strip().lower().split())


def _split_departments(value: object) -> list[str]:
    raw = str(value).strip() if value is not None else ""
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _load_reference_data():
    db = SessionLocal()
    try:
        companies = db.query(Company).order_by(Company.id.asc()).all()
        restaurants = db.query(Restaurant).order_by(Restaurant.id.asc()).all()
        positions = db.query(Position).order_by(Position.id.asc()).all()
        return companies, restaurants, positions
    finally:
        db.close()


def _default_column(columns: list[str], candidates: list[str]) -> Optional[str]:
    for name in candidates:
        if name in columns:
            return name
    return None


def _has_restaurant(
    name: str,
    restaurant_name_lookup: dict[str, Restaurant],
    restaurant_map: dict[str, object],
) -> bool:
    if not name:
        return False
    key = _normalize_key(name)
    if key in restaurant_map:
        return True
    return key in restaurant_name_lookup


def _has_position(
    name: str,
    position_name_lookup: dict[str, Position],
    position_map: dict[str, object],
) -> bool:
    if not name:
        return True
    key = _normalize_key(name)
    if key in position_map:
        return position_map[key] is None or position_map[key] != ""
    return key in position_name_lookup


def _collect_problem_rows(
    df: pd.DataFrame,
    column_map: dict[str, str],
    restaurant_name_lookup: dict[str, Restaurant],
    position_name_lookup: dict[str, Position],
    restaurant_map: dict[str, object],
    position_map: dict[str, object],
) -> pd.DataFrame:
    dept_col = column_map.get("department")
    pos_col = column_map.get("position")
    if not dept_col and not pos_col:
        return pd.DataFrame()

    problem_indices: list[int] = []
    reasons: dict[int, str] = {}
    for idx, row in df.iterrows():
        missing: list[str] = []
        if dept_col:
            departments = _split_departments(row.get(dept_col))
            if not departments:
                missing.append("нет подразделения")
            else:
                if not _has_restaurant(
                    departments[0], restaurant_name_lookup, restaurant_map
                ):
                    missing.append("не найдено место работы")
                if any(
                    not _has_restaurant(name, restaurant_name_lookup, restaurant_map)
                    for name in departments
                ):
                    missing.append("есть неизвестные рестораны")
        if pos_col:
            pos_value = str(row.get(pos_col)).strip() if row.get(pos_col) is not None else ""
            if pos_value and not _has_position(pos_value, position_name_lookup, position_map):
                missing.append("не найдена должность")
        if missing:
            problem_indices.append(idx)
            reasons[idx] = "; ".join(missing)

    if not problem_indices:
        return pd.DataFrame()

    visible_cols = []
    for key in ("last_name", "first_name", "iiko_code", "department", "position"):
        col = column_map.get(key)
        if col and col in df.columns and col not in visible_cols:
            visible_cols.append(col)

    problem_df = df.loc[problem_indices, visible_cols].copy()
    problem_df.insert(0, "Проблема", [reasons[idx] for idx in problem_df.index])
    return problem_df


def main() -> None:
    st.set_page_config(page_title="Импорт сотрудников", layout="wide")
    st.title("Импорт сотрудников из Excel")

    companies, restaurants, positions = _load_reference_data()
    restaurant_options = ["Не выбрано"] + [f"{r.id} - {r.name}" for r in restaurants]
    restaurant_lookup = {f"{r.id} - {r.name}": r for r in restaurants}
    restaurant_name_lookup = {_normalize_key(r.name): r for r in restaurants if r.name}
    position_options = ["Не выбрано", "Не назначать"] + [
        f"{p.id} - {p.name}" for p in positions
    ]
    position_lookup = {f"{p.id} - {p.name}": p for p in positions}
    position_name_lookup = {_normalize_key(p.name): p for p in positions if p.name}

    uploaded = st.file_uploader("Загрузите Excel файл", type=["xlsx", "xls"])
    if not uploaded:
        st.info("Загрузите файл, чтобы перейти к предпросмотру и настройкам импорта.")
        return

    xl = pd.ExcelFile(uploaded)
    sheet = st.selectbox("Лист", xl.sheet_names, index=0)
    df = xl.parse(sheet)
    st.subheader("Предпросмотр")
    st.dataframe(df.head(50), use_container_width=True)

    columns = list(df.columns)
    st.subheader("Маппинг колонок")
    column_map: dict[str, str] = {}
    col_department = st.selectbox(
        "Подразделение (рестораны)",
        ["Не выбрано"] + columns,
        index=(["Не выбрано"] + columns).index(
            _default_column(columns, ["Подразделение"]) or "Не выбрано"
        ),
    )
    if col_department != "Не выбрано":
        column_map["department"] = col_department
    col_iiko_code = st.selectbox(
        "Табельный номер (iiko_code)",
        ["Не выбрано"] + columns,
        index=(["Не выбрано"] + columns).index(
            _default_column(columns, ["Табельный номер", "iiko_code"]) or "Не выбрано"
        ),
    )
    if col_iiko_code != "Не выбрано":
        column_map["iiko_code"] = col_iiko_code
    col_first_name = st.selectbox(
        "Имя",
        ["Не выбрано"] + columns,
        index=(["Не выбрано"] + columns).index(
            _default_column(columns, ["Имя"]) or "Не выбрано"
        ),
    )
    if col_first_name != "Не выбрано":
        column_map["first_name"] = col_first_name
    col_last_name = st.selectbox(
        "Фамилия",
        ["Не выбрано"] + columns,
        index=(["Не выбрано"] + columns).index(
            _default_column(columns, ["Фамилия"]) or "Не выбрано"
        ),
    )
    if col_last_name != "Не выбрано":
        column_map["last_name"] = col_last_name
    col_position = st.selectbox(
        "Должность",
        ["Не выбрано"] + columns,
        index=(["Не выбрано"] + columns).index(
            _default_column(columns, ["Должность", "Должности", "Position"]) or "Не выбрано"
        ),
    )
    if col_position != "Не выбрано":
        column_map["position"] = col_position
    col_staff_code = st.selectbox(
        "ПИН (staff_code)",
        ["Не выбрано"] + columns,
        index=(["Не выбрано"] + columns).index(
            _default_column(columns, ["ПИН", "PIN", "staff_code"]) or "Не выбрано"
        ),
    )
    if col_staff_code != "Не выбрано":
        column_map["staff_code"] = col_staff_code
    col_birth_date = st.selectbox(
        "Дата рождения",
        ["Не выбрано"] + columns,
        index=(["Не выбрано"] + columns).index(
            _default_column(columns, ["Дата рождения"]) or "Не выбрано"
        ),
    )
    if col_birth_date != "Не выбрано":
        column_map["birth_date"] = col_birth_date
    col_phone = st.selectbox(
        "Телефон",
        ["Не выбрано"] + columns,
        index=(["Не выбрано"] + columns).index(
            _default_column(columns, ["Телефон"]) or "Не выбрано"
        ),
    )
    if col_phone != "Не выбрано":
        column_map["phone"] = col_phone
    col_mobile = st.selectbox(
        "Моб. телефон",
        ["Не выбрано"] + columns,
        index=(["Не выбрано"] + columns).index(
            _default_column(
                columns,
                ["Моб. телефон", "Моб телефон", "Мобильный телефон", "Mobile"],
            )
            or "Не выбрано"
        ),
    )
    if col_mobile != "Не выбрано":
        column_map["mobile"] = col_mobile

    st.subheader("Маппинг ресторанов")
    restaurant_map: dict[str, object] = {}
    if "department" in column_map:
        raw_departments = df[column_map["department"]].dropna().astype(str).tolist()
        unique_names: list[str] = []
        for value in raw_departments:
            for name in _split_departments(value):
                if name not in unique_names:
                    unique_names.append(name)
        with st.expander("Сопоставление подразделений", expanded=True):
            for name in unique_names:
                default_restaurant = restaurant_name_lookup.get(_normalize_key(name))
                default_label = (
                    f"{default_restaurant.id} - {default_restaurant.name}"
                    if default_restaurant
                    else "Не выбрано"
                )
                selected = st.selectbox(
                    f"{name}",
                    restaurant_options,
                    index=restaurant_options.index(default_label),
                    key=f"rest_map_{name}",
                )
                if selected != "Не выбрано":
                    restaurant_map[name] = restaurant_lookup[selected].id
    else:
        st.info(
            "Выберите колонку с подразделениями, чтобы настроить маппинг ресторанов."
        )

    st.subheader("Маппинг должностей")
    position_map: dict[str, object] = {}
    if "position" in column_map:
        raw_positions = df[column_map["position"]].dropna().astype(str).tolist()
        unique_positions: list[str] = []
        for value in raw_positions:
            cleaned = value.strip()
            if cleaned and cleaned not in unique_positions:
                unique_positions.append(cleaned)
        with st.expander("Сопоставление должностей", expanded=False):
            for name in unique_positions:
                default_position = position_name_lookup.get(_normalize_key(name))
                default_label = (
                    f"{default_position.id} - {default_position.name}"
                    if default_position
                    else "Не выбрано"
                )
                selected = st.selectbox(
                    f"{name}",
                    position_options,
                    index=position_options.index(default_label),
                    key=f"pos_map_{name}",
                )
                if selected == "Не назначать":
                    position_map[name] = None
                elif selected != "Не выбрано":
                    position_map[name] = position_lookup[selected].id
    else:
        st.info("Выберите колонку с должностями, чтобы настроить маппинг.")

    st.subheader("Проблемные строки")
    restaurant_map_normalized = {
        _normalize_key(key): value for key, value in restaurant_map.items()
    }
    position_map_normalized = {
        _normalize_key(key): value for key, value in position_map.items()
    }
    problem_df = _collect_problem_rows(
        df,
        column_map,
        restaurant_name_lookup,
        position_name_lookup,
        restaurant_map_normalized,
        position_map_normalized,
    )
    if problem_df.empty:
        st.success("Проблемные строки не найдены.")
        edited_problem_df = pd.DataFrame()
    else:
        st.write(
            "Можно исправить значения прямо здесь и повторно импортировать."
        )
        edited_problem_df = st.data_editor(
            problem_df,
            use_container_width=True,
            key="problem_editor",
        )

    st.subheader("Проверка дублей")
    if col_iiko_code != "Не выбрано":
        dup_iiko = df[col_iiko_code].dropna().astype(str).duplicated().sum()
        st.write(f"Дубликаты по iiko_code: {dup_iiko}")
    if col_staff_code != "Не выбрано":
        dup_staff = df[col_staff_code].dropna().astype(str).duplicated().sum()
        st.write(f"Дубликаты по staff_code: {dup_staff}")

    st.subheader("Параметры импорта")
    company_options = {f"{c.id} - {c.name}": c.id for c in companies}
    company_label = st.selectbox("Компания", list(company_options.keys()) or ["Не выбрано"])
    company_id = company_options.get(company_label)
    update_existing = st.checkbox("Обновлять существующих", value=False)
    sync_iiko = st.checkbox("Подтягивать iiko GUID", value=False)
    dry_run = st.checkbox("Пробный запуск (без записи в БД)", value=False)
    limit = st.number_input(
        "Ограничение строк (0 = без лимита)", min_value=0, value=0, step=1
    )

    if st.button("Запустить импорт"):
        if not company_id:
            st.error("Выберите компанию для импорта.")
            return
        df_for_import = df.copy()
        if not edited_problem_df.empty:
            edited_clean = edited_problem_df.drop(columns=["Проблема"], errors="ignore")
            df_for_import.loc[edited_clean.index, edited_clean.columns] = edited_clean
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(uploaded.getbuffer())
            tmp_path = Path(tmp.name)
        summary = import_employees(
            file_path=tmp_path,
            dataframe=df_for_import,
            sheet_name=sheet,
            company_id=company_id,
            update_existing=update_existing,
            sync_iiko=sync_iiko,
            limit=limit or None,
            dry_run=dry_run,
            restaurant_map=restaurant_map_normalized,
            position_map=position_map_normalized,
            column_map=column_map,
        )
        st.success("Импорт завершен")
        st.text(format_summary(summary, sync_iiko=sync_iiko))
        with st.expander("Технический отчет"):
            st.json(summary)


if __name__ == "__main__":
    main()
