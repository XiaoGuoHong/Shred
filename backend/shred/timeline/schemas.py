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


class TimelineGroup(BaseModel):
    source_message_id: str
    original_text: str
    submitted_at: datetime
    timezone: str
    events: list[TimelineEvent]


class TimelinePage(BaseModel):
    items: list[TimelineGroup]
    total: int
    page: int
    page_size: int
