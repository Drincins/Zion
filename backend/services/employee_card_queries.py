from __future__ import annotations

import logging
from datetime import date
from typing import Optional
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload, load_only, noload, selectinload

from backend.bd.models import (
    CisDocumentRecord,
    MedicalCheckRecord,
    Position,
    Role,
    User,
    user_restaurants,
)
from backend.schemas import (
    CisDocumentRecordPublic,
    CisDocumentTypeRead,
    EmployeeCardPublic,
    EmployeeListItem,
    MedicalCheckRecordPublic,
    MedicalCheckTypeRead,
)
from backend.services.permissions import PermissionCode, can_manage_user, can_view_rate, ensure_permissions, has_permission
from backend.services.s3 import generate_presigned_url
from backend.utils import get_user_restaurant_ids

logger = logging.getLogger(__name__)


def ensure_staff_view(user: User) -> None:
    ensure_permissions(
        user,
        PermissionCode.STAFF_VIEW_SENSITIVE,
        PermissionCode.STAFF_MANAGE_SUBORDINATES,
        PermissionCode.STAFF_MANAGE_ALL,
        PermissionCode.STAFF_EMPLOYEES_VIEW,
        PermissionCode.EMPLOYEES_CARD_VIEW,
    )


def to_list_item(user: User) -> EmployeeListItem:
    return EmployeeListItem(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        staff_code=user.staff_code,
        gender=user.gender,
        role_id=user.role_id,
        role_name=(user.role.name if user.role else None),
        position_id=user.position_id,
        position_name=(user.position.name if user.position else None),
        position_rate=float(user.position.rate) if user.position and user.position.rate is not None else None,
        fired=bool(user.fired),
    )


def _resolve_attachment_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return value
    try:
        return generate_presigned_url(value)
    except Exception:
        logger.warning("Failed to generate attachment URL for employee card", exc_info=True)
        return value


def _medical_record_to_public(record: MedicalCheckRecord) -> MedicalCheckRecordPublic:
    return MedicalCheckRecordPublic(
        id=record.id,
        user_id=record.user_id,
        medical_check_type=MedicalCheckTypeRead.model_validate(record.check_type),
        passed_at=record.passed_at,
        next_due_at=record.next_due_at,
        status=record.status,
        comment=record.comment,
    )


def _cis_record_to_public(record: CisDocumentRecord) -> CisDocumentRecordPublic:
    return CisDocumentRecordPublic(
        id=record.id,
        user_id=record.user_id,
        cis_document_type=CisDocumentTypeRead.model_validate(record.document_type),
        number=record.number,
        issued_at=record.issued_at,
        expires_at=record.expires_at,
        status=record.status,
        issuer=record.issuer,
        comment=record.comment,
        attachment_url=_resolve_attachment_url(record.attachment_url),
    )


def can_view_medical_documents(viewer: Optional[User]) -> bool:
    if viewer is None:
        return True
    return any(
        has_permission(viewer, permission)
        for permission in (
            PermissionCode.MEDICAL_CHECKS_VIEW,
            PermissionCode.MEDICAL_CHECKS_MANAGE,
            PermissionCode.STAFF_MANAGE_ALL,
            PermissionCode.SYSTEM_ADMIN,
        )
    )


def can_view_cis_documents(viewer: Optional[User]) -> bool:
    if viewer is None:
        return True
    return any(
        has_permission(viewer, permission)
        for permission in (
            PermissionCode.CIS_DOCUMENTS_VIEW,
            PermissionCode.CIS_DOCUMENTS_MANAGE,
            PermissionCode.STAFF_MANAGE_ALL,
            PermissionCode.SYSTEM_ADMIN,
        )
    )


def to_card(
    user: User,
    viewer: Optional[User] = None,
    *,
    include_medical_checks: bool = True,
    include_cis_documents: bool = True,
) -> EmployeeCardPublic:
    can_see_rate = can_view_rate(viewer, user) if viewer else True
    medical_records = []
    cis_docs = []
    if include_medical_checks:
        medical_records = sorted(
            user.medical_check_records or [],
            key=lambda record: record.passed_at or date.min,
            reverse=True,
        )
    if include_cis_documents:
        cis_docs = sorted(
            user.cis_document_records or [],
            key=lambda record: record.issued_at or date.min,
            reverse=True,
        )
    photo_url = None
    if user.photo_key:
        try:
            photo_url = generate_presigned_url(user.photo_key)
        except Exception:
            logger.warning("Failed to build photo URL for user %s", user.id, exc_info=True)
            photo_url = None

    return EmployeeCardPublic(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        middle_name=user.middle_name,
        iiko_code=user.iiko_code,
        iiko_id=user.iiko_id,
        company_id=(user.company.id if user.company else None),
        company_name=(user.company.name if user.company else None),
        role_id=user.role_id,
        role_name=(user.role.name if user.role else None),
        position_id=user.position_id,
        position_name=(user.position.name if user.position else None),
        rate=float(user.rate) if can_see_rate and user.rate is not None else None,
        hire_date=user.hire_date,
        fire_date=user.fire_date,
        fired=bool(user.fired),
        staff_code=user.staff_code,
        gender=user.gender,
        phone_number=user.phone_number,
        email=user.email,
        birth_date=user.birth_date,
        photo_key=user.photo_key,
        photo_url=photo_url,
        is_cis_employee=bool(getattr(user, "is_cis_employee", False)),
        confidential_data_consent=bool(getattr(user, "confidential_data_consent", False)),
        is_formalized=bool(getattr(user, "is_formalized", False)),
        workplace_restaurant_id=getattr(user, "workplace_restaurant_id", None),
        individual_rate=float(user.individual_rate) if can_see_rate and user.individual_rate is not None else None,
        medical_checks=[_medical_record_to_public(record) for record in medical_records],
        cis_documents=[_cis_record_to_public(record) for record in cis_docs],
        has_fingerprint=bool(getattr(user, "has_fingerprint", False)),
        rate_hidden=not can_see_rate,
    )


