import base64
import json
import logging
import os
import re
import secrets

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from backend.bd.database import get_db
from backend.bd.models import User
from backend.services.fingerprint_events import log_fingerprint_event
from backend.services.s3 import download_bytes, upload_bytes

router = APIRouter(prefix="/fingerprints", tags=["Fingerprint templates"])

_DATASET_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_RESET_MISSING = os.getenv("FINGERPRINT_RESET_MISSING", "").lower() in {"1", "true", "yes"}
_REQUIRE_SYNC_TOKEN = os.getenv("FINGERPRINT_SYNC_TOKEN_REQUIRED", "").lower() in {"1", "true", "yes"}
_ALLOWED_ACTIONS = {"enroll", "identify", "login"}
logger = logging.getLogger(__name__)


def _get_sync_token() -> str:
    load_dotenv()
    return (os.getenv("FINGERPRINT_SYNC_TOKEN") or "").strip()


def _ensure_token_configured() -> None:
    if not _get_sync_token():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fingerprint sync token is not configured",
        )


def _ensure_token(request: Request, *, required: bool = False) -> None:
    expected_token = _get_sync_token()
    if not expected_token:
        if _REQUIRE_SYNC_TOKEN:
            _ensure_token_configured()
        if required:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return
    token = (request.headers.get("X-Fingerprint-Token") or "").strip()
    if not token or not secrets.compare_digest(token, expected_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def _normalize_dataset(raw: str | None) -> str:
    dataset = (raw or "default").strip()
    if not dataset:
        dataset = "default"
    if not _DATASET_RE.match(dataset):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid dataset")
    return dataset


def _decode_template_text(content: bytes) -> str:
    if not content:
        return ""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("utf-8", errors="replace")
    text = text.lstrip()
    if text.startswith("ï»¿"):
        text = text[3:].lstrip()
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff").lstrip()
    return text


def _parse_template_payload(content: bytes) -> tuple[list[dict], bool]:
    if not content:
        return [], True
    text = _decode_template_text(content)
    if not text:
        return [], True
    try:
        payload = json.loads(text)
    except Exception:
        logger.warning("Failed to parse fingerprint templates JSON", exc_info=True)
        return [], False
    if not isinstance(payload, list):
        return [], False
    return [item for item in payload if isinstance(item, dict)], True


def _extract_staff_codes(content: bytes) -> set[str] | None:
    records, ok = _parse_template_payload(content)
    if not ok:
        return None
    if not records:
        return set()
    staff_codes: set[str] = set()
    for item in records:
        code = str(item.get("staff_code") or "").strip()
        if code:
            staff_codes.add(code)
    return staff_codes


def _normalize_templates(records: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for item in records:
        staff_code = str(item.get("staff_code") or "").strip()
        if not staff_code:
            continue

        slot_value = item.get("slot", 1)
        try:
            slot = int(slot_value)
        except (TypeError, ValueError):
            continue
        if slot < 1 or slot > 3:
            continue

        template_base64 = str(item.get("template_base64") or "").strip()
        if not template_base64:
            continue
        try:
            base64.b64decode(template_base64, validate=True)
        except Exception:
            continue

        fid_value = item.get("fid")
        fid = None
        if fid_value is not None:
            try:
                fid = int(fid_value)
            except (TypeError, ValueError):
                fid = None
        if fid is not None and fid < 0:
            fid = None

        normalized.append(
            {
                "fid": fid,
                "staff_code": staff_code,
                "slot": slot,
                "template_base64": template_base64,
            }
        )

    return normalized


def _merge_templates(existing: list[dict], incoming: list[dict]) -> list[dict]:
    by_key: dict[tuple[str, int], dict] = {}
    order: list[tuple[str, int]] = []

    for record in existing:
        key = (record["staff_code"].lower(), record["slot"])
        if key not in by_key:
            by_key[key] = record
            order.append(key)

    for record in incoming:
        key = (record["staff_code"].lower(), record["slot"])
        if key not in by_key:
            order.append(key)
        by_key[key] = record

    used_fids: set[int] = set()
    max_fid = 0
    for record in by_key.values():
        fid = record.get("fid")
        if isinstance(fid, int) and fid >= 0:
            used_fids.add(fid)
            if fid > max_fid:
                max_fid = fid

    next_fid = max_fid + 1 if used_fids else 1
    used_fids.clear()

    for key in order:
        record = by_key[key]
        fid = record.get("fid")
        if not isinstance(fid, int) or fid < 0 or fid in used_fids:
            while next_fid in used_fids:
                next_fid += 1
            record["fid"] = next_fid
            used_fids.add(next_fid)
            next_fid += 1
        else:
            used_fids.add(fid)

    return [by_key[key] for key in order]


def _update_staff_fingerprint_flags(db: Session, staff_codes: set[str]) -> None:
    if not staff_codes:
        return
    db.query(User).filter(User.staff_code.in_(staff_codes)).update(
        {User.has_fingerprint: True},
        synchronize_session=False,
    )
    if _RESET_MISSING:
        db.query(User).filter(User.staff_code.isnot(None), ~User.staff_code.in_(staff_codes)).update(
            {User.has_fingerprint: False},
            synchronize_session=False,
        )
    db.commit()


class FingerprintEventPayload(BaseModel):
    staff_code: str
    action: str
    ok: bool = True
    source: str | None = None
    slot: int | None = Field(default=None, ge=1, le=3)
    score: int | None = None
    error_code: str | None = None


@router.post("/templates", status_code=status.HTTP_201_CREATED)
async def upload_template(
    request: Request,
    dataset: str = "default",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    _ensure_token(request)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    dataset_name = _normalize_dataset(dataset)
    key = f"fingerprints/{dataset_name}.json"

    existing_content = b""
    try:
        existing_content = download_bytes(key)
    except FileNotFoundError:
        existing_content = b""

    existing_payload, existing_ok = _parse_template_payload(existing_content)
    incoming_payload, incoming_ok = _parse_template_payload(content)
    if not incoming_ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid templates JSON")

    existing_records = _normalize_templates(existing_payload if existing_ok else [])
    incoming_records = _normalize_templates(incoming_payload)
    merged_records = _merge_templates(existing_records, incoming_records)
    merged_content = json.dumps(merged_records, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    upload_bytes(key, merged_content, file.content_type or "application/json")

    staff_codes = _extract_staff_codes(merged_content)
    if staff_codes is not None:
        _update_staff_fingerprint_flags(db, staff_codes)

    return {"dataset": dataset_name, "key": key, "size": len(merged_content)}


@router.get("/templates")
def download_template(request: Request, dataset: str = "default") -> Response:
    _ensure_token(request)

    dataset_name = _normalize_dataset(dataset)
    key = f"fingerprints/{dataset_name}.json"
    try:
        content = download_bytes(key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found") from exc

    headers = {"Content-Disposition": f'attachment; filename="{dataset_name}.json"'}
    return Response(content=content, media_type="application/json", headers=headers)


@router.post("/events")
def create_fingerprint_event(
    request: Request,
    payload: FingerprintEventPayload,
    db: Session = Depends(get_db),
) -> dict:
    _ensure_token(request)

    staff_code = (payload.staff_code or "").strip()
    if not staff_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="staff_code required")

    action = (payload.action or "").strip().lower()
    if action not in _ALLOWED_ACTIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action")

    event = log_fingerprint_event(
        db,
        staff_code=staff_code,
        action=action,
        ok=payload.ok,
        source=payload.source,
        slot=payload.slot,
        score=payload.score,
        error_code=payload.error_code,
    )
    return {"ok": True, "id": event.id if event else None}


@router.get("/staff")
def get_staff_info(
    request: Request,
    staff_code: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> dict:
    # Staff lookup is part of the enrollment bootstrap flow in ZionScan.
    # Keep the legacy behavior: if a sync token is configured, require it;
    # otherwise allow lookup so existing agent setups without a token keep working.
    _ensure_token(request)

    staff_code = staff_code.strip()
    if not staff_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="staff_code required")

    user = db.query(User).filter(User.staff_code == staff_code).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")

    return {
        "ok": True,
        "staff_code": staff_code,
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "middle_name": user.middle_name or "",
    }
