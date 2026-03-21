# backend/utils.py
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Set

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from backend.bd.database import get_db
from backend.bd.models import User, user_restaurants
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
# читаем любой из ключей, чтобы было совместимо со старым кодом
SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET") or "supersecret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 часа

def create_access_token(sub: str, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    exp = datetime.utcnow() + timedelta(minutes=expires_minutes)
    payload = {"sub": str(sub), "exp": exp}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_jwt_token(user_id: int) -> str:
    return create_access_token(str(user_id))

def decode_jwt_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except JWTError:
        return None

# ===== OAuth2 dependency (для Swagger авторизации) =====
# укажи здесь свой фактический эндпоинт логина, у тебя в логах это был /api/login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    user_id = decode_jwt_token(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный токен")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    if user.fired:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь уволен")
    return user


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
