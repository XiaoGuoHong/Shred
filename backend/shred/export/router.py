# ruff: noqa: B008

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from shred.core.database import get_session
from shred.db.models import (
    ActivityEvent,
    Category,
    CorrectionMemory,
    EventTag,
    SourceMessage,
    Tag,
)

router = APIRouter()


@router.get("")
def export_data(session: Session = Depends(get_session)) -> JSONResponse:
    now = datetime.now(UTC)
    timestamp = now.strftime("%Y%m%d-%H%M%S")

    source_messages: list[dict[str, object]] = []
    for sm in session.query(SourceMessage).all():
        source_messages.append({
            "id": sm.id,
            "submission_uuid": sm.submission_uuid,
            "original_text": sm.original_text,
            "submitted_at": sm.submitted_at.isoformat(),
            "timezone": sm.timezone,
            "status": sm.status,
            "error_code": sm.error_code,
            "created_at": sm.created_at.isoformat(),
            "updated_at": sm.updated_at.isoformat(),
        })

    events: list[dict[str, object]] = []
    for evt in session.query(ActivityEvent).all():
        events.append({
            "id": evt.id,
            "source_message_id": evt.source_message_id,
            "position": evt.position,
            "title": evt.title,
            "source_fragment": evt.source_fragment,
            "occurred_at": evt.occurred_at.isoformat(),
            "occurrence_precision": evt.occurrence_precision,
            "part_of_day": evt.part_of_day,
            "category_id": evt.category_id,
            "status": evt.status,
            "created_at": evt.created_at.isoformat(),
            "updated_at": evt.updated_at.isoformat(),
        })

    categories: list[dict[str, object]] = []
    for cat in session.query(Category).all():
        categories.append({
            "id": cat.id,
            "name": cat.name,
            "normalized_name": cat.normalized_name,
            "parent_id": cat.parent_id,
            "origin": cat.origin,
            "origin_message_id": cat.origin_message_id,
            "created_at": cat.created_at.isoformat(),
            "updated_at": cat.updated_at.isoformat(),
        })

    tags: list[dict[str, object]] = []
    for tag in session.query(Tag).all():
        event_tags = (
            session.query(EventTag).filter(EventTag.tag_id == tag.id).all()
        )
        tags.append({
            "id": tag.id,
            "name": tag.name,
            "normalized_name": tag.normalized_name,
            "event_ids": [et.event_id for et in event_tags],
        })

    corrections: list[dict[str, object]] = []
    for corr in (
        session.query(CorrectionMemory)
        .filter(CorrectionMemory.active.is_(True))
        .all()
    ):
        corrections.append({
            "id": corr.id,
            "event_id": corr.event_id,
            "event_text": corr.event_text,
            "original_category_id": corr.original_category_id,
            "final_category_id": corr.final_category_id,
            "created_at": corr.created_at.isoformat(),
        })

    data: dict[str, object] = {
        "schema_version": "1.0",
        "generated_at": now.isoformat(),
        "source_messages": source_messages,
        "events": events,
        "categories": categories,
        "tags": tags,
        "corrections": corrections,
    }

    filename = f"shred-export-{timestamp}.json"

    return JSONResponse(
        content=data,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        media_type="application/json; charset=utf-8",
    )
