"""Checklist CRUD endpoints."""
from __future__ import annotations

import os
from datetime import date, datetime, time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Response
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from backend.bd.database import get_db
from backend.bd.models import (
    Checklist,
    ChecklistAnswer,
    ChecklistQuestion,
    ChecklistQuestionAnswer,
    ChecklistSection,
    ChecklistDraft,
    ChecklistDraftAnswer,
    Position,
    Role,
    User,
    Restaurant,
)
from backend.schemas.checklists import (
    ChecklistCreate,
    ChecklistUpdate,
    ChecklistRead,
    ChecklistDetail,
    ChecklistSectionCreate,
    ChecklistSectionUpdate,
    ChecklistSectionRead,
    ChecklistQuestionCreate,
    ChecklistQuestionUpdate,
    ChecklistQuestionRead,
    ChecklistReportSummaryItem,
    ChecklistAttemptListItem,
    ChecklistAttemptListResponse,
    ChecklistAttemptDetail,
    ChecklistAttemptAnswer,
    ChecklistReportMetrics,
    ChecklistReportDailyCount,
    ChecklistPortalLoginStartRequest,
    ChecklistPortalLoginStartResponse,
    ChecklistPortalLoginFinishRequest,
    ChecklistPortalLoginResponse,
    ChecklistPortalUser,
    ChecklistPortalChecklistItem,
    ChecklistPortalChecklistDetail,
    ChecklistPortalSection,
    ChecklistPortalQuestion,
    ChecklistPortalDraftRequest,
    ChecklistPortalDraftResponse,
    ChecklistPortalDraftAnswer,
    ChecklistPortalSubmitRequest,
    ChecklistPortalSubmitResponse,
    ChecklistPortalUploadResponse,
    ChecklistPortalAttemptSummary,
)
from backend.services.permissions import PermissionKey, has_any_permission
from backend.utils import get_current_user, verify_password
from backend.services import s3 as s3_service
from backend.utils import create_jwt_token
from backend.services.checklists_export import export_attempt_to_files
from backend.services.checklists_report_data import get_attempt_data, get_attempt_scores_map, format_attempt_result
from backend.services.checklists_timezone import format_moscow


router = APIRouter(prefix="/checklists", tags=["checklists"])
CHECKLISTS_EDIT_ALL_PERMISSION = PermissionKey.CHECKLISTS_EDIT_ALL


def _ensure_manage_access(user) -> None:
    if not has_any_permission(
        user,
        {
            PermissionKey.SYSTEM_ADMIN,
            PermissionKey.STAFF_MANAGE_ALL,
            PermissionKey.COMPANIES_MANAGE,
            CHECKLISTS_EDIT_ALL_PERMISSION,
        },
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

def _is_global_admin(user) -> bool:
    return has_any_permission(user, {PermissionKey.SYSTEM_ADMIN, PermissionKey.STAFF_MANAGE_ALL})

def _apply_company_scope(query, user):
    if _is_global_admin(user):
        return query
    if getattr(user, "company_id", None):
        return query.filter(Checklist.company_id == user.company_id)
    return query


def _format_user_name(user: User | None) -> str | None:
    if not user:
        return None
    last_name = (getattr(user, "last_name", None) or "").strip()
    first_name = (getattr(user, "first_name", None) or "").strip()
    full_name = " ".join([part for part in [last_name, first_name] if part]).strip()
    if full_name:
        return full_name
    username = (getattr(user, "username", None) or "").strip()
    return username or None


def _has_checklists_edit_all_access(user) -> bool:
    return has_any_permission(
        user,
        {
            PermissionKey.SYSTEM_ADMIN,
            PermissionKey.STAFF_MANAGE_ALL,
            PermissionKey.COMPANIES_MANAGE,
            CHECKLISTS_EDIT_ALL_PERMISSION,
        },
    )


def _ensure_checklist_edit_access(user, checklist: Checklist) -> None:
    if _has_checklists_edit_all_access(user):
        return
    # Legacy checklists may have no author set in old databases.
    # Allow edit for checklist managers in this case to avoid blocking existing data.
    if checklist.created_by is None:
        return
    if checklist.created_by and checklist.created_by == user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для редактирования чек-листа")


def _to_checklist_read(checklist: Checklist) -> ChecklistRead:
    return ChecklistRead(
        id=checklist.id,
        name=checklist.name,
        description=checklist.description,
        company_id=checklist.company_id,
        is_scored=checklist.is_scored,
        scope_type=checklist.scope_type,
        all_restaurants=bool(checklist.all_restaurants),
        restaurant_id=checklist.restaurant_id,
        restaurant_subdivision_id=checklist.restaurant_subdivision_id,
        access_subdivision_ids=checklist.access_subdivision_ids,
        access_all_subdivisions=bool(checklist.access_all_subdivisions),
        control_restaurant_ids=checklist.control_restaurant_ids,
        control_subdivision_ids=checklist.control_subdivision_ids,
        control_all_restaurants=bool(checklist.control_all_restaurants),
        control_all_subdivisions=bool(checklist.control_all_subdivisions),
        created_by=checklist.created_by,
        creator_name=_format_user_name(getattr(checklist, "creator", None)),
        created_at=checklist.created_at,
        position_ids=[p.id for p in (checklist.positions or [])],
    )

def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None

def _apply_date_range(query, date_from: Optional[str], date_to: Optional[str]):
    start = _parse_date(date_from)
    end = _parse_date(date_to)
    local_dt = func.timezone("Europe/Moscow", ChecklistAnswer.submitted_at)
    if start:
        query = query.filter(local_dt >= datetime.combine(start, time.min))
    if end:
        query = query.filter(local_dt <= datetime.combine(end, time.max))
    return query


def _portal_user_payload(user: User) -> ChecklistPortalUser:
    position = getattr(getattr(user, "position", None), "name", None)
    default_department = None
    if getattr(user, "workplace_restaurant", None):
        default_department = user.workplace_restaurant.name
    return ChecklistPortalUser(
        id=user.id,
        name=" ".join([p for p in [user.last_name, user.first_name, user.middle_name] if p])
        or user.username,
        phone=user.phone_number,
        position=position,
        company_id=user.company_id,
        company_name=getattr(getattr(user, "company", None), "name", None),
        default_department=default_department,
    )


PORTAL_TIME_CONTROL_ROLE_NAMES = {"таймконтроль", "тайм-контроль", "timecontrol", "time_control"}


def _portal_get_user_by_staff_code(db: Session, staff_code: str) -> User:
    code = (staff_code or "").strip()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Введите табельный номер")
    user: User | None = db.query(User).filter(User.staff_code == code).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Табельный номер не найден")
    if user.fired:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь деактивирован")
    return user


def _normalize_role_name(name: Optional[str]) -> str:
    return (name or "").strip().lower().replace(" ", "")


def _portal_resolve_user_role(user: User) -> Optional[Role]:
    if getattr(user, "role", None):
        return user.role
    if getattr(user, "position", None) and getattr(user.position, "role", None):
        return user.position.role
    return None


def _portal_time_control_max_level(db: Session) -> Optional[int]:
    max_level: Optional[int] = None
    for row in db.query(Role.level, Role.name).all():
        level = row[0]
        name = row[1]
        if level is None:
            continue
        if _normalize_role_name(name) in PORTAL_TIME_CONTROL_ROLE_NAMES:
            max_level = level if max_level is None else max(max_level, level)
    return max_level


def _portal_requires_password_step(db: Session, user: User) -> bool:
    role = _portal_resolve_user_role(user)
    if not role:
        return True

    role_name = _normalize_role_name(getattr(role, "name", None))
    if role_name in PORTAL_TIME_CONTROL_ROLE_NAMES:
        return False

    role_level = getattr(role, "level", None)
    threshold = _portal_time_control_max_level(db)
    if role_level is not None and threshold is not None and role_level <= threshold:
        # Same level as Time Control (or lower) -> only staff code.
        return False

    username = (user.username or "").strip()
    hashed = (user.hashed_password or "").strip()
    if not username or not hashed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для этой роли нужен логин и пароль. Обратитесь к администратору.",
        )
    return True


