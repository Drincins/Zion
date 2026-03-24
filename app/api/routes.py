from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from backend.bd.database import get_db
from backend.bd.models import User
from backend.utils import verify_password, create_jwt_token, set_auth_cookie

from pydantic import BaseModel

router = APIRouter(prefix="", tags=["API"])

@router.get("/ping")
def ping():
    return {"message": "pong"}

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str | None = None
    token_type: str = "bearer"
    user: dict | None = None

@router.post("/login", response_model=TokenResponse)
async def login(request: Request, response: Response, db: Session = Depends(get_db)):
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
    if user.fired:
        raise HTTPException(status_code=403, detail="Пользователь уволен")
    token = create_jwt_token(db, user.id)
    set_auth_cookie(response, token, request)
    return TokenResponse(
        user={
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "iiko_code": user.iiko_code,
        },
    )
