from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
import os
import sys
from dotenv import load_dotenv

# ---- sys.path к корню проекта ----
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# ---- .env ----
load_dotenv()

# ---- Alembic Config ----
config = context.config

# ---- Готовим DATABASE URL (поддержка двух вариантов) ----
db_url = os.getenv("DATABASE_URL")
if not db_url:
    # Фолбэк к POSTGRES_* как в backend/bd/database.py
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "55432")
    user = os.getenv("POSTGRES_USER", "myuser")
    pwd  = os.getenv("POSTGRES_PASSWORD", "mypass")
    name = os.getenv("POSTGRES_DB", "mydb")
    db_url = f"postgresql://{user}:{pwd}@{host}:{port}/{name}"

config.set_main_option("sqlalchemy.url", db_url)

# ---- Логи alembic ----
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---- ВАЖНО: импортируем единый Base и ВСЕ модели ----
from backend.bd.database import Base  # единый Base
# сам импорт модуля с моделями регистрирует классы в Base.metadata
from backend.bd import models          # старые модели (users, restaurants, и т.д.)
from backend.bd import iiko_olap       # новая модель iiko_olap_rows (если вынесена отдельно)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Offline режим: без Engine, только URL."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Online режим: создаём Engine и подключаемся."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
