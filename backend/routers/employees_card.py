# backend/routers/employees_card.py
from __future__ import annotations

import logging
from urllib.parse import urlparse
import os
from datetime import date, datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from backend.services.s3 import generate_presigned_url
from sqlalchemy.orm import Session, joinedload, selectinload, load_only, noload
from sqlalchemy import and_, or_, func

from backend.bd.database import get_db
from backend.bd.models import User, Attendance, Position, Role, user_restaurants, MedicalCheckRecord, CisDocumentRecord
from backend.schemas import (
		EmployeeListItem, EmployeeListResponse, EmployeeCardPublic,
				AttendancePublic, AttendanceRangeResponse,
								AttendanceManualCreate, AttendanceManualUpdate, AttendanceRecalculateNightRequest,
								MedicalCheckTypeRead, MedicalCheckRecordPublic,
								CisDocumentTypeRead, CisDocumentRecordPublic,
)

logger = logging.getLogger(__name__)
from backend.services.attendance_calculations import (
		combine_date_time,
		calc_duration_minutes,
		calc_night_minutes,
        calc_attendance_pay,
)
from backend.services.payroll_recalc import recalc_salary_for_user_month
from backend.services.employee_changes import log_employee_changes

# --- используем вашу зависимость, если она есть ---
try:
	from backend.utils import get_current_user, get_user_restaurant_ids, users_share_restaurant, today_local
	from backend.services.permissions import (
		PermissionCode,
		ensure_permissions,
		has_permission,
		can_manage_user,
		ensure_can_manage_user,
		can_view_rate,
	)
except Exception:
	# fallback (на случай отсутствия)
	# fallback (на случай отсутствия)
	from fastapi.security import OAuth2PasswordBearer
	from jose import jwt, JWTError
	oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
	SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME")
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

	def today_local():
		return date.today()

	def get_user_restaurant_ids(db: Session, user: User):
		return None

	def users_share_restaurant(db: Session, viewer: User, target_user_id: int) -> bool:
		return viewer.id == target_user_id

	class PermissionCode:
		STAFF_VIEW_SENSITIVE = "staff.view_sensitive"
		STAFF_MANAGE_SUBORDINATES = "staff.manage_subordinates"
		STAFF_MANAGE_ALL = "staff.manage_all"

	def ensure_permissions(user: User, *codes: str) -> None:
		return

	def has_permission(user: User, code: str) -> bool:
		return True

	def can_manage_user(viewer: User, target: User) -> bool:
		return True

	def ensure_can_manage_user(viewer: User, target: User) -> None:
		return

	def can_view_rate(viewer: User, target: User) -> bool:
		return True

router = APIRouter(prefix="/employees", tags=["Employees"])

# -------------------------
# Helpers
# -------------------------
def _month_bounds(d: date) -> tuple[date, date]:
	start = date(d.year, d.month, 1)
	if d.month == 12:
		end = date(d.year + 1, 1, 1) - timedelta(days=1)
	else:
		end = date(d.year, d.month + 1, 1) - timedelta(days=1)
	return start, end

def _to_list_item(u: User) -> EmployeeListItem:
	return EmployeeListItem(
		id=u.id,
		username=u.username,
		first_name=u.first_name,
		last_name=u.last_name,
		staff_code=u.staff_code,
		gender=u.gender,
		role_id=u.role_id,
		role_name=(u.role.name if u.role else None),
		position_id=u.position_id,
		position_name=(u.position.name if u.position else None),
		position_rate=float(u.position.rate) if u.position and u.position.rate is not None else None,
		fired=bool(u.fired),
	)

def _medical_record_to_public(record: MedicalCheckRecord) -> MedicalCheckRecordPublic:
	# Build the schema explicitly to avoid missing relationship attributes during validation.
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


def _resolve_attachment_url(value: str | None) -> str | None:
        if not value:
                return None
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https"}:
                return value
        try:
                return generate_presigned_url(value)
        except Exception:  # noqa: BLE001
                logger.warning("Failed to generate attachment URL for employee card", exc_info=True)
                return value


