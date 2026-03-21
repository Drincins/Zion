from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend.bd.database import get_db
from backend.bd.models import Position, PositionTrainingRequirement, TrainingEventRecord, TrainingEventType, User
from backend.services.reference_cache import cached_reference_data, invalidate_reference_scope
from backend.schemas import (
    TrainingEventRecordCreate,
    TrainingEventRecordListResponse,
    TrainingEventRecordPublic,
    TrainingEventRecordUpdate,
    TrainingEventTypeCreate,
    TrainingEventTypeListResponse,
    TrainingEventTypePublic,
    TrainingEventTypeUpdate,
    PositionTrainingRequirementCreate,
    PositionTrainingRequirementUpdate,
    PositionTrainingRequirementPublic,
    PositionTrainingRequirementListResponse,
    TrainingRequirementSuggestion,
    TrainingRequirementSuggestionList,
)

try:  # pragma: no cover - shared dependency in project
    from backend.utils import get_current_user, users_share_restaurant
    from backend.services.permissions import (
        PermissionCode,
        ensure_permissions,
        has_permission,
        has_global_access,
        can_manage_user,
        ensure_can_manage_user,
    )
except Exception:  # pragma: no cover
    from fastapi.security import OAuth2PasswordBearer
    from jose import JWTError, jwt
    import os

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")
    SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET") or "CHANGE_ME"
    ALGORITHM = "HS256"

    def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            sub = payload.get("sub")
            if not sub:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
            user = db.query(User).get(int(sub))
            if not user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
            if user.fired:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь уволен")
            return user
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


    def users_share_restaurant(db: Session, viewer: User, target_user_id: int) -> bool:
        return viewer.id == target_user_id


    class PermissionCode:
        TRAINING_VIEW = "training.view"
        TRAINING_MANAGE = "training.manage"
        STAFF_MANAGE_ALL = "staff.manage_all"
        STAFF_MANAGE_SUBORDINATES = "staff.manage_subordinates"

    def ensure_permissions(user: User, *codes: str) -> None:
        return

    def has_permission(user: User, code: str) -> bool:
        return True

    def has_global_access(user: User) -> bool:
        return True

    def can_manage_user(viewer: User, target: User) -> bool:
        return True

    def ensure_can_manage_user(viewer: User, target: User) -> None:
        return


router = APIRouter(prefix="/training-events", tags=["Training events"])
TRAINING_EVENT_TYPES_CACHE_SCOPE = "training_events:types"
TRAINING_EVENT_TYPES_CACHE_TTL_SECONDS = 60


def _has_training_view(user: User) -> bool:
    return has_global_access(user) or has_permission(user, PermissionCode.TRAINING_VIEW) or has_permission(user, PermissionCode.TRAINING_MANAGE)


def _has_training_manage(user: User) -> bool:
    return has_global_access(user) or has_permission(user, PermissionCode.TRAINING_MANAGE)


