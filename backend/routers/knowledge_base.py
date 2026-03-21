from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, load_only

from backend.bd.database import get_db
from backend.bd.models import (
    KnowledgeBaseAuditLog,
    KnowledgeBaseDocument,
    KnowledgeBaseDocumentVersion,
    KnowledgeBaseFolder,
    KnowledgeBaseFolderAccessRule,
    Position,
    Restaurant,
    Role,
    User,
)
from backend.schemas.knowledge_base import (
    KnowledgeBaseAccessOption,
    KnowledgeBaseAccessOptionsResponse,
    KnowledgeBaseAuditLogRead,
    KnowledgeBaseBootstrapResponse,
    KnowledgeBaseBreadcrumbItem,
    KnowledgeBaseDocumentContentUpdate,
    KnowledgeBaseDocumentHistoryResponse,
    KnowledgeBaseDocumentRead,
    KnowledgeBaseDocumentUpdate,
    KnowledgeBaseDocumentVersionRead,
    KnowledgeBaseDownloadResponse,
    KnowledgeBaseFolderCreate,
    KnowledgeBaseFolderAccessRead,
    KnowledgeBaseFolderAccessSelection,
    KnowledgeBaseFolderRead,
    KnowledgeBaseFolderStyle,
    KnowledgeBaseFolderUpdate,
    KnowledgeBaseFolderTreeNode,
    KnowledgeBaseItemRead,
    KnowledgeBaseListResponse,
    KnowledgeBaseTextDocumentCreate,
)
from backend.services.knowledge_base import (
    KNOWLEDGE_BASE_FOLDER_STYLES,
    assert_unique_item_name,
    build_breadcrumbs,
    build_user_name_map,
    collect_descendant_folder_ids,
    create_document_version,
    get_document_or_404,
    get_file_extension,
    get_folder_or_404,
    is_folder_descendant,
    log_audit_event,
    normalize_name,
    resolve_document_download_url,
    resolve_preview_type,
    validate_folder_style,
)
from backend.services.permissions import PermissionKey, ensure_permissions, has_global_access, has_permission
from backend.services.s3 import upload_bytes_for_knowledge_base
from backend.utils import get_current_user

router = APIRouter(prefix="/knowledge-base", tags=["Knowledge base"])

KNOWLEDGE_BASE_S3_PREFIX = (os.getenv("KNOWLEDGE_BASE_S3_PREFIX") or "knowledge_base").strip("/") or "knowledge_base"
KNOWLEDGE_BASE_MAX_FILE_SIZE_MB = max(int(os.getenv("KNOWLEDGE_BASE_MAX_FILE_SIZE_MB", "25")), 1)
KNOWLEDGE_BASE_MAX_FILE_SIZE_BYTES = KNOWLEDGE_BASE_MAX_FILE_SIZE_MB * 1024 * 1024

FOLDER_BASE_LOAD_ONLY = (
    KnowledgeBaseFolder.id,
    KnowledgeBaseFolder.parent_id,
    KnowledgeBaseFolder.name,
    KnowledgeBaseFolder.style_key,
)

DOCUMENT_TREE_LOAD_ONLY = (
    KnowledgeBaseDocument.id,
    KnowledgeBaseDocument.folder_id,
    KnowledgeBaseDocument.name,
    KnowledgeBaseDocument.document_type,
    KnowledgeBaseDocument.mime_type,
    KnowledgeBaseDocument.extension,
    KnowledgeBaseDocument.file_size,
)

FOLDER_ITEM_LOAD_ONLY = (
    KnowledgeBaseFolder.id,
    KnowledgeBaseFolder.parent_id,
    KnowledgeBaseFolder.name,
    KnowledgeBaseFolder.style_key,
    KnowledgeBaseFolder.created_by_user_id,
    KnowledgeBaseFolder.updated_by_user_id,
    KnowledgeBaseFolder.created_at,
    KnowledgeBaseFolder.updated_at,
)

DOCUMENT_ITEM_LOAD_ONLY = (
    KnowledgeBaseDocument.id,
    KnowledgeBaseDocument.folder_id,
    KnowledgeBaseDocument.name,
    KnowledgeBaseDocument.document_type,
    KnowledgeBaseDocument.mime_type,
    KnowledgeBaseDocument.extension,
    KnowledgeBaseDocument.file_size,
    KnowledgeBaseDocument.created_by_user_id,
    KnowledgeBaseDocument.updated_by_user_id,
    KnowledgeBaseDocument.created_at,
    KnowledgeBaseDocument.updated_at,
)


def _ensure_can_view(user: User) -> None:
    ensure_permissions(user, PermissionKey.KNOWLEDGE_BASE_SECTION)


def _ensure_can_manage(user: User) -> None:
    ensure_permissions(user, PermissionKey.KNOWLEDGE_BASE_SECTION)


def _ensure_can_upload(user: User) -> None:
    ensure_permissions(user, PermissionKey.KNOWLEDGE_BASE_SECTION)


def _to_folder_read(
    folder: KnowledgeBaseFolder,
    *,
    user_map: dict[int, str],
    children_count: int = 0,
    documents_count: int = 0,
    include_access: bool = False,
) -> KnowledgeBaseFolderRead:
    return KnowledgeBaseFolderRead(
        id=folder.id,
        parent_id=folder.parent_id,
        name=folder.name,
        style_key=folder.style_key,
        created_by_user_id=folder.created_by_user_id,
        created_by_name=user_map.get(folder.created_by_user_id or -1),
        updated_by_user_id=folder.updated_by_user_id,
        updated_by_name=user_map.get(folder.updated_by_user_id or -1),
        created_at=folder.created_at,
        updated_at=folder.updated_at,
        children_count=children_count,
        documents_count=documents_count,
        access=_folder_access_to_selection(folder) if include_access else None,
    )


