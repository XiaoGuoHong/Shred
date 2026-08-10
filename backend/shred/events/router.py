# ruff: noqa: B008

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from shred.classification.contracts import Classifier
from shred.core.database import get_session
from shred.events.schemas import EventView, UpdateEvent
from shred.events.service import EventService
from shred.messages.schemas import ErrorDetail, ErrorResponse

router = APIRouter()


def _error(code: str, message: str, status: int) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail=ErrorResponse(error=ErrorDetail(code=code, message=message)).model_dump(),
    )


def get_classifier() -> Classifier:
    from shred.classification.openai_adapter import OpenAIClassifier

    return OpenAIClassifier()


@router.patch("/{event_id}", response_model=EventView)
def update_event(
    event_id: str,
    changes: UpdateEvent,
    session: Session = Depends(get_session),
) -> EventView:
    try:
        with session.begin():
            return EventService(session).update(event_id, changes)
    except ValueError as exc:
        raise _error("event_not_found", str(exc), 404)


@router.delete("/{event_id}", status_code=204)
def delete_event(
    event_id: str,
    session: Session = Depends(get_session),
) -> None:
    try:
        with session.begin():
            EventService(session).delete(event_id)
    except ValueError as exc:
        raise _error("event_not_found", str(exc), 404)


@router.post("/{event_id}/reclassify", response_model=EventView)
def reclassify_event(
    event_id: str,
    session: Session = Depends(get_session),
    classifier: Classifier = Depends(get_classifier),
) -> EventView:
    try:
        with session.begin():
            return EventService(session).reclassify(event_id, classifier)
    except ValueError as exc:
        msg = str(exc)
        if "不存在" in msg:
            raise _error("event_not_found", msg, 404)
        raise _error("invalid_request", msg, 422)
