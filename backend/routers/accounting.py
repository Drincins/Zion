# backend/routers/accounting.py
from __future__ import annotations

import logging
import os
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.bd.database import get_db
from backend.bd.models import (
    AccountingInvoice,
    AccountingInvoiceChange,
    AccountingInvoiceClosingDocument,
    AccountingInvoiceEvent,
    Restaurant,
    User,
)
from backend.schemas.accounting import (
    ACCOUNTING_STATUSES,
    AccountingInvoiceChangeRead,
    AccountingInvoiceCreate,
    AccountingInvoiceEventRead,
    AccountingInvoiceListResponse,
    AccountingInvoiceRead,
    AccountingInvoiceStatusUpdate,
    AccountingInvoiceUpdate,
    AccountingInvoiceClosingDocumentRead,
)
from backend.services.permissions import ensure_permissions, PermissionKey
from backend.services.s3 import upload_bytes, generate_presigned_url
from backend.services.ocr import analyze_invoice_content
from backend.services.llm import analyze_invoice_text_llm, analyze_invoice_image_llm
from backend.utils import get_current_user

router = APIRouter(prefix="/accounting", tags=["Accounting"])
logger = logging.getLogger(__name__)

ACCOUNTING_S3_PREFIX = (os.getenv("ACCOUNTING_S3_PREFIX") or "accounting_invoices").strip("/") or "accounting_invoices"


def _build_file_key(kind: str, filename: str | None = None) -> str:
    base, ext = os.path.splitext(filename or "file")
    safe_base = base.replace("/", "_") or "file"
    safe_ext = ext if ext else ".bin"
    return f"{ACCOUNTING_S3_PREFIX}/{kind}/{safe_base}_{uuid4().hex}{safe_ext}"


def _resolve_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return value
    try:
        return generate_presigned_url(value)
    except Exception:  # noqa: BLE001
        logger.warning("Failed to generate presigned URL for %s", value, exc_info=True)
        return value


def _log_change(
    db: Session,
    *,
    invoice_id: int,
    field: str,
    old_value,
    new_value,
    user_id: int | None,
) -> None:
    if (old_value or "") == (new_value or ""):
        return
    db.add(
        AccountingInvoiceChange(
            invoice_id=invoice_id,
            field=field,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            changed_by_user_id=user_id,
        )
    )


def _log_event(
    db: Session,
    *,
    invoice_id: int,
    event_type: str,
    message: str | None,
    actor_user_id: int | None,
) -> None:
    db.add(
        AccountingInvoiceEvent(
            invoice_id=invoice_id,
            event_type=event_type,
            message=message,
            actor_user_id=actor_user_id,
        )
    )


def _invoice_schema(invoice: AccountingInvoice) -> AccountingInvoiceRead:
    closing_docs = [
        AccountingInvoiceClosingDocumentRead(
            id=doc.id,
            invoice_id=doc.invoice_id,
            file_key=doc.file_key,
            file_url=_resolve_url(doc.file_key),
            uploaded_by_user_id=doc.uploaded_by_user_id,
            uploaded_at=doc.uploaded_at,
            original_filename=doc.original_filename,
            content_type=doc.content_type,
        )
        for doc in getattr(invoice, "closing_documents", []) or []
    ]
    return AccountingInvoiceRead(
        id=invoice.id,
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
        created_by_user_id=invoice.created_by_user_id,
        from_restaurant_id=invoice.from_restaurant_id,
        for_restaurant_id=invoice.for_restaurant_id,
        amount=invoice.amount,
        payee=invoice.payee,
        purpose=invoice.purpose,
        invoice_date=invoice.invoice_date,
        sent_at=invoice.sent_at,
        comment=invoice.comment,
        status=invoice.status,
        include_in_expenses=bool(invoice.include_in_expenses),
        closing_received_edo=bool(invoice.closing_received_edo),
        invoice_file_key=invoice.invoice_file_key,
        invoice_file_url=_resolve_url(invoice.invoice_file_key),
        payment_order_file_key=invoice.payment_order_file_key,
        payment_order_file_url=_resolve_url(invoice.payment_order_file_key),
        closing_documents=closing_docs,
    )


def _ensure_status(value: str) -> str:
    if value not in ACCOUNTING_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported status value")
    return value


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format")  # noqa: B904


