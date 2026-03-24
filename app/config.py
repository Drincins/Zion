import json
import os
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


@lru_cache(maxsize=1)
def _load_secret_payload() -> dict[str, Any]:
    provider = (_env("SECRET_MANAGER_PROVIDER", "") or "").lower()
    if provider not in {"aws", "aws_secrets_manager"}:
        return {}

    secret_id = _env("SECRET_MANAGER_SECRET_ID")
    if not secret_id:
        return {}

    client_kwargs: dict[str, str] = {}
    region = (
        _env("SECRET_MANAGER_AWS_REGION")
        or _env("AWS_REGION")
        or _env("AWS_DEFAULT_REGION")
    )
    if region:
        client_kwargs["region_name"] = region

    try:
        import boto3

        response = boto3.client("secretsmanager", **client_kwargs).get_secret_value(
            SecretId=secret_id
        )
    except Exception:
        return {}

    secret_string = response.get("SecretString")
    if not secret_string:
        secret_binary = response.get("SecretBinary")
        if not secret_binary:
            return {}
        try:
            secret_string = secret_binary.decode("utf-8")
        except Exception:
            return {}

    try:
        parsed = json.loads(secret_string)
    except json.JSONDecodeError:
        return {}

    if not isinstance(parsed, dict):
        return {}
    return parsed


def _env_or_secret(
    env_key: str,
    *,
    secret_key: str | None = None,
    default: str | None = None,
) -> str | None:
    value = _env(env_key)
    if value is not None:
        return value

    payload = _load_secret_payload()
    key = secret_key or env_key
    secret_value = payload.get(key)
    if secret_value is None:
        return default
    if isinstance(secret_value, str):
        secret_value = secret_value.strip()
        return secret_value if secret_value else default
    return str(secret_value)


def _json_map_from_env_or_secret(
    env_key: str,
    *,
    secret_key: str | None = None,
    default: dict[str, str] | None = None,
) -> dict[str, str]:
    raw = _env(env_key)
    if raw is None:
        payload = _load_secret_payload()
        key = secret_key or env_key
        secret_value = payload.get(key)
        if secret_value is None:
            return dict(default or {})
        if isinstance(secret_value, dict):
            return {
                str(key_item): str(value_item)
                for key_item, value_item in secret_value.items()
            }
        if not isinstance(secret_value, str):
            raise RuntimeError(
                f"{env_key} in secret manager must be a JSON object or string"
            )
        raw = secret_value.strip()
        if not raw:
            return dict(default or {})

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{env_key} must contain a valid JSON object") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError(f"{env_key} must contain a JSON object")

    return {str(key): str(value) for key, value in parsed.items()}


LOGIN = _env_or_secret("IIKO_LOGIN", default="") or ""
PASSWORD = _env_or_secret("IIKO_PASSWORD", default="") or ""

RESTAURANTS = _json_map_from_env_or_secret("IIKO_RESTAURANTS_JSON", default={})

TRANSLATIONS = _json_map_from_env_or_secret(
    "IIKO_TRANSLATIONS_JSON",
    default={
        "stopListItemAdded": "Добавлено в стоп-лист",
        "stopListItemRemoved": "Удалено из стоп-листа",
    },
)

DATA_DIR = _env_or_secret("IIKO_DATA_DIR", default="data_stoplist") or "data_stoplist"
MENU_DIR = _env_or_secret("IIKO_MENU_DIR", default="data_menu") or "data_menu"
