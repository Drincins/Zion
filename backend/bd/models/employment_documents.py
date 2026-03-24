"""Models for employment-related documents of formalized employees."""
from __future__ import annotations

import enum

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, Text, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.bd.database import Base


class EmploymentDocumentKind(str, enum.Enum):
    EMPLOYMENT_ORDER = "employment_order"
    EMPLOYMENT_CONTRACT = "employment_contract"


EMPLOYMENT_DOCUMENT_KIND = Enum(
    EmploymentDocumentKind,
    name="employment_document_kind",
    values_callable=lambda obj: [member.value for member in obj],
)


class EmploymentDocumentRecord(Base):
    __tablename__ = "employment_document_records"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document_kind = Column(EMPLOYMENT_DOCUMENT_KIND, nullable=False, index=True)
    issued_at = Column(Date, nullable=True)
    comment = Column(Text, nullable=True)
    attachment_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User", back_populates="employment_document_records")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "document_kind",
            name="uq_employment_document_record_user_kind",
        ),
        Index("ix_employment_document_records_user_kind", "user_id", "document_kind"),
    )
