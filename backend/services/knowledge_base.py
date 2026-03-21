"""Helpers for the knowledge base module."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.bd.models import (
    KnowledgeBaseAuditLog,
    KnowledgeBaseDocument,
    KnowledgeBaseDocumentVersion,
    KnowledgeBaseFolder,
    User,
)
from backend.services.s3 import generate_presigned_url, generate_presigned_url_for_knowledge_base


DEFAULT_FOLDER_STYLE_KEY = "amber"
KNOWLEDGE_BASE_FOLDER_STYLES = [
    {"key": "amber", "label": "Янтарный", "accent": "#d78a2f"},
    {"key": "sky", "label": "Небесный", "accent": "#4d9de0"},
    {"key": "mint", "label": "Мятный", "accent": "#3cb48f"},
    {"key": "rose", "label": "Розовый", "accent": "#cf5a7a"},
    {"key": "violet", "label": "Фиолетовый", "accent": "#7a68d1"},
    {"key": "slate", "label": "Графитовый", "accent": "#6f7a87"},
    {"key": "sunset", "label": "Закатный", "accent": "#da634a"},
    {"key": "forest", "label": "Лесной", "accent": "#2f8c4f"},
]

_FOLDER_STYLE_KEYS = {item["key"] for item in KNOWLEDGE_BASE_FOLDER_STYLES}
_SPREADSHEET_EXTENSIONS = {"xls", "xlsx", "xlsm", "csv", "ods"}


def normalize_name(value: str) -> str:
    normalized = " ".join((value or "").strip().split())
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Название не может быть пустым")
    if len(normalized) > 255:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Название слишком длинное")
    return normalized


def validate_folder_style(style_key: str | None) -> str:
    candidate = (style_key or "").strip().lower()
    if not candidate:
        return DEFAULT_FOLDER_STYLE_KEY
    if candidate not in _FOLDER_STYLE_KEYS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неподдерживаемый стиль папки")
    return candidate


def get_folder_or_404(db: Session, folder_id: int) -> KnowledgeBaseFolder:
    folder = db.query(KnowledgeBaseFolder).filter(KnowledgeBaseFolder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Папка не найдена")
    return folder


def get_document_or_404(db: Session, document_id: int) -> KnowledgeBaseDocument:
    document = db.query(KnowledgeBaseDocument).filter(KnowledgeBaseDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")
    return document


def assert_unique_item_name(
    db: Session,
    *,
    parent_id: int | None,
    name: str,
    exclude_folder_id: int | None = None,
    exclude_document_id: int | None = None,
) -> None:
    lowered = name.lower()

    folder_query = db.query(KnowledgeBaseFolder.id).filter(func.lower(KnowledgeBaseFolder.name) == lowered)
    if parent_id is None:
        folder_query = folder_query.filter(KnowledgeBaseFolder.parent_id.is_(None))
    else:
        folder_query = folder_query.filter(KnowledgeBaseFolder.parent_id == parent_id)
    if exclude_folder_id is not None:
        folder_query = folder_query.filter(KnowledgeBaseFolder.id != exclude_folder_id)
    if folder_query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Элемент с таким названием уже существует в этой папке",
        )

    document_query = db.query(KnowledgeBaseDocument.id).filter(func.lower(KnowledgeBaseDocument.name) == lowered)
    if parent_id is None:
        document_query = document_query.filter(KnowledgeBaseDocument.folder_id.is_(None))
    else:
        document_query = document_query.filter(KnowledgeBaseDocument.folder_id == parent_id)
    if exclude_document_id is not None:
        document_query = document_query.filter(KnowledgeBaseDocument.id != exclude_document_id)
    if document_query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Элемент с таким названием уже существует в этой папке",
        )


def is_folder_descendant(db: Session, *, folder_id: int, parent_candidate_id: int | None) -> bool:
    """Check whether parent_candidate_id is folder itself or one of its descendants."""
    if parent_candidate_id is None:
        return False

    target_id = int(folder_id)
    current: int | None = int(parent_candidate_id)
    visited: set[int] = set()

    while current is not None and current not in visited:
        if current == target_id:
            return True
        visited.add(current)
        parent_id = (
            db.query(KnowledgeBaseFolder.parent_id)
            .filter(KnowledgeBaseFolder.id == current)
            .scalar()
        )
        current = int(parent_id) if parent_id is not None else None
    return False


def collect_descendant_folder_ids(db: Session, folder_id: int) -> set[int]:
    collected: set[int] = set()
    frontier: set[int] = {int(folder_id)}

    while frontier:
        frontier = {folder for folder in frontier if folder not in collected}
        if not frontier:
            break

        collected.update(frontier)
        child_rows = (
            db.query(KnowledgeBaseFolder.id)
            .filter(KnowledgeBaseFolder.parent_id.in_(frontier))
            .all()
        )
        frontier = {
            int(row.id)
            for row in child_rows
            if row.id is not None and int(row.id) not in collected
        }
    return collected


def build_breadcrumbs(db: Session, folder_id: int | None) -> list[tuple[int | None, str]]:
    breadcrumbs: list[tuple[int | None, str]] = [(None, "Главная")]
    if folder_id is None:
        return breadcrumbs

    chain: list[tuple[int | None, str]] = []
    current: int | None = int(folder_id)
    visited: set[int] = set()

    while current is not None:
        if current in visited:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Обнаружен циклический путь папок")
        visited.add(current)

        row = (
            db.query(KnowledgeBaseFolder.id, KnowledgeBaseFolder.parent_id, KnowledgeBaseFolder.name)
            .filter(KnowledgeBaseFolder.id == current)
            .first()
        )
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Папка не найдена")

        chain.append((int(row.id), row.name))
        current = int(row.parent_id) if row.parent_id is not None else None

    chain.reverse()
    breadcrumbs.extend(chain)
    return breadcrumbs

def build_user_name_map(db: Session, user_ids: Iterable[int | None]) -> dict[int, str]:
    normalized_ids = sorted({int(user_id) for user_id in user_ids if user_id is not None})
    if not normalized_ids:
        return {}
    rows = (
        db.query(User.id, User.first_name, User.last_name, User.username)
        .filter(User.id.in_(normalized_ids))
        .all()
    )
    result: dict[int, str] = {}
    for row in rows:
        full_name = " ".join(part for part in [(row.first_name or "").strip(), (row.last_name or "").strip()] if part)
        result[int(row.id)] = full_name or (row.username or f"Пользователь #{row.id}")
    return result


def resolve_preview_type(document: KnowledgeBaseDocument) -> str:
    if document.document_type == "text":
        return "text"
    extension = ((document.extension or "").strip().lower()).lstrip(".")
    mime_type = (document.mime_type or "").strip().lower()
    if extension == "pdf" or mime_type == "application/pdf":
        return "pdf"
    if (
        extension in _SPREADSHEET_EXTENSIONS
        or "spreadsheet" in mime_type
        or "excel" in mime_type
        or mime_type == "text/csv"
    ):
        return "spreadsheet"
    return "file"


def resolve_document_download_url(document: KnowledgeBaseDocument) -> str | None:
    key = (document.storage_key or "").strip()
    if not key:
        return None
    try:
        return generate_presigned_url_for_knowledge_base(key)
    except Exception:
        try:
            return generate_presigned_url(key)
        except Exception:
            return None


def get_file_extension(filename: str | None) -> str | None:
    if not filename:
        return None
    suffix = Path(filename).suffix.lower().lstrip(".")
    return suffix or None


def log_audit_event(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    action: str,
    created_by_user_id: int | None,
    payload: dict | None = None,
) -> KnowledgeBaseAuditLog:
    record = KnowledgeBaseAuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        created_by_user_id=created_by_user_id,
        payload=payload or None,
    )
    db.add(record)
    return record


def create_document_version(
    db: Session,
    *,
    document: KnowledgeBaseDocument,
    created_by_user_id: int | None,
    comment: str | None = None,
) -> KnowledgeBaseDocumentVersion:
    current_version = (
        db.query(func.max(KnowledgeBaseDocumentVersion.version_number))
        .filter(KnowledgeBaseDocumentVersion.document_id == document.id)
        .scalar()
    )
    version = KnowledgeBaseDocumentVersion(
        document_id=document.id,
        version_number=int(current_version or 0) + 1,
        document_type=document.document_type,
        name=document.name,
        mime_type=document.mime_type,
        extension=document.extension,
        file_size=document.file_size,
        storage_key=document.storage_key,
        content_text=document.content_text,
        comment=(comment or "").strip() or None,
        created_by_user_id=created_by_user_id,
    )
    db.add(version)
    return version
