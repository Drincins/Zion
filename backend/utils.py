# backend/utils.py
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Set

import bcrypt
from dotenv import load_dotenv
from jose import JWTError, jwt
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer

from backend.bd.database import get_db
from backend.bd.models import AuthSession, User, user_restaurants
from backend.services.permissions import has_global_access


def user_has_global_access(user: User) -> bool:
    """Return True if the user should have unrestricted access to data."""
    return has_global_access(user)


# ===== Timezone helpers =====
try:
    from zoneinfo import ZoneInfo  # py3.9+
except Exception:
    ZoneInfo = None

APP_TZ_NAME = os.getenv("APP_TZ", "Europe/Moscow")

if ZoneInfo:
    try:
        LOCAL_TZ = ZoneInfo(APP_TZ_NAME)
    except Exception:
        LOCAL_TZ = timezone.utc
else:
    LOCAL_TZ = timezone.utc  # если нет ZoneInfo, добавь пакет tzdata в requirements

def now_local() -> datetime:
    return datetime.now(LOCAL_TZ).replace(microsecond=0)

def today_local():
    return now_local().date()

def local_time():
    return now_local().time()

# ===== Password hashing =====
def hash_password(password: str) -> str:
    """Hash password using bcrypt with sane defaults."""
    salt_rounds = int(os.getenv("BCRYPT_ROUNDS", "12"))
    salt = bcrypt.gensalt(rounds=salt_rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # Invalid hash format or unsupported value
        return False

# ===== JWT =====
_JWT_INSECURE_DEFAULTS = {"supersecret", "change_me", "CHANGE_ME"}
_JWT_CONFIG_ERROR_DETAIL = "Конфигурация авторизации не настроена"
_FALSE_VALUES = {"0", "false", "no", "off"}
AUTH_SESSION_SCOPE_MAIN = "main"
AUTH_SESSION_SCOPE_CHECKLIST_PORTAL = "checklist_portal"


def get_jwt_secret() -> str:
    load_dotenv()
    secret = (os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET") or "").strip()
    if not secret:
        raise RuntimeError("SECRET_KEY or JWT_SECRET must be set")
    if secret in _JWT_INSECURE_DEFAULTS:
        raise RuntimeError("SECRET_KEY/JWT_SECRET uses an insecure default value")
    return secret


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 часа

def create_access_token(
    sub: str,
    expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
    *,
    session_id: str | None = None,
) -> str:
    exp = datetime.utcnow() + timedelta(minutes=expires_minutes)
    payload = {"sub": str(sub), "exp": exp}
    if session_id:
        payload["sid"] = session_id
    return jwt.encode(payload, get_jwt_secret(), algorithm=ALGORITHM)


def _normalize_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def create_session_jwt_token(
    db: Session,
    user_id: int,
    *,
    scope: str = AUTH_SESSION_SCOPE_MAIN,
    expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
) -> str:
    session_id = uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    db.add(
        AuthSession(
            id=session_id,
            user_id=user_id,
            scope=scope,
            expires_at=expires_at,
        )
    )
    db.commit()
    return create_access_token(str(user_id), expires_minutes=expires_minutes, session_id=session_id)


def create_jwt_token(
    db: Session,
    user_id: int,
    *,
    scope: str = AUTH_SESSION_SCOPE_MAIN,
    expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
) -> str:
    return create_session_jwt_token(db, user_id, scope=scope, expires_minutes=expires_minutes)


def decode_jwt_payload(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, get_jwt_secret(), algorithms=[ALGORITHM])
    except JWTError:
        return None

def decode_jwt_token(token: str) -> Optional[int]:
    payload = decode_jwt_payload(token)
    if not payload:
        return None
    sub = payload.get("sub")
    return int(sub) if sub is not None else None


def extract_bearer_token(authorization_header: str | None) -> Optional[str]:
    if not authorization_header:
        return None
    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer":
        return None
    clean_token = token.strip()
    return clean_token or None


def get_auth_cookie_name() -> str:
    return (os.getenv("AUTH_COOKIE_NAME") or "zion_auth").strip() or "zion_auth"


def get_checklist_portal_auth_cookie_name() -> str:
    return (os.getenv("CHECKLIST_PORTAL_AUTH_COOKIE_NAME") or "zion_checklist_auth").strip() or "zion_checklist_auth"


def get_auth_cookie_samesite() -> str:
    raw = (os.getenv("AUTH_COOKIE_SAMESITE") or "lax").strip().lower()
    if raw not in {"lax", "strict", "none"}:
        return "lax"
    return raw


def _bool_env_enabled(name: str) -> Optional[bool]:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return None
    return raw not in _FALSE_VALUES


def should_use_secure_auth_cookie(request: Request | None = None) -> bool:
    forced = _bool_env_enabled("AUTH_COOKIE_SECURE")
    if forced is not None:
        return forced
    if request is None:
        return False
    forwarded_proto = (request.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
    if forwarded_proto:
        return forwarded_proto == "https"
    return request.url.scheme == "https"


def set_auth_cookie(
    response: Response,
    token: str,
    request: Request | None = None,
    *,
    cookie_name: str | None = None,
) -> None:
    response.set_cookie(
        key=(cookie_name or get_auth_cookie_name()),
        value=token,
        httponly=True,
        secure=should_use_secure_auth_cookie(request),
        samesite=get_auth_cookie_samesite(),
        path="/",
    )


def clear_auth_cookie(
    response: Response,
    request: Request | None = None,
    *,
    cookie_name: str | None = None,
) -> None:
    response.delete_cookie(
        key=(cookie_name or get_auth_cookie_name()),
        path="/",
        secure=should_use_secure_auth_cookie(request),
        httponly=True,
        samesite=get_auth_cookie_samesite(),
    )


def _resolve_cookie_names_for_request(request: Request) -> tuple[str, ...]:
    path = (request.url.path or "").rstrip("/") or "/"
    if path.startswith("/api/checklists/portal"):
        return (get_checklist_portal_auth_cookie_name(),)
    return (get_auth_cookie_name(),)


def extract_auth_token_from_request(request: Request, bearer_token: str | None = None) -> Optional[str]:
    if bearer_token:
        return bearer_token
    for cookie_name in _resolve_cookie_names_for_request(request):
        cookie_token = (request.cookies.get(cookie_name) or "").strip()
        if cookie_token:
            return cookie_token
    return None


def get_expected_auth_scopes_for_request(request: Request) -> set[str]:
    path = (request.url.path or "").rstrip("/") or "/"
    if path.startswith("/api/checklists/portal"):
        return {AUTH_SESSION_SCOPE_CHECKLIST_PORTAL}
    return {AUTH_SESSION_SCOPE_MAIN}


def resolve_user_from_token(
    token: str,
    db: Session,
    *,
    allowed_scopes: set[str] | None = None,
    not_found_status: int = status.HTTP_404_NOT_FOUND,
) -> User:
    try:
        payload = decode_jwt_payload(token)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_JWT_CONFIG_ERROR_DETAIL,
        ) from exc
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный токен")
    sub = payload.get("sub")
    sid = (payload.get("sid") or "").strip()
    try:
        user_id = int(sub) if sub is not None else None
    except (TypeError, ValueError):
        user_id = None
    if user_id is None or not sid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия недействительна")

    auth_session = (
        db.query(AuthSession)
        .filter(AuthSession.id == sid, AuthSession.user_id == user_id)
        .first()
    )
    if auth_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия недействительна")
    expires_at = _normalize_utc_datetime(auth_session.expires_at)
    if auth_session.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия завершена")
    if expires_at is None or expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия истекла")
    if allowed_scopes and auth_session.scope not in allowed_scopes:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия недействительна")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=not_found_status, detail="Пользователь не найден")
    if user.fired:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь уволен")
    return user


def revoke_session_token(token: str, db: Session, *, reason: str = "logout") -> bool:
    try:
        payload = decode_jwt_payload(token)
    except RuntimeError:
        return False
    if not payload:
        return False
    sid = (payload.get("sid") or "").strip()
    if not sid:
        return False
    auth_session = db.query(AuthSession).filter(AuthSession.id == sid).first()
    if auth_session is None:
        return False
    if auth_session.revoked_at is None:
        auth_session.revoked_at = datetime.now(timezone.utc)
        auth_session.revoked_reason = reason
        db.commit()
    return True

# ===== OAuth2 dependency (для Swagger авторизации) =====
# укажи здесь свой фактический эндпоинт логина, у тебя в логах это был /api/login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login", auto_error=False)

def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    auth_token = extract_auth_token_from_request(request, token)
    if not auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется авторизация")
    return resolve_user_from_token(
        auth_token,
        db,
        allowed_scopes=get_expected_auth_scopes_for_request(request),
    )


def get_user_restaurant_ids(db: Session, user: User) -> Optional[Set[int]]:
    """Return set of restaurant IDs available to the user. None means unrestricted access."""
    if user_has_global_access(user) or getattr(user, "has_full_restaurant_access", False):
        return None
    result = db.execute(
        select(user_restaurants.c.restaurant_id).where(user_restaurants.c.user_id == user.id)
    )
    ids = {row[0] for row in result}
    return ids


def users_share_restaurant(db: Session, viewer: User, target_user_id: int) -> bool:
    """Check whether two users share at least one restaurant."""
    if user_has_global_access(viewer) or viewer.id == target_user_id:
        return True
    viewer_restaurants = get_user_restaurant_ids(db, viewer)
    if viewer_restaurants is None:
        return True
    if not viewer_restaurants:
        return False
    result = db.execute(
        select(user_restaurants.c.restaurant_id)
        .where(user_restaurants.c.user_id == target_user_id)
        .where(user_restaurants.c.restaurant_id.in_(viewer_restaurants))
        .limit(1)
    )
    return result.first() is not None

# ===== UPSERT helper =====
def upsert(db: Session, model, data_list: list[dict], keys: list[str]):
    """
    Выполняет UPSERT (insert or update) для списка словарей data_list.
    - model: SQLAlchemy модель
    - data_list: список словарей данных
    - keys: список полей, по которым определяется уникальность записи (ON CONFLICT)
    """
    if not data_list:
        return
    stmt = insert(model).values(data_list)
    update_stmt = {c.name: c for c in stmt.excluded if c.name not in keys}
    db.execute(stmt.on_conflict_do_update(index_elements=keys, set_=update_stmt))
    db.commit()
