"""Timeline API integration tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from shred.core import database as db_mod
from shred.db.models import (
    ActivityEvent,
    Base,
    Category,
    SourceMessage,
)
from shred.main import create_app


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

    return engine


def _seed_data(session: Session) -> tuple[SourceMessage, SourceMessage, Category]:
    day1 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    day2 = datetime(2026, 1, 16, 14, 0, 0, tzinfo=UTC)

    source_a = SourceMessage(
        submission_uuid="uuid-a",
        original_text="上午开会，下午写代码",
        submitted_at=day1,
        timezone="Asia/Shanghai",
        status="classified",
    )
    session.add(source_a)
    session.flush()

    source_b = SourceMessage(
        submission_uuid="uuid-b",
        original_text="明天去医院体检",
        submitted_at=day2,
        timezone="Asia/Shanghai",
        status="classified",
    )
    session.add(source_b)
    session.flush()

    source_c = SourceMessage(
        submission_uuid="uuid-c",
        original_text="分类失败的记录",
        submitted_at=datetime(2026, 1, 16, 15, 0, 0, tzinfo=UTC),
        timezone="Asia/Shanghai",
        status="pending",
        error_code="model_timeout",
        error_summary="请求超时",
    )
    session.add(source_c)
    session.flush()

    cat_work = Category(id="cat-work", name="工作", normalized_name="工作", origin="agent")
    cat_health = Category(id="cat-health", name="健康", normalized_name="健康", origin="agent")
    session.add_all([cat_work, cat_health])
    session.flush()

    event_a1 = ActivityEvent(
        id="evt-a1",
        source_message_id=source_a.id,
        position=0,
        title="上午开会",
        source_fragment="上午开会",
        occurred_at=datetime(2026, 1, 15, 9, 0, 0, tzinfo=UTC),
        occurrence_precision="part_of_day",
        part_of_day="morning",
        category_id=cat_work.id,
        status="classified",
    )
    event_a2 = ActivityEvent(
        id="evt-a2",
        source_message_id=source_a.id,
        position=1,
        title="下午写代码",
        source_fragment="下午写代码",
        occurred_at=datetime(2026, 1, 15, 14, 0, 0, tzinfo=UTC),
        occurrence_precision="part_of_day",
        part_of_day="afternoon",
        category_id=cat_work.id,
        status="pending",
    )
    event_b1 = ActivityEvent(
        id="evt-b1",
        source_message_id=source_b.id,
        position=0,
        title="去医院体检",
        source_fragment="去医院体检",
        occurred_at=datetime(2026, 1, 17, 8, 0, 0, tzinfo=UTC),
        occurrence_precision="date",
        category_id=cat_health.id,
        status="classified",
    )
    session.add_all([event_a1, event_a2, event_b1])
    session.commit()

    return source_a, source_b, cat_work


@pytest.fixture
def client(engine):
    Base.metadata.create_all(engine)

    session = Session(engine, expire_on_commit=False)
    _seed_data(session)

    def _get_session_override():
        s = Session(engine, expire_on_commit=False)
        try:
            yield s
        finally:
            s.close()

    app = create_app()
    app.dependency_overrides[db_mod.get_session] = _get_session_override

    with TestClient(app) as c:
        yield c

    Base.metadata.drop_all(engine)
    session.close()


class TestTimelineAll:
    def test_get_all_returns_200_with_groups(self, client: TestClient) -> None:
        r = client.get("/api/timeline")
        assert r.status_code == 200
        data = r.json()
        assert "groups" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_groups_ordered_by_occurrence_desc(self, client: TestClient) -> None:
        r = client.get("/api/timeline")
        groups = r.json()["groups"]
        assert len(groups) >= 2

        def _sort_key(group: dict) -> str:
            if group["events"]:
                return max(e["occurred_at"] for e in group["events"])
            return group["message"]["submitted_at"]

        first_key = _sort_key(groups[0])
        second_key = _sort_key(groups[1])
        assert first_key >= second_key

    def test_each_group_has_source_text(self, client: TestClient) -> None:
        r = client.get("/api/timeline")
        for group in r.json()["groups"]:
            assert "original_text" in group["message"]
            assert len(group["message"]["original_text"]) > 0
            assert "submitted_at" in group["message"]
            assert "timezone" in group["message"]
            assert "status" in group["message"]
            if group["message"]["status"] == "pending":
                continue
            assert len(group["events"]) > 0

    def test_events_have_category_path(self, client: TestClient) -> None:
        r = client.get("/api/timeline")
        for group in r.json()["groups"]:
            for evt in group["events"]:
                assert "category_path" in evt
                assert isinstance(evt["category_path"], list)


class TestTimelineCategoryFilter:
    def test_filter_by_category_returns_only_matching_events(self, client: TestClient) -> None:
        r = client.get("/api/timeline?category_id=cat-health")
        assert r.status_code == 200
        groups = r.json()["groups"]
        assert len(groups) >= 1
        found_health = False
        for group in groups:
            for evt in group["events"]:
                assert evt["category_id"] == "cat-health"
                found_health = True
        assert found_health

    def test_filter_by_category_keeps_source_group(self, client: TestClient) -> None:
        r = client.get("/api/timeline?category_id=cat-health")
        groups = r.json()["groups"]
        for group in groups:
            assert "original_text" in group["message"]
            assert len(group["message"]["original_text"]) > 0


class TestTimelineStatusAndPagination:
    def test_filter_by_status_pending(self, client: TestClient) -> None:
        r = client.get("/api/timeline?status=pending")
        assert r.status_code == 200
        groups = r.json()["groups"]
        assert len(groups) >= 1
        found_pending = False
        found_pending_source = False
        for group in groups:
            if group["message"]["status"] == "pending":
                found_pending_source = True
            for evt in group["events"]:
                assert evt["status"] == "pending"
                found_pending = True
        assert found_pending
        assert found_pending_source

    def test_pagination_defaults(self, client: TestClient) -> None:
        r = client.get("/api/timeline?page=1&page_size=50")
        assert r.status_code == 200
        data = r.json()
        assert data["page"] == 1
        assert data["page_size"] == 50

    def test_page_size_rejected_above_100(self, client: TestClient) -> None:
        r = client.get("/api/timeline?page_size=101")
        assert r.status_code == 422

    def test_total_matches_item_count(self, client: TestClient) -> None:
        r = client.get("/api/timeline")
        data = r.json()
        assert data["total"] >= len(data["groups"])
