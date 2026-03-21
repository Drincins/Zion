"""Endpoints for CIS document tracking."""
from __future__ import annotations

from typing import List, Optional

import logging
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from backend.bd.database import get_db
from backend.bd.models import (
    CisDocumentRecord,
    CisDocumentStatus,
    CisDocumentType,
    User,
)
from backend.schemas import (
    CisDocumentTypeCreate,
    CisDocumentTypeUpdate,
    CisDocumentTypeRead,
    CisDocumentRecordCreate,
    CisDocumentRecordUpdate,
    CisDocumentRecordPublic,
    CisDocumentRecordListResponse,
    AttachmentUploadResponse,
)
from backend.utils import get_current_user, users_share_restaurant
from backend.services.permissions import (
    PermissionCode,
    ensure_permissions,
    has_permission,
    has_global_access,
)
from backend.services.cis_documents import refresh_document_state
from backend.services.s3 import generate_presigned_url, upload_user_attachment_with_url

router = APIRouter(prefix="/cis-documents", tags=["CIS documents"])
logger = logging.getLogger(__name__)


def _ensure_user_access(db: Session, viewer: User, target_user_id: int) -> None:
    if viewer.id == target_user_id:
        return
    if has_global_access(viewer) or has_permission(viewer, PermissionCode.STAFF_MANAGE_ALL):
        return
    if not users_share_restaurant(db, viewer, target_user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access to employee is not allowed")


def _type_schema(item: CisDocumentType) -> CisDocumentTypeRead:
    return CisDocumentTypeRead.model_validate(item)


def _record_schema(record: CisDocumentRecord) -> CisDocumentRecordPublic:
    return CisDocumentRecordPublic(
        id=record.id,
        user_id=record.user_id,
        cis_document_type=_type_schema(record.document_type),
        number=record.number,
        issued_at=record.issued_at,
        expires_at=record.expires_at,
        status=record.status,
        issuer=record.issuer,
        comment=record.comment,
        attachment_url=_resolve_attachment_url(record.attachment_url),
    )


def _resolve_attachment_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return value
    try:
        return generate_presigned_url(value)
    except Exception:  # noqa: BLE001
        logger.warning("Failed to build presigned URL for CIS document attachment", exc_info=True)
        return value


def _get_type(db: Session, type_id: int) -> CisDocumentType:
    obj = db.get(CisDocumentType, type_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document type not found")
    return obj


def _get_record(db: Session, record_id: int) -> CisDocumentRecord:
    record = (
        db.query(CisDocumentRecord)
        .options(joinedload(CisDocumentRecord.document_type))
        .filter(CisDocumentRecord.id == record_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CIS document record not found")
    return record


@router.post(
    "/users/{user_id}/attachment",
    response_model=AttachmentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_cis_document_attachment(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttachmentUploadResponse:
    ensure_permissions(current_user, PermissionCode.CIS_DOCUMENTS_MANAGE)
    _ensure_user_access(db, current_user, user_id)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    key, url = upload_user_attachment_with_url(
        user_id,
        "cis-documents",
        file.filename or "attachment",
        content,
        file.content_type or "application/octet-stream",
    )
    return AttachmentUploadResponse(attachment_key=key, attachment_url=url)


@router.get("/types", response_model=List[CisDocumentTypeRead])
def list_document_types(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[CisDocumentTypeRead]:
    ensure_permissions(current_user, PermissionCode.CIS_DOCUMENTS_VIEW, PermissionCode.CIS_DOCUMENTS_MANAGE)
    query = db.query(CisDocumentType).order_by(CisDocumentType.name.asc())
    if not include_inactive:
        query = query.filter(CisDocumentType.is_active.is_(True))
    return [_type_schema(item) for item in query.all()]


@router.post("/types", response_model=CisDocumentTypeRead, status_code=status.HTTP_201_CREATED)
def create_document_type(
    payload: CisDocumentTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CisDocumentTypeRead:
    ensure_permissions(current_user, PermissionCode.CIS_DOCUMENTS_MANAGE)
    obj = CisDocumentType(
        code=payload.code,
        name=payload.name,
        validity_months=payload.validity_months,
        notice_days=payload.notice_days if payload.notice_days is not None else 30,
        comment=payload.comment,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _type_schema(obj)


@router.put("/types/{type_id}", response_model=CisDocumentTypeRead)
def update_document_type(
    type_id: int,
    payload: CisDocumentTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CisDocumentTypeRead:
    ensure_permissions(current_user, PermissionCode.CIS_DOCUMENTS_MANAGE)
    obj = _get_type(db, type_id)
    data = payload.model_dump(exclude_unset=True)
    for field in ("code", "name", "validity_months", "notice_days", "comment", "is_active"):
        if field in data:
            setattr(obj, field, data[field])
    db.commit()
    db.refresh(obj)
    return _type_schema(obj)


@router.delete("/types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    ensure_permissions(current_user, PermissionCode.CIS_DOCUMENTS_MANAGE)
    obj = _get_type(db, type_id)
    db.delete(obj)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/records", response_model=CisDocumentRecordListResponse)
def list_document_records(
    user_id: Optional[int] = Query(None),
    status_filter: Optional[CisDocumentStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CisDocumentRecordListResponse:
    ensure_permissions(current_user, PermissionCode.CIS_DOCUMENTS_VIEW, PermissionCode.CIS_DOCUMENTS_MANAGE)
    target_user_id = user_id or current_user.id
    _ensure_user_access(db, current_user, target_user_id)

    query = (
        db.query(CisDocumentRecord)
        .options(joinedload(CisDocumentRecord.document_type))
        .filter(CisDocumentRecord.user_id == target_user_id)
        .order_by(CisDocumentRecord.issued_at.desc().nullslast())
    )
    if status_filter:
        query = query.filter(CisDocumentRecord.status == status_filter)
    records = query.all()

    updated = False
    for record in records:
        refresh_document_state(record)
        db.add(record)
        updated = True
    if updated:
        db.commit()
        for record in records:
            db.refresh(record)

    items = [_record_schema(record) for record in records]
    return CisDocumentRecordListResponse(items=items)


@router.get("/records/{record_id}", response_model=CisDocumentRecordPublic)
def get_document_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CisDocumentRecordPublic:
    ensure_permissions(current_user, PermissionCode.CIS_DOCUMENTS_VIEW, PermissionCode.CIS_DOCUMENTS_MANAGE)
    record = _get_record(db, record_id)
    _ensure_user_access(db, current_user, record.user_id)
    refresh_document_state(record)
    db.commit()
    db.refresh(record)
    return _record_schema(record)


@router.post("/records", response_model=CisDocumentRecordPublic, status_code=status.HTTP_201_CREATED)
def create_document_record(
    payload: CisDocumentRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CisDocumentRecordPublic:
    ensure_permissions(current_user, PermissionCode.CIS_DOCUMENTS_MANAGE)
    _ensure_user_access(db, current_user, payload.user_id)
    doc_type = _get_type(db, payload.cis_document_type_id)

    record = CisDocumentRecord(
        user_id=payload.user_id,
        cis_document_type_id=payload.cis_document_type_id,
        number=payload.number,
        issued_at=payload.issued_at,
        expires_at=payload.expires_at,
        issuer=payload.issuer,
        comment=payload.comment,
        attachment_url=payload.attachment_url,
    )
    record.document_type = doc_type
    refresh_document_state(record)
    db.add(record)
    db.commit()
    db.refresh(record)
    return _record_schema(record)


@router.put("/records/{record_id}", response_model=CisDocumentRecordPublic)
def update_document_record(
    record_id: int,
    payload: CisDocumentRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CisDocumentRecordPublic:
    ensure_permissions(current_user, PermissionCode.CIS_DOCUMENTS_MANAGE)
    record = _get_record(db, record_id)
    _ensure_user_access(db, current_user, record.user_id)
    data = payload.model_dump(exclude_unset=True)
    if "cis_document_type_id" in data:
        record.document_type = _get_type(db, data["cis_document_type_id"])
        record.cis_document_type_id = data["cis_document_type_id"]
    for field in ("number", "issued_at", "expires_at", "issuer", "comment", "attachment_url"):
        if field in data:
            setattr(record, field, data[field])
    refresh_document_state(record)
    db.commit()
    db.refresh(record)
    return _record_schema(record)


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    ensure_permissions(current_user, PermissionCode.CIS_DOCUMENTS_MANAGE)
    record = _get_record(db, record_id)
    _ensure_user_access(db, current_user, record.user_id)
    db.delete(record)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
