from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TimelineEvent(BaseModel):
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


class TimelineMessage(BaseModel):
    id: str
    submission_uuid: str
    original_text: str
    submitted_at: datetime
    timezone: str
    status: str
    error_code: str | None
    error_summary: str | None


class TimelineGroup(BaseModel):
    message: TimelineMessage
    events: list[TimelineEvent]


class TimelinePage(BaseModel):
    groups: list[TimelineGroup]
    total: int
    page: int
    page_size: int
