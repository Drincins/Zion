from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from backend.bd.database import get_db
from backend.bd.models import User
from backend.utils import hash_password, verify_password, create_jwt_token

from pydantic import BaseModel

router = APIRouter(prefix="", tags=["API"])

@router.get("/ping")
def ping():
    return {"message": "pong"}

# --- ??????????? ---
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

# --- ??????????? ---
@router.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if user:
        raise HTTPException(status_code=400, detail="???????????? ??? ??????????")
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
    return {"message": "???????????? ??????? ???????????????"}

# --- ????? ---
@router.post("/login", response_model=TokenResponse)
async def login(request: Request, db: Session = Depends(get_db)):
    # ???????????? JSON ? form-data (???? Authorize ? Swagger)
    username = None
    password = None
    content_type = (request.headers.get("content-type") or "").split(";")[0].strip().lower()

    if content_type == "application/x-www-form-urlencoded":
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
    else:
        try:
            payload = await request.json()
        except Exception:
            payload = None
        if isinstance(payload, dict):
            username = payload.get("username")
            password = payload.get("password")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="???????? ??? ???????????? ??? ??????")
    token = create_jwt_token(user.id)
    return TokenResponse(access_token=token)
