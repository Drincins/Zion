"""
Streamlit утилита для iiko employees:
- Сайдбар: авторизация (авто SHA1 пароля), key подставляется автоматически.
- Таб «Поиск/редактирование»: по табельному номеру, форма с данными, отправка POST (частичное) или PUT (полная замена).
- Таб «Создание»: заполнение и PUT /employees/byCode/{code} с XML.

Запуск: streamlit run tools/iiko_employee_tester.py
"""
from __future__ import annotations

import textwrap
import xml.etree.ElementTree as ET
from hashlib import sha1
from typing import Any, Dict, Optional

import requests
import streamlit as st


DEFAULT_BASE_URL = "https://restoran-razgar.iiko.it/resto/api"
DEFAULT_LOGIN = "Andrey"
DEFAULT_PASSWORD = "415278"
REQUEST_TIMEOUT = 30


def build_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def send_request(
    method: str,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    body: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
    verify_ssl: bool = False,
) -> Dict[str, Any]:
    try:
        response = requests.request(
            method=method.upper(),
            url=url,
            params=params,
            data=body,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            verify=verify_ssl,
        )
    except requests.RequestException as exc:
        # Возвращаем текст и тип исключения, чтобы в UI было понятно, что случилось (таймаут/SSL и т.п.)
        return {"error": f"{exc.__class__.__name__}: {exc}", "response": None}
    except Exception as exc:  # pragma: no cover - неожиданные ошибки
        return {"error": f"{exc.__class__.__name__}: {exc}", "response": None}
    return {"error": None, "response": response}


def fetch_key(base_url: str, login: str, password: str, verify_ssl: bool) -> Optional[str]:
    hashed = sha1(password.encode("utf-8")).hexdigest()
    auth_url = build_url(base_url, "/auth")
    result = send_request(
        "GET",
        auth_url,
        params={"login": login, "pass": hashed},
        verify_ssl=verify_ssl,
    )
    if result["error"] or not result["response"]:
        st.sidebar.error(result["error"] or "Нет ответа от /auth")
        st.sidebar.caption(f"Запрос: GET {auth_url}")
        return None
    if result["response"].status_code != 200:
        st.sidebar.error(f"Ошибка /auth {result['response'].status_code}: {result['response'].text}")
        return None
    key = (result["response"].text or "").strip()
    if not key:
        st.sidebar.error("Пустой key от /auth")
        return None
    return key