def _to_document_read(
    db: Session,
    document: KnowledgeBaseDocument,
    *,
    user_map: dict[int, str],
) -> KnowledgeBaseDocumentRead:
    latest_version_number = (
        db.query(func.max(KnowledgeBaseDocumentVersion.version_number))
        .filter(KnowledgeBaseDocumentVersion.document_id == document.id)
        .scalar()
    )
    preview_type = resolve_preview_type(document)
    download_url = resolve_document_download_url(document) if document.document_type == "file" else None
    return KnowledgeBaseDocumentRead(
        id=document.id,
        folder_id=document.folder_id,
        name=document.name,
        document_type=document.document_type,
        mime_type=document.mime_type,
        extension=document.extension,
        file_size=document.file_size,
        storage_key=document.storage_key,
        content_text=document.content_text if document.document_type == "text" else None,
        preview_type=preview_type,
        download_url=download_url,
        latest_version_number=int(latest_version_number) if latest_version_number is not None else None,
        created_by_user_id=document.created_by_user_id,
        created_by_name=user_map.get(document.created_by_user_id or -1),
        updated_by_user_id=document.updated_by_user_id,
        updated_by_name=user_map.get(document.updated_by_user_id or -1),
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _to_item_from_folder(folder: KnowledgeBaseFolder, *, user_map: dict[int, str]) -> KnowledgeBaseItemRead:
    return KnowledgeBaseItemRead(
        id=folder.id,
        item_type="folder",
        name=folder.name,
        parent_id=folder.parent_id,
        style_key=folder.style_key,
        created_by_user_id=folder.created_by_user_id,
        created_by_name=user_map.get(folder.created_by_user_id or -1),
        updated_by_user_id=folder.updated_by_user_id,
        updated_by_name=user_map.get(folder.updated_by_user_id or -1),
        created_at=folder.created_at,
        updated_at=folder.updated_at,
    )


def _to_item_from_document(document: KnowledgeBaseDocument, *, user_map: dict[int, str]) -> KnowledgeBaseItemRead:
    return KnowledgeBaseItemRead(
        id=document.id,
        item_type="document",
        name=document.name,
        parent_id=document.folder_id,
        document_type=document.document_type,
        mime_type=document.mime_type,
        extension=document.extension,
        file_size=document.file_size,
        preview_type=resolve_preview_type(document),
        created_by_user_id=document.created_by_user_id,
        created_by_name=user_map.get(document.created_by_user_id or -1),
        updated_by_user_id=document.updated_by_user_id,
        updated_by_name=user_map.get(document.updated_by_user_id or -1),
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _folder_counts(db: Session, folder_ids: list[int]) -> tuple[dict[int, int], dict[int, int]]:
    if not folder_ids:
        return {}, {}
    children_rows = (
        db.query(KnowledgeBaseFolder.parent_id, func.count(KnowledgeBaseFolder.id))
        .filter(KnowledgeBaseFolder.parent_id.in_(folder_ids))
        .group_by(KnowledgeBaseFolder.parent_id)
        .all()
    )
    document_rows = (
        db.query(KnowledgeBaseDocument.folder_id, func.count(KnowledgeBaseDocument.id))
        .filter(KnowledgeBaseDocument.folder_id.in_(folder_ids))
        .group_by(KnowledgeBaseDocument.folder_id)
        .all()
    )
    children_count_map = {int(parent_id): int(count) for parent_id, count in children_rows if parent_id is not None}
    documents_count_map = {int(folder_id): int(count) for folder_id, count in document_rows if folder_id is not None}
    return children_count_map, documents_count_map


def _normalize_upload_filename(value: str | None) -> str:
    candidate = Path((value or "").strip()).name
    if not candidate:
        candidate = f"file-{uuid4().hex}.bin"
    clean = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in candidate)
    return clean or f"file-{uuid4().hex}.bin"


def _map_audit_rows(rows: list[KnowledgeBaseAuditLog], user_map: dict[int, str]) -> list[KnowledgeBaseAuditLogRead]:
    return [
        KnowledgeBaseAuditLogRead(
            id=row.id,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            action=row.action,
            payload=row.payload,
            created_by_user_id=row.created_by_user_id,
            created_by_name=user_map.get(row.created_by_user_id or -1),
            created_at=row.created_at,
        )
        for row in rows
    ]


def _map_version_rows(
    rows: list[KnowledgeBaseDocumentVersion],
    user_map: dict[int, str],
) -> list[KnowledgeBaseDocumentVersionRead]:
    return [
        KnowledgeBaseDocumentVersionRead(
            id=row.id,
            document_id=row.document_id,
            version_number=row.version_number,
            document_type=row.document_type,
            name=row.name,
            mime_type=row.mime_type,
            extension=row.extension,
            file_size=row.file_size,
            storage_key=row.storage_key,
            content_text=row.content_text,
            comment=row.comment,
            created_by_user_id=row.created_by_user_id,
            created_by_name=user_map.get(row.created_by_user_id or -1),
            created_at=row.created_at,
        )
        for row in rows
    ]


def _normalize_id_list(values: list[int] | None) -> list[int]:
    if not values:
        return []
    normalized: set[int] = set()
    for value in values:
        try:
            parsed = int(value)
        except Exception:
            continue
        if parsed > 0:
            normalized.add(parsed)
    return sorted(normalized)


def _validate_existing_ids(db: Session, model, ids: list[int], *, label: str) -> list[int]:
    if not ids:
        return []
    existing_ids = {
        int(row[0])
        for row in db.query(model.id).filter(model.id.in_(ids)).all()
        if row and row[0] is not None
    }
    missing_ids = sorted(set(ids).difference(existing_ids))
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Не найдены {label}: {', '.join(str(item) for item in missing_ids)}",
        )
    return sorted(existing_ids)


def _resolve_access_selection(
    db: Session,
    payload: KnowledgeBaseFolderAccessSelection | None,
) -> KnowledgeBaseFolderAccessSelection:
    if payload is None:
        return KnowledgeBaseFolderAccessSelection()
    role_ids = _validate_existing_ids(db, Role, _normalize_id_list(payload.role_ids), label="роли")
    position_ids = _validate_existing_ids(db, Position, _normalize_id_list(payload.position_ids), label="должности")
    user_ids = _validate_existing_ids(db, User, _normalize_id_list(payload.user_ids), label="сотрудники")
    restaurant_ids = _validate_existing_ids(db, Restaurant, _normalize_id_list(payload.restaurant_ids), label="рестораны")
    return KnowledgeBaseFolderAccessSelection(
        role_ids=role_ids,
        position_ids=position_ids,
        user_ids=user_ids,
        restaurant_ids=restaurant_ids,
    )


