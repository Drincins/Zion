from __future__ import annotations

import os
import urllib3
from datetime import datetime
from typing import Any, Dict, List

import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _olap_timeout_seconds() -> int:
    raw = str(os.getenv("IIKO_OLAP_TIMEOUT_SECONDS", "180")).strip()
    try:
        value = int(raw)
    except Exception:
        value = 180
    return max(30, min(value, 3600))


def get_token(server: str, login: str, password_sha1: str) -> str:
    url = f"{server.rstrip('/')}/resto/api/auth"
    resp = requests.get(
        url,
        params={"login": login, "pass": password_sha1},
        verify=False,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.text.strip()


def get_olap_columns(server: str, token: str, report_type: str = "SALES") -> dict:
    url = f"{server.rstrip('/')}/resto/api/v2/reports/olap/columns"
    resp = requests.get(
        url,
        params={"key": token, "reportType": report_type},
        verify=False,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def to_iso_date(ddmmyyyy_or_iso: str) -> str:
    """Accepts 'DD.MM.YYYY' or 'YYYY-MM-DD' and returns 'YYYY-MM-DD'."""
    s = (ddmmyyyy_or_iso or "").strip()
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return s
    return datetime.strptime(s, "%d.%m.%Y").strftime("%Y-%m-%d")


def to_iso_dt_start(ddmmyyyy_or_iso: str) -> str:
    """For OpenDate (not Typed) -> DateTimeRange from."""
    s = (ddmmyyyy_or_iso or "").strip()
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        dt = datetime.strptime(s, "%Y-%m-%d")
    else:
        dt = datetime.strptime(s, "%d.%m.%Y")
    return dt.strftime("%Y-%m-%dT00:00:00.000")


def to_iso_dt_end(ddmmyyyy_or_iso: str) -> str:
    """For OpenDate (not Typed) -> DateTimeRange to."""
    s = (ddmmyyyy_or_iso or "").strip()
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        dt = datetime.strptime(s, "%Y-%m-%d")
    else:
        dt = datetime.strptime(s, "%d.%m.%Y")
    return dt.strftime("%Y-%m-%dT23:59:59.999")


def post_olap_report(
    server: str,
    token: str,
    *,
    report_type: str,
    groups: List[str],
    aggregates: List[str],
    date_field: str,
    from_date: str,
    to_date: str,
) -> requests.Response:
    """
    POST iiko OLAP report with a correct date filter.

    NOTE: `date_field` is used in filters only; it does not have to be present in `groups`.
    """
    url = f"{server.rstrip('/')}/resto/api/v2/reports/olap"
    if date_field.endswith(".Typed"):
        filt: Dict[str, Any] = {
            "filterType": "DateRange",
            "periodType": "CUSTOM",
            "from": to_iso_date(from_date),
            "to": to_iso_date(to_date),
            "includeLow": True,
            "includeHigh": True,
        }
    else:
        filt = {
            "filterType": "DateTimeRange",
            "periodType": "CUSTOM",
            "from": to_iso_dt_start(from_date),
            "to": to_iso_dt_end(to_date),
            "includeLow": True,
            "includeHigh": True,
        }

    payload: Dict[str, Any] = {
        "reportType": report_type,
        "buildSummary": False,
        "groupByRowFields": groups,
        "groupByColFields": [],
        "aggregateFields": aggregates,
        "filters": {date_field: filt},
    }
    return requests.post(
        url,
        params={"key": token},
        json=payload,
        verify=False,
        timeout=_olap_timeout_seconds(),
    )
