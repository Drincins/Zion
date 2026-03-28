import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.bd.models import Company, User, Restaurant, Role, UserThemePreference
from backend.bd.database import get_db
from backend.utils import (
    hash_password,
    verify_password,
    create_jwt_token,
    get_auth_cookie_name,
    get_current_user,
    set_auth_cookie,
    clear_auth_cookie,
    revoke_session_token,
)
from backend.services.permissions import (
    PermissionCode,
    ensure_permissions,
    get_user_permission_codes,
    has_global_access,
)
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Auth"])

AVAILABLE_THEME_MODE_KEYS = ("light", "dark")
DEFAULT_THEME_MODE_KEY = "dark"
AVAILABLE_INTERFACE_THEME_KEYS = ("classic", "blue", "green", "red", "pink", "purple")
DEFAULT_INTERFACE_THEME_KEY = "classic"

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
    access_token: str | None = None
    token_type: str = "bearer"
    user: dict | None = None


class SessionUserResponse(BaseModel):
    id: int
    username: str
    first_name: str | None = None
    last_name: str | None = None
    iiko_code: str | None = None


class ThemePreferenceResponse(BaseModel):
    mode: str
    interface_theme: str
    can_customize_interface_theme: bool
    available_modes: list[str] = Field(default_factory=list)
    available_interface_themes: list[str] = Field(default_factory=list)


class ThemePreferenceUpdateRequest(BaseModel):
    mode: str | None = None
    interface_theme: str | None = None


def _normalize_theme_mode_key(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized in AVAILABLE_THEME_MODE_KEYS:
        return normalized
    return DEFAULT_THEME_MODE_KEY


def _normalize_interface_theme_key(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized in AVAILABLE_INTERFACE_THEME_KEYS:
        return normalized
    return DEFAULT_INTERFACE_THEME_KEY


def _can_customize_interface_theme(current_user: User) -> bool:
    if has_global_access(current_user):
        return True
    codes = get_user_permission_codes(current_user)
    if any(code.startswith("sections.") for code in codes):
        return True
    return any(
        code in codes
        for code in (
            PermissionCode.USERS_VIEW,
            PermissionCode.USERS_MANAGE,
            PermissionCode.STAFF_EMPLOYEES_VIEW,
            PermissionCode.STAFF_EMPLOYEES_MANAGE,
            PermissionCode.ACCESS_CONTROL_READ,
            PermissionCode.ACCESS_CONTROL_MANAGE,
            PermissionCode.INVENTORY_VIEW,
            PermissionCode.PAYROLL_VIEW,
            PermissionCode.KPI_VIEW,
            PermissionCode.SALES_REPORT_VIEW_QTY,
            PermissionCode.SALES_REPORT_VIEW_MONEY,
            PermissionCode.ACCOUNTING_INVOICES_VIEW,
            PermissionCode.KNOWLEDGE_BASE_SECTION,
        )
    )


def _build_theme_preference_response(
    *,
    mode: str,
    interface_theme: str,
    can_customize_interface_theme: bool,
) -> ThemePreferenceResponse:
    if not can_customize_interface_theme:
        return ThemePreferenceResponse(
            mode=_normalize_theme_mode_key(mode),
            interface_theme=DEFAULT_INTERFACE_THEME_KEY,
            can_customize_interface_theme=False,
            available_modes=list(AVAILABLE_THEME_MODE_KEYS),
            available_interface_themes=[DEFAULT_INTERFACE_THEME_KEY],
        )
    return ThemePreferenceResponse(
        mode=_normalize_theme_mode_key(mode),
        interface_theme=_normalize_interface_theme_key(interface_theme),
        can_customize_interface_theme=True,
        available_modes=list(AVAILABLE_THEME_MODE_KEYS),
        available_interface_themes=list(AVAILABLE_INTERFACE_THEME_KEYS),
    )

@router.post("/login", response_model=TokenResponse)
def login(user: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    if db_user.fired:
        raise HTTPException(status_code=403, detail="Пользователь уволен")

    token = create_jwt_token(db, db_user.id)
    set_auth_cookie(response, token, request)
    return TokenResponse(
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
def login_swagger(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    db_user = db.query(User).filter(User.username == form_data.username).first()
    if not db_user or not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    if db_user.fired:
        raise HTTPException(status_code=403, detail="Пользователь уволен")

    token = create_jwt_token(db, db_user.id)
    set_auth_cookie(response, token, request)
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


@router.get("/me", response_model=SessionUserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return SessionUserResponse(
        id=current_user.id,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        iiko_code=current_user.iiko_code,
    )


@router.get("/theme", response_model=ThemePreferenceResponse)
def get_theme_preference(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    can_customize_interface_theme = _can_customize_interface_theme(current_user)

    preference = (
        db.query(UserThemePreference)
        .filter(UserThemePreference.user_id == current_user.id)
        .first()
    )
    saved_mode = preference.theme_key if preference else DEFAULT_THEME_MODE_KEY
    saved_interface_theme = (
        preference.interface_theme_key
        if preference
        else DEFAULT_INTERFACE_THEME_KEY
    )
    return _build_theme_preference_response(
        mode=saved_mode,
        interface_theme=saved_interface_theme,
        can_customize_interface_theme=can_customize_interface_theme,
    )


@router.put("/theme", response_model=ThemePreferenceResponse)
def set_theme_preference(
    payload: ThemePreferenceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.mode is None and payload.interface_theme is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No theme fields provided")

    can_customize_interface_theme = _can_customize_interface_theme(current_user)

    preference = (
        db.query(UserThemePreference)
        .filter(UserThemePreference.user_id == current_user.id)
        .first()
    )
    if not preference:
        preference = UserThemePreference(
            user_id=current_user.id,
            theme_key=DEFAULT_THEME_MODE_KEY,
            interface_theme_key=DEFAULT_INTERFACE_THEME_KEY,
        )
        db.add(preference)

    current_mode = _normalize_theme_mode_key(preference.theme_key)
    current_interface_theme = _normalize_interface_theme_key(preference.interface_theme_key)

    if payload.mode is not None:
        requested_mode = (payload.mode or "").strip().lower()
        if requested_mode not in AVAILABLE_THEME_MODE_KEYS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported mode")
        current_mode = requested_mode

    if payload.interface_theme is not None:
        requested_interface_theme = (payload.interface_theme or "").strip().lower()
        if requested_interface_theme not in AVAILABLE_INTERFACE_THEME_KEYS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported interface theme")
        if not can_customize_interface_theme and requested_interface_theme != DEFAULT_INTERFACE_THEME_KEY:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Interface theme customization is available only in admin panel",
            )
        current_interface_theme = requested_interface_theme

    if not can_customize_interface_theme:
        current_interface_theme = DEFAULT_INTERFACE_THEME_KEY

    preference.theme_key = current_mode
    preference.interface_theme_key = current_interface_theme

    db.commit()

    return _build_theme_preference_response(
        mode=current_mode,
        interface_theme=current_interface_theme,
        can_customize_interface_theme=can_customize_interface_theme,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    authorization = request.headers.get("Authorization")
    bearer = authorization.split(" ", 1)[1].strip() if authorization and authorization.lower().startswith("bearer ") else None
    token = bearer or (request.cookies.get(get_auth_cookie_name()) or "").strip()
    if token:
        revoke_session_token(token, db, reason="logout")
    clear_auth_cookie(response, request)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