def _folder_access_to_selection(folder: KnowledgeBaseFolder) -> KnowledgeBaseFolderAccessSelection:
    role_ids: set[int] = set()
    position_ids: set[int] = set()
    user_ids: set[int] = set()
    restaurant_ids: set[int] = set()
    for rule in folder.access_rules or []:
        try:
            scope_id = int(rule.scope_id)
        except Exception:
            continue
        if scope_id <= 0:
            continue
        if rule.scope_type == "role":
            role_ids.add(scope_id)
        elif rule.scope_type == "position":
            position_ids.add(scope_id)
        elif rule.scope_type == "user":
            user_ids.add(scope_id)
        elif rule.scope_type == "restaurant":
            restaurant_ids.add(scope_id)
    return KnowledgeBaseFolderAccessSelection(
        role_ids=sorted(role_ids),
        position_ids=sorted(position_ids),
        user_ids=sorted(user_ids),
        restaurant_ids=sorted(restaurant_ids),
    )


def _replace_folder_access_rules(
    db: Session,
    folder: KnowledgeBaseFolder,
    *,
    access: KnowledgeBaseFolderAccessSelection,
    actor_user_id: int | None,
) -> bool:
    desired_keys = {
        ("role", int(scope_id)) for scope_id in access.role_ids
    } | {
        ("position", int(scope_id)) for scope_id in access.position_ids
    } | {
        ("user", int(scope_id)) for scope_id in access.user_ids
    } | {
        ("restaurant", int(scope_id)) for scope_id in access.restaurant_ids
    }

    existing_map = {
        (str(rule.scope_type), int(rule.scope_id)): rule
        for rule in (folder.access_rules or [])
    }
    changed = False

    for key, rule in existing_map.items():
        if key in desired_keys:
            continue
        db.delete(rule)
        changed = True

    for scope_type, scope_id in desired_keys:
        if (scope_type, scope_id) in existing_map:
            continue
        db.add(
            KnowledgeBaseFolderAccessRule(
                folder_id=folder.id,
                scope_type=scope_type,
                scope_id=scope_id,
                created_by_user_id=actor_user_id,
            )
        )
        changed = True

    return changed


def _build_user_access_scope(user: User) -> dict[str, object]:
    role_id = user.role_id or getattr(getattr(user, "position", None), "role_id", None)
    position_id = user.position_id
    restaurant_ids = {
        int(restaurant.id)
        for restaurant in (user.restaurants or [])
        if getattr(restaurant, "id", None) is not None
    }
    if getattr(user, "workplace_restaurant_id", None):
        restaurant_ids.add(int(user.workplace_restaurant_id))
    return {
        "role_ids": {int(role_id)} if role_id else set(),
        "position_ids": {int(position_id)} if position_id else set(),
        "user_ids": {int(user.id)} if getattr(user, "id", None) else set(),
        "restaurant_ids": restaurant_ids,
        "restaurant_all": bool(getattr(user, "has_full_restaurant_access", False)),
    }


def _resolve_accessible_folder_ids(db: Session, user: User) -> set[int] | None:
    if has_global_access(user):
        return None

    folder_rows = db.query(KnowledgeBaseFolder.id, KnowledgeBaseFolder.parent_id).all()
    parent_map = {
        int(row.id): (int(row.parent_id) if row.parent_id is not None else None)
        for row in folder_rows
    }

    folders_with_rules = {
        int(folder_id)
        for (folder_id,) in db.query(KnowledgeBaseFolderAccessRule.folder_id)
        .distinct()
        .all()
        if folder_id is not None
    }

    scope = _build_user_access_scope(user)
    matched_rule_clauses = []
    role_ids = sorted(int(item) for item in scope["role_ids"])
    if role_ids:
        matched_rule_clauses.append(
            and_(
                KnowledgeBaseFolderAccessRule.scope_type == "role",
                KnowledgeBaseFolderAccessRule.scope_id.in_(role_ids),
            )
        )

    position_ids = sorted(int(item) for item in scope["position_ids"])
    if position_ids:
        matched_rule_clauses.append(
            and_(
                KnowledgeBaseFolderAccessRule.scope_type == "position",
                KnowledgeBaseFolderAccessRule.scope_id.in_(position_ids),
            )
        )

    user_ids = sorted(int(item) for item in scope["user_ids"])
    if user_ids:
        matched_rule_clauses.append(
            and_(
                KnowledgeBaseFolderAccessRule.scope_type == "user",
                KnowledgeBaseFolderAccessRule.scope_id.in_(user_ids),
            )
        )

    if bool(scope["restaurant_all"]):
        matched_rule_clauses.append(KnowledgeBaseFolderAccessRule.scope_type == "restaurant")
    else:
        restaurant_ids = sorted(int(item) for item in scope["restaurant_ids"])
        if restaurant_ids:
            matched_rule_clauses.append(
                and_(
                    KnowledgeBaseFolderAccessRule.scope_type == "restaurant",
                    KnowledgeBaseFolderAccessRule.scope_id.in_(restaurant_ids),
                )
            )

    matched_rule_folders: set[int] = set()
    if matched_rule_clauses:
        matched_rule_folders = {
            int(folder_id)
            for (folder_id,) in db.query(KnowledgeBaseFolderAccessRule.folder_id)
            .filter(or_(*matched_rule_clauses))
            .distinct()
            .all()
            if folder_id is not None
        }

    memo: dict[int, bool] = {}

    def is_accessible(folder_id: int) -> bool:
        if folder_id in memo:
            return memo[folder_id]

        parent_id = parent_map.get(folder_id)
        if parent_id is not None and not is_accessible(parent_id):
            memo[folder_id] = False
            return False

        if folder_id not in folders_with_rules:
            memo[folder_id] = True
            return True

        allowed = folder_id in matched_rule_folders
        memo[folder_id] = allowed
        return allowed

    return {folder_id for folder_id in parent_map if is_accessible(folder_id)}


def _ensure_folder_allowed(
    db: Session,
    user: User,
    folder_id: int | None,
    *,
    accessible_folder_ids: set[int] | None = None,
) -> None:
    if folder_id is None:
        return
    resolved_ids = accessible_folder_ids if accessible_folder_ids is not None else _resolve_accessible_folder_ids(db, user)
    if resolved_ids is None:
        return
    if int(folder_id) not in resolved_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к папке")


def _ensure_document_allowed(
    db: Session,
    user: User,
    document: KnowledgeBaseDocument,
    *,
    accessible_folder_ids: set[int] | None = None,
) -> None:
    _ensure_folder_allowed(
        db,
        user,
        document.folder_id,
        accessible_folder_ids=accessible_folder_ids,
    )


def _to_access_options(rows: list[tuple[int, str]]) -> list[KnowledgeBaseAccessOption]:
    return [
        KnowledgeBaseAccessOption(id=int(item_id), name=(name or "").strip() or f"#{item_id}")
        for item_id, name in rows
        if item_id is not None
    ]


