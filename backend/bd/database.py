from collections.abc import Generator
from typing import Any
from sqlalchemy.orm import Session, sessionmaker, declarative_base
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

# Load local .env; in Docker vars come from the container environment
load_dotenv()


# Prefer full URL if provided
DATABASE_URL = os.getenv("DATABASE_URL")


def _require_env(name: str, *, message: str | None = None) -> str:
    value = (os.getenv(name) or "").strip()
    if value:
        return value
    raise RuntimeError(message or f"{name} must be set")


if not DATABASE_URL:
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "zion_user")
    POSTGRES_PASSWORD = _require_env(
        "POSTGRES_PASSWORD",
        message="POSTGRES_PASSWORD must be set when DATABASE_URL is not configured",
    )
    POSTGRES_DB = os.getenv("POSTGRES_DB", "zion")

    DATABASE_URL = (
        f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL resolved to an empty value")

DATABASE_URL = DATABASE_URL.strip()
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL resolved to an empty value")


def _env_int(name: str, default: int, min_value: int = 0) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= min_value else min_value


engine_options: dict[str, Any] = {
    "pool_pre_ping": True,
    "future": True,
}

if not DATABASE_URL.startswith("sqlite"):
    # Tunable PostgreSQL pool settings for production workloads.
    engine_options.update(
        {
            # These values are per backend worker process.
            # Keep defaults conservative to avoid exhausting postgres max_connections.
            "pool_size": _env_int("DB_POOL_SIZE", 6, 1),
            "max_overflow": _env_int("DB_POOL_MAX_OVERFLOW", 3, 0),
            "pool_timeout": _env_int("DB_POOL_TIMEOUT", 30, 1),
            "pool_recycle": _env_int("DB_POOL_RECYCLE", 1800, 30),
            "pool_use_lifo": True,
        }
    )

engine = create_engine(DATABASE_URL, **engine_options)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