@router.get("/invoices", response_model=AccountingInvoiceListResponse)
def list_invoices(
    status_filter: Optional[str] = Query(None, alias="status"),
    from_restaurant_id: Optional[int] = Query(None),
    for_restaurant_id: Optional[int] = Query(None),
    created_by_user_id: Optional[int] = Query(None),
    include_in_expenses: Optional[bool] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    search: Optional[str] = Query(None, description="Search by payee or purpose"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountingInvoiceListResponse:
    ensure_permissions(current_user, PermissionKey.ACCOUNTING_INVOICES_VIEW)

    query = db.query(AccountingInvoice)
    if status_filter:
        query = query.filter(AccountingInvoice.status == status_filter)
    if from_restaurant_id:
        query = query.filter(AccountingInvoice.from_restaurant_id == from_restaurant_id)
    if for_restaurant_id:
        query = query.filter(AccountingInvoice.for_restaurant_id == for_restaurant_id)
    if created_by_user_id:
        query = query.filter(AccountingInvoice.created_by_user_id == created_by_user_id)
    if include_in_expenses is not None:
        query = query.filter(AccountingInvoice.include_in_expenses == include_in_expenses)
    if date_from:
        query = query.filter(AccountingInvoice.sent_at >= date_from)
    if date_to:
        query = query.filter(AccountingInvoice.sent_at <= date_to)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            func.lower(AccountingInvoice.payee).like(func.lower(pattern))
            | func.lower(AccountingInvoice.purpose).like(func.lower(pattern))
        )

    total = query.count()
    items = (
        query.order_by(AccountingInvoice.sent_at.desc().nullslast(), AccountingInvoice.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return AccountingInvoiceListResponse(items=[_invoice_schema(item) for item in items], total=total)


@router.post("/invoices", response_model=AccountingInvoiceRead, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    from_restaurant_id: int = Form(...),
    for_restaurant_id: int = Form(...),
    amount: Decimal = Form(...),
    payee: str = Form(...),
    purpose: str = Form(...),
    invoice_date: Optional[str] = Form(None),
    sent_at: Optional[str] = Form(None),
    comment: Optional[str] = Form(None),
    include_in_expenses: bool = Form(False),
    invoice_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountingInvoiceRead:
    ensure_permissions(current_user, PermissionKey.ACCOUNTING_INVOICES_CREATE)
    if not invoice_file:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice file is required")
    content = await invoice_file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    key = _build_file_key("invoice", invoice_file.filename)
    upload_bytes(key, content, invoice_file.content_type or "application/octet-stream")
    invoice_date_parsed = _parse_date(invoice_date)
    sent_at_parsed = _parse_date(sent_at)

    invoice = AccountingInvoice(
        created_by_user_id=current_user.id,
        from_restaurant_id=from_restaurant_id,
        for_restaurant_id=for_restaurant_id,
        amount=amount,
        payee=payee,
        purpose=purpose,
        invoice_date=invoice_date_parsed,
        sent_at=sent_at_parsed or date.today(),
        comment=comment,
        status="Отправлен в бухгалтерию",
        invoice_file_key=key,
        include_in_expenses=include_in_expenses,
        closing_received_edo=False,
    )
    db.add(invoice)
    db.flush()
    _log_event(
        db,
        invoice_id=invoice.id,
        event_type="created",
        message="Счет создан",
        actor_user_id=current_user.id,
    )
    db.commit()
    db.refresh(invoice)
    return _invoice_schema(invoice)


@router.put("/invoices/{invoice_id}", response_model=AccountingInvoiceRead)
def update_invoice(
    invoice_id: int,
    payload: AccountingInvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountingInvoiceRead:
    ensure_permissions(current_user, PermissionKey.ACCOUNTING_INVOICES_EDIT)
    invoice = db.query(AccountingInvoice).filter(AccountingInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    original = {
        "from_restaurant_id": invoice.from_restaurant_id,
        "for_restaurant_id": invoice.for_restaurant_id,
        "amount": invoice.amount,
        "payee": invoice.payee,
        "purpose": invoice.purpose,
        "invoice_date": invoice.invoice_date,
        "sent_at": invoice.sent_at,
        "comment": invoice.comment,
        "include_in_expenses": invoice.include_in_expenses,
        "closing_received_edo": invoice.closing_received_edo,
        "invoice_file_key": invoice.invoice_file_key,
        "payment_order_file_key": invoice.payment_order_file_key,
    }

    if payload.from_restaurant_id is not None:
        invoice.from_restaurant_id = payload.from_restaurant_id
    if payload.for_restaurant_id is not None:
        invoice.for_restaurant_id = payload.for_restaurant_id
    if payload.amount is not None:
        invoice.amount = payload.amount
    if payload.payee is not None:
        invoice.payee = payload.payee
    if payload.purpose is not None:
        invoice.purpose = payload.purpose
    if payload.invoice_date is not None:
        invoice.invoice_date = payload.invoice_date
    if payload.sent_at is not None:
        invoice.sent_at = payload.sent_at
    if payload.comment is not None:
        invoice.comment = payload.comment
    if payload.include_in_expenses is not None:
        invoice.include_in_expenses = payload.include_in_expenses
    if payload.closing_received_edo is not None:
        invoice.closing_received_edo = payload.closing_received_edo
    if payload.invoice_file_key is not None:
        invoice.invoice_file_key = payload.invoice_file_key
    if payload.payment_order_file_key is not None:
        invoice.payment_order_file_key = payload.payment_order_file_key

    # Автоматически закрываем, если отметили получение в ЭДО
    if invoice.closing_received_edo and invoice.status == "Требуются закрывающие документы":
        old_status = invoice.status
        invoice.status = "Счет закрыт"
        _log_change(
            db,
            invoice_id=invoice.id,
            field="status",
            old_value=old_status,
            new_value="Счет закрыт",
            user_id=current_user.id,
        )
        _log_event(
            db,
            invoice_id=invoice.id,
            event_type="status_changed",
            message="Статус автоматически изменен на 'Счет закрыт' (документы получены в ЭДО)",
            actor_user_id=current_user.id,
        )

    for field, old_value in original.items():
        _log_change(
            db,
            invoice_id=invoice.id,
            field=field,
            old_value=old_value,
            new_value=getattr(invoice, field),
            user_id=current_user.id,
        )

    _log_event(db, invoice_id=invoice.id, event_type="updated", message="Счет обновлен", actor_user_id=current_user.id)
    db.commit()
    db.refresh(invoice)
    return _invoice_schema(invoice)


@router.put("/invoices/{invoice_id}/status", response_model=AccountingInvoiceRead)
def update_invoice_status(
    invoice_id: int,
    payload: AccountingInvoiceStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountingInvoiceRead:
    ensure_permissions(current_user, PermissionKey.ACCOUNTING_INVOICES_STATUS)
    invoice = db.query(AccountingInvoice).filter(AccountingInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    new_status = _ensure_status(payload.status)
    old_status = invoice.status
    invoice.status = new_status
    _log_change(db, invoice_id=invoice.id, field="status", old_value=old_status, new_value=new_status, user_id=current_user.id)
    _log_event(
        db,
        invoice_id=invoice.id,
        event_type="status_changed",
        message=f"Статус изменен: {old_status or '-'} → {new_status}",
        actor_user_id=current_user.id,
    )
    db.commit()
    db.refresh(invoice)
    return _invoice_schema(invoice)


@router.delete("/invoices/{invoice_id}")
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    ensure_permissions(current_user, PermissionKey.ACCOUNTING_INVOICES_DELETE)
    invoice = db.query(AccountingInvoice).filter(AccountingInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    db.delete(invoice)
    _log_event(db, invoice_id=invoice_id, event_type="deleted", message="Счет удален", actor_user_id=current_user.id)
    db.commit()
    return {"ok": True}


@router.post("/invoices/ocr")
async def analyze_invoice_ocr(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Run OCR on uploaded invoice and return guessed fields."""
    ensure_permissions(current_user, PermissionKey.ACCOUNTING_INVOICES_CREATE)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    try:
        result = analyze_invoice_content(content, file.filename)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to analyze invoice via OCR")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="OCR service unavailable") from exc
    return result


@router.post("/invoices/ocr-llm")
async def analyze_invoice_ocr_llm(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Run vision-LLM parsing with OCR fallback on uploaded invoice."""
    ensure_permissions(current_user, PermissionKey.ACCOUNTING_INVOICES_CREATE)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    try:
        ocr_result = analyze_invoice_content(content, file.filename)
        text = ocr_result.get("text") or "\n".join(ocr_result.get("lines") or [])
        try:
            llm_result = analyze_invoice_image_llm(content, file.filename)
            source = "vision"
        except Exception:
            logger.warning("Vision LLM failed, trying text LLM", exc_info=True)
            llm_result = None
            source = "vision_failed"
        if llm_result is None:
            try:
                llm_result = analyze_invoice_text_llm(text)
                source = "text"
            except Exception:
                logger.warning("Text LLM failed, fallback to OCR", exc_info=True)
                return {
                    "text": text,
                    "lines": ocr_result.get("lines") or [],
                    "amount": ocr_result.get("amount"),
                    "payee": ocr_result.get("payee"),
                    "purpose": ocr_result.get("purpose"),
                    "invoice_date": ocr_result.get("invoice_date"),
                    "sent_at": ocr_result.get("sent_at"),
                    "comment": ocr_result.get("comment"),
                    "llm_error": "failed",
                    "source": "ocr_only",
                }

        return {
            "text": text,
            "lines": ocr_result.get("lines") or [],
            "amount": llm_result.get("amount") or ocr_result.get("amount"),
            "payee": llm_result.get("payee") or ocr_result.get("payee"),
            "purpose": llm_result.get("purpose") or ocr_result.get("purpose"),
            "invoice_date": llm_result.get("invoice_date") or ocr_result.get("invoice_date"),
            "sent_at": llm_result.get("sent_at") or ocr_result.get("sent_at"),
            "inn": llm_result.get("inn"),
            "comment": llm_result.get("comment") or "",
            "llm_raw": llm_result,
            "source": source,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to analyze invoice via LLM OCR")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="LLM OCR service unavailable") from exc


@router.get("/invoices/{invoice_id}/changes", response_model=list[AccountingInvoiceChangeRead])
def list_invoice_changes(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AccountingInvoiceChangeRead]:
    ensure_permissions(current_user, PermissionKey.ACCOUNTING_INVOICES_VIEW)
    changes = (
        db.query(AccountingInvoiceChange)
        .filter(AccountingInvoiceChange.invoice_id == invoice_id)
        .order_by(AccountingInvoiceChange.changed_at.desc())
        .all()
    )
    return changes


@router.get("/invoices/{invoice_id}/events", response_model=list[AccountingInvoiceEventRead])
def list_invoice_events(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AccountingInvoiceEventRead]:
    ensure_permissions(current_user, PermissionKey.ACCOUNTING_INVOICES_VIEW)
    events = (
        db.query(AccountingInvoiceEvent)
        .filter(AccountingInvoiceEvent.invoice_id == invoice_id)
        .order_by(AccountingInvoiceEvent.created_at.desc())
        .all()
    )
    return events


@router.post("/invoices/{invoice_id}/payment-order", response_model=AccountingInvoiceRead)
async def upload_payment_order(
    invoice_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountingInvoiceRead:
    ensure_permissions(current_user, PermissionKey.ACCOUNTING_INVOICES_EDIT)
    invoice = db.query(AccountingInvoice).filter(AccountingInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    key = _build_file_key("payment_order", file.filename)
    upload_bytes(key, content, file.content_type or "application/octet-stream")
    old_value = invoice.payment_order_file_key
    invoice.payment_order_file_key = key
    _log_change(db, invoice_id=invoice.id, field="payment_order_file_key", old_value=old_value, new_value=key, user_id=current_user.id)
    _log_event(db, invoice_id=invoice.id, event_type="payment_order_uploaded", message="Загружено платежное поручение", actor_user_id=current_user.id)
    db.commit()
    db.refresh(invoice)
    return _invoice_schema(invoice)


@router.post("/invoices/{invoice_id}/invoice-file", response_model=AccountingInvoiceRead)
async def upload_invoice_file(
    invoice_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountingInvoiceRead:
    ensure_permissions(current_user, PermissionKey.ACCOUNTING_INVOICES_EDIT)
    invoice = db.query(AccountingInvoice).filter(AccountingInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    key = _build_file_key("invoice", file.filename)
    upload_bytes(key, content, file.content_type or "application/octet-stream")
    old_value = invoice.invoice_file_key
    invoice.invoice_file_key = key
    _log_change(db, invoice_id=invoice.id, field="invoice_file_key", old_value=old_value, new_value=key, user_id=current_user.id)
    _log_event(db, invoice_id=invoice.id, event_type="invoice_file_uploaded", message="Загружен файл счета", actor_user_id=current_user.id)
    db.commit()
    db.refresh(invoice)
    return _invoice_schema(invoice)


@router.post("/invoices/{invoice_id}/closing-documents", response_model=AccountingInvoiceRead)
async def upload_closing_document(
    invoice_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountingInvoiceRead:
    ensure_permissions(current_user, PermissionKey.ACCOUNTING_INVOICES_EDIT)
    invoice = (
        db.query(AccountingInvoice)
        .filter(AccountingInvoice.id == invoice_id)
        .first()
    )
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    key = _build_file_key("closing", file.filename)
    upload_bytes(key, content, file.content_type or "application/octet-stream")
    doc = AccountingInvoiceClosingDocument(
        invoice_id=invoice.id,
        file_key=key,
        uploaded_by_user_id=current_user.id,
        original_filename=file.filename,
        content_type=file.content_type,
    )
    db.add(doc)
    _log_event(
        db,
        invoice_id=invoice.id,
        event_type="closing_document_uploaded",
        message="Загружен закрывающий документ",
        actor_user_id=current_user.id,
    )
    # Автоматически закрываем счет, если статус требовал закрывающие
    if invoice.status == "Требуются закрывающие документы":
        old_status = invoice.status
        invoice.status = "Счет закрыт"
        _log_change(db, invoice_id=invoice.id, field="status", old_value=old_status, new_value="Счет закрыт", user_id=current_user.id)
        _log_event(
            db,
            invoice_id=invoice.id,
            event_type="status_changed",
            message="Статус автоматически изменен на 'Счет закрыт' после загрузки закрывающих документов",
            actor_user_id=current_user.id,
        )
    db.commit()
    db.refresh(invoice)
    return _invoice_schema(invoice)
