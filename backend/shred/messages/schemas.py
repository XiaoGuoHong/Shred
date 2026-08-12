from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class SubmitMessage(BaseModel):
    text: str
    timezone: str
    submitted_at: datetime
    submission_uuid: str = Field(default_factory=lambda: str(uuid4()))


class EventDetail(BaseModel):
    id: str
    position: int
    title: str
    source_fragment: str
    occurred_at: datetime
    occurrence_precision: str
    part_of_day: str | None
    category_path: list[str]
    category_id: str | None
    tags: list[str]
    status: str


class MessageView(BaseModel):
    id: str
    submission_uuid: str
    original_text: str
    submitted_at: datetime
    timezone: str
    status: str
    error_code: str | None
    error_summary: str | None
    created_at: datetime
    updated_at: datetime


class MessageDetail(BaseModel):
    message: MessageView
    events: list[EventDetail]


class DeleteImpact(BaseModel):
    message_id: str
    deleted_events: int


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ErrorDetail(BaseModel):
    code: str
    message: str
