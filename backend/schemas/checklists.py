"""Checklist schemas."""
from __future__ import annotations

from datetime import datetime, date
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, ConfigDict, Field


class ChecklistSectionBase(BaseModel):
    title: str = Field(..., min_length=1)
    order: Optional[int] = None
    is_required: bool = False


class ChecklistSectionCreate(ChecklistSectionBase):
    pass


class ChecklistSectionUpdate(BaseModel):
    title: Optional[str] = None
    order: Optional[int] = None
    is_required: Optional[bool] = None


class ChecklistSectionRead(ChecklistSectionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ChecklistQuestionBase(BaseModel):
    text: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    order: Optional[int] = None
    required: bool = True
    meta: Optional[Dict[str, Any]] = None
    weight: Optional[int] = None
    require_photo: bool = False
    require_comment: bool = False
    section_id: Optional[int] = None


class ChecklistQuestionCreate(ChecklistQuestionBase):
    pass


class ChecklistQuestionUpdate(BaseModel):
    text: Optional[str] = None
    type: Optional[str] = None
    order: Optional[int] = None
    required: Optional[bool] = None
    meta: Optional[Dict[str, Any]] = None
    weight: Optional[int] = None
    require_photo: Optional[bool] = None
    require_comment: Optional[bool] = None
    section_id: Optional[int] = None


class ChecklistQuestionRead(ChecklistQuestionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ChecklistBase(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    company_id: int
    is_scored: bool = False
    scope_type: Optional[str] = None  # restaurant | restaurants_multi | subdivision
    all_restaurants: bool = False
    restaurant_id: Optional[int] = None
    restaurant_subdivision_id: Optional[int] = None
    access_subdivision_ids: Optional[List[int]] = None
    access_all_subdivisions: bool = False
    control_restaurant_ids: Optional[List[int]] = None
    control_subdivision_ids: Optional[List[int]] = None
    control_all_restaurants: bool = False
    control_all_subdivisions: bool = False
    position_ids: List[int] = Field(default_factory=list)


class ChecklistCreate(ChecklistBase):
    pass


class ChecklistUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    company_id: Optional[int] = None
    is_scored: Optional[bool] = None
    scope_type: Optional[str] = None
    all_restaurants: Optional[bool] = None
    restaurant_id: Optional[int] = None
    restaurant_subdivision_id: Optional[int] = None
    access_subdivision_ids: Optional[List[int]] = None
    access_all_subdivisions: Optional[bool] = None
    control_restaurant_ids: Optional[List[int]] = None
    control_subdivision_ids: Optional[List[int]] = None
    control_all_restaurants: Optional[bool] = None
    control_all_subdivisions: Optional[bool] = None
    position_ids: Optional[List[int]] = None


class ChecklistRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    company_id: int
    is_scored: bool
    scope_type: Optional[str] = None
    all_restaurants: bool = False
    restaurant_id: Optional[int] = None
    restaurant_subdivision_id: Optional[int] = None
    access_subdivision_ids: Optional[List[int]] = None
    access_all_subdivisions: bool = False
    control_restaurant_ids: Optional[List[int]] = None
    control_subdivision_ids: Optional[List[int]] = None
    control_all_restaurants: bool = False
    control_all_subdivisions: bool = False
    created_by: Optional[int] = None
    creator_name: Optional[str] = None
    created_at: datetime
    position_ids: List[int] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ChecklistDetail(ChecklistRead):
    sections: List[ChecklistSectionRead] = Field(default_factory=list)
    questions: List[ChecklistQuestionRead] = Field(default_factory=list)


class ChecklistReportSummaryItem(BaseModel):
    checklist_id: int
    checklist_name: str
    total_completed: int
    last_submitted_at: Optional[datetime] = None


class ChecklistAttemptListItem(BaseModel):
    id: int
    checklist_id: int
    checklist_name: str
    user_id: int
    user_name: str
    department: Optional[str] = None
    is_scored: bool = False
    total_score: Optional[float] = None
    total_max: Optional[float] = None
    percent: Optional[float] = None
    result: Optional[str] = None
    submitted_at: datetime


class ChecklistAttemptListResponse(BaseModel):
    items: List[ChecklistAttemptListItem] = Field(default_factory=list)
    total: int = 0


class ChecklistAttemptAnswer(BaseModel):
    question_id: int
    question_text: str
    question_type: str
    section_title: Optional[str] = None
    response_value: Optional[str] = None
    comment: Optional[str] = None
    photo_path: Optional[str] = None


class ChecklistAttemptDetail(BaseModel):
    id: int
    checklist_id: int
    checklist_name: str
    user_id: int
    user_name: str
    department: Optional[str] = None
    result: Optional[str] = None
    submitted_at: datetime
    answers: List[ChecklistAttemptAnswer] = Field(default_factory=list)


class ChecklistReportDailyCount(BaseModel):
    date: date
    total: int


class ChecklistReportMetrics(BaseModel):
    daily_counts: List[ChecklistReportDailyCount] = Field(default_factory=list)
    average_scored_percent: Optional[float] = None
    scored_total: int = 0
    departments: List[str] = Field(default_factory=list)


class ChecklistPortalLoginStartRequest(BaseModel):
    staff_code: str


class ChecklistPortalLoginFinishRequest(BaseModel):
    staff_code: str
    username: str
    password: str


class ChecklistPortalUser(BaseModel):
    id: int
    name: str
    phone: Optional[str] = None
    position: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    default_department: Optional[str] = None


class ChecklistPortalLoginResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: str = "bearer"
    user: ChecklistPortalUser


class ChecklistPortalLoginStartResponse(BaseModel):
    requires_credentials: bool
    access_token: Optional[str] = None
    token_type: str = "bearer"
    user: Optional[ChecklistPortalUser] = None
    username_hint: Optional[str] = None


class ChecklistPortalChecklistItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_scored: bool = False
    has_control_objects: bool = False


class ChecklistPortalSection(BaseModel):
    id: int
    name: str
    order: Optional[int] = None


class ChecklistPortalQuestion(BaseModel):
    id: int
    text: str
    type: str
    order: Optional[int] = None
    required: bool = False
    meta: Optional[Dict[str, Any]] = None
    section_id: Optional[int] = None
    section_title: Optional[str] = None
    require_photo: bool = False
    require_comment: bool = False


class ChecklistPortalChecklistDetail(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_scored: bool = False
    sections: List[ChecklistPortalSection] = Field(default_factory=list)
    questions: List[ChecklistPortalQuestion] = Field(default_factory=list)


class ChecklistPortalAnswerPayload(BaseModel):
    question_id: int
    response_value: Optional[str] = None
    comment: Optional[str] = None
    photo_path: Optional[str] = None


class ChecklistPortalDraftRequest(BaseModel):
    department: Optional[str] = None
    answers: List[ChecklistPortalAnswerPayload] = Field(default_factory=list)


class ChecklistPortalDraftAnswer(BaseModel):
    question_id: int
    response_value: Optional[str] = None
    comment: Optional[str] = None
    photo_path: Optional[str] = None
    photo_url: Optional[str] = None


class ChecklistPortalDraftResponse(BaseModel):
    checklist_id: int
    department: Optional[str] = None
    answers: List[ChecklistPortalDraftAnswer] = Field(default_factory=list)


class ChecklistPortalSubmitRequest(BaseModel):
    checklist_id: int
    department: Optional[str] = None
    answers: List[ChecklistPortalAnswerPayload] = Field(default_factory=list)


class ChecklistPortalSubmitResponse(BaseModel):
    attempt_id: int


class ChecklistPortalUploadResponse(BaseModel):
    photo_path: str
    url: Optional[str] = None


class ChecklistPortalAttemptSummary(BaseModel):
    attempt_id: int
    checklist_name: str
    user_name: str
    department: Optional[str] = None
    started_at: Optional[str] = None
    submitted_at: Optional[str] = None
    result_text: Optional[str] = None
    is_scored: bool = False
    total_score: Optional[float] = None
    total_max: Optional[float] = None
    percent: Optional[float] = None
