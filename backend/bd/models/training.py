"""Training events models."""
from __future__ import annotations

from sqlalchemy import Boolean, Column, Date, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.bd.database import Base


class TrainingEventType(Base):
    __tablename__ = "training_event_types"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    events = relationship(
        "TrainingEventRecord",
        back_populates="event_type",
        cascade="all, delete-orphan",
    )
    position_requirements = relationship(
        "PositionTrainingRequirement",
        back_populates="event_type",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class TrainingEventRecord(Base):
    __tablename__ = "training_event_records"

    id = Column(Integer, primary_key=True)
    event_type_id = Column(Integer, ForeignKey("training_event_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    comment = Column(Text, nullable=True)

    event_type = relationship("TrainingEventType", back_populates="events")
    user = relationship("User", back_populates="training_events")

    __table_args__ = (
        Index("ix_training_event_records_user_date", "user_id", "date"),
    )


class PositionTrainingRequirement(Base):
    __tablename__ = "position_training_requirements"

    id = Column(Integer, primary_key=True)
    position_id = Column(Integer, ForeignKey("positions.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type_id = Column(Integer, ForeignKey("training_event_types.id", ondelete="CASCADE"), nullable=False, index=True)
    required = Column(Boolean, nullable=False, default=True)

    position = relationship("Position", back_populates="training_requirements")
    event_type = relationship("TrainingEventType", back_populates="position_requirements")

    __table_args__ = (
        UniqueConstraint("position_id", "event_type_id", name="uq_position_training_requirements_position_event"),
    )