def _portal_checklist_allowed(db: Session, user: User, checklist: Checklist) -> bool:
    if not user.position_id:
        return False
    position: Position | None = db.query(Position).get(user.position_id)  # type: ignore[arg-type]
    if not position:
        return False
    if checklist not in (position.checklists or []):
        return False

    def _restaurant_allowed() -> bool:
        if checklist.scope_type == "restaurants_multi":
            restaurant_ids = _parse_int_list(getattr(checklist, "control_restaurant_ids", None))
            if not restaurant_ids:
                return False
            if user.workplace_restaurant_id and int(user.workplace_restaurant_id) in restaurant_ids:
                return True
            if user.restaurants and any(int(r.id) in restaurant_ids for r in user.restaurants if getattr(r, "id", None)):
                return True
            return False

        if checklist.all_restaurants:
            return True
        if not checklist.restaurant_id:
            return True
        if user.workplace_restaurant_id and user.workplace_restaurant_id == checklist.restaurant_id:
            return True
        if user.restaurants and any(r.id == checklist.restaurant_id for r in user.restaurants):
            return True
        return False

    def _subdivision_allowed() -> bool:
        if checklist.access_all_subdivisions:
            return True
        if not checklist.access_subdivision_ids:
            return True
        if not position.restaurant_subdivision_id:
            return False
        return position.restaurant_subdivision_id in checklist.access_subdivision_ids

    return _restaurant_allowed() and _subdivision_allowed()