def _to_card(u: User, viewer: Optional[User] = None) -> EmployeeCardPublic:
    can_see_rate = can_view_rate(viewer, u) if viewer else True
    medical_records = sorted(
        u.medical_check_records or [],
        key=lambda record: record.passed_at or date.min,
        reverse=True,
    )
    cis_docs = sorted(
        u.cis_document_records or [],
        key=lambda record: record.issued_at or date.min,
        reverse=True,
    )
    photo_url = None
    if u.photo_key:
        try:
            photo_url = generate_presigned_url(u.photo_key)
        except Exception:
            logger.warning("Failed to build photo URL for user %s", u.id, exc_info=True)
            photo_url = None

    return EmployeeCardPublic(
        id=u.id,
        username=u.username,
        first_name=u.first_name,
        last_name=u.last_name,
        middle_name=u.middle_name,
        iiko_code=u.iiko_code,
        iiko_id=u.iiko_id,
        company_id=(u.company.id if u.company else None),
        company_name=(u.company.name if u.company else None),
        role_id=u.role_id,
        role_name=(u.role.name if u.role else None),
        position_id=u.position_id,
        position_name=(u.position.name if u.position else None),
        rate=float(u.rate) if can_see_rate and u.rate is not None else None,
        hire_date=u.hire_date,
        fire_date=u.fire_date,
        fired=bool(u.fired),
        staff_code=u.staff_code,
        gender=u.gender,
        phone_number=u.phone_number,
        email=u.email,
        birth_date=u.birth_date,
        photo_key=u.photo_key,
        photo_url=photo_url,
        is_cis_employee=bool(getattr(u, "is_cis_employee", False)),
        confidential_data_consent=bool(getattr(u, "confidential_data_consent", False)),
        is_formalized=bool(getattr(u, "is_formalized", False)),
        workplace_restaurant_id=getattr(u, "workplace_restaurant_id", None),
        individual_rate=float(u.individual_rate) if can_see_rate and u.individual_rate is not None else None,
        medical_checks=[_medical_record_to_public(record) for record in medical_records],
        cis_documents=[_cis_record_to_public(record) for record in cis_docs],
        has_fingerprint=bool(getattr(u, "has_fingerprint", False)),
        rate_hidden=not can_see_rate,
    )

def _attendance_to_public(
		a: Attendance,
		viewer: Optional[User] = None,
		target: Optional[User] = None,
) -> AttendancePublic:
	can_see_rate = True
	if viewer is not None and target is not None:
		can_see_rate = can_view_rate(viewer, target)
	return AttendancePublic(
		id=a.id,
		user_id=a.user_id,
		position_id=a.position_id,
		position_name=(a.position.name if a.position else None),
		restaurant_id=a.restaurant_id,
		restaurant_name=(a.restaurant.name if a.restaurant else None),
		rate=float(a.rate) if can_see_rate and a.rate is not None else None,
		pay_amount=float(a.pay_amount) if can_see_rate and a.pay_amount is not None else None,
		open_date=a.open_date,
		open_time=a.open_time,
		close_date=a.close_date,
		close_time=a.close_time,
		duration_minutes=a.duration_minutes,
		night_minutes=a.night_minutes or 0,
	)


def _ensure_close_after_open(opened_dt: datetime, closed_dt: datetime) -> None:
	if closed_dt < opened_dt:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="время закрытия должно быть позже времени открытия")


def _apply_close_stats(a: Attendance, opened_dt: datetime, closed_dt: datetime) -> None:
	_ensure_close_after_open(opened_dt, closed_dt)
	a.duration_minutes = calc_duration_minutes(opened_dt, closed_dt)
	a.night_minutes = calc_night_minutes(opened_dt, closed_dt)

def _calculate_and_set_pay(db: Session, attendance: Attendance) -> None:
	position = attendance.position or (db.query(Position).get(attendance.position_id) if attendance.position_id else None)
	payment_format = getattr(position, "payment_format", None)
	calc_mode = getattr(payment_format, "calculation_mode", None) if payment_format else None
	hours_per_shift = getattr(position, "hours_per_shift", None) if position else None
	monthly_shift_norm = getattr(position, "monthly_shift_norm", None) if position else None
	night_bonus_enabled = bool(getattr(position, "night_bonus_enabled", False)) if position else False
	night_bonus_percent = getattr(position, "night_bonus_percent", None) if position else None

	attendance.pay_amount = calc_attendance_pay(
		rate=attendance.rate,
		calculation_mode=calc_mode,
		duration_minutes=attendance.duration_minutes,
		night_minutes=attendance.night_minutes,
		hours_per_shift=hours_per_shift,
		monthly_shift_norm=monthly_shift_norm,
		night_bonus_enabled=night_bonus_enabled,
		night_bonus_percent=night_bonus_percent,
	)


