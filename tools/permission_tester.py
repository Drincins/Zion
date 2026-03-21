"""Интерактивная утилита Streamlit для проверки ролей, прав и маршрутов API.

Запуск из корня проекта:

    streamlit run tools/permission_tester.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import requests
import streamlit as st


# ---- Конфигурация --------------------------------------------------------

DEFAULT_BASE_URL = "http://localhost:8000/api"
REQUEST_TIMEOUT = 30


# ---- Вспомогательные структуры ------------------------------------------

@dataclass
class ApiResult:
    ok: bool
    response: Optional[requests.Response] = None
    error: Optional[str] = None


def api_request(
    method: str,
    base_url: str,
    path: str,
    token: Optional[str],
    *,
    params: Optional[Dict[str, Any]] = None,
    json_payload: Optional[Any] = None,
) -> ApiResult:
    """Отправить запрос к API и вернуть результат в виде объекта ApiResult."""
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    headers: Dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            params=params,
            json=json_payload,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:  # pragma: no cover - UI вывод
        return ApiResult(ok=False, error=str(exc))

    return ApiResult(ok=True, response=response)


def render_response(result: ApiResult) -> None:
    """Показать информацию об ответе API в интерфейсе Streamlit."""
    if not result.ok or not result.response:
        st.error(result.error or "Не удалось выполнить запрос")
        return

    response = result.response
    st.write(f"Статус: `{response.status_code}`")
    st.write("Заголовки:")
    st.json(dict(response.headers))
    if not response.text:
        st.info("Тело ответа отсутствует.")
        return
    try:
        st.json(response.json())
    except Exception:  # pragma: no cover - показываем «как есть»
        st.code(response.text, language="json")


def permission_lookup(permissions: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}
    for item in permissions:
        code = (item or {}).get("code")
        if code:
            lookup[code] = item
    return lookup


def routes_by_permission(routes: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for route in routes:
        codes = route.get("permission_codes") or []
        if not codes:
            continue
        entry = {
            "method": str(route.get("method", "")).upper(),
            "path": route.get("path", ""),
            "summary": route.get("summary") or "",
            "tags": route.get("tags") or [],
        }
        entry["label"] = format_route_label(entry)
        for code in codes:
            if not code:
                continue
            grouped.setdefault(code, []).append(entry)
    return grouped


def format_route_label(route: Dict[str, Any]) -> str:
    method = route.get("method", "")
    path = route.get("path", "")
    summary = route.get("summary", "")
    tags = route.get("tags") or []
    parts: List[str] = []
    main = f"{method} {path}".strip()
    if main:
        parts.append(main)
    if summary:
        parts.append(f"- {summary}")
    if tags:
        parts.append(f"[{', '.join(tags)}]")
    return " ".join(parts) if parts else (path or method or "-")


def parse_json_input(label: str, value: str) -> Optional[Any]:
    """Разобрать JSON из текстового поля и вывести ошибку при невалидном вводе."""
    if not value.strip():
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        st.error(f"{label}: неверный JSON — {exc}")
        return None


# ---- Настройка страницы --------------------------------------------------

st.set_page_config(page_title="Тестер прав доступа", layout="wide")


def ensure_session_defaults() -> None:
    defaults = {
        "base_url": DEFAULT_BASE_URL,
        "token": None,
        "user": None,
        "permissions": [],
        "roles": [],
        "positions": [],
        "permission_routes": [],
        "companies": [],
        "restaurants": [],
        "restaurant_subdivisions": [],
        "restaurants_loaded_for_company": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


ensure_session_defaults()


# ---- Боковая панель: авторизация и настройки -----------------------------

st.sidebar.title("Подключение")
st.sidebar.caption(
    "Укажите адрес API и выполните вход под пользователем, который имеет доступ "
    "к маршрутам управления правами."
)

with st.sidebar.form("login_form"):
    base_url = st.text_input("Базовый URL", value=st.session_state.base_url)
    username = st.text_input("Имя пользователя", value="", autocomplete="username")
    password = st.text_input("Пароль", value="", type="password", autocomplete="current-password")
    submitted = st.form_submit_button("Войти")

    if submitted:
        st.session_state.base_url = base_url or DEFAULT_BASE_URL
        payload = {"username": username.strip(), "password": password}
        result = api_request("POST", st.session_state.base_url, "/auth/login", None, json_payload=payload)
        if not result.ok or not result.response:
            st.error(result.error or "Ошибка авторизации")
        elif result.response.status_code != 200:
            st.error(f"Авторизация отклонена: {result.response.text or result.response.status_code}")
        else:
            data = result.response.json()
            st.session_state.token = data.get("access_token")
            st.session_state.user = data.get("user")
            username_display = st.session_state.user.get("username") if st.session_state.user else username
            st.success(f"Выполнен вход как {username_display}")

if st.sidebar.button("Выйти", disabled=st.session_state.token is None):
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.permissions = []
    st.session_state.roles = []
    st.session_state.positions = []
    st.session_state.permission_routes = []
    st.success("Сессия завершена")

if st.session_state.user:
    st.sidebar.markdown("### Текущий пользователь")
    st.sidebar.json(st.session_state.user)

if st.session_state.token:
    with st.sidebar.expander("JWT-токен", expanded=False):
        st.code(st.session_state.token, language="text")


# ---- Загрузка данных -----------------------------------------------------

st.title("Тестер прав доступа")

if st.session_state.token is None:
    st.info("Авторизуйтесь через форму слева, чтобы продолжить.")
    st.stop()


def load_permissions() -> None:
    result = api_request("GET", st.session_state.base_url, "/access/permissions", st.session_state.token)
    if not result.ok or not result.response:
        st.error(result.error or "Не удалось получить список прав")
        return
    if result.response.status_code != 200:
        st.error(f"Не удалось получить список прав: {result.response.text or result.response.status_code}")
        return
    st.session_state.permissions = result.response.json()
    st.success(f"Загружено прав: {len(st.session_state.permissions)}")


def load_roles() -> None:
    result = api_request("GET", st.session_state.base_url, "/access/roles", st.session_state.token)
    if not result.ok or not result.response:
        st.error(result.error or "Не удалось получить список ролей")
        return
    if result.response.status_code != 200:
        st.error(f"Не удалось получить список ролей: {result.response.text or result.response.status_code}")
        return
    st.session_state.roles = result.response.json()
    st.success(f"Загружено ролей: {len(st.session_state.roles)}")


def load_positions() -> None:
    result = api_request("GET", st.session_state.base_url, "/access/positions", st.session_state.token)
    if not result.ok or not result.response:
        st.error(result.error or "Не удалось получить список должностей")
        return
    if result.response.status_code != 200:
        st.error(f"Не удалось получить список должностей: {result.response.text or result.response.status_code}")
        return
    st.session_state.positions = result.response.json()
    st.success(f"Загружено должностей: {len(st.session_state.positions)}")


def load_permission_map() -> None:
    result = api_request("GET", st.session_state.base_url, "/access/permission-map", st.session_state.token)
    if not result.ok or not result.response:
        st.error(result.error or "Не удалось получить карту маршрутов")
        return
    if result.response.status_code != 200:
        st.error(f"Не удалось получить карту маршрутов: {result.response.text or result.response.status_code}")
        return
    data = result.response.json() or {}
    st.session_state.permission_routes = data.get("routes", [])
    st.success(f"Загружено маршрутов: {len(st.session_state.permission_routes)}")


# ---- Справочники для payroll --------------------------------------------------

def load_companies() -> None:
    result = api_request("GET", st.session_state.base_url, "/companies/", st.session_state.token)
    if not result.ok or not result.response:
        st.error(result.error or "Не удалось получить компании")
        return
    if result.response.status_code != 200:
        st.error(
            f"Не удалось получить компании: {result.response.status_code} "
            f"{result.response.text[:400] if result.response.text else ''}"
        )
        return
    st.session_state.companies = result.response.json()
    st.success(f"Компаний: {len(st.session_state.companies)}")


def load_restaurants(company_id: str | None = None) -> None:
    params = {}
    if company_id:
        params["company_id"] = company_id
    result = api_request("GET", st.session_state.base_url, "/restaurants/", st.session_state.token, params=params)
    if not result.ok or not result.response:
        st.error(result.error or "Не удалось получить рестораны")
        return
    if result.response.status_code != 200:
        st.error(
            f"Не удалось получить рестораны: {result.response.status_code} "
            f"{result.response.text[:400] if result.response.text else ''}"
        )
        return
    st.session_state.restaurants = result.response.json()
    st.session_state.restaurants_loaded_for_company = company_id
    st.success(f"Ресторанов: {len(st.session_state.restaurants)}")


def load_subdivisions() -> None:
    result = api_request("GET", st.session_state.base_url, "/access/restaurant-subdivisions", st.session_state.token)
    if not result.ok or not result.response:
        st.error(result.error or "Не удалось получить подразделения")
        return
    if result.response.status_code != 200:
        st.error(f"Не удалось получить подразделения: {result.response.text or result.response.status_code}")
        return
    st.session_state.restaurant_subdivisions = result.response.json()
    st.success(f"Подразделений: {len(st.session_state.restaurant_subdivisions)}")


with st.expander("Загрузить данные", expanded=False):
    cols = st.columns(4)
    if cols[0].button("Загрузить права"):
        load_permissions()
    if cols[1].button("Загрузить роли"):
        load_roles()
    if cols[2].button("Загрузить должности"):
        load_positions()
    if cols[3].button("Загрузить маршруты"):
        load_permission_map()


# ---- Вкладки -------------------------------------------------------------

tab_api, tab_payroll, tab_permissions, tab_roles, tab_positions, tab_routes = st.tabs(
    ['API', 'Payroll export', 'Permissions', 'Roles', 'Positions', 'Routes map']
)


with tab_api:
    st.subheader("Произвольный API-запрос")
    method = st.selectbox("Метод", ["GET", "POST", "PUT", "PATCH", "DELETE"], index=0)
    path = st.text_input("Путь", value="/users")
    query_params_raw = st.text_area("Query params (JSON)", value="", height=120)
    json_body_raw = st.text_area("Тело запроса (JSON)", value="", height=200)

    if st.button("Выполнить запрос"):
        params = parse_json_input("Query params", query_params_raw)
        if params is None and query_params_raw.strip():
            st.stop()
        payload = parse_json_input("Тело запроса", json_body_raw)
        if payload is None and json_body_raw.strip():
            st.stop()
        result = api_request(
            method,
            st.session_state.base_url,
            path,
            st.session_state.token,
            params=params,
            json_payload=payload,
        )
        render_response(result)



with tab_payroll:
    st.subheader("Payroll export (xlsx)")
    col_p, col_c, col_r, col_s = st.columns(4)
    period = col_p.text_input("Period YYYY-MM", value="2025-11")

    if st.button("Refresh lists (companies/restaurants/subdivisions)"):
        load_companies()
        load_restaurants(None)
        load_subdivisions()

    companies = st.session_state.companies or []
    if companies:
        company_options = ["" ] + [f"{c.get('id')} ? {c.get('name')}" for c in companies]
        company_choice = col_c.selectbox("Company", options=company_options, index=0)
        company_id = company_choice.split(" ? ")[0] if company_choice else ""
    else:
        company_id = col_c.text_input("company_id (manual if list empty)", value="")

    # Auto-load restaurants for selected company
    if company_id and st.session_state.restaurants_loaded_for_company != company_id:
        load_restaurants(company_id)
    elif not company_id and st.session_state.restaurants_loaded_for_company not in (None, ""):
        load_restaurants(None)

    restaurants = st.session_state.restaurants or []
    if restaurants:
        restaurant_options = ["" ] + [f"{r.get('id')} ? {r.get('name')}" for r in restaurants]
        restaurant_choice = col_r.selectbox("Restaurant", options=restaurant_options, index=0)
        restaurant_id = restaurant_choice.split(" ? ")[0] if restaurant_choice else ""
    else:
        restaurant_id = col_r.text_input("restaurant_id (manual if list empty)", value="")

    subdivisions = st.session_state.restaurant_subdivisions or []
    if subdivisions:
        subdivision_options = ["", "ALL"] + [f"{s.get('id')} ? {s.get('name')}" for s in subdivisions]
        subdivision_choice = col_s.selectbox("Subdivision", options=subdivision_options, index=0)
        if subdivision_choice == "ALL":
            subdivision_id = ""
        else:
            subdivision_id = subdivision_choice.split(" ? ")[0] if subdivision_choice else ""
    else:
        subdivision_id = col_s.text_input("restaurant_subdivision_id (manual if list empty)", value="")

    if st.button("Download report"):
        params = {"period": period}
        if company_id:
            params["company_id"] = company_id
        if restaurant_id:
            params["restaurant_id"] = restaurant_id
        if subdivision_id:
            params["restaurant_subdivision_id"] = subdivision_id

        headers = {}
        if st.session_state.token:
            headers["Authorization"] = f"Bearer {st.session_state.token}"

        try:
            resp = requests.get(
                f"{st.session_state.base_url.rstrip('/')}/payroll/export",
                params=params,
                headers=headers,
                timeout=60,
            )
        except Exception as exc:  # pragma: no cover - UI helper
            st.error(f"Request error: {exc}")
        else:
            if resp.status_code != 200:
                content_type = resp.headers.get("content-type", "")
                try:
                    payload = resp.json()
                except Exception:
                    payload = resp.text
                st.error(f"Error {resp.status_code}: {payload}")
                st.caption(f"content-type: {content_type}")
            else:
                st.success("File ready")
                st.download_button(
                    "Download file",
                    data=resp.content,
                    file_name=f"payroll_{period}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )


with tab_permissions:
    st.subheader("Права доступа")
    if not st.session_state.permissions:
        st.info("Нажмите «Загрузить права» в блоке выше.")
    else:
        lookup = permission_lookup(st.session_state.permissions)
        codes = sorted(lookup.keys())
        selected_code = st.selectbox("Код права", options=codes)
        if selected_code:
            st.json(lookup[selected_code])
        st.markdown("### Все права")
        st.json(st.session_state.permissions)


with tab_roles:
    st.subheader("Роли")
    if not st.session_state.roles:
        st.info("Нажмите «Загрузить роли» в блоке выше.")
    else:
        st.dataframe(st.session_state.roles, use_container_width=True)


with tab_positions:
    st.subheader("Должности")
    if not st.session_state.positions:
        st.info("Нажмите «Загрузить должности» в блоке выше.")
    else:
        st.dataframe(st.session_state.positions, use_container_width=True)


with tab_routes:
    st.subheader("Маршруты по правам")
    if not st.session_state.permission_routes:
        st.info("Нажмите «Загрузить маршруты» в блоке выше.")
    else:
        grouped = routes_by_permission(st.session_state.permission_routes)
        available_codes = sorted(grouped.keys())
        selected_code = st.selectbox("Код права", options=available_codes)
        if selected_code:
            st.write(f"Маршруты, которые требуют `{selected_code}`:")
            for item in grouped[selected_code]:
                st.write(f"- {item['label']}")
        st.markdown("### Все маршруты")
        st.json(st.session_state.permission_routes)
