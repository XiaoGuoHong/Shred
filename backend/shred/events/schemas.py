from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UpdateEvent(BaseModel):
    title: str | None = None
    occurred_at: datetime | None = None
    occurrence_precision: str | None = None
    part_of_day: str | None = None
    category_id: str | None = None
    tags: list[str] | None = None


class SourceMessageContext(BaseModel):
    id: str
    original_text: str
    submitted_at: datetime
    timezone: str


class EventView(BaseModel):
    id: str
    position: int
    title: str
    source_fragment: str
    occurred_at: datetime
    occurrence_precision: str
    part_of_day: str | None
    category_id: str | None
    category_path: list[str]
    tags: list[str]
    status: str


class EventDetail(EventView):
    source_message: SourceMessageContext | None = None
