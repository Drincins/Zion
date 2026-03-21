from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from backend.bd.database import Base


position_checklist_access = Table(
    "position_checklist_access",
    Base.metadata,
    Column("position_id", Integer, ForeignKey("positions.id", ondelete="CASCADE"), primary_key=True),
    Column("checklist_id", Integer, ForeignKey("checklists.id", ondelete="CASCADE"), primary_key=True),
)


class Checklist(Base):
    __tablename__ = "checklists"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    is_scored = Column(Boolean, nullable=False, default=False)
    scope_type = Column(String, nullable=True)  # restaurant | subdivision
    all_restaurants = Column(Boolean, nullable=False, default=False)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True)
    restaurant_subdivision_id = Column(
        Integer,
        ForeignKey("restaurant_subdivisions.id", ondelete="SET NULL"),
        nullable=True,
    )
    access_subdivision_ids = Column(JSON, nullable=True)
    access_all_subdivisions = Column(Boolean, nullable=False, default=False)
    control_restaurant_ids = Column(JSON, nullable=True)
    control_subdivision_ids = Column(JSON, nullable=True)
    control_all_restaurants = Column(Boolean, nullable=False, default=False)
    control_all_subdivisions = Column(Boolean, nullable=False, default=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    company = relationship("Company")
    creator = relationship("User", foreign_keys=[created_by])
    restaurant = relationship("Restaurant")
    restaurant_subdivision = relationship("RestaurantSubdivision")
    positions = relationship(
        "Position",
        secondary=position_checklist_access,
        backref="checklists",
    )
    sections = relationship(
        "ChecklistSection",
        back_populates="checklist",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_checklists_company_created_at", "company_id", "created_at"),
        Index("ix_checklists_company_creator", "company_id", "created_by"),
    )


class ChecklistSection(Base):
    __tablename__ = "checklist_sections"

    id = Column(Integer, primary_key=True)
    checklist_id = Column(Integer, ForeignKey("checklists.id", ondelete="CASCADE"), nullable=False)
    name = Column("title", String, nullable=False)
    order = Column(Integer, nullable=True)
    is_required = Column(Boolean, nullable=False, default=False)

    checklist = relationship("Checklist", back_populates="sections")
    questions = relationship(
        "ChecklistQuestion",
        back_populates="section",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_checklist_sections_checklist_order", "checklist_id", "order"),
    )


class ChecklistQuestion(Base):
    __tablename__ = "checklist_questions"

    id = Column(Integer, primary_key=True)
    checklist_id = Column(Integer, ForeignKey("checklists.id", ondelete="CASCADE"), nullable=False)
    order = Column(Integer, nullable=False)
    text = Column(String, nullable=False)
    type = Column(String, nullable=False)
    required = Column(Boolean, default=True)
    meta = Column(JSON, nullable=True)
    weight = Column(Integer, nullable=True)
    require_photo = Column(Boolean, nullable=False, default=False)
    require_comment = Column(Boolean, nullable=False, default=False)
    section_id = Column(Integer, ForeignKey("checklist_sections.id", ondelete="SET NULL"), nullable=True)

    section = relationship("ChecklistSection", back_populates="questions")

    __table_args__ = (
        Index("ix_checklist_questions_checklist_order", "checklist_id", "order"),
        Index("ix_checklist_questions_section_order", "section_id", "order"),
    )


class ChecklistAnswer(Base):
    __tablename__ = "checklist_answers"

    id = Column(Integer, primary_key=True)
    checklist_id = Column(Integer, ForeignKey("checklists.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    department = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_ca_ck_user_date", "checklist_id", "user_id", "submitted_at"),
        Index("ix_ca_ck_submitted", "checklist_id", "submitted_at"),
        Index("ix_ca_ck_dept_submitted", "checklist_id", "department", "submitted_at"),
    )


class ChecklistQuestionAnswer(Base):
    __tablename__ = "checklist_question_answers"

    id = Column(Integer, primary_key=True)
    answer_id = Column(Integer, ForeignKey("checklist_answers.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("checklist_questions.id", ondelete="CASCADE"), nullable=False)
    response_value = Column(String, nullable=True)
    comment = Column(String, nullable=True)
    photo_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_cqa_answer_id", "answer_id"),
        Index("ix_cqa_question_id", "question_id"),
        Index("ix_cqa_answer_question", "answer_id", "question_id"),
    )


class ChecklistDraft(Base):
    __tablename__ = "checklist_drafts"

    id = Column(Integer, primary_key=True)
    checklist_id = Column(Integer, ForeignKey("checklists.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    department = Column(String, nullable=True)

    checklist = relationship("Checklist")
    answers = relationship(
        "ChecklistDraftAnswer",
        back_populates="draft",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_cd_user", "user_id"),
        UniqueConstraint("user_id", "checklist_id", name="uq_cd_user_checklist"),
    )


class ChecklistDraftAnswer(Base):
    __tablename__ = "checklist_draft_answers"

    id = Column(Integer, primary_key=True)
    draft_id = Column(Integer, ForeignKey("checklist_drafts.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("checklist_questions.id", ondelete="CASCADE"), nullable=False)
    response_value = Column(String, nullable=True)
    comment = Column(String, nullable=True)
    photo_path = Column(String, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    draft = relationship("ChecklistDraft", back_populates="answers")
    question = relationship("ChecklistQuestion")

    __table_args__ = (
        Index("ix_cda_draft_id", "draft_id"),
        Index("ix_cda_question_id", "question_id"),
        UniqueConstraint("draft_id", "question_id", name="uq_cda_draft_question"),
    )