def _att_range_condition(date_from: date, date_to: date):
	# берём смены по дате открытия (open_date) в диапазоне [date_from, date_to]
	return and_(
		Attendance.open_date >= date_from,
		Attendance.open_date <= date_to,
	)

def _format_value(value):
	if value is None:
		return None
	if hasattr(value, "isoformat"):
		return value.isoformat()
	return str(value)

def _attendance_summary(attendance: Attendance) -> dict:
	return {
		"attendance_id": attendance.id,
		"open_date": _format_value(attendance.open_date),
		"open_time": _format_value(attendance.open_time),
		"close_date": _format_value(attendance.close_date),
		"close_time": _format_value(attendance.close_time),
		"restaurant_id": attendance.restaurant_id,
		"position_id": attendance.position_id,
		"rate": _format_value(attendance.rate),
		"pay_amount": _format_value(attendance.pay_amount),
		"duration_minutes": attendance.duration_minutes,
		"night_minutes": attendance.night_minutes,
	}

def _attendance_intervals_overlap(
	start_a: datetime,
	end_a: Optional[datetime],
	start_b: datetime,
	end_b: Optional[datetime],
) -> bool:
	end_a_cmp = end_a if end_a is not None else datetime.max
	end_b_cmp = end_b if end_b is not None else datetime.max
	return start_a <= end_b_cmp and start_b <= end_a_cmp

def _find_attendance_overlap(
	db: Session,
	user_id: int,
	start_dt: datetime,
	end_dt: Optional[datetime],
	exclude_attendance_id: Optional[int] = None,
) -> Optional[Attendance]:
	start_date = start_dt.date()
	end_date = end_dt.date() if end_dt else start_dt.date()
	query = (
		db.query(Attendance)
		  .filter(
			  Attendance.user_id == user_id,
			  Attendance.open_date <= end_date,
			  or_(Attendance.close_date.is_(None), Attendance.close_date >= start_date),
		  )
	)
	if exclude_attendance_id is not None:
		query = query.filter(Attendance.id != exclude_attendance_id)
	candidates = query.all()
	for attendance in candidates:
		a_start = combine_date_time(attendance.open_date, attendance.open_time)
		a_end = None
		if attendance.close_date and attendance.close_time:
			a_end = combine_date_time(attendance.close_date, attendance.close_time)
		if _attendance_intervals_overlap(start_dt, end_dt, a_start, a_end):
			return attendance
	return None

def _ensure_staff_view(user: User) -> None:
	ensure_permissions(
		user,
		PermissionCode.STAFF_VIEW_SENSITIVE,
		PermissionCode.STAFF_MANAGE_SUBORDINATES,
		PermissionCode.STAFF_MANAGE_ALL,
		PermissionCode.STAFF_EMPLOYEES_VIEW,
		PermissionCode.EMPLOYEES_CARD_VIEW,
	)

def _ensure_can_edit_user(db: Session, viewer: User, target: User) -> None:
	if viewer.id == target.id:
		if has_permission(viewer, PermissionCode.STAFF_MANAGE_ALL):
			return
		if has_permission(viewer, PermissionCode.STAFF_MANAGE_SUBORDINATES):
			return
		if (
			has_permission(viewer, PermissionCode.EMPLOYEES_CARD_MANAGE)
			or has_permission(viewer, PermissionCode.STAFF_EMPLOYEES_MANAGE)
		):
			return
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Access denied: insufficient permissions to modify employee card",
		)
	if has_permission(viewer, PermissionCode.STAFF_MANAGE_ALL):
		return
	if has_permission(viewer, PermissionCode.STAFF_MANAGE_SUBORDINATES):
		ensure_can_manage_user(viewer, target)
		return
	if (
		has_permission(viewer, PermissionCode.EMPLOYEES_CARD_MANAGE)
		or has_permission(viewer, PermissionCode.STAFF_EMPLOYEES_MANAGE)
	) and users_share_restaurant(db, viewer, target.id):
		return
	raise HTTPException(
		status_code=status.HTTP_403_FORBIDDEN,
		detail="Access denied: insufficient permissions to modify employee card",
	)

