"""Models for CIS document tracking."""
from __future__ import annotations

import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.bd.database import Base


class CisDocumentStatus(str, enum.Enum):
    OK = "ok"
    EXPIRING = "expiring"
    EXPIRED = "expired"


# Explicitly persist enum *values* (ok/expiring/expired) to match the existing
# PostgreSQL type that was created in the migration.
CIS_DOCUMENT_STATUS = Enum(
    CisDocumentStatus,
    name="cis_document_status",
    values_callable=lambda obj: [member.value for member in obj],
)


class CisDocumentType(Base):
    __tablename__ = "cis_document_types"

    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    validity_months = Column(Integer, nullable=True)
    notice_days = Column(Integer, nullable=False, default=30)
    is_active = Column(Boolean, nullable=False, default=True)
    comment = Column(Text, nullable=True)

    records = relationship(
        "CisDocumentRecord",
        back_populates="document_type",
        cascade="all, delete-orphan",
    )


class CisDocumentRecord(Base):
    __tablename__ = "cis_document_records"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    cis_document_type_id = Column(
        Integer,
        ForeignKey("cis_document_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    number = Column(String(128), nullable=True)
    issued_at = Column(Date, nullable=True)
    expires_at = Column(Date, nullable=True, index=True)
    status = Column(CIS_DOCUMENT_STATUS, nullable=False, default=CisDocumentStatus.OK)
    issuer = Column(String(255), nullable=True)
    comment = Column(Text, nullable=True)
    attachment_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User", back_populates="cis_document_records")
    document_type = relationship("CisDocumentType", back_populates="records")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "cis_document_type_id",
            "number",
            name="uq_cis_document_record_user_type_number",
        ),
        Index("ix_cis_document_records_user_type", "user_id", "cis_document_type_id"),
    )
