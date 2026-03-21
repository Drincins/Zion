"""Endpoints for managing employee medical checks."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session, joinedload

from backend.bd.database import get_db
from backend.bd.models import (
    MedicalCheckType,
    MedicalCheckRecord,
    MedicalCheckStatus,
    User,
)
from backend.schemas import (
    MedicalCheckTypeCreate,
    MedicalCheckTypeUpdate,
    MedicalCheckTypeRead,
    MedicalCheckRecordCreate,
    MedicalCheckRecordUpdate,
    MedicalCheckRecordPublic,
    MedicalCheckRecordListResponse,
)
from backend.utils import get_current_user, users_share_restaurant
from backend.services.permissions import (
    PermissionCode,
    ensure_permissions,
    has_permission,
    has_global_access,
)
from backend.services.medical_checks import refresh_record_state

router = APIRouter(prefix="/medical-checks", tags=["Medical checks"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _check_user_access(db: Session, viewer: User, target_user_id: int) -> None:
    if viewer.id == target_user_id:
        return
    if has_global_access(viewer) or has_permission(viewer, PermissionCode.STAFF_MANAGE_ALL):
        return
    if not users_share_restaurant(db, viewer, target_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to the selected employee is not allowed",
        )


def _type_to_schema(obj: MedicalCheckType) -> MedicalCheckTypeRead:
    return MedicalCheckTypeRead.model_validate(obj)


def _record_to_schema(obj: MedicalCheckRecord) -> MedicalCheckRecordPublic:
    return MedicalCheckRecordPublic(
        id=obj.id,
        user_id=obj.user_id,
        medical_check_type=_type_to_schema(obj.check_type),
        passed_at=obj.passed_at,
        next_due_at=obj.next_due_at,
        status=obj.status,
        comment=obj.comment,
    )


def _apply_record_state(record: MedicalCheckRecord, db: Session) -> None:
    prev_status = record.status
    prev_due = record.next_due_at
    refresh_record_state(record)
    if record.status != prev_status or record.next_due_at != prev_due:
        db.add(record)


def _get_type_or_404(db: Session, type_id: int) -> MedicalCheckType:
    obj = db.get(MedicalCheckType, type_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medical check type not found")
    return obj


def _get_record_or_404(db: Session, record_id: int) -> MedicalCheckRecord:
    obj = (
        db.query(MedicalCheckRecord)
        .options(joinedload(MedicalCheckRecord.check_type))
        .filter(MedicalCheckRecord.id == record_id)
        .first()
    )
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medical check record not found")
    return obj


# ---------------------------------------------------------------------------
# Type dictionary endpoints
# ---------------------------------------------------------------------------
@router.get("/types", response_model=List[MedicalCheckTypeRead])
def list_medical_check_types(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[MedicalCheckTypeRead]:
    ensure_permissions(current_user, PermissionCode.MEDICAL_CHECKS_VIEW, PermissionCode.MEDICAL_CHECKS_MANAGE)

    query = db.query(MedicalCheckType).order_by(MedicalCheckType.name.asc())
    if not include_inactive:
        query = query.filter(MedicalCheckType.is_active.is_(True))
    items = query.all()
    return [_type_to_schema(item) for item in items]


@router.post("/types", response_model=MedicalCheckTypeRead, status_code=status.HTTP_201_CREATED)
def create_medical_check_type(
    payload: MedicalCheckTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MedicalCheckTypeRead:
    ensure_permissions(current_user, PermissionCode.MEDICAL_CHECKS_MANAGE)

    obj = MedicalCheckType(
        code=payload.code,
        name=payload.name,
        validity_months=payload.validity_months,
        notice_days=payload.notice_days if payload.notice_days is not None else 30,
        comment=payload.comment,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _type_to_schema(obj)


@router.put("/types/{type_id}", response_model=MedicalCheckTypeRead)
def update_medical_check_type(
    type_id: int,
    payload: MedicalCheckTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MedicalCheckTypeRead:
    ensure_permissions(current_user, PermissionCode.MEDICAL_CHECKS_MANAGE)
    obj = _get_type_or_404(db, type_id)

    data = payload.model_dump(exclude_unset=True)
    for field in ("code", "name", "validity_months", "notice_days", "comment", "is_active"):
        if field in data:
            setattr(obj, field, data[field])

    db.commit()
    db.refresh(obj)
    return _type_to_schema(obj)


@router.delete("/types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_medical_check_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    ensure_permissions(current_user, PermissionCode.MEDICAL_CHECKS_MANAGE)
    obj = _get_type_or_404(db, type_id)
    db.delete(obj)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Records endpoints
# ---------------------------------------------------------------------------
@router.get("/records", response_model=MedicalCheckRecordListResponse)
def list_medical_check_records(
    user_id: Optional[int] = Query(None),
    status_filter: Optional[MedicalCheckStatus] = Query(
        None, description="Filter by status: ok, expiring, expired"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MedicalCheckRecordListResponse:
    ensure_permissions(current_user, PermissionCode.MEDICAL_CHECKS_VIEW, PermissionCode.MEDICAL_CHECKS_MANAGE)
    target_user_id = user_id or current_user.id
    _check_user_access(db, current_user, target_user_id)

    query = (
        db.query(MedicalCheckRecord)
        .options(joinedload(MedicalCheckRecord.check_type))
        .filter(MedicalCheckRecord.user_id == target_user_id)
        .order_by(MedicalCheckRecord.passed_at.desc())
    )
    if status_filter:
        query = query.filter(MedicalCheckRecord.status == status_filter)
    records = query.all()

    updated = False
    for record in records:
        prev_status = record.status
        prev_due = record.next_due_at
        refresh_record_state(record)
        if record.status != prev_status or record.next_due_at != prev_due:
            db.add(record)
            updated = True

    if updated:
        db.commit()
        for record in records:
            db.refresh(record)

    items = [_record_to_schema(record) for record in records]
    return MedicalCheckRecordListResponse(items=items)


@router.get("/records/{record_id}", response_model=MedicalCheckRecordPublic)
def get_medical_check_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MedicalCheckRecordPublic:
    ensure_permissions(current_user, PermissionCode.MEDICAL_CHECKS_VIEW, PermissionCode.MEDICAL_CHECKS_MANAGE)
    record = _get_record_or_404(db, record_id)
    _check_user_access(db, current_user, record.user_id)
    refresh_record_state(record)
    db.commit()
    db.refresh(record)
    return _record_to_schema(record)


@router.post("/records", response_model=MedicalCheckRecordPublic, status_code=status.HTTP_201_CREATED)
def create_medical_check_record(
    payload: MedicalCheckRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MedicalCheckRecordPublic:
    ensure_permissions(current_user, PermissionCode.MEDICAL_CHECKS_MANAGE)
    _check_user_access(db, current_user, payload.user_id)
    check_type = _get_type_or_404(db, payload.medical_check_type_id)

    record = MedicalCheckRecord(
        user_id=payload.user_id,
        medical_check_type_id=payload.medical_check_type_id,
        passed_at=payload.passed_at,
        comment=payload.comment,
    )
    record.check_type = check_type
    refresh_record_state(record)

    db.add(record)
    db.commit()
    db.refresh(record)
    return _record_to_schema(record)


@router.put("/records/{record_id}", response_model=MedicalCheckRecordPublic)
def update_medical_check_record(
    record_id: int,
    payload: MedicalCheckRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MedicalCheckRecordPublic:
    ensure_permissions(current_user, PermissionCode.MEDICAL_CHECKS_MANAGE)
    record = _get_record_or_404(db, record_id)
    _check_user_access(db, current_user, record.user_id)

    data = payload.model_dump(exclude_unset=True)
    if "medical_check_type_id" in data:
        record.check_type = _get_type_or_404(db, data["medical_check_type_id"])
        record.medical_check_type_id = data["medical_check_type_id"]
    if "passed_at" in data:
        record.passed_at = data["passed_at"]
    if "comment" in data:
        record.comment = data["comment"]

    refresh_record_state(record)
    db.commit()
    db.refresh(record)
    return _record_to_schema(record)


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_medical_check_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    ensure_permissions(current_user, PermissionCode.MEDICAL_CHECKS_MANAGE)
    record = _get_record_or_404(db, record_id)
    _check_user_access(db, current_user, record.user_id)

    db.delete(record)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
