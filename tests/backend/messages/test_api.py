"""Message API integration tests."""

# ruff: noqa: DTZ001

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from shred.core import database as db_mod
from shred.db.models import Base
from shred.main import create_app
from shred.messages.router import get_classifier
from tests.backend.messages.fakes import (
    failing_classifier,
    make_interview_classifier,
)


@pytest.fixture(scope="module")
def engine():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection: object, _: object) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")  # type: ignore[attr-defined]

    yield engine
    engine.dispose()


@pytest.fixture
def classifier():
    return make_interview_classifier(datetime(2026, 1, 15).date())


@pytest.fixture
def client(engine, classifier):
    Base.metadata.create_all(engine)

    def _get_session_override():
        session = Session(engine, expire_on_commit=False)
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[db_mod.get_session] = _get_session_override
    app.dependency_overrides[get_classifier] = lambda: classifier

    with TestClient(app) as c:
        yield c

    Base.metadata.drop_all(engine)


class TestSubmitAPI:
    def test_post_returns_201_for_classified(self, client: TestClient) -> None:
        r = client.post(
            "/api/messages",
            json={"text": "上午预约下周一的面试", "timezone": "Asia/Shanghai", "submitted_at": "2026-01-15T02:00:00+00:00"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["message"]["status"] == "classified"
        assert len(data["events"]) == 3

    def test_post_returns_201_for_pending(self, client: TestClient) -> None:
        client.app.dependency_overrides[get_classifier] = lambda: failing_classifier()

        r = client.post(
            "/api/messages",
            json={"text": "测试", "timezone": "UTC", "submitted_at": "2026-01-15T02:00:00+00:00"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["message"]["status"] == "pending"

    def test_post_with_custom_uuid(self, client: TestClient) -> None:
        r = client.post(
            "/api/messages",
            json={
                "text": "测试",
                "submitted_at": "2026-01-15T02:00:00+00:00",
                "timezone": "UTC",
                "submission_uuid": "custom-uuid-123",
            },
        )
        assert r.status_code == 201
        assert r.json()["message"]["submission_uuid"] == "custom-uuid-123"

    def test_post_idempotent_same_uuid(self, client: TestClient) -> None:
        payload = {"text": "测试",
                "submitted_at": "2026-01-15T02:00:00+00:00", "timezone": "UTC", "submission_uuid": "idem-test"}
        first = client.post("/api/messages", json=payload)
        second = client.post("/api/messages", json=payload)
        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["message"]["id"] == second.json()["message"]["id"]


class TestGetAPI:
    def test_get_returns_200(self, client: TestClient) -> None:
        r = client.post(
            "/api/messages",
            json={"text": "测试", "timezone": "UTC", "submitted_at": "2026-01-15T02:00:00+00:00"},
        )
        msg_id = r.json()["message"]["id"]

        r = client.get(f"/api/messages/{msg_id}")
        assert r.status_code == 200
        assert r.json()["message"]["id"] == msg_id

    def test_get_nonexistent_returns_404(self, client: TestClient) -> None:
        r = client.get("/api/messages/nonexistent")
        assert r.status_code == 404


class TestRetryAPI:
    def test_retry_pending_to_classified(self, client: TestClient) -> None:
        client.app.dependency_overrides[get_classifier] = lambda: failing_classifier()

        r = client.post(
            "/api/messages",
            json={"text": "上午预约下周一的面试", "timezone": "Asia/Shanghai", "submitted_at": "2026-01-15T02:00:00+00:00"},
        )
        assert r.json()["message"]["status"] == "pending"
        msg_id = r.json()["message"]["id"]

        client.app.dependency_overrides[get_classifier] = lambda: make_interview_classifier(
            datetime(2026, 1, 15).date()
        )

        r = client.post(f"/api/messages/{msg_id}/retry")
        assert r.status_code == 200
        assert r.json()["message"]["status"] == "classified"
        assert len(r.json()["events"]) == 3

    def test_retry_nonexistent_returns_404(self, client: TestClient) -> None:
        r = client.post("/api/messages/nonexistent/retry")
        assert r.status_code == 404


class TestUndoAPI:
    def test_undo_returns_204_within_window(self, client: TestClient) -> None:
        r = client.post(
            "/api/messages",
            json={"text": "测试", "timezone": "UTC", "submitted_at": "2026-01-15T02:00:00+00:00"},
        )
        msg_id = r.json()["message"]["id"]

        r = client.post(f"/api/messages/{msg_id}/undo")
        assert r.status_code == 204

    def test_undo_nonexistent_returns_404(self, client: TestClient) -> None:
        r = client.post("/api/messages/nonexistent/undo")
        assert r.status_code == 404


class TestDeleteAPI:
    def test_delete_returns_204(self, client: TestClient) -> None:
        r = client.post(
            "/api/messages",
            json={"text": "测试", "timezone": "UTC", "submitted_at": "2026-01-15T02:00:00+00:00"},
        )
        msg_id = r.json()["message"]["id"]

        r = client.delete(f"/api/messages/{msg_id}")
        assert r.status_code == 204

    def test_delete_nonexistent_returns_404(self, client: TestClient) -> None:
        r = client.delete("/api/messages/nonexistent")
        assert r.status_code == 404
