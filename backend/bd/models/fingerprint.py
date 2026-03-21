"""Fingerprint event models."""
from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.bd.database import Base


class FingerprintEvent(Base):
    __tablename__ = "fingerprint_events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    staff_code = Column(String, nullable=True, index=True)
    action = Column(String, nullable=False)
    source = Column(String, nullable=True)
    slot = Column(Integer, nullable=True)
    score = Column(Integer, nullable=True)
    ok = Column(Boolean, nullable=False, default=False)
    error_code = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    user = relationship("User")
