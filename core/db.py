import os
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

# Загружаем .env из корня проекта SkladBot
load_dotenv()





def _env_value(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    trimmed = value.strip()
    return trimmed or default


def _build_db_url() -> str:
    url = _env_value("DATABASE_URL")
    if url:
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        return url

    host = _env_value("POSTGRES_HOST", "localhost")
    port_raw = _env_value("POSTGRES_PORT")
    try:
        port = int(port_raw) if port_raw else 5432
    except (TypeError, ValueError):
        port = 5432
    user = _env_value("POSTGRES_USER", "postgres")
    password = _env_value("POSTGRES_PASSWORD") or None
    database = _env_value("POSTGRES_DB", "postgres")
    sslmode = _env_value("POSTGRES_SSLMODE")

    url_obj = URL.create(
        "postgresql+psycopg2",
        username=user,
        password=password,
        host=host,
        port=port,
        database=database,
        query={"sslmode": sslmode} if sslmode else None,
    )
    return url_obj.render_as_string(hide_password=False)

DATABASE_URL = _build_db_url()

# Создаём engine и сессию
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # автоматически пингует соединения
    future=True,             # современный стиль SQLAlchemy 2.x
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def get_session():
    """Контекстная сессия для FastAPI/скриптов (если понадобится)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def db_version() -> Optional[str]:
    """Вернёт версию сервера PostgreSQL, либо None при ошибке."""
    try:
        with engine.connect() as conn:
            return conn.execute(text("select version()")).scalar_one()
    except Exception:
        return None
