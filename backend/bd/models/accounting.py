"""Accounting models (invoices, files, audit)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.bd.database import Base


class AccountingInvoice(Base):
    __tablename__ = "accounting_invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    from_restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    for_restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    payee: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    invoice_date: Mapped[datetime | None] = mapped_column(Date, nullable=True, index=True)
    sent_at: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    invoice_file_key: Mapped[str] = mapped_column(Text, nullable=False)
    payment_order_file_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    include_in_expenses: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    closing_received_edo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    closing_documents: Mapped[list["AccountingInvoiceClosingDocument"]] = relationship(
        "AccountingInvoiceClosingDocument",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    changes: Mapped[list["AccountingInvoiceChange"]] = relationship(
        "AccountingInvoiceChange",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    events: Mapped[list["AccountingInvoiceEvent"]] = relationship(
        "AccountingInvoiceEvent",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index(
            "ix_accounting_invoices_restaurants",
            "from_restaurant_id",
            "for_restaurant_id",
        ),
        Index("ix_accounting_invoices_sent_at", "sent_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<AccountingInvoice id={self.id} status={self.status!r} amount={self.amount}>"

    @property
    def created_by_name(self) -> str | None:
        user = self.created_by
        if not user:
            return None
        parts = [getattr(user, "last_name", None), getattr(user, "first_name", None), getattr(user, "middle_name", None)]
        name = " ".join(part for part in parts if part)
        return name or getattr(user, "username", None)


class AccountingInvoiceClosingDocument(Base):
    __tablename__ = "accounting_invoice_closing_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounting_invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_key: Mapped[str] = mapped_column(Text, nullable=False)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    original_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)

    invoice: Mapped[AccountingInvoice] = relationship("AccountingInvoice", back_populates="closing_documents")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_user_id])

    @property
    def uploaded_by_name(self) -> str | None:
        user = self.uploaded_by
        if not user:
            return None
        parts = [getattr(user, "last_name", None), getattr(user, "first_name", None), getattr(user, "middle_name", None)]
        name = " ".join(part for part in parts if part)
        return name or getattr(user, "username", None)


class AccountingInvoiceChange(Base):
    __tablename__ = "accounting_invoice_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounting_invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    invoice: Mapped[AccountingInvoice] = relationship("AccountingInvoice", back_populates="changes")
    changed_by = relationship("User", foreign_keys=[changed_by_user_id])

    @property
    def changed_by_name(self) -> str | None:
        user = self.changed_by
        if not user:
            return None
        parts = [getattr(user, "last_name", None), getattr(user, "first_name", None), getattr(user, "middle_name", None)]
        name = " ".join(part for part in parts if part)
        return name or getattr(user, "username", None)


class AccountingInvoiceEvent(Base):
    __tablename__ = "accounting_invoice_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounting_invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    invoice: Mapped[AccountingInvoice] = relationship("AccountingInvoice", back_populates="events")
    actor = relationship("User", foreign_keys=[actor_user_id])

    @property
    def actor_name(self) -> str | None:
        user = self.actor
        if not user:
            return None
        parts = [getattr(user, "last_name", None), getattr(user, "first_name", None), getattr(user, "middle_name", None)]
        name = " ".join(part for part in parts if part)
        return name or getattr(user, "username", None)


class AccountingCounterparty(Base):
    __tablename__ = "accounting_counterparties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    inn: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
