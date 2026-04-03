from __future__ import annotations

import logging
import os

from backend.bd.database import SessionLocal
from backend.bd.models import Permission, User
from backend.services.permissions import PermissionKey
from backend.tasks.task_locks import try_task_lock
from backend.utils import hash_password

logger = logging.getLogger(__name__)

STARTUP_BOOTSTRAP_LOCK_KEY = 810000
_FALSE_VALUES = {"0", "false", "no", "off"}


def _bootstrap_enabled() -> bool:
    raw = (os.getenv("AUTO_BOOTSTRAP_ON_STARTUP") or "true").strip().lower()
    return raw not in _FALSE_VALUES


def _get_default_permission_payloads() -> list[dict[str, str]]:
    return [
        {
            "api_router": PermissionKey.STAFF_EMPLOYEES_IIKO_SYNC,
            "router_description": "Синхронизация сотрудников с iiko",
            "comment": "Право на создание/обновление сотрудника в iiko из раздела сотрудников",
            "display_name": "Синхронизация сотрудников с iiko",
            "responsibility_zone": "Сотрудники",
        },
        {
            "api_router": PermissionKey.STAFF_EMPLOYEE_ORDERS_MANAGE,
            "router_description": "Кадровые изменения сотрудников",
            "comment": "Создание, отмена и применение кадровых изменений сотрудника с датой вступления в силу.",
            "display_name": "Кадровые изменения сотрудников",
            "responsibility_zone": "Сотрудники",
        },
        {
            "api_router": PermissionKey.POSITIONS_CHANGE_ORDERS_MANAGE,
            "router_description": "Кадровые изменения должностей",
            "comment": "Создание, отмена и применение отложенных изменений ставок должностей с датой вступления в силу.",
            "display_name": "Кадровые изменения должностей",
            "responsibility_zone": "Доступ",
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


def _create_default_admin(db) -> bool:
    username = (os.getenv("DEFAULT_USERNAME") or "").strip()
    password = (os.getenv("DEFAULT_PASSWORD") or "").strip()
    if not username or not password:
        return False

    existing = db.query(User.id).filter(User.username == username).first()
    if existing:
        return False

    db.add(
        User(
            username=username,
            hashed_password=hash_password(password),
        )
    )
    return True


def _ensure_default_permissions(db) -> int:
    created = 0
    for payload in _get_default_permission_payloads():
        existing = (
            db.query(Permission.id)
            .filter(Permission.api_router == payload["api_router"])
            .first()
        )
        if existing:
            continue
        db.add(Permission(**payload))
        created += 1
    return created


def run_startup_bootstrap() -> None:
    if not _bootstrap_enabled():
        logger.info("Startup bootstrap is disabled by AUTO_BOOTSTRAP_ON_STARTUP")
        return

    with SessionLocal() as db:
        try:
            with try_task_lock(db, STARTUP_BOOTSTRAP_LOCK_KEY) as acquired:
                if not acquired:
                    logger.debug("Skipping startup bootstrap: lock is already held")
                    return

                admin_created = _create_default_admin(db)
                permissions_created = _ensure_default_permissions(db)

                if admin_created or permissions_created:
                    db.commit()
                    logger.info(
                        "Startup bootstrap applied: admin_created=%s, permissions_created=%s",
                        admin_created,
                        permissions_created,
                    )
                else:
                    db.rollback()
                    logger.debug("Startup bootstrap skipped: nothing to seed")
        except Exception:
            db.rollback()
            logger.exception("Startup bootstrap failed")
