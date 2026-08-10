"""Settings API integration tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from shred.classification.contracts import (
    ClassificationDraft,
    ClassificationRequest,
    ClassifierFailure,
)
from shred.core import database as db_mod
from shred.db.models import (
    ActivityEvent,
    Base,
    Category,
    CorrectionMemory,
    SourceMessage,
)
from shred.main import create_app
from shred.settings.router import get_connection_classifier


class FakeConnectionClassifier:
    def __init__(self, should_fail: bool = False) -> None:
        self._should_fail = should_fail
        self._connection_tested = False

    def classify(self, _request: ClassificationRequest) -> ClassificationDraft:
        return ClassificationDraft(events=[])

    def test_connection(self) -> None:
        self._connection_tested = True
        if self._should_fail:
            raise ClassifierFailure(code="model_unreachable", summary="连接失败")


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


def _seed_data(session: Session) -> tuple[Category, ActivityEvent, CorrectionMemory]:
    cat = Category(id="cat-s", name="体育", normalized_name="体育", origin="user")
    session.add(cat)
    session.flush()

    source = SourceMessage(
        submission_uuid="settings-uuid",
        original_text="设置测试",
        submitted_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC),
        timezone="Asia/Shanghai",
        status="classified",
    )
    session.add(source)
    session.flush()

    event = ActivityEvent(
        id="evt-s1",
        source_message_id=source.id,
        position=0,
        title="设置测试事件",
        source_fragment="测试",
        occurred_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC),
        occurrence_precision="date",
        category_id=cat.id,
        status="classified",
    )
    session.add(event)
    session.flush()

    correction = CorrectionMemory(
        event_id=event.id,
        event_text="测试",
        original_category_id=cat.id,
        final_category_id=cat.id,
        active=True,
    )
    session.add(correction)
    session.commit()

    return cat, event, correction


@pytest.fixture
def client(engine):
    Base.metadata.create_all(engine)

    session = Session(engine, expire_on_commit=False)
    _seed_data(session)
    session.close()

    fake_cls = FakeConnectionClassifier(should_fail=False)

    def _get_session_override():
        s = Session(engine, expire_on_commit=False)
        try:
            yield s
        finally:
            s.close()

    app = create_app()
    app.dependency_overrides[db_mod.get_session] = _get_session_override
    app.dependency_overrides[get_connection_classifier] = lambda: fake_cls

    with TestClient(app) as c:
        c._fake_classifier = fake_cls
        yield c

    Base.metadata.drop_all(engine)


class TestGetSettings:
    def test_get_returns_200(self, client: TestClient) -> None:
        r = client.get("/api/settings")
        assert r.status_code == 200

    def test_get_has_expected_fields(self, client: TestClient) -> None:
        r = client.get("/api/settings")
        data = r.json()
        assert "api_base_url" in data
        assert "model_name" in data
        assert "api_key_configured" in data
        assert "preference_count" in data

    def test_api_key_configured_is_bool(self, client: TestClient) -> None:
        r = client.get("/api/settings")
        assert isinstance(r.json()["api_key_configured"], bool)

    def test_no_api_key_text_exposed(self, client: TestClient) -> None:
        r = client.get("/api/settings")
        data = r.json()
        for value in data.values():
            if isinstance(value, str):
                assert "sk-" not in value.lower()

    def test_preference_count_positive(self, client: TestClient) -> None:
        r = client.get("/api/settings")
        assert r.json()["preference_count"] >= 1


class TestPatchSettings:
    def test_patch_api_base_url(self, client: TestClient) -> None:
        r = client.patch("/api/settings", json={"api_base_url": "https://custom.api/v1"})
        assert r.status_code == 200
        assert r.json()["api_base_url"] == "https://custom.api/v1"

    def test_patch_model_name(self, client: TestClient) -> None:
        r = client.patch("/api/settings", json={"model_name": "custom-model"})
        assert r.status_code == 200
        assert r.json()["model_name"] == "custom-model"

    def test_api_key_field_ignored(self, client: TestClient) -> None:
        before = client.get("/api/settings").json()
        r = client.patch("/api/settings", json={
            "api_base_url": before["api_base_url"],
            "model_name": before["model_name"],
            "api_key": "sk-should-be-ignored",
        })
        assert r.status_code == 200
        after = r.json()
        assert after["api_base_url"] == before["api_base_url"]
        assert after["model_name"] == before["model_name"]
        assert isinstance(after["api_key_configured"], bool)


class TestTestConnection:
    def test_test_connection_ok(self, client: TestClient) -> None:
        r = client.post("/api/settings/test-connection")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_test_connection_failure(self, client: TestClient) -> None:
        failing = FakeConnectionClassifier(should_fail=True)
        client.app.dependency_overrides[get_connection_classifier] = lambda: failing
        r = client.post("/api/settings/test-connection")
        assert r.json()["ok"] is False
        assert r.json()["error_code"] is not None


class TestPreferences:
    def test_delete_without_confirm_fails(self, client: TestClient) -> None:
        r = client.request("DELETE", "/api/preferences", json={"confirm": False})
        assert r.status_code == 422

    def test_delete_with_confirm_clears_corrections(self, client: TestClient) -> None:
        pre = client.get("/api/settings").json()
        assert pre["preference_count"] >= 1

        r = client.request("DELETE", "/api/preferences", json={"confirm": True})
        assert r.status_code == 204

        post = client.get("/api/settings").json()
        assert post["preference_count"] == 0
