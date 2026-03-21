"""Employee change history models."""
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from backend.bd.database import Base


class EmployeeChangeEvent(Base):
    __tablename__ = "employee_change_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    changed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    entity_type = Column(String, nullable=True, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    field = Column(String, nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    old_value_json = Column(JSONB, nullable=True)
    new_value_json = Column(JSONB, nullable=True)
    source = Column(String, nullable=True)
    comment = Column(Text, nullable=True)
    request_id = Column(String, nullable=True, index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    endpoint = Column(String, nullable=True)
    method = Column(String, nullable=True)
    restaurant_id = Column(Integer, nullable=True, index=True)
    position_id = Column(Integer, nullable=True, index=True)
    role_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    user = relationship("User", foreign_keys=[user_id])
    changed_by = relationship("User", foreign_keys=[changed_by_id])

    __table_args__ = (
        Index("ix_employee_change_events_user_created", "user_id", "created_at"),
        Index("ix_employee_change_events_field_created", "field", "created_at"),
        Index("ix_employee_change_events_created_id", "created_at", "id"),
    )

    @property
    def changed_by_name(self) -> Optional[str]:
        user = self.changed_by
        if not user:
            return None
        parts = [user.last_name, user.first_name, user.middle_name]
        name = " ".join(part for part in parts if part)
        return name or user.username

    @property
    def user_name(self) -> Optional[str]:
        user = self.user
        if not user:
            return None
        parts = [user.last_name, user.first_name, user.middle_name]
        name = " ".join(part for part in parts if part)
        return name or user.username
