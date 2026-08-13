"""Event API integration tests."""

# ruff: noqa: DTZ001

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from shred.classification.contracts import (
    CategoryChoice,
    ClassificationDraft,
    ClassificationRequest,
    ClassifierFailure,
    EventDraft,
)
from shred.core import database as db_mod
from shred.db.models import (
    ActivityEvent,
    Base,
    Category,
    SourceMessage,
)
from shred.events.router import get_classifier
from shred.main import create_app


class FakeClassifier:
    def __init__(
        self,
        drafts: ClassificationDraft | None = None,
        failure: ClassifierFailure | None = None,
    ) -> None:
        self._drafts = drafts
        self._failure = failure
        self._call_count = 0
        self._last_request: ClassificationRequest | None = None

    def classify(self, request: ClassificationRequest) -> ClassificationDraft:
        self._call_count += 1
        self._last_request = request
        if self._failure is not None:
            raise self._failure
        assert self._drafts is not None
        return self._drafts

    def test_connection(self) -> None:
        pass

    @property
    def call_count(self) -> int:
        return self._call_count


def _make_reclassify_classifier(category_id: str) -> FakeClassifier:
    return FakeClassifier(
        drafts=ClassificationDraft(
            events=[
                EventDraft(
                    title="重新分类事件",
                    source_fragment="忽略",
                    local_date=datetime(2026, 1, 14).date(),
                    precision="date",
                    category=CategoryChoice(existing_id=category_id),
                    tags=["重分类标签"],
                )
            ]
        )
    )


def _failing_classifier() -> FakeClassifier:
    return FakeClassifier(failure=ClassifierFailure(code="model_timeout", summary="超时"))


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


def _seed_data(session: Session) -> tuple[SourceMessage, Category, ActivityEvent, ActivityEvent]:
    source = SourceMessage(
        submission_uuid="api-test-uuid",
        original_text="测试消息内容",
        submitted_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC),
        timezone="Asia/Shanghai",
        status="classified",
    )
    session.add(source)
    session.flush()

    cat = Category(id="cat-001", name="工作", normalized_name="工作", origin="agent")
    session.add(cat)
    session.flush()

    event1 = ActivityEvent(
        id="evt-001",
        source_message_id=source.id,
        position=0,
        title="事件一",
        source_fragment="第一个事件",
        occurred_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC),
        occurrence_precision="date",
        part_of_day=None,
        category_id=cat.id,
        status="classified",
    )
    session.add(event1)

    event2 = ActivityEvent(
        id="evt-002",
        source_message_id=source.id,
        position=1,
        title="事件二",
        source_fragment="第二个事件",
        occurred_at=datetime(2026, 1, 16, 12, 0, 0, tzinfo=UTC),
        occurrence_precision="date",
        part_of_day=None,
        category_id=cat.id,
        status="classified",
    )
    session.add(event2)

    session.commit()
    return source, cat, event1, event2


@pytest.fixture
def client(engine):
    Base.metadata.create_all(engine)

    session = Session(engine, expire_on_commit=False)
    source, cat, event1, event2 = _seed_data(session)
    reclassify_cls = _make_reclassify_classifier(cat.id)

    def _get_session_override():
        s = Session(engine, expire_on_commit=False)
        try:
            yield s
        finally:
            s.close()

    app = create_app()
    app.dependency_overrides[db_mod.get_session] = _get_session_override
    app.dependency_overrides[get_classifier] = lambda: reclassify_cls

    with TestClient(app) as c:
        c._test_data = {"source": source, "cat": cat, "event1": event1, "event2": event2, "classifier": reclassify_cls}
        yield c

    Base.metadata.drop_all(engine)
    session.close()


# ------------------------------------------------------------------
# PATCH /api/events/{event_id}
# ------------------------------------------------------------------


class TestPatchEvent:
    def test_patch_title_returns_200(self, client: TestClient) -> None:
        r = client.patch("/api/events/evt-001", json={"title": "修改后标题"})
        assert r.status_code == 200
        assert r.json()["title"] == "修改后标题"

    def test_patch_category_returns_200(self, client: TestClient) -> None:
        cat_b = Category(id="cat-002", name="学习", normalized_name="学习", origin="agent")
        s = next(client.app.dependency_overrides[db_mod.get_session]())
        s.add(cat_b)
        s.commit()
        s.close()

        r = client.patch("/api/events/evt-001", json={"category_id": "cat-002"})
        assert r.status_code == 200
        assert r.json()["category_id"] == "cat-002"

    def test_patch_tags_returns_200(self, client: TestClient) -> None:
        r = client.patch("/api/events/evt-001", json={"tags": ["紧急", "重要"]})
        assert r.status_code == 200
        assert set(r.json()["tags"]) == {"紧急", "重要"}

    def test_patch_nonexistent_returns_404(self, client: TestClient) -> None:
        r = client.patch("/api/events/nonexistent", json={"title": "测试"})
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "event_not_found"

    def test_patch_invalid_occurred_at_returns_422(self, client: TestClient) -> None:
        r = client.patch("/api/events/evt-001", json={"occurred_at": "not-a-datetime"})
        assert r.status_code == 422


# ------------------------------------------------------------------
# DELETE /api/events/{event_id}
# ------------------------------------------------------------------


class TestDeleteEvent:
    def test_delete_returns_204(self, client: TestClient) -> None:
        r = client.delete("/api/events/evt-002")
        assert r.status_code == 204

    def test_delete_nonexistent_returns_404(self, client: TestClient) -> None:
        r = client.delete("/api/events/nonexistent")
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "event_not_found"


# ------------------------------------------------------------------
# POST /api/events/{event_id}/reclassify
# ------------------------------------------------------------------


class TestReclassifyEvent:
    def test_reclassify_returns_200(self, client: TestClient) -> None:
        r = client.post("/api/events/evt-001/reclassify")
        assert r.status_code == 200
        data = r.json()
        assert data["title"] == "重新分类事件"
        assert data["tags"] == ["重分类标签"]

    def test_reclassify_nonexistent_returns_404(self, client: TestClient) -> None:
        r = client.post("/api/events/nonexistent/reclassify")
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "event_not_found"

    def test_reclassify_classifier_failure_returns_200_pending(self, client: TestClient) -> None:
        client.app.dependency_overrides[get_classifier] = lambda: _failing_classifier()

        r = client.post("/api/events/evt-001/reclassify")
        assert r.status_code == 200
        assert r.json()["status"] == "pending"
