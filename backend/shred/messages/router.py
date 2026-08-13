# ruff: noqa: B008

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from shred.classification.contracts import Classifier, ClassifierFailure
from shred.core.database import get_session
from shred.core.errors import UndoWindowExpired
from shred.messages.schemas import (
    ErrorDetail,
    ErrorResponse,
    MessageDetail,
    SubmitMessage,
)
from shred.messages.service import MessageService

router = APIRouter()


def _error(code: str, message: str, status: int) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail=ErrorResponse(error=ErrorDetail(code=code, message=message)).model_dump(),
    )


def get_classifier() -> Classifier:
    from shred.core.config import get_env_settings

    if get_env_settings().e2e_fake_classifier:
        from shred.classification.fake_classifier import E2EFakeClassifier

        return E2EFakeClassifier()

    from shred.classification.openai_adapter import OpenAIClassifier

    return OpenAIClassifier()


@router.post("", response_model=MessageDetail, status_code=201)
def submit_message(
    command: SubmitMessage,
    session: Session = Depends(get_session),
    classifier: Classifier = Depends(get_classifier),
) -> MessageDetail:
    try:
        return MessageService(session).submit(command, classifier)
    except ClassifierFailure as exc:
        raise _error(exc.code, exc.summary, 502)
    except ValueError as exc:
        raise _error("invalid_request", str(exc), 422)


@router.get("/{message_id}", response_model=MessageDetail)
def get_message(
    message_id: str,
    session: Session = Depends(get_session),
) -> MessageDetail:
    try:
        return MessageService(session).get(message_id)
    except ValueError as exc:
        raise _error("message_not_found", str(exc), 404)


@router.post("/{message_id}/retry", response_model=MessageDetail)
def retry_message(
    message_id: str,
    session: Session = Depends(get_session),
    classifier: Classifier = Depends(get_classifier),
) -> MessageDetail:
    try:
        return MessageService(session).retry(message_id, classifier)
    except ValueError as exc:
        msg = str(exc)
        if "不存在" in msg:
            raise _error("message_not_found", msg, 404)
        raise _error("invalid_request", msg, 422)


@router.post("/{message_id}/undo", status_code=204)
def undo_message(
    message_id: str,
    session: Session = Depends(get_session),
) -> None:
    now = datetime.now(UTC)
    try:
        MessageService(session).undo(message_id, now)
    except ValueError as exc:
        msg = str(exc)
        if "不存在" in msg:
            raise _error("message_not_found", msg, 404)
        raise _error("invalid_request", msg, 422)
    except UndoWindowExpired as exc:
        raise _error("undo_window_expired", str(exc), 409)


@router.delete("/{message_id}", status_code=204)
def delete_message(
    message_id: str,
    session: Session = Depends(get_session),
) -> None:
    try:
        MessageService(session).delete_source(message_id)
    except ValueError as exc:
        raise _error("message_not_found", str(exc), 404)
