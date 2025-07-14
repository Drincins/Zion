from pydantic import BaseModel
from fastapi import Body

# 👤 Модель входных данных
class RegisterRequest(BaseModel):
    username: str
    password: str
    confirm_password: str
    first_name: str
    last_name: str
    iiko_code: str

@router.post("/register")
def register(user: RegisterRequest, db: Session = Depends(get_db)):
    # Проверка на совпадение паролей
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Пароли не совпадают")

    # Проверка, есть ли пользователь
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")

    # Добавление нового пользователя
    new_user = User(
        username=user.username,
        hashed_password=hash_password(user.password),
        first_name=user.first_name,
        last_name=user.last_name,
        iiko_code=user.iiko_code
    )
    db.add(new_user)
    db.commit()
    return {"message": f"Пользователь '{user.username}' зарегистрирован"}
class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(user: LoginRequest, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    from .utils import verify_password
    if not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный пароль")
    
    return {
        "message": "Успешный вход",
        "user": {
            "username": db_user.username,
            "first_name": db_user.first_name,
            "last_name": db_user.last_name,
            "iiko_code": db_user.iiko_code
        }
    }