@router.get("/bootstrap", response_model=KnowledgeBaseBootstrapResponse)
def get_bootstrap(current_user: User = Depends(get_current_user)) -> KnowledgeBaseBootstrapResponse:
    _ensure_can_view(current_user)
    folder_styles = [KnowledgeBaseFolderStyle(**style) for style in KNOWLEDGE_BASE_FOLDER_STYLES]
    return KnowledgeBaseBootstrapResponse(
        folder_styles=folder_styles,
        can_view=has_permission(current_user, PermissionKey.KNOWLEDGE_BASE_SECTION),
        can_manage=has_permission(current_user, PermissionKey.KNOWLEDGE_BASE_SECTION),
        can_upload=has_permission(current_user, PermissionKey.KNOWLEDGE_BASE_SECTION),
    )


@router.get("/access/options", response_model=KnowledgeBaseAccessOptionsResponse)
def get_access_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseAccessOptionsResponse:
    _ensure_can_manage(current_user)
    roles_raw = db.query(Role.id, Role.name).order_by(func.lower(Role.name).asc(), Role.id.asc()).all()
    positions_raw = db.query(Position.id, Position.name).order_by(func.lower(Position.name).asc(), Position.id.asc()).all()
    restaurants_raw = (
        db.query(Restaurant.id, Restaurant.name)
        .order_by(func.lower(Restaurant.name).asc(), Restaurant.id.asc())
        .all()
    )
    users_raw = (
        db.query(User.id, User.first_name, User.last_name, User.username)
        .filter(User.fired.is_(False))
        .order_by(func.lower(User.last_name).nullslast(), func.lower(User.first_name).nullslast(), User.id.asc())
        .limit(1000)
        .all()
    )
    user_options = []
    for row in users_raw:
        full_name = " ".join(part for part in [(row.first_name or "").strip(), (row.last_name or "").strip()] if part)
        label = full_name or (row.username or f"Сотрудник #{row.id}")
        user_options.append((int(row.id), label))

    return KnowledgeBaseAccessOptionsResponse(
        roles=_to_access_options(roles_raw),
        positions=_to_access_options(positions_raw),
        users=_to_access_options(user_options),
        restaurants=_to_access_options(restaurants_raw),
    )


