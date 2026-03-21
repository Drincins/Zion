"""Schemas for training events."""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class TrainingEventTypeCreate(BaseModel):
    name: str


class TrainingEventTypeUpdate(BaseModel):
    name: Optional[str] = None

    model_config = ConfigDict(validate_default=False)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> str:
        if value is None:
            raise ValueError("name may not be null")
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("name must not be empty")
        return trimmed


class TrainingEventTypePublic(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class TrainingEventTypeListResponse(BaseModel):
    items: List[TrainingEventTypePublic]


class TrainingEventRecordBase(BaseModel):
    event_type_id: int
    user_id: int
    date: date
    comment: Optional[str] = None


class TrainingEventRecordCreate(TrainingEventRecordBase):
    pass


class TrainingEventRecordUpdate(TrainingEventRecordBase):
    """Full update payload for training event records."""

    model_config = ConfigDict(validate_default=False)


class TrainingEventRecordPublic(TrainingEventRecordBase):
    id: int
    event_type: Optional[TrainingEventTypePublic] = None

    model_config = ConfigDict(from_attributes=True)


class TrainingEventRecordListResponse(BaseModel):
    items: List[TrainingEventRecordPublic]


class PositionTrainingRequirementBase(BaseModel):
    position_id: int
    event_type_id: int
    required: bool = True


class PositionTrainingRequirementCreate(PositionTrainingRequirementBase):
    pass


class PositionTrainingRequirementUpdate(BaseModel):
    required: Optional[bool] = None


class PositionTrainingRequirementPublic(PositionTrainingRequirementBase):
    id: int
    event_type: Optional[TrainingEventTypePublic] = None

    model_config = ConfigDict(from_attributes=True)


class PositionTrainingRequirementListResponse(BaseModel):
    items: List[PositionTrainingRequirementPublic]


class TrainingRequirementSuggestion(BaseModel):
    event_type_id: int
    event_type: TrainingEventTypePublic
    required: bool
    requirement_id: Optional[int] = None
    completed: bool
    completed_at: Optional[date] = None


class TrainingRequirementSuggestionList(BaseModel):
    items: List[TrainingRequirementSuggestion]
