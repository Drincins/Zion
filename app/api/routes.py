from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import User
from backend.utils import hash_password, verify_password, create_jwt_token

from pydantic import BaseModel

router = APIRouter()

@router.get("/ping")
def ping():
    return {"message": "pong"}

# --- Схемы запросов и ответов ---

class RegisterRequest(BaseModel):
    username: str
    password: str
    first_name: str
    last_name: str
    iiko_code: str

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# --- Зависимость для получения сессии ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Регистрация ---
@router.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if user:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    new_user = User(
        username=request.username,
        hashed_password=hash_password(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        iiko_code=request.iiko_code
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Пользователь успешно зарегистрирован"}

# --- Авторизация ---
@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    token = create_jwt_token(user.id)
    return TokenResponse(access_token=token)
