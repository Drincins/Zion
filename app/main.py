from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.api.routes import router as api_router

app = FastAPI()

# Разрешённые источники
origins = [
    "http://localhost:5173",            # Локальная разработка Vue
    "http://localhost:8000",
    "http://172.18.0.2:5173",
    "https://your-frontend-domain.com", # Продакшн фронтенд
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем API
app.include_router(api_router, prefix="/api")

# Если ты собираешь фронтенд Vue и кладёшь его в папку static:
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

# Чтобы открыть SPA без 404
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join("app/static", "index.html"))