def _portal_dedupe_names(values: List[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for raw in values:
        value = (raw or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _parse_int_list(raw: object) -> list[int]:
    if not raw or not isinstance(raw, list):
        return []
    values: list[int] = []
    for item in raw:
        try:
            values.append(int(item))
        except (TypeError, ValueError):
            continue
    return values


def _portal_resolve_control_objects(db: Session, user: User, checklist: Checklist | None = None) -> List[str]:
    is_unrestricted = bool(getattr(user, "has_global_access", False) or getattr(user, "has_full_restaurant_access", False))

    restaurant_ids: set[int] = set()
    if getattr(user, "workplace_restaurant_id", None):
        try:
            restaurant_ids.add(int(user.workplace_restaurant_id))
        except (TypeError, ValueError):
            pass
    for row in (user.restaurants or []):
        rid = getattr(row, "id", None)
        if rid is None:
            continue
        try:
            restaurant_ids.add(int(rid))
        except (TypeError, ValueError):
            continue

    restaurants_query = db.query(Restaurant)
    if getattr(user, "company_id", None):
        restaurants_query = restaurants_query.filter(Restaurant.company_id == user.company_id)
    if not is_unrestricted:
        if not restaurant_ids:
            restaurants_query = restaurants_query.filter(Restaurant.id == -1)
        else:
            restaurants_query = restaurants_query.filter(Restaurant.id.in_(restaurant_ids))
    if checklist:
        if checklist.scope_type == "restaurants_multi":
            restaurant_ids = _parse_int_list(getattr(checklist, "control_restaurant_ids", None))
            if restaurant_ids:
                restaurants_query = restaurants_query.filter(Restaurant.id.in_(restaurant_ids))
            else:
                restaurants_query = restaurants_query.filter(Restaurant.id == -1)
        elif checklist.restaurant_id:
            restaurants_query = restaurants_query.filter(Restaurant.id == checklist.restaurant_id)

    restaurants = restaurants_query.order_by(Restaurant.name.asc()).all()
    options: List[str] = [row.name for row in restaurants if getattr(row, "name", None)]

    if not options and getattr(getattr(user, "workplace_restaurant", None), "name", None):
        options.append(user.workplace_restaurant.name)

    return _portal_dedupe_names(options)


def _apply_positions(checklist: Checklist, positions: List[Position]) -> None:
    checklist.positions = positions


def _resolve_checklist_state(checklist: Checklist | None, payload) -> dict:
    current_position_ids = [int(item.id) for item in (checklist.positions or [])] if checklist else []
    state = {
        "company_id": getattr(payload, "company_id", None) if getattr(payload, "company_id", None) is not None else getattr(checklist, "company_id", None),
        "scope_type": getattr(payload, "scope_type", None) if getattr(payload, "scope_type", None) is not None else getattr(checklist, "scope_type", None),
        "all_restaurants": (
            bool(payload.all_restaurants)
            if getattr(payload, "all_restaurants", None) is not None
            else bool(getattr(checklist, "all_restaurants", False))
        ),
        "restaurant_id": getattr(payload, "restaurant_id", None) if getattr(payload, "restaurant_id", None) is not None else getattr(checklist, "restaurant_id", None),
        "control_restaurant_ids": (
            getattr(payload, "control_restaurant_ids", None)
            if getattr(payload, "control_restaurant_ids", None) is not None
            else getattr(checklist, "control_restaurant_ids", None)
        ),
        "access_subdivision_ids": (
            getattr(payload, "access_subdivision_ids", None)
            if getattr(payload, "access_subdivision_ids", None) is not None
            else getattr(checklist, "access_subdivision_ids", None)
        ),
        "position_ids": (
            getattr(payload, "position_ids", None)
            if getattr(payload, "position_ids", None) is not None
            else current_position_ids
        ),
    }
    return state


def _validate_checklist_hierarchy(db: Session, checklist: Checklist | None, payload) -> List[Position]:
    state = _resolve_checklist_state(checklist, payload)
    position_ids = sorted(set(_parse_int_list(state["position_ids"])))
    if not position_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Выберите хотя бы одну должность")

    positions = (
        db.query(Position)
        .options(selectinload(Position.restaurant_subdivision))
        .filter(Position.id.in_(position_ids))
        .all()
    )
    if len(positions) != len(position_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Часть выбранных должностей не найдена")

    subdivision_ids = set(_parse_int_list(state["access_subdivision_ids"]))
    if subdivision_ids:
        invalid_positions = [
            position.name
            for position in positions
            if position.restaurant_subdivision_id is None or position.restaurant_subdivision_id not in subdivision_ids
        ]
        if invalid_positions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Выбранные должности не относятся к выбранным подразделениям",
            )

    restaurant_ids: list[int] = []
    scope_type = state["scope_type"]
    if scope_type == "restaurants_multi":
        restaurant_ids = sorted(set(_parse_int_list(state["control_restaurant_ids"])))
        if not restaurant_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Выберите хотя бы один ресторан")
    elif scope_type == "restaurant" and not state["all_restaurants"]:
        restaurant_id = state["restaurant_id"]
        if restaurant_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Выберите хотя бы один ресторан")
        restaurant_ids = [int(restaurant_id)]

    if restaurant_ids:
        restaurants = db.query(Restaurant).filter(Restaurant.id.in_(restaurant_ids)).all()
        if len(restaurants) != len(restaurant_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Часть выбранных ресторанов не найдена")
        company_id = state["company_id"]
        if company_id is not None and any(restaurant.company_id != company_id for restaurant in restaurants):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Чек-лист можно привязать только к ресторанам одной компании",
            )

    return positions


def _normalize_scope(payload, checklist: Checklist) -> None:
    scope = payload.scope_type
    if scope:
        checklist.scope_type = scope
    if getattr(payload, "all_restaurants", None) is not None:
        checklist.all_restaurants = bool(payload.all_restaurants)
    if scope == "restaurant":
        checklist.restaurant_id = None if checklist.all_restaurants else payload.restaurant_id
        checklist.restaurant_subdivision_id = None
    elif scope == "restaurants_multi":
        checklist.restaurant_id = None
        checklist.restaurant_subdivision_id = None
        checklist.all_restaurants = False
    elif scope == "subdivision":
        checklist.restaurant_subdivision_id = payload.restaurant_subdivision_id
        checklist.restaurant_id = None
        checklist.all_restaurants = False


def _get_next_section_order(db: Session, checklist_id: int) -> int:
    max_order = (
        db.query(func.max(ChecklistSection.order))
        .filter(ChecklistSection.checklist_id == checklist_id)
        .scalar()
    )
    return int(max_order or 0) + 1


def _get_next_question_order(db: Session, checklist_id: int) -> int:
    max_order = (
        db.query(func.max(ChecklistQuestion.order))
        .filter(ChecklistQuestion.checklist_id == checklist_id)
        .scalar()
    )
    return int(max_order or 0) + 1


@router.get("", response_model=List[ChecklistRead])
def list_checklists(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_manage_access(current_user)
    items = (
        _apply_company_scope(db.query(Checklist), current_user)
        .options(selectinload(Checklist.positions), selectinload(Checklist.creator))
        .order_by(Checklist.created_at.desc())
        .all()
    )
    return [_to_checklist_read(item) for item in items]


@router.get("/{checklist_id}", response_model=ChecklistDetail)
def get_checklist(
    checklist_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_manage_access(current_user)
    checklist: Checklist | None = (
        _apply_company_scope(db.query(Checklist), current_user)
        .options(
            selectinload(Checklist.sections),
            selectinload(Checklist.positions),
            selectinload(Checklist.creator),
        )
        .filter(Checklist.id == checklist_id)
        .first()
    )
    if not checklist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found")
    _ensure_checklist_edit_access(current_user, checklist)

    questions = (
        db.query(ChecklistQuestion)
        .filter(ChecklistQuestion.checklist_id == checklist_id)
        .order_by(ChecklistQuestion.order.asc())
        .all()
    )
    return ChecklistDetail(
        id=checklist.id,
        name=checklist.name,
        description=checklist.description,
        company_id=checklist.company_id,
        is_scored=checklist.is_scored,
        scope_type=checklist.scope_type,
        all_restaurants=bool(checklist.all_restaurants),
        restaurant_id=checklist.restaurant_id,
        restaurant_subdivision_id=checklist.restaurant_subdivision_id,
        access_subdivision_ids=checklist.access_subdivision_ids,
        access_all_subdivisions=bool(checklist.access_all_subdivisions),
        control_restaurant_ids=checklist.control_restaurant_ids,
        control_subdivision_ids=checklist.control_subdivision_ids,
        control_all_restaurants=bool(checklist.control_all_restaurants),
        control_all_subdivisions=bool(checklist.control_all_subdivisions),
        created_by=checklist.created_by,
        creator_name=_format_user_name(getattr(checklist, "creator", None)),
        created_at=checklist.created_at,
        position_ids=[p.id for p in (checklist.positions or [])],
        sections=[
            ChecklistSectionRead(
                id=sec.id,
                title=sec.name,
                order=sec.order,
                is_required=sec.is_required,
            )
            for sec in (checklist.sections or [])
        ],
        questions=[
            ChecklistQuestionRead(
                id=q.id,
                text=q.text,
                type=q.type,
                order=q.order,
                required=q.required,
                meta=q.meta,
                weight=q.weight,
                require_photo=q.require_photo,
                require_comment=q.require_comment,
                section_id=q.section_id,
            )
            for q in questions
        ],
    )


@router.post("", response_model=ChecklistRead, status_code=status.HTTP_201_CREATED)
def create_checklist(
    payload: ChecklistCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_manage_access(current_user)
    if not _is_global_admin(current_user) and current_user.company_id != payload.company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    positions = _validate_checklist_hierarchy(db, None, payload)
    checklist = Checklist(
        name=payload.name.strip(),
        description=payload.description,
        company_id=payload.company_id,
        is_scored=payload.is_scored,
        access_subdivision_ids=payload.access_subdivision_ids,
        access_all_subdivisions=payload.access_all_subdivisions,
        control_restaurant_ids=payload.control_restaurant_ids,
        control_subdivision_ids=payload.control_subdivision_ids,
        control_all_restaurants=payload.control_all_restaurants,
        control_all_subdivisions=payload.control_all_subdivisions,
        created_by=current_user.id,
    )
    _normalize_scope(payload, checklist)
    db.add(checklist)
    db.flush()
    _apply_positions(checklist, positions)

    db.commit()
    db.refresh(checklist)
    return _to_checklist_read(checklist)


@router.patch("/{checklist_id}", response_model=ChecklistRead)
def update_checklist(
    checklist_id: int,
    payload: ChecklistUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_manage_access(current_user)
    checklist: Checklist | None = (
        _apply_company_scope(db.query(Checklist), current_user)
        .filter(Checklist.id == checklist_id)
        .first()
    )
    if not checklist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found")
    _ensure_checklist_edit_access(current_user, checklist)
    validated_positions = _validate_checklist_hierarchy(db, checklist, payload)

    if payload.name is not None:
        checklist.name = payload.name.strip()
    if payload.company_id is not None:
        if not _is_global_admin(current_user) and current_user.company_id != payload.company_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
        checklist.company_id = payload.company_id
    if payload.is_scored is not None:
        checklist.is_scored = payload.is_scored
    if payload.description is not None:
        checklist.description = payload.description
    if payload.access_subdivision_ids is not None:
        checklist.access_subdivision_ids = payload.access_subdivision_ids
    if payload.access_all_subdivisions is not None:
        checklist.access_all_subdivisions = payload.access_all_subdivisions
    if payload.control_restaurant_ids is not None:
        checklist.control_restaurant_ids = payload.control_restaurant_ids
    if payload.control_subdivision_ids is not None:
        checklist.control_subdivision_ids = payload.control_subdivision_ids
    if payload.control_all_restaurants is not None:
        checklist.control_all_restaurants = payload.control_all_restaurants
    if payload.control_all_subdivisions is not None:
        checklist.control_all_subdivisions = payload.control_all_subdivisions
    if (
        payload.scope_type is not None
        or payload.all_restaurants is not None
        or payload.restaurant_id is not None
        or payload.restaurant_subdivision_id is not None
    ):
        _normalize_scope(payload, checklist)
    if payload.position_ids is not None:
        _apply_positions(checklist, validated_positions)

    db.commit()
    db.refresh(checklist)
    return _to_checklist_read(checklist)


@router.delete("/{checklist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_checklist(
    checklist_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_manage_access(current_user)
    checklist: Checklist | None = (
        _apply_company_scope(db.query(Checklist), current_user)
        .filter(Checklist.id == checklist_id)
        .first()
    )
    if not checklist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found")
    _ensure_checklist_edit_access(current_user, checklist)
    db.delete(checklist)
    db.commit()
    return None


@router.post("/{checklist_id}/sections", response_model=ChecklistSectionRead, status_code=status.HTTP_201_CREATED)
def create_section(
    checklist_id: int,
    payload: ChecklistSectionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_manage_access(current_user)
    checklist: Checklist | None = (
        _apply_company_scope(db.query(Checklist), current_user)
        .filter(Checklist.id == checklist_id)
        .first()
    )
    if not checklist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found")
    _ensure_checklist_edit_access(current_user, checklist)

    order = payload.order if payload.order is not None else _get_next_section_order(db, checklist_id)
    section = ChecklistSection(
        checklist_id=checklist_id,
        name=payload.title.strip(),
        order=order,
        is_required=payload.is_required,
    )
    db.add(section)
    db.commit()
    db.refresh(section)
    return ChecklistSectionRead(
        id=section.id,
        title=section.name,
        order=section.order,
        is_required=section.is_required,
    )


@router.patch("/{checklist_id}/sections/{section_id}", response_model=ChecklistSectionRead)
def update_section(
    checklist_id: int,
    section_id: int,
    payload: ChecklistSectionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_manage_access(current_user)
    section: ChecklistSection | None = (
        _apply_company_scope(db.query(ChecklistSection).join(Checklist), current_user)
        .filter(ChecklistSection.id == section_id, ChecklistSection.checklist_id == checklist_id)
        .first()
    )
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    _ensure_checklist_edit_access(current_user, section.checklist)

    if payload.title is not None:
        section.name = payload.title.strip()
    if payload.order is not None:
        section.order = payload.order
    if payload.is_required is not None:
        section.is_required = payload.is_required

    db.commit()
    db.refresh(section)
    return ChecklistSectionRead(
        id=section.id,
        title=section.name,
        order=section.order,
        is_required=section.is_required,
    )


@router.delete("/{checklist_id}/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_section(
    checklist_id: int,
    section_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_manage_access(current_user)
    section: ChecklistSection | None = (
        _apply_company_scope(db.query(ChecklistSection).join(Checklist), current_user)
        .filter(ChecklistSection.id == section_id, ChecklistSection.checklist_id == checklist_id)
        .first()
    )
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    _ensure_checklist_edit_access(current_user, section.checklist)
    db.delete(section)
    db.commit()
    return None


@router.post("/{checklist_id}/questions", response_model=ChecklistQuestionRead, status_code=status.HTTP_201_CREATED)
def create_question(
    checklist_id: int,
    payload: ChecklistQuestionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_manage_access(current_user)
    checklist: Checklist | None = (
        _apply_company_scope(db.query(Checklist), current_user)
        .filter(Checklist.id == checklist_id)
        .first()
    )
    if not checklist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found")
    _ensure_checklist_edit_access(current_user, checklist)

    order = payload.order if payload.order is not None else _get_next_question_order(db, checklist_id)
    question = ChecklistQuestion(
        checklist_id=checklist_id,
        order=order,
        text=payload.text.strip(),
        type=payload.type.strip(),
        required=payload.required,
        meta=payload.meta,
        weight=payload.weight,
        require_photo=payload.require_photo,
        require_comment=payload.require_comment,
        section_id=payload.section_id,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return ChecklistQuestionRead(
        id=question.id,
        text=question.text,
        type=question.type,
        order=question.order,
        required=question.required,
        meta=question.meta,
        weight=question.weight,
        require_photo=question.require_photo,
        require_comment=question.require_comment,
        section_id=question.section_id,
    )


@router.patch("/{checklist_id}/questions/{question_id}", response_model=ChecklistQuestionRead)
def update_question(
    checklist_id: int,
    question_id: int,
    payload: ChecklistQuestionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_manage_access(current_user)
    question: ChecklistQuestion | None = (
        _apply_company_scope(db.query(ChecklistQuestion).join(Checklist), current_user)
        .filter(ChecklistQuestion.id == question_id, ChecklistQuestion.checklist_id == checklist_id)
        .first()
    )
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    checklist_for_edit: Checklist | None = db.query(Checklist).filter(Checklist.id == question.checklist_id).first()
    if not checklist_for_edit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found")
    _ensure_checklist_edit_access(current_user, checklist_for_edit)

    if payload.text is not None:
        question.text = payload.text.strip()
    if payload.type is not None:
        question.type = payload.type.strip()
    if payload.order is not None:
        question.order = payload.order
    if payload.required is not None:
        question.required = payload.required
    if payload.meta is not None:
        question.meta = payload.meta
    if payload.weight is not None:
        question.weight = payload.weight
    if payload.require_photo is not None:
        question.require_photo = payload.require_photo
    if payload.require_comment is not None:
        question.require_comment = payload.require_comment
    if payload.section_id is not None:
        question.section_id = payload.section_id

    db.commit()
    db.refresh(question)
    return ChecklistQuestionRead(
        id=question.id,
        text=question.text,
        type=question.type,
        order=question.order,
        required=question.required,
        meta=question.meta,
        weight=question.weight,
        require_photo=question.require_photo,
        require_comment=question.require_comment,
        section_id=question.section_id,
    )


@router.delete("/{checklist_id}/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    checklist_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_manage_access(current_user)
    question: ChecklistQuestion | None = (
        _apply_company_scope(db.query(ChecklistQuestion).join(Checklist), current_user)
        .filter(ChecklistQuestion.id == question_id, ChecklistQuestion.checklist_id == checklist_id)
        .first()
    )
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    checklist_for_edit: Checklist | None = db.query(Checklist).filter(Checklist.id == question.checklist_id).first()
    if not checklist_for_edit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found")
    _ensure_checklist_edit_access(current_user, checklist_for_edit)
    db.delete(question)
    db.commit()
    return None


@router.get("/reports/summary", response_model=List[ChecklistReportSummaryItem])
def report_summary(
    checklist_id: Optional[int] = None,
    checklist_ids: Optional[List[int]] = Query(None),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    department: Optional[str] = None,
    departments: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_manage_access(current_user)
    base = (
        _apply_company_scope(db.query(Checklist), current_user)
        .join(ChecklistAnswer, ChecklistAnswer.checklist_id == Checklist.id)
        .filter(ChecklistAnswer.submitted_at.isnot(None))
    )
    checklist_filter: List[int] = []
    if checklist_id:
        checklist_filter.append(checklist_id)
    if checklist_ids:
        checklist_filter.extend(checklist_ids)
    if checklist_filter:
        base = base.filter(Checklist.id.in_(set(checklist_filter)))
    dept_filter: List[str] = []
    if department:
        dept_filter.append(department)
    if departments:
        dept_filter.extend([d for d in departments if d])
    if dept_filter:
        base = base.filter(ChecklistAnswer.department.in_(set(dept_filter)))
    base = _apply_date_range(base, date_from, date_to)

    rows = (
        base.with_entities(
            Checklist.id.label("checklist_id"),
            Checklist.name.label("checklist_name"),
            func.count(ChecklistAnswer.id).label("total_completed"),
            func.max(ChecklistAnswer.submitted_at).label("last_submitted_at"),
        )
        .group_by(Checklist.id, Checklist.name)
        .order_by(Checklist.name.asc())
        .all()
    )
    return [
        ChecklistReportSummaryItem(
            checklist_id=row.checklist_id,
            checklist_name=row.checklist_name,
            total_completed=row.total_completed,
            last_submitted_at=row.last_submitted_at,
        )
        for row in rows
    ]


@router.get("/reports/attempts", response_model=ChecklistAttemptListResponse)
def report_attempts(
    checklist_id: Optional[int] = None,
    checklist_ids: Optional[List[int]] = Query(None),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    department: Optional[str] = None,
    departments: Optional[List[str]] = Query(None),
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_manage_access(current_user)
    base = (
        _apply_company_scope(db.query(Checklist), current_user)
        .join(ChecklistAnswer, ChecklistAnswer.checklist_id == Checklist.id)
        .join(User, User.id == ChecklistAnswer.user_id)
        .filter(ChecklistAnswer.submitted_at.isnot(None))
    )
    checklist_filter: List[int] = []
    if checklist_id:
        checklist_filter.append(checklist_id)
    if checklist_ids:
        checklist_filter.extend(checklist_ids)
    if checklist_filter:
        base = base.filter(Checklist.id.in_(set(checklist_filter)))
    dept_filter: List[str] = []
    if department:
        dept_filter.append(department)
    if departments:
        dept_filter.extend([d for d in departments if d])
    if dept_filter:
        base = base.filter(ChecklistAnswer.department.in_(set(dept_filter)))
    base = _apply_date_range(base, date_from, date_to)

    total = base.with_entities(func.count(ChecklistAnswer.id)).scalar() or 0

    rows = (
        base.with_entities(
            ChecklistAnswer.id.label("id"),
            Checklist.id.label("checklist_id"),
            Checklist.name.label("checklist_name"),
            User.id.label("user_id"),
            User.first_name,
            User.last_name,
            User.middle_name,
            User.username,
            ChecklistAnswer.department,
            ChecklistAnswer.submitted_at,
        )
        .order_by(ChecklistAnswer.submitted_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    attempt_scores = get_attempt_scores_map([int(row.id) for row in rows if getattr(row, "id", None) is not None])
    items: List[ChecklistAttemptListItem] = []

    def _fmt_num(value: float | None) -> str:
        if value is None:
            return ""
        return ("{:.2f}".format(float(value))).rstrip("0").rstrip(".")

    for row in rows:
        parts = [row.last_name, row.first_name, row.middle_name]
        cleaned = [p.strip() for p in parts if p and p.strip()]
        user_name = " ".join(cleaned) if cleaned else (row.username or "Сотрудник")
        is_scored = False
        total_score = None
        total_max = None
        percent = None
        result = None
        score_data = attempt_scores.get(int(row.id))
        if score_data:
            is_scored = bool(score_data.is_scored)
            total_score = score_data.total_score
            total_max = score_data.total_max
            percent = score_data.percent
            if is_scored and total_score is not None and total_max is not None:
                result = f"{_fmt_num(total_score)} / {_fmt_num(total_max)}"
                if percent is not None:
                    result = f"{result} ({_fmt_num(percent)}%)"
        items.append(
            ChecklistAttemptListItem(
                id=row.id,
                checklist_id=row.checklist_id,
                checklist_name=row.checklist_name,
                user_id=row.user_id,
                user_name=user_name,
                department=row.department,
                is_scored=is_scored,
                total_score=total_score,
                total_max=total_max,
                percent=percent,
                result=result,
                submitted_at=row.submitted_at,
            )
        )
    return ChecklistAttemptListResponse(items=items, total=int(total))


@router.get("/reports/metrics", response_model=ChecklistReportMetrics)
def report_metrics(
    checklist_id: Optional[int] = None,
    checklist_ids: Optional[List[int]] = Query(None),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    department: Optional[str] = None,
    departments: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_manage_access(current_user)
    base = (
        _apply_company_scope(db.query(Checklist), current_user)
        .join(ChecklistAnswer, ChecklistAnswer.checklist_id == Checklist.id)
        .filter(ChecklistAnswer.submitted_at.isnot(None))
    )
    checklist_filter: List[int] = []
    if checklist_id:
        checklist_filter.append(checklist_id)
    if checklist_ids:
        checklist_filter.extend(checklist_ids)
    if checklist_filter:
        base = base.filter(Checklist.id.in_(set(checklist_filter)))
    base = _apply_date_range(base, date_from, date_to)

    dept_base = base
    dept_filter: List[str] = []
    if department:
        dept_filter.append(department)
    if departments:
        dept_filter.extend([d for d in departments if d])
    if dept_filter:
        base = base.filter(ChecklistAnswer.department.in_(set(dept_filter)))

    dept_rows = (
        dept_base.with_entities(ChecklistAnswer.department)
        .distinct()
        .order_by(ChecklistAnswer.department.asc())
        .all()
    )
    department_list = [row.department for row in dept_rows if row.department]

    day_expr = func.date_trunc("day", func.timezone("Europe/Moscow", ChecklistAnswer.submitted_at))
    day_rows = (
        base.with_entities(day_expr.label("day"), func.count(ChecklistAnswer.id).label("total"))
        .group_by(day_expr)
        .order_by(day_expr)
        .all()
    )
    daily_counts = [
        ChecklistReportDailyCount(date=row.day.date(), total=int(row.total or 0)) for row in day_rows
    ]

    scored_rows = (
        base.filter(Checklist.is_scored.is_(True))
        .with_entities(ChecklistAnswer.id)
        .order_by(ChecklistAnswer.id.asc())
        .all()
    )
    score_map = get_attempt_scores_map([int(row.id) for row in scored_rows if getattr(row, "id", None) is not None])
    percents: List[float] = [
        float(data.percent)
        for data in score_map.values()
        if data.percent is not None
    ]
    avg_percent = round(sum(percents) / len(percents), 2) if percents else None

    return ChecklistReportMetrics(
        daily_counts=daily_counts,
        average_scored_percent=avg_percent,
        scored_total=len(percents),
        departments=department_list,
    )


@router.post("/portal/login/start", response_model=ChecklistPortalLoginStartResponse)
def portal_login_start(payload: ChecklistPortalLoginStartRequest, db: Session = Depends(get_db)):
    user = _portal_get_user_by_staff_code(db, payload.staff_code)
    if _portal_requires_password_step(db, user):
        return ChecklistPortalLoginStartResponse(
            requires_credentials=True,
            username_hint=(user.username or "").strip() or None,
        )

    token = create_jwt_token(user.id)
    return ChecklistPortalLoginStartResponse(
        requires_credentials=False,
        access_token=token,
        user=_portal_user_payload(user),
    )


@router.post("/portal/login/finish", response_model=ChecklistPortalLoginResponse)
def portal_login_finish(payload: ChecklistPortalLoginFinishRequest, db: Session = Depends(get_db)):
    user = _portal_get_user_by_staff_code(db, payload.staff_code)
    if not _portal_requires_password_step(db, user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для этого сотрудника дополнительная авторизация не требуется",
        )

    username = (payload.username or "").strip()
    password = payload.password or ""
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Введите логин и пароль",
        )
    if username != (user.username or "").strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")

    token = create_jwt_token(user.id)
    return ChecklistPortalLoginResponse(
        access_token=token,
        user=_portal_user_payload(user),
    )


@router.get("/portal/me", response_model=ChecklistPortalUser)
def portal_me(current_user: User = Depends(get_current_user)):
    return _portal_user_payload(current_user)


@router.get("/portal/checklists", response_model=List[ChecklistPortalChecklistItem])
def portal_checklists(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = current_user
    if not user.position_id:
        return []
    position: Position | None = db.query(Position).get(user.position_id)  # type: ignore[arg-type]
    if not position:
        return []

    items: List[ChecklistPortalChecklistItem] = []
    for checklist in (position.checklists or []):
        if not _portal_checklist_allowed(db, user, checklist):
            continue
        has_control = bool(_portal_resolve_control_objects(db, user, checklist))
        items.append(
            ChecklistPortalChecklistItem(
                id=checklist.id,
                name=checklist.name,
                description=getattr(checklist, "description", None),
                is_scored=bool(checklist.is_scored),
                has_control_objects=has_control,
            )
        )
    return items


@router.get("/portal/checklists/{checklist_id}", response_model=ChecklistPortalChecklistDetail)
def portal_checklist_detail(
    checklist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    checklist: Checklist | None = (
        db.query(Checklist)
        .options(selectinload(Checklist.sections))
        .filter(Checklist.id == checklist_id)
        .first()
    )
    if not checklist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found")
    if not _portal_checklist_allowed(db, current_user, checklist):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    sections = [
        ChecklistPortalSection(id=s.id, name=s.name, order=s.order)
        for s in (checklist.sections or [])
    ]
    question_rows = (
        db.query(ChecklistQuestion)
        .filter(ChecklistQuestion.checklist_id == checklist_id)
        .order_by(ChecklistQuestion.order.asc())
        .all()
    )
    questions = []
    for q in question_rows:
        section_title = None
        if q.section_id:
            for section in sections:
                if section.id == q.section_id:
                    section_title = section.name
                    break
        questions.append(
            ChecklistPortalQuestion(
                id=q.id,
                text=q.text,
                type=q.type,
                order=q.order,
                required=bool(q.required),
                meta=q.meta,
                section_id=q.section_id,
                section_title=section_title,
                require_photo=bool(getattr(q, "require_photo", False)),
                require_comment=bool(getattr(q, "require_comment", False)),
            )
        )
    return ChecklistPortalChecklistDetail(
        id=checklist.id,
        name=checklist.name,
        description=getattr(checklist, "description", None),
        is_scored=bool(checklist.is_scored),
        sections=sections,
        questions=questions,
    )


@router.get("/portal/checklists/{checklist_id}/control-objects", response_model=List[str])
def portal_control_objects(
    checklist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    checklist: Checklist | None = db.query(Checklist).get(checklist_id)  # type: ignore[arg-type]
    if not checklist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found")
    if not _portal_checklist_allowed(db, current_user, checklist):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    return _portal_resolve_control_objects(db, current_user, checklist)


def _build_portal_draft_response(draft: ChecklistDraft) -> ChecklistPortalDraftResponse:
    answers: List[ChecklistPortalDraftAnswer] = []
    for item in (draft.answers or []):
        url = None
        if item.photo_path:
            try:
                url = s3_service.generate_presigned_url_for_checklist(item.photo_path)
            except Exception:
                url = None
        answers.append(
            ChecklistPortalDraftAnswer(
                question_id=item.question_id,
                response_value=item.response_value,
                comment=item.comment,
                photo_path=item.photo_path,
                photo_url=url,
            )
        )
    return ChecklistPortalDraftResponse(
        checklist_id=draft.checklist_id,
        department=draft.department,
        answers=answers,
    )


@router.get("/portal/checklists/{checklist_id}/draft", response_model=ChecklistPortalDraftResponse)
def portal_get_draft(
    checklist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    checklist: Checklist | None = db.query(Checklist).get(checklist_id)  # type: ignore[arg-type]
    if not checklist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found")
    if not _portal_checklist_allowed(db, current_user, checklist):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    draft: ChecklistDraft | None = (
        db.query(ChecklistDraft)
        .options(selectinload(ChecklistDraft.answers))
        .filter(ChecklistDraft.checklist_id == checklist_id, ChecklistDraft.user_id == current_user.id)
        .first()
    )
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    return _build_portal_draft_response(draft)


@router.post("/portal/checklists/{checklist_id}/draft", response_model=ChecklistPortalDraftResponse)
def portal_save_draft(
    checklist_id: int,
    payload: ChecklistPortalDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    checklist: Checklist | None = db.query(Checklist).get(checklist_id)  # type: ignore[arg-type]
    if not checklist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found")
    if not _portal_checklist_allowed(db, current_user, checklist):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    now = datetime.utcnow()
    draft: ChecklistDraft | None = (
        db.query(ChecklistDraft)
        .options(selectinload(ChecklistDraft.answers))
        .filter(ChecklistDraft.checklist_id == checklist_id, ChecklistDraft.user_id == current_user.id)
        .first()
    )
    if not draft:
        draft = ChecklistDraft(
            checklist_id=checklist_id,
            user_id=current_user.id,
            started_at=now,
            updated_at=now,
            department=payload.department,
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)
    else:
        draft.department = payload.department
        draft.updated_at = now

    existing = {item.question_id: item for item in (draft.answers or [])}
    for item in payload.answers:
        if item.question_id in existing:
            row = existing[item.question_id]
            row.response_value = item.response_value
            row.comment = item.comment
            row.photo_path = item.photo_path
            row.updated_at = now
        else:
            db.add(
                ChecklistDraftAnswer(
                    draft_id=draft.id,
                    question_id=item.question_id,
                    response_value=item.response_value,
                    comment=item.comment,
                    photo_path=item.photo_path,
                    updated_at=now,
                )
            )
    db.commit()
    db.refresh(draft)
    return _build_portal_draft_response(draft)


@router.delete("/portal/checklists/{checklist_id}/draft", status_code=status.HTTP_204_NO_CONTENT)
def portal_delete_draft(
    checklist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    checklist: Checklist | None = db.query(Checklist).get(checklist_id)  # type: ignore[arg-type]
    if not checklist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found")
    if not _portal_checklist_allowed(db, current_user, checklist):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    draft: ChecklistDraft | None = (
        db.query(ChecklistDraft)
        .filter(ChecklistDraft.checklist_id == checklist_id, ChecklistDraft.user_id == current_user.id)
        .first()
    )
    if draft:
        db.delete(draft)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/portal/attempts", response_model=ChecklistPortalSubmitResponse)
def portal_submit_attempt(
    payload: ChecklistPortalSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    checklist: Checklist | None = db.query(Checklist).get(payload.checklist_id)  # type: ignore[arg-type]
    if not checklist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found")
    if not _portal_checklist_allowed(db, current_user, checklist):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    draft = (
        db.query(ChecklistDraft)
        .filter(ChecklistDraft.checklist_id == checklist.id, ChecklistDraft.user_id == current_user.id)
        .first()
    )
    started_at = draft.started_at if draft else datetime.utcnow()

    attempt = ChecklistAnswer(
        checklist_id=checklist.id,
        user_id=current_user.id,
        department=(payload.department or None),
        started_at=started_at,
        submitted_at=datetime.utcnow(),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    answers = []
    for item in payload.answers:
        answers.append(
            ChecklistQuestionAnswer(
                answer_id=attempt.id,
                question_id=item.question_id,
                response_value=item.response_value,
                comment=item.comment,
                photo_path=item.photo_path,
                created_at=datetime.utcnow(),
            )
        )
    if answers:
        db.add_all(answers)
        db.commit()

    if draft:
        db.delete(draft)
        db.commit()

    return ChecklistPortalSubmitResponse(attempt_id=attempt.id)


@router.post("/portal/photos", response_model=ChecklistPortalUploadResponse)
def portal_upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    content = file.file.read()
    ext = os.path.splitext(file.filename or "photo.jpg")[-1].lower() or ".jpg"
    key = f"checklists/portal/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}{ext}"
    s3_service.upload_bytes_to_bucket(key, content, content_type=file.content_type, bucket=s3_service.S3_CHECKLIST_BUCKET)
    raw = f"s3://{s3_service.S3_CHECKLIST_BUCKET}/{key}"
    try:
        url = s3_service.generate_presigned_url_for_checklist(raw)
    except Exception:
        url = None
    return ChecklistPortalUploadResponse(photo_path=raw, url=url)


@router.get("/portal/attempts/{attempt_id}/export")
def portal_export_attempt(
    attempt_id: int,
    format: str = Query("pdf", pattern="^(pdf|xlsx)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attempt: ChecklistAnswer | None = (
        db.query(ChecklistAnswer)
        .filter(ChecklistAnswer.id == attempt_id, ChecklistAnswer.user_id == current_user.id)
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    checklist: Checklist | None = db.query(Checklist).get(attempt.checklist_id)  # type: ignore[arg-type]
    if not checklist or not _portal_checklist_allowed(db, current_user, checklist):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    data = get_attempt_data(attempt_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    pdf_path, xlsx_path = export_attempt_to_files(tmp_dir=None, data=data)
    if format == "pdf":
        return FileResponse(pdf_path, media_type="application/pdf", filename=os.path.basename(pdf_path))
    return FileResponse(
        xlsx_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(xlsx_path),
    )


@router.get("/portal/attempts/{attempt_id}", response_model=ChecklistPortalAttemptSummary)
def portal_attempt_summary(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attempt = (
        db.query(ChecklistAnswer)
        .join(Checklist, ChecklistAnswer.checklist_id == Checklist.id)
        .join(User, User.id == ChecklistAnswer.user_id)
        .filter(ChecklistAnswer.id == attempt_id, ChecklistAnswer.user_id == current_user.id)
        .with_entities(
            ChecklistAnswer.id.label("id"),
            ChecklistAnswer.started_at,
            ChecklistAnswer.submitted_at,
            ChecklistAnswer.department,
            Checklist.id.label("checklist_id"),
            Checklist.name.label("checklist_name"),
            User.first_name,
            User.last_name,
            User.middle_name,
            User.username,
        )
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    checklist: Checklist | None = db.query(Checklist).get(attempt.checklist_id)  # type: ignore[arg-type]
    if not checklist or not _portal_checklist_allowed(db, current_user, checklist):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    data = get_attempt_data(attempt_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    parts = [attempt.last_name, attempt.first_name, attempt.middle_name]
    cleaned = [p.strip() for p in parts if p and p.strip()]
    user_name = " ".join(cleaned) if cleaned else (attempt.username or "Сотрудник")
    result_text = format_attempt_result(data, include_unscored=True)

    return ChecklistPortalAttemptSummary(
        attempt_id=attempt.id,
        checklist_name=attempt.checklist_name,
        user_name=user_name,
        department=attempt.department,
        started_at=format_moscow(attempt.started_at, "%Y-%m-%d %H:%M") if attempt.started_at else None,
        submitted_at=format_moscow(attempt.submitted_at, "%Y-%m-%d %H:%M") if attempt.submitted_at else None,
        result_text=result_text,
        is_scored=bool(data.is_scored),
        total_score=data.total_score,
        total_max=data.total_max,
        percent=data.percent,
    )


@router.get("/reports/attempts/{attempt_id}", response_model=ChecklistAttemptDetail)
def report_attempt_detail(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_manage_access(current_user)

    attempt = (
        _apply_company_scope(db.query(Checklist), current_user)
        .join(ChecklistAnswer, ChecklistAnswer.checklist_id == Checklist.id)
        .join(User, User.id == ChecklistAnswer.user_id)
        .filter(ChecklistAnswer.id == attempt_id)
        .with_entities(
            ChecklistAnswer.id.label("id"),
            Checklist.id.label("checklist_id"),
            Checklist.name.label("checklist_name"),
            User.id.label("user_id"),
            User.first_name,
            User.last_name,
            User.middle_name,
            User.username,
            ChecklistAnswer.department,
            ChecklistAnswer.submitted_at,
        )
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    parts = [attempt.last_name, attempt.first_name, attempt.middle_name]
    cleaned = [p.strip() for p in parts if p and p.strip()]
    user_name = " ".join(cleaned) if cleaned else (attempt.username or "Сотрудник")

    answers_rows = (
        db.query(
            ChecklistQuestionAnswer.question_id,
            ChecklistQuestion.text,
            ChecklistQuestion.type,
            ChecklistSection.name.label("section_title"),
            ChecklistQuestionAnswer.response_value,
            ChecklistQuestionAnswer.comment,
            ChecklistQuestionAnswer.photo_path,
        )
        .join(ChecklistQuestion, ChecklistQuestion.id == ChecklistQuestionAnswer.question_id)
        .outerjoin(ChecklistSection, ChecklistSection.id == ChecklistQuestion.section_id)
        .filter(ChecklistQuestionAnswer.answer_id == attempt_id)
        .order_by(ChecklistQuestion.order.asc(), ChecklistQuestion.id.asc())
        .all()
    )

    answers = [
        ChecklistAttemptAnswer(
            question_id=row.question_id,
            question_text=row.text,
            question_type=row.type,
            section_title=row.section_title,
            response_value=row.response_value,
            comment=row.comment,
            photo_path=_resolve_photo_path(row.photo_path),
        )
        for row in answers_rows
    ]
    result_text = None
    try:
        data = get_attempt_data(attempt_id)
        if data:
            result_text = format_attempt_result(data, include_unscored=True)
    except Exception:
        result_text = None

    return ChecklistAttemptDetail(
        id=attempt.id,
        checklist_id=attempt.checklist_id,
        checklist_name=attempt.checklist_name,
        user_id=attempt.user_id,
        user_name=user_name,
        department=attempt.department,
        result=result_text,
        submitted_at=attempt.submitted_at,
        answers=answers,
    )


def _resolve_photo_path(raw: str | None) -> str | None:
    if not raw:
        return None
    value = raw.strip()
    if value.startswith("s3://"):
        try:
            return s3_service.generate_presigned_url_for_checklist(value)
        except Exception:
            return None
    return value


@router.get("/reports/attempts/{attempt_id}/export")
def export_attempt(
    attempt_id: int,
    format: str = Query("pdf", pattern="^(pdf|xlsx)$"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_manage_access(current_user)
    attempt = (
        _apply_company_scope(db.query(Checklist), current_user)
        .join(ChecklistAnswer, ChecklistAnswer.checklist_id == Checklist.id)
        .filter(ChecklistAnswer.id == attempt_id)
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    data = get_attempt_data(attempt_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    pdf_path, xlsx_path = export_attempt_to_files(tmp_dir=None, data=data)
    if format == "pdf":
        return FileResponse(pdf_path, media_type="application/pdf", filename=os.path.basename(pdf_path))
    return FileResponse(
        xlsx_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(xlsx_path),
    )


@router.delete("/reports/attempts/{attempt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_manage_access(current_user)
    attempt = (
        _apply_company_scope(db.query(Checklist), current_user)
        .join(ChecklistAnswer, ChecklistAnswer.checklist_id == Checklist.id)
        .filter(ChecklistAnswer.id == attempt_id)
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    db.query(ChecklistQuestionAnswer).filter(ChecklistQuestionAnswer.answer_id == attempt_id).delete()
    db.delete(attempt)
    db.commit()
    return None