def _ensure_training_view(user: User) -> None:
    if not _has_training_view(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")


def _effective_user(db: Session, viewer: User, requested_user_id: Optional[int]) -> Optional[int]:
    if requested_user_id is None:
        return None if _has_training_view(viewer) else viewer.id
    if requested_user_id == viewer.id:
        return requested_user_id
    if _has_training_view(viewer):
        return requested_user_id
    if has_permission(viewer, PermissionCode.STAFF_MANAGE_SUBORDINATES):
        target = db.query(User).options(joinedload(User.position)).filter(User.id == requested_user_id).first()
        if target and can_manage_user(viewer, target):
            return requested_user_id
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not enough permissions')


def _ensure_training_manage(user: User) -> None:
    ensure_permissions(user, PermissionCode.TRAINING_MANAGE)


def _load_user_with_position(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).options(joinedload(User.position)).filter(User.id == user_id).first()


def _to_type_public(obj: TrainingEventType) -> TrainingEventTypePublic:
    return TrainingEventTypePublic(id=obj.id, name=obj.name)


def _to_record_public(record: TrainingEventRecord) -> TrainingEventRecordPublic:
    return TrainingEventRecordPublic(
        id=record.id,
        event_type_id=record.event_type_id,
        user_id=record.user_id,
        date=record.date,
        comment=record.comment,
        event_type=_to_type_public(record.event_type) if record.event_type else None,
    )


def _to_requirement_public(row: PositionTrainingRequirement) -> PositionTrainingRequirementPublic:
    return PositionTrainingRequirementPublic(
        id=row.id,
        position_id=row.position_id,
        event_type_id=row.event_type_id,
        required=row.required,
        event_type=_to_type_public(row.event_type) if row.event_type else None,
    )


def _load_position(db: Session, position_id: int) -> Position:
    position = db.query(Position).get(position_id)
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    return position


@router.get("/types", response_model=TrainingEventTypeListResponse)
def list_training_event_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingEventTypeListResponse:
    _ensure_training_view(current_user)
    def _load_types() -> list[dict]:
        rows = db.query(TrainingEventType).order_by(TrainingEventType.name.asc()).all()
        return [_to_type_public(item).model_dump(mode="json") for item in rows]

    payload = cached_reference_data(
        TRAINING_EVENT_TYPES_CACHE_SCOPE,
        "all",
        _load_types,
        ttl_seconds=TRAINING_EVENT_TYPES_CACHE_TTL_SECONDS,
    )
    items = [TrainingEventTypePublic.model_validate(item) for item in payload]
    return TrainingEventTypeListResponse(items=items)


@router.post("/types", response_model=TrainingEventTypePublic, status_code=status.HTTP_201_CREATED)
def create_training_event_type(
    payload: TrainingEventTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingEventTypePublic:
    _ensure_training_manage(current_user)
    normalized = func.lower(TrainingEventType.name)
    duplicate = (
        db.query(TrainingEventType)
        .filter(normalized == payload.name.lower())
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Training event type already exists")

    obj = TrainingEventType(name=payload.name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    invalidate_reference_scope(TRAINING_EVENT_TYPES_CACHE_SCOPE)
    return _to_type_public(obj)


@router.put("/types/{type_id}", response_model=TrainingEventTypePublic)
def update_training_event_type(
    type_id: int,
    payload: TrainingEventTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingEventTypePublic:
    _ensure_training_manage(current_user)
    obj = db.query(TrainingEventType).get(type_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training event type not found")

    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        normalized = func.lower(TrainingEventType.name)
        duplicate = (
            db.query(TrainingEventType)
            .filter(normalized == data["name"].lower(), TrainingEventType.id != type_id)
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Training event type already exists")
        obj.name = data["name"]

    db.commit()
    db.refresh(obj)
    invalidate_reference_scope(TRAINING_EVENT_TYPES_CACHE_SCOPE)
    return _to_type_public(obj)


@router.delete("/types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_training_event_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _ensure_training_manage(current_user)
    obj = db.query(TrainingEventType).get(type_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training event type not found")
    db.delete(obj)
    db.commit()
    invalidate_reference_scope(TRAINING_EVENT_TYPES_CACHE_SCOPE)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/position-requirements", response_model=PositionTrainingRequirementListResponse)
def list_position_training_requirements(
    position_id: int = Query(..., description="ID позиции"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PositionTrainingRequirementListResponse:
    _ensure_training_manage(current_user)
    _load_position(db, position_id)
    rows = (
        db.query(PositionTrainingRequirement)
        .options(joinedload(PositionTrainingRequirement.event_type))
        .filter(PositionTrainingRequirement.position_id == position_id)
        .order_by(PositionTrainingRequirement.required.desc(), PositionTrainingRequirement.id.asc())
        .all()
    )
    items = [_to_requirement_public(row) for row in rows]
    return PositionTrainingRequirementListResponse(items=items)


@router.post("/position-requirements", response_model=PositionTrainingRequirementPublic, status_code=status.HTTP_201_CREATED)
def create_position_training_requirement(
    payload: PositionTrainingRequirementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PositionTrainingRequirementPublic:
    _ensure_training_manage(current_user)
    _load_position(db, payload.position_id)
    event_type = db.query(TrainingEventType).get(payload.event_type_id)
    if not event_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training event type not found")
    duplicate = (
        db.query(PositionTrainingRequirement)
        .filter(
            PositionTrainingRequirement.position_id == payload.position_id,
            PositionTrainingRequirement.event_type_id == payload.event_type_id,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Requirement already exists")

    obj = PositionTrainingRequirement(
        position_id=payload.position_id,
        event_type_id=payload.event_type_id,
        required=payload.required,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    db.refresh(event_type)
    return _to_requirement_public(obj)


@router.put("/position-requirements/{requirement_id}", response_model=PositionTrainingRequirementPublic)
def update_position_training_requirement(
    requirement_id: int,
    payload: PositionTrainingRequirementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PositionTrainingRequirementPublic:
    _ensure_training_manage(current_user)
    obj = (
        db.query(PositionTrainingRequirement)
        .options(joinedload(PositionTrainingRequirement.event_type))
        .get(requirement_id)
    )
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")
    data = payload.model_dump(exclude_unset=True)
    if "required" in data and data["required"] is not None:
        obj.required = data["required"]
    db.commit()
    db.refresh(obj)
    return _to_requirement_public(obj)


@router.delete("/position-requirements/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_position_training_requirement(
    requirement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _ensure_training_manage(current_user)
    obj = db.query(PositionTrainingRequirement).get(requirement_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")
    db.delete(obj)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=TrainingEventRecordListResponse)
def list_training_event_records(
    user_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingEventRecordListResponse:
    _ensure_training_view(current_user)
    effective_user_id = _effective_user(db, current_user, user_id)

    qry = db.query(TrainingEventRecord).options(joinedload(TrainingEventRecord.event_type))
    if effective_user_id is not None:
        qry = qry.filter(TrainingEventRecord.user_id == effective_user_id)
    if date_from is not None:
        qry = qry.filter(TrainingEventRecord.date >= date_from)
    if date_to is not None:
        qry = qry.filter(TrainingEventRecord.date <= date_to)

    records = (
        qry.order_by(TrainingEventRecord.date.desc(), TrainingEventRecord.id.desc())
        .limit(limit)
        .all()
    )

    items = [_to_record_public(r) for r in records]
    return TrainingEventRecordListResponse(items=items)


@router.get("/position-requirements/suggestions", response_model=TrainingRequirementSuggestionList)
def list_training_requirement_suggestions(
    position_id: int = Query(..., description="ID позиции"),
    user_id: Optional[int] = Query(None, description="ID сотрудника для статуса прохождения"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingRequirementSuggestionList:
    _ensure_training_view(current_user)
    effective_user_id = _effective_user(db, current_user, user_id)
    _load_position(db, position_id)

    requirement_rows = (
        db.query(PositionTrainingRequirement)
        .filter(PositionTrainingRequirement.position_id == position_id)
        .all()
    )
    requirement_map = {row.event_type_id: row for row in requirement_rows}

    completed_map = {}
    if effective_user_id is not None:
        completions = (
            db.query(TrainingEventRecord.event_type_id, func.max(TrainingEventRecord.date))
            .filter(TrainingEventRecord.user_id == effective_user_id)
            .group_by(TrainingEventRecord.event_type_id)
            .all()
        )
        completed_map = {event_type_id: completed_at for event_type_id, completed_at in completions}

    event_types = db.query(TrainingEventType).order_by(TrainingEventType.name.asc()).all()
    items: list[TrainingRequirementSuggestion] = []
    for event_type in event_types:
        req = requirement_map.get(event_type.id)
        items.append(
            TrainingRequirementSuggestion(
                event_type_id=event_type.id,
                event_type=_to_type_public(event_type),
                required=bool(req.required) if req else False,
                requirement_id=req.id if req else None,
                completed=event_type.id in completed_map,
                completed_at=completed_map.get(event_type.id),
            )
        )

    items.sort(key=lambda item: (not item.required, item.event_type.name.lower()))
    return TrainingRequirementSuggestionList(items=items)


@router.post("", response_model=TrainingEventRecordPublic, status_code=status.HTTP_201_CREATED)
def create_training_event_record(
    payload: TrainingEventRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingEventRecordPublic:
    ensure_permissions(
        current_user,
        PermissionCode.TRAINING_MANAGE,
        PermissionCode.STAFF_MANAGE_ALL,
        PermissionCode.STAFF_MANAGE_SUBORDINATES,
    )

    target_user = None
    if payload.user_id != current_user.id:
        target_user = _load_user_with_position(db, payload.user_id)
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        ensure_can_manage_user(current_user, target_user)
    elif not has_permission(current_user, PermissionCode.TRAINING_MANAGE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: training management permission required",
        )

    event_type = db.query(TrainingEventType).get(payload.event_type_id)
    if not event_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training event type not found")

    obj = TrainingEventRecord(
        event_type_id=payload.event_type_id,
        user_id=payload.user_id,
        date=payload.date,
        comment=payload.comment,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_record_public(obj)


@router.put("/{record_id}", response_model=TrainingEventRecordPublic)
def update_training_event_record(
    record_id: int,
    payload: TrainingEventRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingEventRecordPublic:
    record = db.query(TrainingEventRecord).get(record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training event record not found")

    ensure_permissions(
        current_user,
        PermissionCode.TRAINING_MANAGE,
        PermissionCode.STAFF_MANAGE_ALL,
        PermissionCode.STAFF_MANAGE_SUBORDINATES,
    )

    target_user = _load_user_with_position(db, record.user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if record.user_id != current_user.id:
        ensure_can_manage_user(current_user, target_user)
    elif not has_permission(current_user, PermissionCode.TRAINING_MANAGE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: training management permission required",
        )

    data = payload.model_dump(exclude_unset=True)
    data.pop("user_id", None)
    if "event_type_id" in data:
        event_type = db.query(TrainingEventType).get(data["event_type_id"])
        if not event_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training event type not found")
        record.event_type_id = data["event_type_id"]
    if "date" in data:
        record.date = data["date"]
    if "comment" in data:
        record.comment = data["comment"]

    db.commit()
    db.refresh(record)
    return _to_record_public(record)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_training_event_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    record = db.query(TrainingEventRecord).get(record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training event record not found")

    ensure_permissions(
        current_user,
        PermissionCode.TRAINING_MANAGE,
        PermissionCode.STAFF_MANAGE_ALL,
        PermissionCode.STAFF_MANAGE_SUBORDINATES,
    )

    target_user = _load_user_with_position(db, record.user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if record.user_id != current_user.id:
        ensure_can_manage_user(current_user, target_user)
    elif not has_permission(current_user, PermissionCode.TRAINING_MANAGE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: training management permission required",
        )

    db.delete(record)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