def _check_permissions(db: Session, viewer: User, target_user_id: int) -> User:
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
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
	if viewer.id == target.id:
		return target
	_ensure_staff_view(viewer)
	if has_permission(viewer, PermissionCode.STAFF_MANAGE_ALL):
		return target
	if has_permission(viewer, PermissionCode.STAFF_MANAGE_SUBORDINATES) and can_manage_user(viewer, target):
		return target
	if users_share_restaurant(db, viewer, target.id):
		return target
	raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

# -------------------------
# 1) Список сотрудников (для выпадающего списка)
# -------------------------
@router.get("", response_model=EmployeeListResponse)
def list_employees(
	q: Optional[str] = Query(None, description="поиск: username/имя/фамилия/staff_code"),
	include_fired: bool = Query(False),
	limit: int = Query(50, ge=1, le=200),
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	_ensure_staff_view(current_user)
	qry = (
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
			  joinedload(User.position)
			      .load_only(Position.id, Position.name, Position.rate),
			  joinedload(User.position).noload(Position.permission_links),
			  joinedload(User.position).noload(Position.permissions),
			  joinedload(User.position).noload(Position.training_requirements),
		  )
	)
	if not include_fired:
		qry = qry.filter(User.fired == False)
	if q:
		like = f"%{q.lower()}%"
		qry = qry.filter(or_(
			func.lower(User.username).like(like),
			func.lower(func.coalesce(User.first_name, "")).like(like),
			func.lower(func.coalesce(User.last_name, "")).like(like),
			func.lower(func.coalesce(User.staff_code, "")).like(like),
		))

	allowed_restaurants = get_user_restaurant_ids(db, current_user)
	if allowed_restaurants is not None:
		if allowed_restaurants:
			shared_user_ids = (
				db.query(user_restaurants.c.user_id)
				  .filter(user_restaurants.c.restaurant_id.in_(allowed_restaurants))
			)
			qry = qry.filter(or_(User.id == current_user.id, User.id.in_(shared_user_ids)))
		else:
			qry = qry.filter(User.id == current_user.id)
	users = (
		qry
		  .order_by(
			func.lower(User.last_name).nullslast(),
			func.lower(User.first_name).nullslast(),
			User.id.asc(),
		  )
		  .limit(limit)
		  .all()
	)

	items: List[EmployeeListItem] = [_to_list_item(u) for u in users]
	return EmployeeListResponse(items=items)