@router.get("/folders/{folder_id}/access", response_model=KnowledgeBaseFolderAccessRead)
def get_folder_access(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseFolderAccessRead:
    _ensure_can_manage(current_user)
    folder = get_folder_or_404(db, folder_id)
    _ensure_folder_allowed(db, current_user, folder_id)
    selection = _folder_access_to_selection(folder)
    return KnowledgeBaseFolderAccessRead(folder_id=folder.id, **selection.model_dump())


@router.put("/folders/{folder_id}/access", response_model=KnowledgeBaseFolderAccessRead)
def update_folder_access(
    folder_id: int,
    payload: KnowledgeBaseFolderAccessSelection,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseFolderAccessRead:
    _ensure_can_manage(current_user)
    folder = get_folder_or_404(db, folder_id)
    _ensure_folder_allowed(db, current_user, folder_id)
    access = _resolve_access_selection(db, payload)
    changed = _replace_folder_access_rules(
        db,
        folder,
        access=access,
        actor_user_id=current_user.id,
    )
    if changed:
        folder.updated_by_user_id = current_user.id
        log_audit_event(
            db,
            entity_type="folder",
            entity_id=folder.id,
            action="updated_access",
            created_by_user_id=current_user.id,
            payload=access.model_dump(),
        )
        db.commit()
        db.refresh(folder)
    return KnowledgeBaseFolderAccessRead(folder_id=folder.id, **_folder_access_to_selection(folder).model_dump())


@router.get("/tree", response_model=list[KnowledgeBaseFolderTreeNode])
def get_folder_tree(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[KnowledgeBaseFolderTreeNode]:
    _ensure_can_view(current_user)
    accessible_folder_ids = _resolve_accessible_folder_ids(db, current_user)
    folders = (
        db.query(KnowledgeBaseFolder)
        .options(load_only(*FOLDER_BASE_LOAD_ONLY))
        .order_by(KnowledgeBaseFolder.parent_id.asc().nullsfirst(), func.lower(KnowledgeBaseFolder.name).asc())
        .all()
    )
    if accessible_folder_ids is not None:
        folders = [item for item in folders if item.id in accessible_folder_ids]

    folder_ids = [int(folder.id) for folder in folders if folder.id is not None]
    folder_documents_count: dict[int, int] = {}
    if folder_ids:
        folder_documents_count = {
            int(folder_id): int(count)
            for folder_id, count in (
                db.query(KnowledgeBaseDocument.folder_id, func.count(KnowledgeBaseDocument.id))
                .filter(KnowledgeBaseDocument.folder_id.in_(folder_ids))
                .group_by(KnowledgeBaseDocument.folder_id)
                .all()
            )
            if folder_id is not None
        }

    node_map = {
        folder.id: KnowledgeBaseFolderTreeNode(
            id=folder.id,
            item_type="folder",
            parent_id=folder.parent_id,
            name=folder.name,
            has_documents=bool(folder_documents_count.get(int(folder.id), 0)),
            style_key=folder.style_key,
            children=[],
        )
        for folder in folders
    }

    roots: list[KnowledgeBaseFolderTreeNode] = []
    for folder in folders:
        node = node_map[folder.id]
        if folder.parent_id is None or folder.parent_id not in node_map:
            roots.append(node)
            continue
        node_map[folder.parent_id].children.append(node)

    def sort_nodes(nodes: list[KnowledgeBaseFolderTreeNode]) -> None:
        nodes.sort(key=lambda item: item.name.lower())
        for node in nodes:
            sort_nodes(node.children)

    sort_nodes(roots)
    return roots


@router.get("/tree/documents", response_model=list[KnowledgeBaseFolderTreeNode])
def get_tree_documents(
    folder_id: Optional[int] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[KnowledgeBaseFolderTreeNode]:
    _ensure_can_view(current_user)
    accessible_folder_ids = _resolve_accessible_folder_ids(db, current_user)

    if folder_id is not None:
        _ = get_folder_or_404(db, folder_id)
        _ensure_folder_allowed(db, current_user, folder_id, accessible_folder_ids=accessible_folder_ids)

    query = db.query(KnowledgeBaseDocument).options(load_only(*DOCUMENT_TREE_LOAD_ONLY))
    if folder_id is None:
        query = query.filter(KnowledgeBaseDocument.folder_id.is_(None))
    else:
        query = query.filter(KnowledgeBaseDocument.folder_id == folder_id)

    documents = (
        query
        .order_by(func.lower(KnowledgeBaseDocument.name).asc(), KnowledgeBaseDocument.id.asc())
        .limit(limit)
        .all()
    )

    return [
        KnowledgeBaseFolderTreeNode(
            id=document.id,
            item_type="document",
            parent_id=document.folder_id,
            name=document.name,
            document_type=document.document_type,
            mime_type=document.mime_type,
            extension=document.extension,
            file_size=document.file_size,
            preview_type=resolve_preview_type(document),
            children=[],
        )
        for document in documents
    ]


@router.get("/items", response_model=KnowledgeBaseListResponse)
def list_items(
    folder_id: Optional[int] = Query(None),
    search: str | None = Query(None),
    item_kind: Literal["all", "folder", "document"] = Query("all"),
    document_type: Literal["all", "text", "file"] = Query("all"),
    limit: int = Query(300, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseListResponse:
    _ensure_can_view(current_user)
    accessible_folder_ids = _resolve_accessible_folder_ids(db, current_user)

    if folder_id is not None:
        _ = get_folder_or_404(db, folder_id)
        _ensure_folder_allowed(db, current_user, folder_id, accessible_folder_ids=accessible_folder_ids)

    breadcrumbs_raw = build_breadcrumbs(db, folder_id)
    breadcrumbs = [KnowledgeBaseBreadcrumbItem(id=item_id, name=name) for item_id, name in breadcrumbs_raw]
    search_value = (search or "").strip().lower()
    search_in_text_content = len(search_value) >= 3

    folders: list[KnowledgeBaseFolder] = []
    documents: list[KnowledgeBaseDocument] = []
    scope_folder_ids: set[int] | None = None

    if search_value and folder_id is not None:
        scope_folder_ids = collect_descendant_folder_ids(db, folder_id)
        if accessible_folder_ids is not None:
            scope_folder_ids = scope_folder_ids.intersection(accessible_folder_ids)

    folder_query = None
    document_query = None
    folders_total = 0
    documents_total = 0

    if item_kind in {"all", "folder"}:
        folder_query = db.query(KnowledgeBaseFolder).options(load_only(*FOLDER_ITEM_LOAD_ONLY))
        if search_value:
            folder_query = folder_query.filter(func.lower(KnowledgeBaseFolder.name).like(f"%{search_value}%"))
            if scope_folder_ids is not None:
                folder_query = folder_query.filter(KnowledgeBaseFolder.id.in_(scope_folder_ids))
            elif accessible_folder_ids is not None:
                folder_query = folder_query.filter(KnowledgeBaseFolder.id.in_(accessible_folder_ids))
        else:
            if folder_id is None:
                folder_query = folder_query.filter(KnowledgeBaseFolder.parent_id.is_(None))
            else:
                folder_query = folder_query.filter(KnowledgeBaseFolder.parent_id == folder_id)
            if accessible_folder_ids is not None:
                folder_query = folder_query.filter(KnowledgeBaseFolder.id.in_(accessible_folder_ids))
        folders_total = int(folder_query.with_entities(func.count(KnowledgeBaseFolder.id)).scalar() or 0)

    if item_kind in {"all", "document"}:
        document_query = db.query(KnowledgeBaseDocument).options(load_only(*DOCUMENT_ITEM_LOAD_ONLY))
        if document_type in {"text", "file"}:
            document_query = document_query.filter(KnowledgeBaseDocument.document_type == document_type)
        if search_value:
            search_conditions = [
                func.lower(KnowledgeBaseDocument.name).like(f"%{search_value}%"),
            ]
            if search_in_text_content:
                search_conditions.append(
                    and_(
                        KnowledgeBaseDocument.document_type == "text",
                        func.lower(func.coalesce(KnowledgeBaseDocument.content_text, "")).like(f"%{search_value}%"),
                    )
                )
            document_query = document_query.filter(or_(*search_conditions))
            if scope_folder_ids is not None:
                document_query = document_query.filter(KnowledgeBaseDocument.folder_id.in_(scope_folder_ids))
            elif accessible_folder_ids is not None:
                document_query = document_query.filter(
                    or_(
                        KnowledgeBaseDocument.folder_id.is_(None),
                        KnowledgeBaseDocument.folder_id.in_(accessible_folder_ids),
                    )
                )
        else:
            if folder_id is None:
                document_query = document_query.filter(KnowledgeBaseDocument.folder_id.is_(None))
            else:
                document_query = document_query.filter(KnowledgeBaseDocument.folder_id == folder_id)
        documents_total = int(document_query.with_entities(func.count(KnowledgeBaseDocument.id)).scalar() or 0)

    total = folders_total + documents_total
    current_offset = min(offset, total) if total > 0 else 0

    if search_value:
        fetch_size = max(limit + current_offset + 1, limit + 1)
        if folder_query is not None and fetch_size > 0:
            folders = (
                folder_query
                .order_by(KnowledgeBaseFolder.updated_at.desc(), func.lower(KnowledgeBaseFolder.name).asc())
                .limit(fetch_size)
                .all()
            )
        if document_query is not None and fetch_size > 0:
            documents = (
                document_query
                .order_by(KnowledgeBaseDocument.updated_at.desc(), func.lower(KnowledgeBaseDocument.name).asc())
                .limit(fetch_size)
                .all()
            )
    else:
        remaining = limit
        if folder_query is not None and remaining > 0:
            folder_offset = current_offset
            folder_take = max(min(remaining, max(folders_total - folder_offset, 0)), 0)
            if folder_take > 0:
                folders = (
                    folder_query
                    .order_by(func.lower(KnowledgeBaseFolder.name).asc(), KnowledgeBaseFolder.id.asc())
                    .offset(folder_offset)
                    .limit(folder_take)
                    .all()
                )
                remaining -= len(folders)
        if document_query is not None and remaining > 0:
            if item_kind == "document":
                document_offset = current_offset
            elif item_kind == "folder":
                document_offset = 0
            else:
                document_offset = max(current_offset - folders_total, 0)
            document_take = max(remaining, 0)
            if document_take > 0:
                documents = (
                    document_query
                    .order_by(func.lower(KnowledgeBaseDocument.name).asc(), KnowledgeBaseDocument.id.asc())
                    .offset(document_offset)
                    .limit(document_take)
                    .all()
                )

    user_map = build_user_name_map(
        db,
        [item.created_by_user_id for item in folders]
        + [item.updated_by_user_id for item in folders]
        + [item.created_by_user_id for item in documents]
        + [item.updated_by_user_id for item in documents],
    )

    folder_items = [_to_item_from_folder(folder, user_map=user_map) for folder in folders]
    document_items = [_to_item_from_document(document, user_map=user_map) for document in documents]

    if search_value:
        merged_items = sorted(
            [*folder_items, *document_items],
            key=lambda item: (item.updated_at, item.name.lower()),
            reverse=True,
        )
        items = merged_items[current_offset:current_offset + limit]
    else:
        items = [*folder_items, *document_items]

    has_more = (current_offset + len(items)) < total
    next_offset = (current_offset + len(items)) if has_more else None

    return KnowledgeBaseListResponse(
        folder_id=folder_id,
        breadcrumbs=breadcrumbs,
        items=items,
        total=total,
        offset=current_offset,
        limit=limit,
        has_more=has_more,
        next_offset=next_offset,
    )


@router.post("/folders", response_model=KnowledgeBaseFolderRead, status_code=status.HTTP_201_CREATED)
def create_folder(
    payload: KnowledgeBaseFolderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseFolderRead:
    _ensure_can_manage(current_user)
    parent_id = payload.parent_id
    accessible_folder_ids = _resolve_accessible_folder_ids(db, current_user)
    if parent_id is not None:
        _ = get_folder_or_404(db, parent_id)
        _ensure_folder_allowed(db, current_user, parent_id, accessible_folder_ids=accessible_folder_ids)

    name = normalize_name(payload.name)
    style_key = validate_folder_style(payload.style_key)
    access = _resolve_access_selection(db, payload.access)
    assert_unique_item_name(db, parent_id=parent_id, name=name)

    folder = KnowledgeBaseFolder(
        parent_id=parent_id,
        name=name,
        style_key=style_key,
        created_by_user_id=current_user.id,
        updated_by_user_id=current_user.id,
    )
    db.add(folder)
    db.flush()
    _replace_folder_access_rules(
        db,
        folder,
        access=access,
        actor_user_id=current_user.id,
    )
    log_audit_event(
        db,
        entity_type="folder",
        entity_id=folder.id,
        action="created",
        created_by_user_id=current_user.id,
        payload={
            "name": folder.name,
            "parent_id": folder.parent_id,
            "style_key": folder.style_key,
            "access": access.model_dump(),
        },
    )
    db.commit()
    db.refresh(folder)

    user_map = build_user_name_map(db, [folder.created_by_user_id, folder.updated_by_user_id])
    return _to_folder_read(folder, user_map=user_map)


@router.patch("/folders/{folder_id}", response_model=KnowledgeBaseFolderRead)
def update_folder(
    folder_id: int,
    payload: KnowledgeBaseFolderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseFolderRead:
    _ensure_can_manage(current_user)
    accessible_folder_ids = _resolve_accessible_folder_ids(db, current_user)
    folder = get_folder_or_404(db, folder_id)
    _ensure_folder_allowed(db, current_user, folder_id, accessible_folder_ids=accessible_folder_ids)
    fields_set = getattr(payload, "model_fields_set", set())
    if not fields_set:
        user_map = build_user_name_map(db, [folder.created_by_user_id, folder.updated_by_user_id])
        children_map, docs_map = _folder_counts(db, [folder.id])
        return _to_folder_read(
            folder,
            user_map=user_map,
            children_count=children_map.get(folder.id, 0),
            documents_count=docs_map.get(folder.id, 0),
        )

    next_parent_id = folder.parent_id
    next_name = folder.name
    next_style_key = folder.style_key
    changes: list[dict[str, object]] = []

    if "parent_id" in fields_set:
        if payload.parent_id is not None:
            _ = get_folder_or_404(db, payload.parent_id)
            _ensure_folder_allowed(db, current_user, payload.parent_id, accessible_folder_ids=accessible_folder_ids)
        if is_folder_descendant(db, folder_id=folder.id, parent_candidate_id=payload.parent_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя переместить папку в саму себя или во вложенную папку",
            )
        next_parent_id = payload.parent_id

    if "name" in fields_set and payload.name is not None:
        next_name = normalize_name(payload.name)

    if "style_key" in fields_set:
        next_style_key = validate_folder_style(payload.style_key)

    if next_parent_id != folder.parent_id or next_name.lower() != folder.name.lower():
        assert_unique_item_name(
            db,
            parent_id=next_parent_id,
            name=next_name,
            exclude_folder_id=folder.id,
        )

    if next_name != folder.name:
        changes.append({"field": "name", "old": folder.name, "new": next_name})
        folder.name = next_name
    if next_parent_id != folder.parent_id:
        changes.append({"field": "parent_id", "old": folder.parent_id, "new": next_parent_id})
        folder.parent_id = next_parent_id
    if next_style_key != folder.style_key:
        changes.append({"field": "style_key", "old": folder.style_key, "new": next_style_key})
        folder.style_key = next_style_key

    if changes:
        folder.updated_by_user_id = current_user.id
        for change in changes:
            log_audit_event(
                db,
                entity_type="folder",
                entity_id=folder.id,
                action=f"updated_{change['field']}",
                created_by_user_id=current_user.id,
                payload={"old": change["old"], "new": change["new"]},
            )
        db.commit()
        db.refresh(folder)

    children_map, docs_map = _folder_counts(db, [folder.id])
    user_map = build_user_name_map(db, [folder.created_by_user_id, folder.updated_by_user_id])
    return _to_folder_read(
        folder,
        user_map=user_map,
        children_count=children_map.get(folder.id, 0),
        documents_count=docs_map.get(folder.id, 0),
    )


@router.delete("/folders/{folder_id}")
def delete_folder(
    folder_id: int,
    force: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    _ensure_can_manage(current_user)
    folder = get_folder_or_404(db, folder_id)
    _ensure_folder_allowed(db, current_user, folder_id)
    has_children = db.query(KnowledgeBaseFolder.id).filter(KnowledgeBaseFolder.parent_id == folder_id).first() is not None
    has_documents = db.query(KnowledgeBaseDocument.id).filter(KnowledgeBaseDocument.folder_id == folder_id).first() is not None
    if (has_children or has_documents) and not force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Папка не пуста. Используйте удаление вместе с содержимым.",
        )

    descendant_ids = collect_descendant_folder_ids(db, folder_id)
    document_ids = [
        int(row[0])
        for row in db.query(KnowledgeBaseDocument.id)
        .filter(KnowledgeBaseDocument.folder_id.in_(descendant_ids))
        .all()
    ]
    for document_id in document_ids:
        log_audit_event(
            db,
            entity_type="document",
            entity_id=document_id,
            action="deleted_via_folder",
            created_by_user_id=current_user.id,
            payload={"root_folder_id": folder_id},
        )

    log_audit_event(
        db,
        entity_type="folder",
        entity_id=folder.id,
        action="deleted",
        created_by_user_id=current_user.id,
        payload={
            "force": force,
            "deleted_folders_count": len(descendant_ids),
            "deleted_documents_count": len(document_ids),
        },
    )
    db.delete(folder)
    db.commit()
    return {"ok": True}


@router.get("/folders/{folder_id}", response_model=KnowledgeBaseFolderRead)
def get_folder_info(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseFolderRead:
    _ensure_can_view(current_user)
    folder = get_folder_or_404(db, folder_id)
    _ensure_folder_allowed(db, current_user, folder_id)
    children_map, docs_map = _folder_counts(db, [folder.id])
    user_map = build_user_name_map(db, [folder.created_by_user_id, folder.updated_by_user_id])
    return _to_folder_read(
        folder,
        user_map=user_map,
        children_count=children_map.get(folder.id, 0),
        documents_count=docs_map.get(folder.id, 0),
        include_access=True,
    )


@router.get("/folders/{folder_id}/history", response_model=list[KnowledgeBaseAuditLogRead])
def get_folder_history(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[KnowledgeBaseAuditLogRead]:
    _ensure_can_view(current_user)
    _ = get_folder_or_404(db, folder_id)
    _ensure_folder_allowed(db, current_user, folder_id)
    rows = (
        db.query(KnowledgeBaseAuditLog)
        .filter(
            KnowledgeBaseAuditLog.entity_type == "folder",
            KnowledgeBaseAuditLog.entity_id == folder_id,
        )
        .order_by(KnowledgeBaseAuditLog.created_at.desc(), KnowledgeBaseAuditLog.id.desc())
        .limit(300)
        .all()
    )
    user_map = build_user_name_map(db, [row.created_by_user_id for row in rows])
    return _map_audit_rows(rows, user_map)


@router.post("/documents/text", response_model=KnowledgeBaseDocumentRead, status_code=status.HTTP_201_CREATED)
def create_text_document(
    payload: KnowledgeBaseTextDocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseDocumentRead:
    _ensure_can_manage(current_user)
    accessible_folder_ids = _resolve_accessible_folder_ids(db, current_user)
    if payload.folder_id is not None:
        _ = get_folder_or_404(db, payload.folder_id)
        _ensure_folder_allowed(db, current_user, payload.folder_id, accessible_folder_ids=accessible_folder_ids)

    name = normalize_name(payload.name)
    assert_unique_item_name(db, parent_id=payload.folder_id, name=name)

    document = KnowledgeBaseDocument(
        folder_id=payload.folder_id,
        name=name,
        document_type="text",
        mime_type="text/plain",
        extension="txt",
        content_text=(payload.content or ""),
        created_by_user_id=current_user.id,
        updated_by_user_id=current_user.id,
    )
    db.add(document)
    db.flush()

    version = create_document_version(
        db,
        document=document,
        created_by_user_id=current_user.id,
        comment="Первая версия",
    )
    log_audit_event(
        db,
        entity_type="document",
        entity_id=document.id,
        action="created",
        created_by_user_id=current_user.id,
        payload={"document_type": "text", "version_number": version.version_number},
    )
    db.commit()
    db.refresh(document)

    user_map = build_user_name_map(db, [document.created_by_user_id, document.updated_by_user_id])
    return _to_document_read(db, document, user_map=user_map)


@router.post("/documents/upload", response_model=KnowledgeBaseDocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document_file(
    file: UploadFile = File(...),
    folder_id: Optional[int] = Form(None),
    name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseDocumentRead:
    _ensure_can_upload(current_user)
    accessible_folder_ids = _resolve_accessible_folder_ids(db, current_user)
    if folder_id is not None:
        _ = get_folder_or_404(db, folder_id)
        _ensure_folder_allowed(db, current_user, folder_id, accessible_folder_ids=accessible_folder_ids)

    if not file:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл обязателен")
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Загруженный файл пустой")
    if len(payload) > KNOWLEDGE_BASE_MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Максимальный размер файла: {KNOWLEDGE_BASE_MAX_FILE_SIZE_MB} МБ",
        )

    original_filename = _normalize_upload_filename(file.filename)
    document_name = normalize_name(name or original_filename)
    assert_unique_item_name(db, parent_id=folder_id, name=document_name)

    storage_key = f"{KNOWLEDGE_BASE_S3_PREFIX}/documents/{uuid4().hex}_{original_filename}"
    try:
        upload_bytes_for_knowledge_base(storage_key, payload, file.content_type or "application/octet-stream")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Не удалось загрузить файл") from exc

    extension = get_file_extension(original_filename)
    document = KnowledgeBaseDocument(
        folder_id=folder_id,
        name=document_name,
        document_type="file",
        mime_type=file.content_type or "application/octet-stream",
        extension=extension,
        file_size=len(payload),
        storage_key=storage_key,
        created_by_user_id=current_user.id,
        updated_by_user_id=current_user.id,
    )
    db.add(document)
    db.flush()

    version = create_document_version(
        db,
        document=document,
        created_by_user_id=current_user.id,
        comment="Файл загружен",
    )
    log_audit_event(
        db,
        entity_type="document",
        entity_id=document.id,
        action="uploaded",
        created_by_user_id=current_user.id,
        payload={"version_number": version.version_number, "mime_type": document.mime_type, "file_size": document.file_size},
    )
    db.commit()
    db.refresh(document)

    user_map = build_user_name_map(db, [document.created_by_user_id, document.updated_by_user_id])
    return _to_document_read(db, document, user_map=user_map)


@router.get("/documents/{document_id}", response_model=KnowledgeBaseDocumentRead)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseDocumentRead:
    _ensure_can_view(current_user)
    document = get_document_or_404(db, document_id)
    _ensure_document_allowed(db, current_user, document)
    user_map = build_user_name_map(db, [document.created_by_user_id, document.updated_by_user_id])
    return _to_document_read(db, document, user_map=user_map)


@router.post("/documents/{document_id}/open", response_model=KnowledgeBaseDocumentRead)
def open_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseDocumentRead:
    _ensure_can_view(current_user)
    document = get_document_or_404(db, document_id)
    _ensure_document_allowed(db, current_user, document)
    log_audit_event(
        db,
        entity_type="document",
        entity_id=document.id,
        action="opened",
        created_by_user_id=current_user.id,
    )
    db.commit()
    user_map = build_user_name_map(db, [document.created_by_user_id, document.updated_by_user_id])
    return _to_document_read(db, document, user_map=user_map)


@router.patch("/documents/{document_id}", response_model=KnowledgeBaseDocumentRead)
def update_document(
    document_id: int,
    payload: KnowledgeBaseDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseDocumentRead:
    _ensure_can_manage(current_user)
    document = get_document_or_404(db, document_id)
    accessible_folder_ids = _resolve_accessible_folder_ids(db, current_user)
    _ensure_document_allowed(db, current_user, document, accessible_folder_ids=accessible_folder_ids)
    fields_set = getattr(payload, "model_fields_set", set())
    if not fields_set:
        user_map = build_user_name_map(db, [document.created_by_user_id, document.updated_by_user_id])
        return _to_document_read(db, document, user_map=user_map)

    next_folder_id = document.folder_id
    next_name = document.name

    if "folder_id" in fields_set:
        if payload.folder_id is not None:
            _ = get_folder_or_404(db, payload.folder_id)
            _ensure_folder_allowed(db, current_user, payload.folder_id, accessible_folder_ids=accessible_folder_ids)
        next_folder_id = payload.folder_id
    if "name" in fields_set and payload.name is not None:
        next_name = normalize_name(payload.name)

    if next_folder_id != document.folder_id or next_name.lower() != document.name.lower():
        assert_unique_item_name(
            db,
            parent_id=next_folder_id,
            name=next_name,
            exclude_document_id=document.id,
        )

    changes: list[tuple[str, object, object]] = []
    if next_name != document.name:
        changes.append(("name", document.name, next_name))
        document.name = next_name
    if next_folder_id != document.folder_id:
        changes.append(("folder_id", document.folder_id, next_folder_id))
        document.folder_id = next_folder_id

    if changes:
        document.updated_by_user_id = current_user.id
        for field, old_value, new_value in changes:
            log_audit_event(
                db,
                entity_type="document",
                entity_id=document.id,
                action=f"updated_{field}",
                created_by_user_id=current_user.id,
                payload={"old": old_value, "new": new_value},
            )
        db.commit()
        db.refresh(document)

    user_map = build_user_name_map(db, [document.created_by_user_id, document.updated_by_user_id])
    return _to_document_read(db, document, user_map=user_map)


@router.patch("/documents/{document_id}/content", response_model=KnowledgeBaseDocumentRead)
def update_text_document_content(
    document_id: int,
    payload: KnowledgeBaseDocumentContentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseDocumentRead:
    _ensure_can_manage(current_user)
    document = get_document_or_404(db, document_id)
    _ensure_document_allowed(db, current_user, document)
    if document.document_type != "text":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Редактировать можно только текстовые документы")

    new_content = payload.content or ""
    if new_content != (document.content_text or ""):
        document.content_text = new_content
        document.updated_by_user_id = current_user.id
        version = create_document_version(
            db,
            document=document,
            created_by_user_id=current_user.id,
            comment=payload.comment,
        )
        log_audit_event(
            db,
            entity_type="document",
            entity_id=document.id,
            action="content_updated",
            created_by_user_id=current_user.id,
            payload={
                "version_number": version.version_number,
                "content_size": len(new_content.encode("utf-8")),
                "comment": (payload.comment or "").strip() or None,
            },
        )
        db.commit()
        db.refresh(document)

    user_map = build_user_name_map(db, [document.created_by_user_id, document.updated_by_user_id])
    return _to_document_read(db, document, user_map=user_map)


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    _ensure_can_manage(current_user)
    document = get_document_or_404(db, document_id)
    _ensure_document_allowed(db, current_user, document)
    log_audit_event(
        db,
        entity_type="document",
        entity_id=document.id,
        action="deleted",
        created_by_user_id=current_user.id,
        payload={"document_type": document.document_type},
    )
    db.delete(document)
    db.commit()
    return {"ok": True}


@router.get("/documents/{document_id}/download", response_model=KnowledgeBaseDownloadResponse)
def get_document_download_url(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseDownloadResponse:
    _ensure_can_view(current_user)
    document = get_document_or_404(db, document_id)
    _ensure_document_allowed(db, current_user, document)
    if document.document_type != "file" or not document.storage_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Скачивание доступно только для загруженных файлов")
    url = resolve_document_download_url(document)
    if not url:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Не удалось сформировать ссылку для скачивания")
    return KnowledgeBaseDownloadResponse(download_url=url)


@router.get("/documents/{document_id}/history", response_model=KnowledgeBaseDocumentHistoryResponse)
def get_document_history(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseDocumentHistoryResponse:
    _ensure_can_view(current_user)
    document = get_document_or_404(db, document_id)
    _ensure_document_allowed(db, current_user, document)
    audit_rows = (
        db.query(KnowledgeBaseAuditLog)
        .filter(
            KnowledgeBaseAuditLog.entity_type == "document",
            KnowledgeBaseAuditLog.entity_id == document_id,
        )
        .order_by(KnowledgeBaseAuditLog.created_at.desc(), KnowledgeBaseAuditLog.id.desc())
        .limit(500)
        .all()
    )
    version_rows = (
        db.query(KnowledgeBaseDocumentVersion)
        .filter(KnowledgeBaseDocumentVersion.document_id == document_id)
        .order_by(KnowledgeBaseDocumentVersion.version_number.desc(), KnowledgeBaseDocumentVersion.id.desc())
        .limit(500)
        .all()
    )
    user_map = build_user_name_map(
        db,
        [row.created_by_user_id for row in audit_rows] + [row.created_by_user_id for row in version_rows],
    )
    return KnowledgeBaseDocumentHistoryResponse(
        audit_logs=_map_audit_rows(audit_rows, user_map),
        versions=_map_version_rows(version_rows, user_map),
    )
