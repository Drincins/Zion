import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.bd.models import Company, User, Restaurant, Role
from backend.bd.database import get_db
from backend.utils import hash_password, verify_password, create_jwt_token, get_current_user
from backend.services.permissions import PermissionCode, ensure_permissions
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Auth"])

class RegisterRequest(BaseModel):
    username: str | None = None
    password: str | None = None
    confirm_password: str | None = None
    first_name: str
    last_name: str
    iiko_code: str
    role_name: str  # "admin" или "user"
    company_id: int
    restaurant_ids: list[int]

@router.post("/register")
def register(
    user: RegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.USERS_MANAGE, PermissionCode.STAFF_MANAGE_ALL)

    role = db.query(Role).filter(Role.name == user.role_name).first()
    if not role:
        raise HTTPException(status_code=400, detail="Указанная роль не найдена")

    role_norm = (role.name or "").strip().lower().replace(" ", "")
    is_time_control = role.id == 10 or role_norm in {"таймконтроль", "тайм-контроль", "timecontrol", "time_control"}

    if not is_time_control:
        if not user.username or not user.password or not user.confirm_password:
            raise HTTPException(status_code=400, detail="username/password are required for this role")
        if user.password != user.confirm_password:
            raise HTTPException(status_code=400, detail="Пароли не совпадают")
        existing_user = db.query(User).filter(User.username == user.username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Пользователь уже существует")
        username = user.username
        raw_password = user.password
    else:
        base_username = (user.username or user.iiko_code or f"timecontrol_{uuid.uuid4().hex[:8]}").strip()
        candidate = base_username or f"timecontrol_{uuid.uuid4().hex[:8]}"
        suffix = 1
        while db.query(User).filter(User.username == candidate).first():
            candidate = f"{base_username}_{suffix}"
            suffix += 1
        username = candidate
        raw_password = user.password or uuid.uuid4().hex

    company = db.query(Company).filter(Company.id == user.company_id).first()
    if not company:
        raise HTTPException(status_code=400, detail="Указанная компания не найдена")

    restaurants = db.query(Restaurant).filter(Restaurant.id.in_(user.restaurant_ids)).all()
    if not restaurants:
        raise HTTPException(status_code=400, detail="Рестораны не найдены или список пуст")

    new_user = User(
        username=username,
        hashed_password=hash_password(raw_password),
        first_name=user.first_name,
        last_name=user.last_name,
        iiko_code=user.iiko_code,
        company=company,
        role=role,
        restaurants=restaurants
    )

    db.add(new_user)
    db.commit()
    return {"message": f"Пользователь '{user.username}' зарегистрирован"}

# ======== JWT login (JSON) ========
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict | None = None

@router.post("/login", response_model=TokenResponse)
def login(user: LoginRequest, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    token = create_jwt_token(db_user.id)
    return TokenResponse(
        access_token=token,
        user={
            "id": db_user.id,
            "username": db_user.username,
            "first_name": db_user.first_name,
            "last_name": db_user.last_name,
            "iiko_code": db_user.iiko_code
        }
    )

# ======== JWT login для Swagger (form-data) ========
@router.post("/login/swag", response_model=TokenResponse)
def login_swagger(form_data: OAuth2PasswordRequestForm = Depends(),
                  db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == form_data.username).first()
    if not db_user or not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    token = create_jwt_token(db_user.id)
    return TokenResponse(
        access_token=token,
        user={
            "id": db_user.id,
            "username": db_user.username,
            "first_name": db_user.first_name,
            "last_name": db_user.last_name,
            "iiko_code": db_user.iiko_code
        }
    )
