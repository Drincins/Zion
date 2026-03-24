import os
import asyncio
from uuid import uuid4
from contextlib import suppress
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# ---- Импорты моделей и утилит ----
from backend.bd.database import SessionLocal
from backend.bd.models import Permission, User
from backend.utils import (
    extract_auth_token_from_request,
    get_expected_auth_scopes_for_request,
    hash_password,
    resolve_user_from_token,
)
from backend.services.permissions import PermissionKey
from backend.routers.users import router as users_router
from backend.routers.restaurants import router as restaurants_router
from backend.routers.companies import router as companies_router
from backend.routers.auth import router as auth_router
from backend.routers.iiko_olap_product import router as iiko_olap_product_router
from backend.routers.iiko_olap_read import router as iiko_olap_read_router
from backend.routers.iiko_products_read import router as iiko_products_read_router
from backend.routers.inventory import router as inventory_router
from app.api.routes import router as api_router
from backend.routers.access_control import router as access_control_router
from backend.routers.staff_portal import router as staff_portal_router
from backend.routers.staff_employees import router as staff_employees_router
from backend.routers.training_events import router as training_events_router
from backend.routers.payroll import router as payroll_router
from backend.routers.employees_card import router as employees_card_router
from backend.routers.kpi import router as kpi_router
from backend.routers.medical_checks import router as medical_checks_router
from backend.routers.cis_documents import router as cis_documents_router
from backend.routers.employment_documents import router as employment_documents_router
from backend.routers.fingerprint_templates import router as fingerprint_templates_router
from backend.routers.downloads import router as downloads_router
from backend.routers.employee_change_events import router as employee_change_events_router
from backend.routers.labor_summary import router as labor_summary_router
from backend.routers.accounting import router as accounting_router
from backend.routers.payroll_advances import router as payroll_advances_router
from backend.routers.checklists import router as checklists_router
from backend.routers.knowledge_base import router as knowledge_base_router
from backend.routers.iiko_sales import router as iiko_sales_router
from backend.tasks.attendance_auto_close import attendance_auto_close_loop
from backend.tasks.iiko_olap_daily_sync import iiko_olap_daily_sync_loop
from backend.tasks.iiko_sales_auto_sync import iiko_sales_auto_sync_loop
from backend.services.request_context import (
    RequestContext,
    set_request_context,
    reset_request_context,
)

# ---- Конфиг и создание таблиц ----
load_dotenv()
DEFAULT_USERNAME = os.getenv("DEFAULT_USERNAME")
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD")

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
        print("Админ создан")
    else:
        print("Админ уже есть или переменные не заданы")
    db.close()

create_default_admin()


def ensure_default_permissions():
    db = SessionLocal()
    try:
        defaults = [
            {
                "api_router": PermissionKey.STAFF_EMPLOYEES_IIKO_SYNC,
                "router_description": "Синхронизация сотрудников с iiko",
                "comment": "Право на создание/обновление сотрудника в iiko из раздела сотрудников",
                "display_name": "Синхронизация сотрудников с iiko",
                "responsibility_zone": "Сотрудники",
            },
            {
                "api_router": PermissionKey.KNOWLEDGE_BASE_VIEW,
                "router_description": "Knowledge base: view",
                "comment": "Read access to folders and documents in the knowledge base module.",
                "display_name": "Knowledge base: view",
                "responsibility_zone": "Knowledge base",
            },
            {
                "api_router": PermissionKey.KNOWLEDGE_BASE_MANAGE,
                "router_description": "Knowledge base: manage",
                "comment": "Create, edit, move and delete folders/documents in the knowledge base module.",
                "display_name": "Knowledge base: manage",
                "responsibility_zone": "Knowledge base",
            },
            {
                "api_router": PermissionKey.KNOWLEDGE_BASE_UPLOAD,
                "router_description": "Knowledge base: upload files",
                "comment": "Upload file attachments to the knowledge base module.",
                "display_name": "Knowledge base: upload files",
                "responsibility_zone": "Knowledge base",
            },
        ]

        for payload in defaults:
            existing = (
                db.query(Permission.id)
                .filter(Permission.api_router == payload["api_router"])
                .first()
            )
            if existing:
                continue
            db.add(Permission(**payload))
        db.commit()
    except Exception:
        db.rollback()
        print("Не удалось добавить базовые права")
    finally:
        db.close()


ensure_default_permissions()

# ---- FastAPI приложение ----
app = FastAPI()


PUBLIC_API_PATHS = {
    "/api/ping",
    "/api/login",
    "/api/auth/login",
    "/api/auth/login/swag",
    "/api/auth/logout",
    "/api/staff/login",
    "/api/checklists/portal/login/start",
    "/api/checklists/portal/login/finish",
    "/api/checklists/portal/logout",
}
BEARER_AUTH_BYPASS_PREFIXES = ("/api/fingerprints",)


def _normalize_request_path(path: str) -> str:
    if not path or path == "/":
        return "/"
    return path.rstrip("/") or "/"


