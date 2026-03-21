"""Helpers for interacting with an S3-compatible storage (e.g. FirstVDS)."""

import logging
import os
from typing import Tuple
from uuid import uuid4

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_CHECKLIST_BUCKET = os.getenv("S3_CHECKLIST_BUCKET") or S3_BUCKET
S3_KNOWLEDGE_BASE_BUCKET = os.getenv("S3_KNOWLEDGE_BASE_BUCKET") or "knowledge-base"
S3_REGION = os.getenv("S3_REGION", "ru-1")
PRESIGNED_EXPIRES = int(os.getenv("S3_PRESIGNED_EXPIRES", "3600"))

_session = boto3.session.Session()
_client = None

logger = logging.getLogger(__name__)


def _get_client():
    """Create (once) and return an S3 client after config validation."""

    global _client
    _ensure_configured()
    if _client is None:
        try:
            _client = _session.client(
                "s3",
                endpoint_url=S3_ENDPOINT,
                aws_access_key_id=S3_ACCESS_KEY,
                aws_secret_access_key=S3_SECRET_KEY,
                region_name=S3_REGION,
                config=Config(signature_version="s3v4"),
            )
        except (BotoCoreError, ClientError) as exc:
            logger.exception("Failed to initialize S3 client")
            raise RuntimeError("Failed to initialize S3 client") from exc

    return _client


def _ensure_configured() -> None:
    missing = [
        name
        for name, value in {
            "S3_ENDPOINT": S3_ENDPOINT,
            "S3_ACCESS_KEY": S3_ACCESS_KEY,
            "S3_SECRET_KEY": S3_SECRET_KEY,
            "S3_BUCKET": S3_BUCKET,
        }.items()
        if not value
    ]
    if missing:
        message = f"Missing S3 configuration: {', '.join(missing)}"
        logger.error(message)
        raise RuntimeError(message)


def _build_employee_photo_key(user_id: int, filename: str) -> str:
    base, ext = os.path.splitext(filename or "photo")
    unique = uuid4().hex
    safe_base = base.replace("/", "_") or "photo"
    safe_ext = ext if ext else ".jpg"
    return f"employees/{user_id}/{safe_base}_{unique}{safe_ext}"


def upload_employee_photo(user_id: int, filename: str, content: bytes, content_type: str) -> str:
    """Upload employee photo to the configured bucket and return the object key."""

    client = _get_client()
    key = _build_employee_photo_key(user_id, filename)
    client.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=content,
        ContentType=content_type,
    )
    return key


def upload_bytes(key: str, content: bytes, content_type: str | None = None) -> str:
    """Upload raw bytes to the configured bucket and return the object key."""

    client = _get_client()
    client.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=content,
        ContentType=content_type or "application/octet-stream",
    )
    return key


def upload_bytes_to_bucket(
    key: str,
    content: bytes,
    content_type: str | None = None,
    bucket: str | None = None,
) -> str:
    client = _get_client()
    target_bucket = bucket or S3_BUCKET
    client.put_object(
        Bucket=target_bucket,
        Key=key,
        Body=content,
        ContentType=content_type or "application/octet-stream",
    )
    return key


def upload_bytes_for_knowledge_base(
    key: str,
    content: bytes,
    content_type: str | None = None,
) -> str:
    """Upload bytes to the dedicated knowledge-base bucket."""

    return upload_bytes_to_bucket(
        key=key,
        content=content,
        content_type=content_type,
        bucket=S3_KNOWLEDGE_BASE_BUCKET,
    )


def download_bytes(key: str) -> bytes:
    """Download object bytes from the configured bucket."""

    client = _get_client()
    try:
        obj = client.get_object(Bucket=S3_BUCKET, Key=key)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in {"NoSuchKey", "404", "NotFound"}:
            raise FileNotFoundError(key) from exc
        logger.exception("Failed to download object %s", key)
        raise RuntimeError("Failed to download object") from exc
    except BotoCoreError as exc:
        logger.exception("Failed to download object %s", key)
        raise RuntimeError("Failed to download object") from exc

    body = obj.get("Body")
    return body.read() if body else b""


def _split_s3_ref(raw: str, default_bucket: str | None = None) -> tuple[str | None, str | None]:
    if not raw or not raw.startswith("s3://"):
        return None, None
    path = raw.replace("s3://", "", 1).lstrip("/")
    if not path:
        return None, None
    if "/" in path:
        bucket, key = path.split("/", 1)
        return bucket, key
    return default_bucket, path


def generate_presigned_url_for_checklist(raw: str, expires_in: int | None = None) -> str:
    bucket, key = _split_s3_ref(raw, S3_CHECKLIST_BUCKET)
    if not bucket or not key:
        raise RuntimeError("Invalid S3 reference")
    client = _get_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in or PRESIGNED_EXPIRES,
    )


def download_bytes_for_checklist(raw: str) -> bytes:
    bucket, key = _split_s3_ref(raw, S3_CHECKLIST_BUCKET)
    if not bucket or not key:
        raise RuntimeError("Invalid S3 reference")
    client = _get_client()
    obj = client.get_object(Bucket=bucket, Key=key)
    body = obj.get("Body")
    return body.read() if body else b""


def generate_presigned_url(key: str, expires_in: int | None = None) -> str:
    """Generate a presigned GET URL for the given object key."""

    client = _get_client()
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=expires_in or PRESIGNED_EXPIRES,
        )
    except (BotoCoreError, ClientError) as exc:
        logger.exception("Failed to generate presigned URL for %s", key)
        raise RuntimeError("Failed to generate presigned URL") from exc


def generate_presigned_url_for_knowledge_base(key: str, expires_in: int | None = None) -> str:
    """Generate a presigned GET URL for an object stored in the KB bucket."""

    client = _get_client()
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_KNOWLEDGE_BASE_BUCKET, "Key": key},
            ExpiresIn=expires_in or PRESIGNED_EXPIRES,
        )
    except (BotoCoreError, ClientError) as exc:
        logger.exception("Failed to generate KB presigned URL for %s", key)
        raise RuntimeError("Failed to generate presigned URL") from exc


def upload_employee_photo_with_url(
    user_id: int, filename: str, content: bytes, content_type: str
) -> Tuple[str, str]:
    """Upload employee photo and return both the key and a presigned URL."""

    key = upload_employee_photo(user_id, filename, content, content_type)
    url = generate_presigned_url(key)
    return key, url


def _build_user_attachment_key(user_id: int, category: str, filename: str) -> str:
    base, ext = os.path.splitext(filename or "file")
    unique = uuid4().hex
    safe_base = base.replace("/", "_") or "file"
    safe_ext = ext if ext else ""
    clean_category = category.strip("/ ") or "attachments"
    return f"{clean_category}/{user_id}/{safe_base}_{unique}{safe_ext or '.bin'}"


def upload_user_attachment(
    user_id: int, category: str, filename: str, content: bytes, content_type: str
) -> str:
    """Upload a generic attachment for a user and return the object key."""

    client = _get_client()
    key = _build_user_attachment_key(user_id, category, filename)
    client.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=content,
        ContentType=content_type or "application/octet-stream",
    )
    return key


def upload_user_attachment_with_url(
    user_id: int, category: str, filename: str, content: bytes, content_type: str
) -> Tuple[str, str]:
    """Upload user attachment and return both the key and its presigned URL."""

    key = upload_user_attachment(user_id, category, filename, content, content_type)
    url = generate_presigned_url(key)
    return key, url
