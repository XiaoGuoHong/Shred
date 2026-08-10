# ruff: noqa: B008

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from shred.core.database import get_session
from shred.db.models import (
    ActivityEvent,
    Category,
    EventTag,
    SourceMessage,
    Tag,
)
from shred.timeline.schemas import TimelineEvent, TimelineGroup, TimelinePage

router = APIRouter()


def _category_path(session: Session, category_id: str | None) -> list[str]:
    if category_id is None:
        return []
    category = session.get(Category, category_id)
    if category is None:
        return []
    path: list[Category] = []
    current: Category | None = category
    while current is not None:
        path.append(current)
        current = session.get(Category, current.parent_id) if current.parent_id else None
    return [c.name for c in reversed(path)]


def _get_tags(session: Session, event_id: str) -> list[str]:
    tags = (
        session.query(Tag)
        .join(EventTag, EventTag.tag_id == Tag.id)
        .filter(EventTag.event_id == event_id)
        .all()
    )
    return [t.name for t in tags]


@router.get("", response_model=TimelinePage)
def get_timeline(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    category_id: str | None = Query(None),
    status: str | None = Query(None),
    session: Session = Depends(get_session),
) -> TimelinePage:
    event_query = session.query(ActivityEvent)
    if category_id is not None:
        event_query = event_query.filter(ActivityEvent.category_id == category_id)
    if status is not None:
        event_query = event_query.filter(ActivityEvent.status == status)

    events: list[ActivityEvent] = event_query.all()

    groups_map: dict[str, list[ActivityEvent]] = {}
    for event in events:
        groups_map.setdefault(event.source_message_id, []).append(event)

    groups: list[tuple[object, TimelineGroup]] = []
    for source_id, group_events in groups_map.items():
        source = session.get(SourceMessage, source_id)
        if source is None:
            continue

        timeline_events: list[TimelineEvent] = []
        for evt in group_events:
            timeline_events.append(
                TimelineEvent(
                    id=evt.id,
                    position=evt.position,
                    title=evt.title,
                    source_fragment=evt.source_fragment,
                    occurred_at=evt.occurred_at,
                    occurrence_precision=evt.occurrence_precision,
                    part_of_day=evt.part_of_day,
                    category_id=evt.category_id,
                    category_path=_category_path(session, evt.category_id),
                    tags=_get_tags(session, evt.id),
                    status=evt.status,
                )
            )

        sort_key = max(
            (e.occurred_at for e in group_events if e.occurred_at is not None),
            default=source.submitted_at,
        )

        groups.append(
            (
                sort_key,
                TimelineGroup(
                    source_message_id=source.id,
                    original_text=source.original_text,
                    submitted_at=source.submitted_at,
                    timezone=source.timezone,
                    events=sorted(timeline_events, key=lambda e: e.position),
                ),
            )
        )

    groups.sort(key=lambda g: g[0], reverse=True)
    total = len(groups)

    start = (page - 1) * page_size
    end = start + page_size
    page_items = [g[1] for g in groups[start:end]]

    return TimelinePage(items=page_items, total=total, page=page, page_size=page_size)