def _requires_bearer_auth(path: str, method: str) -> bool:
    normalized_path = _normalize_request_path(path)
    if method.upper() == "OPTIONS":
        return False
    if not normalized_path.startswith("/api"):
        return False
    if normalized_path in PUBLIC_API_PATHS:
        return False
    return not any(normalized_path.startswith(prefix) for prefix in BEARER_AUTH_BYPASS_PREFIXES)


def _authenticate_api_request(request) -> JSONResponse | None:
    token = extract_auth_token_from_request(request)
    if not token:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Требуется авторизация"},
        )

    db = SessionLocal()
    try:
        user = resolve_user_from_token(
            token,
            db,
            allowed_scopes=get_expected_auth_scopes_for_request(request),
            not_found_status=status.HTTP_401_UNAUTHORIZED,
        )
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    finally:
        db.close()

    request.state.current_user_id = user.id
    return None



@app.middleware("http")
async def request_context_middleware(request, call_next):
    request_id = request.headers.get("X-Request-Id") or request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid4())
    ctx = RequestContext(
        request_id=request_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
        endpoint=request.url.path,
        method=request.method,
    )
    token = set_request_context(ctx)
    try:
        auth_response = None
        if _requires_bearer_auth(request.url.path, request.method):
            auth_response = _authenticate_api_request(request)
        if auth_response is not None:
            response = auth_response
        else:
            response = await call_next(request)
    finally:
        reset_request_context(token)
    response.headers.setdefault("X-Request-Id", request_id)
    return response

# ---- CORS ----
def _load_cors_origins() -> list[str]:
    raw = (os.getenv("CORS_ALLOWED_ORIGINS") or "").strip()
    if raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    return [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


origins = _load_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Роуты ----
app.include_router(users_router, prefix="/api")
app.include_router(restaurants_router, prefix="/api")
app.include_router(companies_router, prefix="/api")
app.include_router(api_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(iiko_olap_product_router, prefix="/api")
app.include_router(iiko_olap_read_router, prefix="/api")
app.include_router(iiko_products_read_router, prefix="/api")
app.include_router(iiko_sales_router, prefix="/api")
app.include_router(inventory_router, prefix="/api")
app.include_router(staff_portal_router, prefix="/api")
app.include_router(staff_employees_router, prefix="/api")
app.include_router(access_control_router, prefix="/api")
app.include_router(training_events_router, prefix="/api")
app.include_router(payroll_router, prefix="/api")
app.include_router(employees_card_router, prefix="/api")
app.include_router(kpi_router, prefix="/api")
app.include_router(medical_checks_router, prefix="/api")
app.include_router(cis_documents_router, prefix="/api")
app.include_router(employment_documents_router, prefix="/api")
app.include_router(fingerprint_templates_router, prefix="/api")
app.include_router(downloads_router, prefix="/api")
app.include_router(employee_change_events_router, prefix="/api")
app.include_router(labor_summary_router, prefix="/api")
app.include_router(accounting_router, prefix="/api")
app.include_router(payroll_advances_router, prefix="/api")
app.include_router(checklists_router, prefix="/api")
app.include_router(knowledge_base_router, prefix="/api")

# ---- Статика фронта ----
@app.on_event("startup")
async def start_background_jobs():
    app.state.attendance_auto_close_task = asyncio.create_task(attendance_auto_close_loop())
    app.state.iiko_olap_daily_sync_task = asyncio.create_task(iiko_olap_daily_sync_loop())
    app.state.iiko_sales_auto_sync_task = asyncio.create_task(iiko_sales_auto_sync_loop())


@app.on_event("shutdown")
async def stop_background_jobs():
    task = getattr(app.state, "attendance_auto_close_task", None)
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    task = getattr(app.state, "iiko_olap_daily_sync_task", None)
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    task = getattr(app.state, "iiko_sales_auto_sync_task", None)
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


STATIC_DIR = os.path.join("app", "static")
ASSETS_DIR = os.path.join(STATIC_DIR, "assets")
STATIC_DIR_ABS = os.path.abspath(STATIC_DIR)
INDEX_HTML_PATH = os.path.join(STATIC_DIR, "index.html")


def _resolve_static_file(path_value: str) -> str | None:
    candidate = os.path.abspath(os.path.join(STATIC_DIR, path_value))
    if os.path.commonpath([STATIC_DIR_ABS, candidate]) != STATIC_DIR_ABS:
        return None
    if os.path.isfile(candidate):
        return candidate
    return None

# Раздаём статические файлы Vite (ассеты), но только если они существуют.
if os.path.isdir(STATIC_DIR):
    if os.path.isdir(ASSETS_DIR):
        app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def serve_index_root():
        return FileResponse(INDEX_HTML_PATH)

    # SPA fallback: любые пути (кроме /api) отдаём index.html,
    # чтобы клиентский роутер обработал /login, /admin и т.п.
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not Found")

        static_file = _resolve_static_file(full_path)
        if static_file:
            if full_path.endswith(".webmanifest"):
                return FileResponse(static_file, media_type="application/manifest+json")
            return FileResponse(static_file)

        if "." in os.path.basename(full_path):
            raise HTTPException(status_code=404, detail="Not Found")

        return FileResponse(INDEX_HTML_PATH)
else:
    @app.get("/")
    async def serve_index_root_missing():
        return {"detail": "frontend static not built"}
