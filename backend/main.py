import os
from dotenv import load_dotenv
from .database import SessionLocal, engine
from .models import Base, User
from .utils import hash_password
from fastapi import FastAPI
from app.api.routes import router  # Импортируем router из routes.py

app = FastAPI()

app.include_router(router)

# Загружаем переменные из .env
load_dotenv()
DEFAULT_USERNAME = os.getenv("DEFAULT_USERNAME")
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD")

# Создаём таблицы
Base.metadata.create_all(bind=engine)

# Создаём администратора по умолчанию (если его ещё нет)
def create_default_admin():
    db = SessionLocal()
    user = db.query(User).filter(User.username == DEFAULT_USERNAME).first()
    if not user:
        new_user = User(
            username=DEFAULT_USERNAME,
            hashed_password=hash_password(DEFAULT_PASSWORD)
        )
        db.add(new_user)
        db.commit()
        print("✅ Админ создан")
    else:
        print("ℹ️ Админ уже есть")
    db.close()

create_default_admin()