# -------------------------
# 2) Карточка сотрудника (вкладка 1)
# -------------------------
@router.get("/{user_id}/card", response_model=EmployeeCardPublic)
def get_employee_card(
	user_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	_ = _check_permissions(db, current_user, user_id)

	u = (
		db.query(User)
		  .options(
			  joinedload(User.company),
			  joinedload(User.role),
			  joinedload(User.position).joinedload(Position.payment_format),
			  joinedload(User.position).joinedload(Position.restaurant_subdivision),
			  selectinload(User.medical_check_records).selectinload(MedicalCheckRecord.check_type),
			  selectinload(User.cis_document_records).selectinload(CisDocumentRecord.document_type),
		  )
		  .filter(User.id == user_id)
		  .first()
	)
	if not u:
		raise HTTPException(status_code=404, detail="User not found")
	return _to_card(u, current_user)

# -------------------------
# 3) Смены сотрудника (вкладка 2) — по умолчанию текущий месяц, но есть параметры периода
# -------------------------
@router.get("/{user_id}/attendances", response_model=AttendanceRangeResponse)
def get_employee_attendances(
	user_id: int,
	date_from: Optional[date] = Query(None),
	date_to: Optional[date] = Query(None),
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	target = _check_permissions(db, current_user, user_id)

	# если даты не заданы — текущий месяц
	if not date_from or not date_to:
		start, end = _month_bounds(date.today())
		date_from = date_from or start
		date_to = date_to or end
	if date_from > date_to:
		raise HTTPException(status_code=400, detail="date_from must be <= date_to")

	cond = _att_range_condition(date_from, date_to)

	qry = (
		db.query(Attendance)
		  .options(
			  joinedload(Attendance.position),
			  joinedload(Attendance.restaurant),
		  )
		  .filter(Attendance.user_id == user_id)
		  .filter(cond)
	)

	rows = (
		qry
		  .order_by(Attendance.open_date.asc(), Attendance.open_time.asc())
		  .all()
	)

	items = [_attendance_to_public(a, current_user, target) for a in rows]
	return AttendanceRangeResponse(items=items, date_from=date_from, date_to=date_to)

@router.post("/{user_id}/attendances", response_model=AttendancePublic, status_code=status.HTTP_201_CREATED)
def create_employee_attendance(
		user_id: int,
		payload: AttendanceManualCreate,
		db: Session = Depends(get_db),
		current_user: User = Depends(get_current_user),
):
		target = _check_permissions(db, current_user, user_id)
		_ensure_can_edit_user(db, current_user, target)
		can_edit_rate = can_view_rate(current_user, target)

		data = payload.model_dump()

		close_date = data.get("close_date")
		close_time = data.get("close_time")
		open_date = data.get("open_date")
		open_time = data.get("open_time")
		today = today_local()
		if open_date and open_date > today:
				raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя создавать смены в будущие даты")
		if close_date and close_date > today:
				raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя создавать смены в будущие даты")
		if (close_date is None) != (close_time is None):
				raise HTTPException(
						status_code=status.HTTP_400_BAD_REQUEST,
						detail="close date and time must be provided together",
				)

		opened_dt = combine_date_time(open_date, open_time)
		closed_dt = combine_date_time(close_date, close_time) if close_date and close_time else None
		conflict = _find_attendance_overlap(db, user_id, opened_dt, closed_dt)
		if conflict:
				raise HTTPException(
						status_code=status.HTTP_409_CONFLICT,
						detail=f"Смена пересекается с существующей (id={conflict.id})",
				)

		rate_value = data.get("rate") if can_edit_rate else target.rate
		attendance = Attendance(
				user_id=user_id,
				open_date=open_date,
				open_time=open_time,
				restaurant_id=data.get("restaurant_id"),
				rate=rate_value,
		)

		if "position_id" in data:
				pos_id = data.get("position_id")
				if pos_id is not None and not db.query(Position).get(pos_id):
						raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
				attendance.position_id = pos_id

		explicit_duration = data.get("duration_minutes") is not None
		explicit_night = data.get("night_minutes") is not None

		if close_date is not None and close_time is not None:
				attendance.close_date = close_date
				attendance.close_time = close_time
				opened_dt = combine_date_time(attendance.open_date, attendance.open_time)
				closed_dt = combine_date_time(close_date, close_time)

				if explicit_duration or explicit_night:
						_ensure_close_after_open(opened_dt, closed_dt)
						if not explicit_duration or not explicit_night:
								_apply_close_stats(attendance, opened_dt, closed_dt)
				else:
						_apply_close_stats(attendance, opened_dt, closed_dt)

				if explicit_duration:
						attendance.duration_minutes = data["duration_minutes"]
				if explicit_night:
						attendance.night_minutes = data["night_minutes"] or 0
				_calculate_and_set_pay(db, attendance)
		else:
				attendance.close_date = None
				attendance.close_time = None
				attendance.duration_minutes = data.get("duration_minutes") if explicit_duration else None
				attendance.night_minutes = data.get("night_minutes") or 0 if explicit_night else 0
				attendance.pay_amount = None

		db.add(attendance)
		db.flush()
		log_employee_changes(
				db,
				user_id=user_id,
				changed_by_id=current_user.id,
				changes=[
						{
								"field": "attendance",
								"old_value": None,
								"new_value": _attendance_summary(attendance),
								"source": "attendance_create",
								"comment": "Создана смена",
								"entity_type": "attendance",
								"entity_id": attendance.id,
						}
				],
		)
		db.commit()
		db.refresh(attendance)
		recalc_salary_for_user_month(
				db,
				user_id,
				attendance.open_date or date.today(),
				calculated_by_id=current_user.id if getattr(current_user, "id", None) else None,
		)

		return _attendance_to_public(attendance, current_user, target)


@router.patch("/{user_id}/attendances/{attendance_id}", response_model=AttendancePublic)
def update_employee_attendance(
	user_id: int,
	attendance_id: int,
	payload: AttendanceManualUpdate,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	target = _check_permissions(db, current_user, user_id)
	_ensure_can_edit_user(db, current_user, target)
	can_edit_rate = can_view_rate(current_user, target)

	attendance = db.query(Attendance).filter(Attendance.id == attendance_id, Attendance.user_id == user_id).first()
	if not attendance:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance not found")

	before_summary = _attendance_summary(attendance)
	data = payload.model_dump(exclude_unset=True)
	interval_changed = any(
		field in data for field in ("open_date", "open_time", "close_date", "close_time")
	)
	if interval_changed:
		new_open_date = data.get("open_date", attendance.open_date)
		new_open_time = data.get("open_time", attendance.open_time)
		close_date_provided = "close_date" in data
		close_time_provided = "close_time" in data
		new_close_date = data.get("close_date") if close_date_provided else attendance.close_date
		new_close_time = data.get("close_time") if close_time_provided else attendance.close_time
		if (close_date_provided and data.get("close_date") is None) or (close_time_provided and data.get("close_time") is None):
			new_close_date = None
			new_close_time = None

		today = today_local()
		if new_open_date and new_open_date > today:
			raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя создавать смены в будущие даты")
		if new_close_date and new_close_date > today:
			raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя создавать смены в будущие даты")

		opened_dt = combine_date_time(new_open_date, new_open_time)
		closed_dt = combine_date_time(new_close_date, new_close_time) if new_close_date and new_close_time else None
		conflict = _find_attendance_overlap(
			db,
			user_id,
			opened_dt,
			closed_dt,
			exclude_attendance_id=attendance.id,
		)
		if conflict:
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail=f"Смена пересекается с существующей (id={conflict.id})",
			)

	if "position_id" in data:
		pos_id = data["position_id"]
		if pos_id is not None and not db.query(Position).get(pos_id):
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
		attendance.position_id = pos_id

	if "restaurant_id" in data:
		attendance.restaurant_id = data["restaurant_id"]

	if "rate" in data:
		if can_edit_rate:
			attendance.rate = data["rate"]

	open_changed = False
	if "open_date" in data:
		attendance.open_date = data["open_date"]
		open_changed = True
	if "open_time" in data:
		attendance.open_time = data["open_time"]
		open_changed = True

	close_changed = False
	if "close_date" in data:
		attendance.close_date = data["close_date"]
		close_changed = True
	if "close_time" in data:
		attendance.close_time = data["close_time"]
		close_changed = True

	explicit_duration = data.get("duration_minutes") is not None
	explicit_night = data.get("night_minutes") is not None

	if ("close_date" in data and data["close_date"] is None) or ("close_time" in data and data["close_time"] is None):
		attendance.close_date = None
		attendance.close_time = None
		attendance.duration_minutes = data.get("duration_minutes") if explicit_duration else None
		attendance.night_minutes = data.get("night_minutes") if explicit_night else 0
		attendance.pay_amount = None
	else:
		if explicit_duration:
			attendance.duration_minutes = data["duration_minutes"]
		if explicit_night:
			attendance.night_minutes = data["night_minutes"] or 0

		if attendance.close_date and attendance.close_time and attendance.open_date and attendance.open_time:
			opened_dt = combine_date_time(attendance.open_date, attendance.open_time)
			closed_dt = combine_date_time(attendance.close_date, attendance.close_time)
			if not explicit_duration or not explicit_night:
				_apply_close_stats(attendance, opened_dt, closed_dt)
		else:
			if open_changed or close_changed:
				if not explicit_duration:
					attendance.duration_minutes = None
				if not explicit_night:
					attendance.night_minutes = 0
		if attendance.close_date and attendance.close_time and attendance.duration_minutes is not None:
			_calculate_and_set_pay(db, attendance)
		else:
			attendance.pay_amount = None

	after_summary = _attendance_summary(attendance)
	if before_summary != after_summary:
		log_employee_changes(
			db,
			user_id=user_id,
			changed_by_id=current_user.id,
			changes=[
				{
					"field": "attendance",
					"old_value": before_summary,
					"new_value": after_summary,
					"source": "attendance_update",
					"comment": "Изменена смена",
					"entity_type": "attendance",
					"entity_id": attendance.id,
				}
			],
		)
	db.commit()
	db.refresh(attendance)
	recalc_salary_for_user_month(
		db,
		user_id,
		attendance.open_date or date.today(),
		calculated_by_id=current_user.id if getattr(current_user, "id", None) else None,
	)

	return _attendance_to_public(attendance, current_user, target)


@router.delete("/{user_id}/attendances/{attendance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee_attendance(
	user_id: int,
	attendance_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	target = _check_permissions(db, current_user, user_id)
	_ensure_can_edit_user(db, current_user, target)

	attendance = (
		db.query(Attendance)
		  .filter(Attendance.id == attendance_id, Attendance.user_id == user_id)
		  .first()
	)
	if not attendance:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance not found")
	ref_date = attendance.open_date or date.today()

	deleted_summary = _attendance_summary(attendance)
	log_employee_changes(
		db,
		user_id=user_id,
		changed_by_id=current_user.id,
		changes=[
			{
				"field": "attendance",
				"old_value": deleted_summary,
				"new_value": None,
				"source": "attendance_delete",
				"comment": "Удалена смена",
				"entity_type": "attendance",
				"entity_id": attendance.id,
			}
		],
	)
	db.delete(attendance)
	db.commit()
	recalc_salary_for_user_month(
		db,
		user_id,
		ref_date,
		calculated_by_id=current_user.id if getattr(current_user, "id", None) else None,
	)

	return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{user_id}/attendances/recalculate-night", response_model=AttendanceRangeResponse)
def recalculate_employee_attendance_night(
	user_id: int,
	payload: Optional[AttendanceRecalculateNightRequest] = None,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	target = _check_permissions(db, current_user, user_id)
	_ensure_can_edit_user(db, current_user, target)

	if payload is None:
		payload = AttendanceRecalculateNightRequest()

	date_from = payload.date_from
	date_to = payload.date_to

	if not date_from or not date_to:
		start, end = _month_bounds(date.today())
		date_from = date_from or start
		date_to = date_to or end

	if date_from > date_to:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="date_from must be <= date_to")

	cond = _att_range_condition(date_from, date_to)

	qry = (
		db.query(Attendance)
		  .options(
			  joinedload(Attendance.position),
			  joinedload(Attendance.restaurant),
		  )
		  .filter(Attendance.user_id == user_id)
		  .filter(cond)
	)

	rows: List[Attendance] = (
		qry
		  .order_by(Attendance.open_date.asc(), Attendance.open_time.asc())
		  .all()
	)

	before_map = {attendance.id: _attendance_summary(attendance) for attendance in rows}

	for attendance in rows:
		if attendance.open_date and attendance.open_time and attendance.close_date and attendance.close_time:
			opened_dt = combine_date_time(attendance.open_date, attendance.open_time)
			closed_dt = combine_date_time(attendance.close_date, attendance.close_time)
			_apply_close_stats(attendance, opened_dt, closed_dt)
			_calculate_and_set_pay(db, attendance)
		else:
			attendance.night_minutes = attendance.night_minutes or 0
			attendance.pay_amount = attendance.pay_amount if attendance.pay_amount is not None else None

	changes = []
	for attendance in rows:
		before_summary = before_map.get(attendance.id)
		after_summary = _attendance_summary(attendance)
		if before_summary != after_summary:
			changes.append(
				{
					"field": "attendance",
					"old_value": before_summary,
					"new_value": after_summary,
					"source": "attendance_recalculate",
					"comment": "Пересчитана смена",
					"entity_type": "attendance",
					"entity_id": attendance.id,
				}
			)
	if changes:
		log_employee_changes(
			db,
			user_id=user_id,
			changed_by_id=current_user.id,
			changes=changes,
		)
	db.commit()

	items = [_attendance_to_public(a, current_user, target) for a in rows]
	return AttendanceRangeResponse(items=items, date_from=date_from, date_to=date_to)
