"""Endpoints for formalized employee documents."""
from __future__ import annotations

import logging
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from backend.bd.database import get_db
from backend.bd.models import EmploymentDocumentKind, EmploymentDocumentRecord, User
from backend.schemas import (
    AttachmentUploadResponse,
    EmploymentDocumentRecordCreate,
    EmploymentDocumentRecordListResponse,
    EmploymentDocumentRecordPublic,
    EmploymentDocumentRecordUpdate,
)
from backend.services.permissions import PermissionCode, ensure_permissions, has_global_access, has_permission
from backend.services.s3 import generate_presigned_url, upload_user_attachment_with_url
from backend.utils import get_current_user, users_share_restaurant

router = APIRouter(prefix="/employment-documents", tags=["Employment documents"])
logger = logging.getLogger(__name__)


DOCUMENT_KIND_LABELS = {
    EmploymentDocumentKind.EMPLOYMENT_ORDER: "Приказ о приеме на работу",
    EmploymentDocumentKind.EMPLOYMENT_CONTRACT: "Договор",
}


def _ensure_documents_view_permission(user: User) -> None:
    ensure_permissions(
        user,
        PermissionCode.MEDICAL_CHECKS_VIEW,
        PermissionCode.MEDICAL_CHECKS_MANAGE,
        PermissionCode.CIS_DOCUMENTS_VIEW,
        PermissionCode.CIS_DOCUMENTS_MANAGE,
        PermissionCode.STAFF_MANAGE_ALL,
        PermissionCode.SYSTEM_ADMIN,
    )


def _ensure_documents_manage_permission(user: User) -> None:
    ensure_permissions(
        user,
        PermissionCode.MEDICAL_CHECKS_MANAGE,
        PermissionCode.CIS_DOCUMENTS_MANAGE,
        PermissionCode.STAFF_MANAGE_ALL,
        PermissionCode.SYSTEM_ADMIN,
    )


def _ensure_user_access(db: Session, viewer: User, target_user_id: int) -> None:
    if viewer.id == target_user_id:
        return
    if has_global_access(viewer) or has_permission(viewer, PermissionCode.STAFF_MANAGE_ALL):
        return
    if not users_share_restaurant(db, viewer, target_user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access to employee is not allowed")


def _ensure_formalized_user(db: Session, user_id: int) -> None:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not bool(getattr(user, "is_formalized", False)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Документы оформления доступны только для официально оформленных сотрудников",
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
        logger.warning("Failed to build presigned URL for employment document attachment", exc_info=True)
        return value


def _record_schema(record: EmploymentDocumentRecord) -> EmploymentDocumentRecordPublic:
    return EmploymentDocumentRecordPublic(
        id=record.id,
        user_id=record.user_id,
        document_kind=record.document_kind,
        document_name=DOCUMENT_KIND_LABELS.get(record.document_kind, record.document_kind.value),
        issued_at=record.issued_at,
        comment=record.comment,
        attachment_url=_resolve_attachment_url(record.attachment_url),
    )


def _get_record_or_404(db: Session, record_id: int) -> EmploymentDocumentRecord:
    record = db.get(EmploymentDocumentRecord, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employment document record not found")
    return record


@router.post(
    "/users/{user_id}/attachment",
    response_model=AttachmentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_employment_document_attachment(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttachmentUploadResponse:
    _ensure_documents_manage_permission(current_user)
    _ensure_user_access(db, current_user, user_id)
    _ensure_formalized_user(db, user_id)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    key, url = upload_user_attachment_with_url(
        user_id,
        "employment-documents",
        file.filename or "attachment",
        content,
        file.content_type or "application/octet-stream",
    )
    return AttachmentUploadResponse(attachment_key=key, attachment_url=url)


@router.get("/records", response_model=EmploymentDocumentRecordListResponse)
def list_employment_document_records(
    user_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmploymentDocumentRecordListResponse:
    _ensure_documents_view_permission(current_user)
    _ensure_user_access(db, current_user, user_id)

    records = (
        db.query(EmploymentDocumentRecord)
        .filter(EmploymentDocumentRecord.user_id == user_id)
        .all()
    )
    return EmploymentDocumentRecordListResponse(items=[_record_schema(record) for record in records])


@router.post("/records", response_model=EmploymentDocumentRecordPublic, status_code=status.HTTP_201_CREATED)
def create_employment_document_record(
    payload: EmploymentDocumentRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmploymentDocumentRecordPublic:
    _ensure_documents_manage_permission(current_user)
    _ensure_user_access(db, current_user, payload.user_id)
    _ensure_formalized_user(db, payload.user_id)

    existing = (
        db.query(EmploymentDocumentRecord.id)
        .filter(
            EmploymentDocumentRecord.user_id == payload.user_id,
            EmploymentDocumentRecord.document_kind == payload.document_kind,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Документ этого типа уже добавлен сотруднику",
        )

    record = EmploymentDocumentRecord(
        user_id=payload.user_id,
        document_kind=payload.document_kind,
        issued_at=payload.issued_at,
        comment=payload.comment,
        attachment_url=payload.attachment_url,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _record_schema(record)


@router.put("/records/{record_id}", response_model=EmploymentDocumentRecordPublic)
def update_employment_document_record(
    record_id: int,
    payload: EmploymentDocumentRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmploymentDocumentRecordPublic:
    _ensure_documents_manage_permission(current_user)
    record = _get_record_or_404(db, record_id)
    _ensure_user_access(db, current_user, record.user_id)
    _ensure_formalized_user(db, record.user_id)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(record, field, value)

    db.add(record)
    db.commit()
    db.refresh(record)
    return _record_schema(record)


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employment_document_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _ensure_documents_manage_permission(current_user)
    record = _get_record_or_404(db, record_id)
    _ensure_user_access(db, current_user, record.user_id)

    db.delete(record)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