def parse_employees(xml_text: str) -> list[Dict[str, Any]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    def read_list(parent: ET.Element, tag: str) -> list[str]:
        return [node.text for node in parent.findall(tag) if node.text]

    def val(emp: ET.Element, tag: str) -> Optional[str]:
        node = emp.find(tag)
        return node.text if node is not None and node.text else None

    def extract(emp: ET.Element) -> Dict[str, Any]:
        return {
            "id": val(emp, "id"),
            "code": val(emp, "code"),
            "name": val(emp, "name"),
            "login": val(emp, "login"),
            "mainRoleCode": val(emp, "mainRoleCode"),
            "roleCodes": read_list(emp, "roleCodes") or read_list(emp, "rolesIds"),
            "firstName": val(emp, "firstName"),
            "middleName": val(emp, "middleName"),
            "lastName": val(emp, "lastName"),
            "phone": val(emp, "phone"),
            "cellPhone": val(emp, "cellPhone"),
            "email": val(emp, "email"),
            "birthday": val(emp, "birthday"),
            "hireDate": val(emp, "hireDate"),
            "fireDate": val(emp, "fireDate"),
            "cardNumber": val(emp, "cardNumber"),
            "personalDataConsent": val(emp, "personalDataConsent"),
            "employee": val(emp, "employee"),
            "client": val(emp, "client"),
            "supplier": val(emp, "supplier"),
            "departmentCodes": read_list(emp, "departmentCodes"),
            "preferredDepartmentCode": val(emp, "preferredDepartmentCode"),
            "responsibilityDepartmentCodes": read_list(emp, "responsibilityDepartmentCodes"),
        }

    employees: list[Dict[str, Any]] = []
    if root.tag == "employee":
        employees.append(extract(root))
    else:
        for emp in root.findall(".//employee"):
            employees.append(extract(emp))
    return [e for e in employees if any(v for v in e.values() if v)]


def parse_items(xml_text: str, item_tags: list[str] | None = None) -> list[Dict[str, Any]]:
    """Простой разбор списков; item_tags - список допустимых тегов элементов.
    Если item_tags не задан, берём все узлы (кроме корня) у которых есть дети."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    tags = set(item_tags or [])
    items: list[Dict[str, Any]] = []
    for node in root.iter():
        if node is root:
            continue
        if tags and node.tag not in tags:
            continue
        # если тег не задан и у узла нет детей, пропускаем (это лист, а не элемент-объект)
        if not tags and len(list(node)) == 0:
            continue
        entry: Dict[str, Any] = {}
        for child in list(node):
            tag = child.tag
            value = child.text if child.text is not None else ""
            entry[tag] = value
        if entry:
            items.append(entry)
    return items


def employee_to_xml(data: Dict[str, Any]) -> str:
    role_codes = data.get("roleCodes") or []
    if isinstance(role_codes, str):
        role_codes = [role_codes]
    role_nodes = "".join(f"<roleCodes>{c}</roleCodes>" for c in role_codes if c)
    name = data.get("name") or " ".join(
        x for x in [data.get("lastName"), data.get("firstName"), data.get("middleName")] if x
    )
    xml = textwrap.dedent(
        f"""\
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <employee>
            <code>{data.get("code","")}</code>
            <name>{name}</name>
            <login>{data.get("login","")}</login>
            <mainRoleCode>{data.get("mainRoleCode","")}</mainRoleCode>
            {role_nodes or "<roleCodes></roleCodes>"}
            <phone>{data.get("phone","")}</phone>
            <cellPhone>{data.get("cellPhone","")}</cellPhone>
            <firstName>{data.get("firstName","")}</firstName>
            <middleName>{data.get("middleName","")}</middleName>
            <lastName>{data.get("lastName","")}</lastName>
            <birthday>{data.get("birthday","")}</birthday>
            <email>{data.get("email","")}</email>
            <cardNumber>{data.get("cardNumber","")}</cardNumber>
            <personalDataConsent>{str(data.get("personalDataConsent") or "").lower()}</personalDataConsent>
            <hireDate>{data.get("hireDate","")}</hireDate>
            <fireDate>{data.get("fireDate","")}</fireDate>
            <employee>{str(data.get("employee", True)).lower()}</employee>
            <client>{str(data.get("client", False)).lower()}</client>
            <supplier>{str(data.get("supplier", False)).lower()}</supplier>
            {''.join(f"<departmentCodes>{c}</departmentCodes>" for c in data.get("departmentCodes", []) or [])}
            <preferredDepartmentCode>{data.get("preferredDepartmentCode","")}</preferredDepartmentCode>
            {''.join(f"<responsibilityDepartmentCodes>{c}</responsibilityDepartmentCodes>" for c in data.get("responsibilityDepartmentCodes", []) or [])}
        </employee>
        """
    ).strip()
    return xml


def init_state() -> None:
    defaults = {
        "api_key": "",
        "employee_form": {},
        "new_employee_form": {},
        "auto_auth_done": False,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


st.set_page_config(page_title="iiko employees editor", layout="wide")
init_state()

with st.sidebar:
    st.header("Авторизация")
    base_url = st.text_input("Base URL", value=DEFAULT_BASE_URL)
    login = st.text_input("Логин", value=DEFAULT_LOGIN)
    password = st.text_input("Пароль", value=DEFAULT_PASSWORD, type="password")
    verify_ssl = st.checkbox("Проверять SSL сертификат", value=False)

    if st.button("Обновить key"):
        key = fetch_key(base_url, login, password, verify_ssl)
        if key:
            st.session_state["api_key"] = key
            st.success("Ключ обновлён")

    if not st.session_state["api_key"] and not st.session_state["auto_auth_done"]:
        key = fetch_key(base_url, login, password, verify_ssl)
        st.session_state["auto_auth_done"] = True
        if key:
            st.session_state["api_key"] = key

    st.text_input("Текущий key", value=st.session_state.get("api_key", ""), key="key_display", label_visibility="collapsed")


tab_view, tab_create, tab_codes = st.tabs(["Поиск/редактирование", "Создание", "Коды (подразделения/роли/позиции)"])

# ------------------------ Поиск/редактирование ------------------------------
with tab_view:
    st.subheader("Поиск по табельному номеру")
    col_search, col_btn = st.columns([2, 1])
    staff_code = col_search.text_input(
        "Табельный номер (code)",
        value=st.session_state["employee_form"].get("code", ""),
        key="search_code",
    )
    if col_btn.button("Найти", key="btn_find"):
        if not staff_code.strip():
            st.error("Введите табельный номер.")
        elif not st.session_state.get("api_key"):
            st.error("Нет key. Авторизуйтесь слева.")
        else:
            params = {"key": st.session_state["api_key"]}
            request_url = build_url(base_url, f"/employees/byCode/{staff_code.strip()}")
            result = send_request("GET", request_url, params=params, verify_ssl=verify_ssl)
            if result["error"] or not result["response"]:
                st.error(result["error"] or "Нет ответа")
                st.caption(f"Запрос: GET {request_url}")
            elif result["response"].status_code != 200:
                st.error(f"Ошибка {result['response'].status_code}: {result['response'].text}")
                st.caption(f"Запрос: GET {request_url}")
            else:
                raw_text = result["response"].content.decode(result["response"].encoding or "utf-8", errors="replace")
                employees = parse_employees(raw_text)
                if not employees:
                    st.warning("Сотрудник не найден в ответе.")
                else:
                    st.success("Нашёл, заполнил форму.")
                    st.session_state["employee_form"] = employees[0]

    form = st.session_state.get("employee_form") or {}
    if form:
        st.markdown("### Данные сотрудника")
        c1, c2, c3 = st.columns(3)
        form["code"] = c1.text_input("code", value=form.get("code", ""), key="form_code")
        form["id"] = c2.text_input("id (UUID)", value=form.get("id", ""), key="form_id")
        form["login"] = c3.text_input("login", value=form.get("login", ""), key="form_login")

        c4, c5, c6 = st.columns(3)
        form["lastName"] = c4.text_input("Фамилия", value=form.get("lastName", ""), key="form_lastName")
        form["firstName"] = c5.text_input("Имя", value=form.get("firstName", ""), key="form_firstName")
        form["middleName"] = c6.text_input("Отчество", value=form.get("middleName", ""), key="form_middleName")

        c7, c8, c9 = st.columns(3)
        form["cellPhone"] = c7.text_input("Телефон", value=form.get("cellPhone", ""), key="form_cellPhone")
        form["phone"] = c8.text_input("Раб. телефон", value=form.get("phone", ""), key="form_phone")
        form["email"] = c9.text_input("Email", value=form.get("email", ""), key="form_email")

        c10, c11, c12 = st.columns(3)
        form["birthday"] = c10.text_input("ДР (YYYY-MM-DDTHH:MM:SS+HH:MM)", value=form.get("birthday", ""), key="form_birthday")
        form["hireDate"] = c11.text_input("Дата найма", value=form.get("hireDate", ""), key="form_hireDate")
        form["fireDate"] = c12.text_input("Дата увольнения", value=form.get("fireDate", ""), key="form_fireDate")

        c13, c14 = st.columns(2)
        form["mainRoleCode"] = c13.text_input("mainRoleCode", value=form.get("mainRoleCode", ""), key="form_mainRoleCode")
        roles_str = ",".join(form.get("roleCodes") or [])
        roles_str = c14.text_input("roleCodes (через запятую)", value=roles_str, key="form_roleCodes")
        form["roleCodes"] = [x.strip() for x in roles_str.split(",") if x.strip()]

        c15, c16 = st.columns(2)
        dept_str = ",".join(form.get("departmentCodes") or [])
        dept_str = c15.text_input("departmentCodes (коды подразделений через запятую)", value=dept_str, key="form_departmentCodes")
        form["departmentCodes"] = [d.strip() for d in dept_str.split(",") if d.strip()]
        form["preferredDepartmentCode"] = c16.text_input("preferredDepartmentCode", value=form.get("preferredDepartmentCode",""), key="form_prefDept")

        form["cardNumber"] = st.text_input("cardNumber", value=form.get("cardNumber", ""), key="form_cardNumber")
        consent_bool = str(form.get("personalDataConsent") or "").lower() in ("true", "1", "yes")
        form["personalDataConsent"] = st.checkbox("Согласие на обработку персональных данных", value=consent_bool, key="form_consent")
        form["employee"] = st.checkbox("employee", value=str(form.get("employee","true")).lower() in ("true","1","yes"), key="form_employee")
        form["client"] = st.checkbox("client", value=str(form.get("client","false")).lower() in ("true","1","yes"), key="form_client")
        form["supplier"] = st.checkbox("supplier", value=str(form.get("supplier","false")).lower() in ("true","1","yes"), key="form_supplier")

        st.session_state["employee_form"] = form

        send_mode = st.radio(
            "Способ отправки",
            options=[
                "POST (form-urlencoded, частичное обновление)",
                "PUT (XML, полная замена)",
            ],
            index=0,
        )

        if st.button("Отправить изменения", key="btn_update"):
            if not form.get("id"):
                st.error("Нет UUID (id).")
            else:
                key_value = (st.session_state.get("api_key") or "").strip()
                if not key_value:
                    st.error("Нет key. Авторизуйтесь слева.")
                else:
                    params = {"key": key_value}
                    request_url = build_url(base_url, f"/employees/byId/{form['id']}")
                    url_with_key = f"{request_url}?key={key_value}"
                    method = "POST" if send_mode.startswith("POST") else "PUT"

                    if method == "POST":
                        payload: Dict[str, Any] = {}
                        for key in [
                            "code",
                            "name",
                            "login",
                            "mainRoleCode",
                            "phone",
                            "cellPhone",
                            "firstName",
                            "middleName",
                            "lastName",
                            "birthday",
                            "email",
                            "cardNumber",
                            "hireDate",
                            "fireDate",
                        ]:
                            if form.get(key):
                                payload[key] = form[key]
                        if form.get("roleCodes"):
                            payload["roleCodes"] = ",".join(form["roleCodes"])
                        if form.get("personalDataConsent") is not None:
                            payload["personalDataConsent"] = str(form["personalDataConsent"]).lower()

                        result = send_request(method, request_url, params=params, body=payload, headers=None, verify_ssl=verify_ssl)
                        body_to_show = payload
                    else:
                        xml_body = employee_to_xml(form)
                        result = send_request(
                            method,
                            request_url,
                            params=params,
                            body=xml_body,
                            headers={"Content-Type": "application/xml"},
                            verify_ssl=verify_ssl,
                        )
                        body_to_show = xml_body

                resp = result.get("response")
                if result.get("error") or resp is None:
                    st.error(result.get("error") or "Нет ответа (response пустой)")
                    st.caption(f"verify_ssl={verify_ssl}")
                    st.caption(f"Запрос: {method} {url_with_key}")
                elif resp.status_code not in (200, 201):
                    st.error(f"Ошибка {resp.status_code}: {resp.text}")
                    st.caption(f"Запрос: {method} {url_with_key}")
                else:
                    st.success(f"Отправлено. Статус {resp.status_code}")
                    st.caption(f"Запрос: {method} {url_with_key}")
                    if method == "POST":
                        st.json(body_to_show)
                    else:
                        st.code(body_to_show, language="xml")
    else:
        st.info("Сначала найдите сотрудника по табельному номеру.")

# ----------------------------- Создание -------------------------------------
with tab_create:
    st.subheader("Создание сотрудника (PUT /employees/byCode/{code})")
    new_form = st.session_state.get("new_employee_form") or {}

    c1, c2, c3 = st.columns(3)
    new_form["code"] = c1.text_input("code", value=new_form.get("code", ""), key="new_code")
    new_form["login"] = c2.text_input("login", value=new_form.get("login", ""), key="new_login")
    new_form["mainRoleCode"] = c3.text_input("mainRoleCode", value=new_form.get("mainRoleCode", ""), key="new_mainRoleCode")

    c4, c5, c6 = st.columns(3)
    new_form["lastName"] = c4.text_input("Фамилия", value=new_form.get("lastName", ""), key="new_lastName")
    new_form["firstName"] = c5.text_input("Имя", value=new_form.get("firstName", ""), key="new_firstName")
    new_form["middleName"] = c6.text_input("Отчество", value=new_form.get("middleName", ""), key="new_middleName")

    c7, c8, c9 = st.columns(3)
    new_form["cellPhone"] = c7.text_input("Телефон", value=new_form.get("cellPhone", ""), key="new_cellPhone")
    new_form["phone"] = c8.text_input("Раб. телефон", value=new_form.get("phone", ""), key="new_phone")
    new_form["email"] = c9.text_input("Email", value=new_form.get("email", ""), key="new_email")

    c10, c11, c12 = st.columns(3)
    new_form["birthday"] = c10.text_input("ДР (YYYY-MM-DDTHH:MM:SS+HH:MM)", value=new_form.get("birthday", ""), key="new_birthday")
    new_form["hireDate"] = c11.text_input("Дата найма", value=new_form.get("hireDate", ""), key="new_hireDate")
    new_form["fireDate"] = c12.text_input("Дата увольнения", value=new_form.get("fireDate", ""), key="new_fireDate")

    c13, c14 = st.columns(2)
    new_form["cardNumber"] = c13.text_input("cardNumber", value=new_form.get("cardNumber", ""), key="new_cardNumber")
    roles_new = ",".join(new_form.get("roleCodes") or [])
    roles_new = c14.text_input("roleCodes (через запятую)", value=roles_new, key="new_roleCodes")
    new_form["roleCodes"] = [x.strip() for x in roles_new.split(",") if x.strip()]

    c15, c16 = st.columns(2)
    dept_new = ",".join(new_form.get("departmentCodes") or [])
    dept_new = c15.text_input("departmentCodes (коды подразделений через запятую)", value=dept_new, key="new_departmentCodes")
    new_form["departmentCodes"] = [d.strip() for d in dept_new.split(",") if d.strip()]
    new_form["preferredDepartmentCode"] = c16.text_input("preferredDepartmentCode", value=new_form.get("preferredDepartmentCode",""), key="new_prefDept")

    consent_new = str(new_form.get("personalDataConsent") or "").lower() in ("true", "1", "yes")
    new_form["personalDataConsent"] = st.checkbox("Согласие на обработку персональных данных", value=consent_new, key="new_consent")
    new_form["employee"] = st.checkbox("employee", value=str(new_form.get("employee","true")).lower() in ("true","1","yes"), key="new_employee")
    new_form["client"] = st.checkbox("client", value=str(new_form.get("client","false")).lower() in ("true","1","yes"), key="new_client")
    new_form["supplier"] = st.checkbox("supplier", value=str(new_form.get("supplier","false")).lower() in ("true","1","yes"), key="new_supplier")

    st.session_state["new_employee_form"] = new_form

    if st.button("Создать сотрудника", key="btn_create"):
        if not new_form.get("code"):
            st.error("Введите tabельный номер (code).")
        elif not new_form.get("departmentCodes"):
            st.error("Укажите departmentCodes (хотя бы один код подразделения iiko через запятую).")
        elif not new_form.get("mainRoleCode"):
            st.error("Укажите mainRoleCode (код роли в iiko).")
        elif not new_form.get("roleCodes"):
            st.error("Укажите roleCodes (хотя бы один код роли, через запятую).")
        else:
            key_value = (st.session_state.get("api_key") or "").strip()
            if not key_value:
                st.error("Нет key. Авторизуйтесь слева.")
            else:
                xml_body = employee_to_xml(new_form)
                params = {"key": key_value}
                request_url = build_url(base_url, f"/employees/byCode/{new_form['code']}")
                url_with_key = f"{request_url}?key={key_value}"
                result = send_request(
                    "PUT",
                    request_url,
                    params=params,
                    body=xml_body,
                    headers={"Content-Type": "application/xml"},
                    verify_ssl=verify_ssl,
                )
                resp = result.get("response")
                if result.get("error") or resp is None:
                    st.error(result.get("error") or "Нет ответа (response пустой)")
                    st.caption(f"verify_ssl={verify_ssl}")
                    st.caption(f"Запрос: PUT {url_with_key}")
                elif resp.status_code not in (200, 201):
                    st.error(f"Ошибка {resp.status_code}: {resp.text}")
                    st.caption(f"Запрос: PUT {url_with_key}")
                else:
                    st.success(f"Создание/замена выполнена. Статус {resp.status_code}")
                    st.caption(f"Запрос: PUT {url_with_key}")
                    st.code(xml_body, language="xml")

# ----------------------------- Коды -----------------------------------------
with tab_codes:
    st.subheader("Справочники iiko (департаменты/роли/позиции)")
    key_value = (st.session_state.get("api_key") or "").strip()
    if not key_value:
        st.info("Нет key — авторизуйтесь слева.")
    else:
        def render_lookup(title: str, options: list[str], item_tags: list[str], button_key: str):
            path_choice = st.selectbox(
                f"{title} — выберите endpoint",
                options=options,
                key=f"{button_key}_select",
            )
            custom_path = st.text_input(
                f"{title}: свой путь (опционально)",
                value="",
                key=f"{button_key}_custom",
                help="Если хотите проверить другой endpoint, укажите путь, например /resto/api/... ",
            )
            if st.button(title, key=button_key):
                endpoint = custom_path.strip() or path_choice
                url = build_url(base_url, endpoint)
                result = send_request("GET", url, params={"key": key_value}, verify_ssl=verify_ssl)
                resp = result.get("response")
                if result.get("error") or resp is None:
                    st.error(result.get("error") or "Нет ответа")
                    st.caption(f"Запрос: GET {url}?key={key_value}")
                    return
                st.caption(f"Запрос: GET {url}?key={key_value}")
                if resp.status_code != 200:
                    st.error(f"Ошибка {resp.status_code}: {resp.text}")
                    return
                text = resp.content.decode(resp.encoding or "utf-8", errors="replace")
                st.code(text, language="xml")
                parsed = parse_items(text, item_tags)
                if parsed:
                    st.markdown("Распарсенные значения:")
                    st.dataframe(parsed, use_container_width=True)
                else:
                    st.info("Не удалось распарсить элементы — проверьте XML выше.")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            render_lookup(
                "Департаменты",
                [
                    "/employees/departments",
                    "/corporation/departments",
                    "/corporation/departments/",
                    "/corporation/stores",
                    "/corporation/stores/",
                    "/corporation/groups",
                    "/corporation/groups/",
                ],
                ["department", "corporateItemDto", "store", "groupDto", "pointOfSaleDto"],
                "btn_deps",
            )
        with col_b:
            render_lookup(
                "Должности (roles)",
                ["/employees/roles"],
                ["role"],
                "btn_roles",
            )
        with col_c:
            render_lookup(
                "Позиции",
                ["/positions", "/positions/list", "/employees/positions"],
                ["position"],
                "btn_positions",
            )

        st.markdown("### Поиск подразделения по коду (corporation/departments/search)")
        dept_search_code = st.text_input("departmentCode", value="", key="dept_search_code")
        if st.button("Найти подразделение", key="btn_dept_search"):
            if not dept_search_code.strip():
                st.error("Введите код подразделения.")
            else:
                url = build_url(base_url, "/corporation/departments/search")
                result = send_request(
                    "GET",
                    url,
                    params={"key": key_value, "code": dept_search_code.strip()},
                    verify_ssl=verify_ssl,
                )
                resp = result.get("response")
                if result.get("error") or resp is None:
                    st.error(result.get("error") or "Нет ответа")
                    st.caption(f"Запрос: GET {url}?key={key_value}&code={dept_search_code.strip()}")
                elif resp.status_code != 200:
                    st.error(f"Ошибка {resp.status_code}: {resp.text}")
                    st.caption(f"Запрос: GET {url}?key={key_value}&code={dept_search_code.strip()}")
                else:
                    text = resp.content.decode(resp.encoding or "utf-8", errors="replace")
                    st.code(text, language="xml")
                    parsed = parse_items(text, ["corporateItemDto", "department", "store", "groupDto"])
                    if parsed:
                        st.json(parsed)
                    else:
                        st.info("Не удалось распарсить элементы — проверьте XML выше.")
