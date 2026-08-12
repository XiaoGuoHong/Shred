# ruff: noqa: B008

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from shred.core.database import get_session
from shred.db.models import (
    ActivityEvent,
    Category,
    EventTag,
    SourceMessage,
    Tag,
)
from shred.timeline.schemas import (
    TimelineEvent,
    TimelineGroup,
    TimelineMessage,
    TimelinePage,
)

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


def _build_timeline_event(session: Session, event: ActivityEvent) -> TimelineEvent:
    return TimelineEvent(
        id=event.id,
        position=event.position,
        title=event.title,
        source_fragment=event.source_fragment,
        occurred_at=event.occurred_at,
        occurrence_precision=event.occurrence_precision,
        part_of_day=event.part_of_day,
        category_id=event.category_id,
        category_path=_category_path(session, event.category_id),
        tags=_get_tags(session, event.id),
        status=event.status,
    )


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
    events_by_source: dict[str, list[ActivityEvent]] = {}
    for event in events:
        events_by_source.setdefault(event.source_message_id, []).append(event)

    source_query = session.query(SourceMessage)
    if status is not None:
        matching_source_ids = {e.source_message_id for e in events}
        source_query = source_query.filter(
            or_(
                SourceMessage.status == status,
                SourceMessage.id.in_(matching_source_ids),
            )
        )
    sources: list[SourceMessage] = source_query.all()

    groups: list[tuple[object, TimelineGroup]] = []
    for source in sources:
        group_events = events_by_source.get(source.id, [])
        if category_id is not None and not group_events:
            continue

        sort_key = max(
            (e.occurred_at for e in group_events if e.occurred_at is not None),
            default=source.submitted_at,
        )

        groups.append(
            (
                sort_key,
                TimelineGroup(
                    message=TimelineMessage(
                        id=source.id,
                        submission_uuid=source.submission_uuid,
                        original_text=source.original_text,
                        submitted_at=source.submitted_at,
                        timezone=source.timezone,
                        status=source.status,
                        error_code=source.error_code,
                        error_summary=source.error_summary,
                    ),
                    events=sorted(
                        (_build_timeline_event(session, e) for e in group_events),
                        key=lambda e: e.position,
                    ),
                ),
            )
        )

    groups.sort(key=lambda g: g[0], reverse=True)
    total = len(groups)

    start = (page - 1) * page_size
    end = start + page_size
    page_groups = [g[1] for g in groups[start:end]]

    return TimelinePage(groups=page_groups, total=total, page=page, page_size=page_size)