def list_employee_items(
    db: Session,
    current_user: User,
    *,
    q: Optional[str] = None,
    include_fired: bool = False,
    limit: int = 50,
) -> list[EmployeeListItem]:
    ensure_staff_view(current_user)
    query = (
        db.query(User)
        .options(
            noload(User.permission_links),
            noload(User.direct_permissions),
            noload(User.medical_check_records),
            noload(User.cis_document_records),
            load_only(
                User.id,
                User.username,
                User.first_name,
                User.last_name,
                User.staff_code,
                User.gender,
                User.role_id,
                User.position_id,
                User.fired,
            ),
            joinedload(User.role).load_only(Role.id, Role.name),
            joinedload(User.role).noload(Role.permission_links),
            joinedload(User.role).noload(Role.permissions),
            joinedload(User.position).load_only(Position.id, Position.name, Position.rate),
            joinedload(User.position).noload(Position.permission_links),
            joinedload(User.position).noload(Position.permissions),
            joinedload(User.position).noload(Position.training_requirements),
        )
    )
    if not include_fired:
        query = query.filter(User.fired == False)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(
            or_(
                func.lower(User.username).like(like),
                func.lower(func.coalesce(User.first_name, "")).like(like),
                func.lower(func.coalesce(User.last_name, "")).like(like),
                func.lower(func.coalesce(User.staff_code, "")).like(like),
            )
        )

    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    if allowed_restaurants is not None:
        if allowed_restaurants:
            shared_user_ids = (
                db.query(user_restaurants.c.user_id)
                .filter(user_restaurants.c.restaurant_id.in_(allowed_restaurants))
            )
            query = query.filter(or_(User.id == current_user.id, User.id.in_(shared_user_ids)))
        else:
            query = query.filter(User.id == current_user.id)

    users = (
        query.order_by(
            func.lower(User.last_name).nullslast(),
            func.lower(User.first_name).nullslast(),
            User.id.asc(),
        )
        .limit(limit)
        .all()
    )
    return [to_list_item(user) for user in users]


def load_employee_card(
    db: Session,
    user_id: int,
    viewer: User,
    *,
    include_medical_checks: bool,
    include_cis_documents: bool,
) -> EmployeeCardPublic:
    options = [
        joinedload(User.company),
        joinedload(User.role),
        joinedload(User.position).joinedload(Position.payment_format),
        joinedload(User.position).joinedload(Position.restaurant_subdivision),
    ]
    if include_medical_checks:
        options.append(
            selectinload(User.medical_check_records).selectinload(MedicalCheckRecord.check_type)
        )
    else:
        options.append(noload(User.medical_check_records))
    if include_cis_documents:
        options.append(
            selectinload(User.cis_document_records).selectinload(CisDocumentRecord.document_type)
        )
    else:
        options.append(noload(User.cis_document_records))

    user = (
        db.query(User)
        .options(*options)
        .filter(User.id == user_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return to_card(
        user,
        viewer,
        include_medical_checks=include_medical_checks,
        include_cis_documents=include_cis_documents,
    )


def check_employee_card_permissions(db: Session, viewer: User, target_user_id: int) -> User:
    target = (
        db.query(User)
        .options(
            joinedload(User.position).joinedload(Position.payment_format),
            joinedload(User.position).joinedload(Position.restaurant_subdivision),
        )
        .filter(User.id == target_user_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if viewer.id == target.id:
        return target
    ensure_staff_view(viewer)
    if has_permission(viewer, PermissionCode.STAFF_MANAGE_ALL):
        return target
    if has_permission(viewer, PermissionCode.STAFF_MANAGE_SUBORDINATES) and can_manage_user(viewer, target):
        return target
    allowed_restaurants = get_user_restaurant_ids(db, viewer)
    if allowed_restaurants is None:
        return target
    if allowed_restaurants:
        shared_user_ids = (
            db.query(user_restaurants.c.user_id)
            .filter(user_restaurants.c.restaurant_id.in_(allowed_restaurants))
        )
        if db.query(User.id).filter(User.id == target.id, User.id.in_(shared_user_ids)).first():
            return target
    raise HTTPException(status_code=403, detail="Access denied")
