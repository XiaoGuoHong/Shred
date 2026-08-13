"""Export API integration tests."""

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
    CorrectionMemory,
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

    yield engine
    engine.dispose()


def _seed_data(session: Session) -> None:
    cat = Category(id="cat-exp", name="工作", normalized_name="工作", origin="agent")
    session.add(cat)
    session.flush()

    source_a = SourceMessage(
        submission_uuid="exp-uuid-a",
        original_text="上午开会",
        submitted_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC),
        timezone="Asia/Shanghai",
        status="classified",
        error_code=None,
        error_summary="this should be excluded",
    )
    source_b = SourceMessage(
        submission_uuid="exp-uuid-b",
        original_text="下午写代码",
        submitted_at=datetime(2026, 1, 16, 14, 0, 0, tzinfo=UTC),
        timezone="Asia/Shanghai",
        status="classified",
    )
    session.add_all([source_a, source_b])
    session.flush()

    event1 = ActivityEvent(
        id="evt-exp1",
        source_message_id=source_a.id,
        position=0,
        title="上午开会",
        source_fragment="上午开会",
        occurred_at=datetime(2026, 1, 15, 9, 0, 0, tzinfo=UTC),
        occurrence_precision="part_of_day",
        part_of_day="morning",
        category_id=cat.id,
        status="classified",
    )
    event2 = ActivityEvent(
        id="evt-exp2",
        source_message_id=source_b.id,
        position=0,
        title="下午写代码",
        source_fragment="下午写代码",
        occurred_at=datetime(2026, 1, 16, 14, 0, 0, tzinfo=UTC),
        occurrence_precision="part_of_day",
        part_of_day="afternoon",
        category_id=cat.id,
        status="classified",
    )
    session.add_all([event1, event2])
    session.flush()

    active_correction = CorrectionMemory(
        event_id=event1.id,
        event_text="上午开会",
        original_category_id=cat.id,
        final_category_id=cat.id,
        active=True,
    )
    inactive_correction = CorrectionMemory(
        event_id=event2.id,
        event_text="下午写代码",
        original_category_id=cat.id,
        final_category_id=cat.id,
        active=False,
    )
    session.add_all([active_correction, inactive_correction])
    session.commit()


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


class TestExport:
    def test_get_export_returns_200(self, client: TestClient) -> None:
        r = client.get("/api/export")
        assert r.status_code == 200

    def test_schema_version(self, client: TestClient) -> None:
        r = client.get("/api/export")
        assert r.json()["schema_version"] == "1.0"

    def test_generated_at_present(self, client: TestClient) -> None:
        r = client.get("/api/export")
        assert "generated_at" in r.json()
        assert len(r.json()["generated_at"]) > 0

    def test_all_data_sections_present(self, client: TestClient) -> None:
        data = client.get("/api/export").json()
        assert "source_messages" in data
        assert "events" in data
        assert "categories" in data
        assert "tags" in data
        assert "corrections" in data

    def test_source_messages_exist(self, client: TestClient) -> None:
        data = client.get("/api/export").json()
        assert len(data["source_messages"]) >= 2

    def test_events_exist(self, client: TestClient) -> None:
        data = client.get("/api/export").json()
        assert len(data["events"]) >= 2

    def test_no_api_key_in_export(self, client: TestClient) -> None:
        r = client.get("/api/export")
        raw = r.text.lower()
        assert "sk-" not in raw

    def test_no_error_summary_in_export(self, client: TestClient) -> None:
        data = client.get("/api/export").json()
        for sm in data["source_messages"]:
            assert "error_summary" not in sm

    def test_no_inactive_corrections(self, client: TestClient) -> None:
        data = client.get("/api/export").json()
        assert len(data["corrections"]) >= 1
        for corr in data["corrections"]:
            assert "active" not in corr

    def test_content_disposition_header(self, client: TestClient) -> None:
        r = client.get("/api/export")
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd
        assert "shred-export-" in cd
        assert ".json" in cd

    def test_content_type_json_utf8(self, client: TestClient) -> None:
        r = client.get("/api/export")
        ct = r.headers.get("content-type", "")
        assert "application/json" in ct
        assert "utf-8" in ct.lower()
