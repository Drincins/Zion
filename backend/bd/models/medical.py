"""Models for employee medical checks and health certificates."""
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


class MedicalCheckStatus(str, enum.Enum):
    """Possible states of a medical check record."""

    OK = "ok"
    EXPIRING = "expiring"
    EXPIRED = "expired"


# Persist enum *values* (ok/expiring/expired) to align with existing PostgreSQL type.
MEDICAL_CHECK_STATUS = Enum(
    MedicalCheckStatus,
    name="medical_check_status",
    values_callable=lambda obj: [member.value for member in obj],
)


class MedicalCheckType(Base):
    """Reference table with med-check types and their renewal rules."""

    __tablename__ = "medical_check_types"

    id = Column(Integer, primary_key=True)
    code = Column(String(32), nullable=True, unique=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    validity_months = Column(Integer, nullable=True)
    notice_days = Column(Integer, nullable=False, default=30)
    is_active = Column(Boolean, nullable=False, default=True)
    comment = Column(Text, nullable=True)

    records = relationship(
        "MedicalCheckRecord",
        back_populates="check_type",
        cascade="all, delete-orphan",
    )


class MedicalCheckRecord(Base):
    """Fact table with employee medical check passes."""

    __tablename__ = "medical_check_records"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    medical_check_type_id = Column(
        Integer,
        ForeignKey("medical_check_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    passed_at = Column(Date, nullable=False, index=True)
    next_due_at = Column(Date, nullable=True, index=True)
    status = Column(
        MEDICAL_CHECK_STATUS,
        nullable=False,
        default=MedicalCheckStatus.OK,
    )
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User", back_populates="medical_check_records")
    check_type = relationship("MedicalCheckType", back_populates="records")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "medical_check_type_id",
            "passed_at",
            name="uq_medical_check_records_user_type_date",
        ),
        Index(
            "ix_medical_check_records_user_type",
            "user_id",
            "medical_check_type_id",
        ),
    )

    @property
    def medical_check_type(self) -> MedicalCheckType | None:
        """Compatibility alias for serializers expecting `medical_check_type` attribute."""
        return self.check_type
