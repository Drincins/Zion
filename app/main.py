import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ---- Импорты моделей и утилит ----
# Если твои database/models/utils лежат в app/api или app/, поправь путь.
from backend.database import SessionLocal, engine  # например: from app.database import ...
from backend.models import Base, User              # например: from app.models import ...
from backend.utils import hash_password            # например: from app.utils import ...
from app.api.routes import router as api_router

# ---- Конфиг и создание таблиц ----
load_dotenv()
DEFAULT_USERNAME = os.getenv("DEFAULT_USERNAME")
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD")

Base.metadata.create_all(bind=engine)

# ---- Админ по умолчанию ----
def create_default_admin():
    db = SessionLocal()
    user = db.query(User).filter(User.username == DEFAULT_USERNAME).first()
    if not user and DEFAULT_USERNAME and DEFAULT_PASSWORD:
        new_user = User(
            username=DEFAULT_USERNAME,
            hashed_password=hash_password(DEFAULT_PASSWORD)
        )
        db.add(new_user)
        db.commit()
        print("✅ Админ создан")
    else:
        print("ℹ️ Админ уже есть или переменные не заданы")
    db.close()

create_default_admin()

# ---- FastAPI и CORS ----
app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://localhost:8000",
    "http://172.18.0.2:5173",
    "https://your-frontend-domain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Роуты ----
app.include_router(api_router, prefix="/api")

# ---- Статика фронта ----
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join("app/static", "index.html"))
