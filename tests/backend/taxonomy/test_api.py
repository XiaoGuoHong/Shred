"""Taxonomy API integration tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from shred.core import database as db_mod
from shred.db.models import Base
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


@pytest.fixture(scope="module")
def client(engine):
    Base.metadata.create_all(engine)

    def _get_session_override():
        session = Session(engine, expire_on_commit=False)
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[db_mod.get_session] = _get_session_override

    yield TestClient(app)


class TestEndToEndSequence:
    def test_create_root_child_rename_tree_impact_delete(self, client: TestClient) -> None:
        r = client.post("/api/categories", json={"name": "工作"})
        assert r.status_code == 201
        root = r.json()
        assert root["name"] == "工作"
        assert root["parent_id"] is None

        r = client.post("/api/categories", json={"name": "编程", "parent_id": root["id"]})
        assert r.status_code == 201
        child = r.json()
        assert child["name"] == "编程"
        assert child["parent_id"] == root["id"]

        r = client.patch(f"/api/categories/{child['id']}", json={"name": "写代码"})
        assert r.status_code == 200
        renamed = r.json()
        assert renamed["name"] == "写代码"

        r = client.get("/api/categories")
        assert r.status_code == 200
        tree = r.json()
        assert len(tree) == 1
        assert tree[0]["name"] == "工作"
        assert len(tree[0]["children"]) == 1
        assert tree[0]["children"][0]["name"] == "写代码"

        r = client.post(f"/api/categories/{child['id']}/delete-impact")
        assert r.status_code == 200
        impact = r.json()
        assert impact["category_name"] == "写代码"

        r = client.delete(f"/api/categories/{root['id']}")
        assert r.status_code == 200
        del_impact = r.json()
        assert del_impact["descendant_count"] >= 1


class TestErrorResponses:
    def test_depth_exceeded_returns_422(self, client: TestClient) -> None:
        r = client.post("/api/categories", json={"name": "工作"})
        root_id = r.json()["id"]
        r = client.post("/api/categories", json={"name": "编程", "parent_id": root_id})
        child_id = r.json()["id"]
        r = client.post("/api/categories", json={"name": "Python", "parent_id": child_id})
        assert r.status_code == 422
        body = r.json()
        assert body["error"]["code"] == "category_depth_exceeded"

    def test_sibling_duplicate_returns_409(self, client: TestClient) -> None:
        client.post("/api/categories", json={"name": "工作"})
        r = client.post("/api/categories", json={"name": "工作"})
        assert r.status_code == 409
        body = r.json()
        assert body["error"]["code"] == "category_name_conflict"

    def test_not_found_returns_404(self, client: TestClient) -> None:
        r = client.patch("/api/categories/nonexistent", json={"name": "X"})
        assert r.status_code == 404

    def test_no_orm_internals_in_response(self, client: TestClient) -> None:
        r = client.post("/api/categories", json={"name": "测试"})
        assert r.status_code == 201
        data = r.json()
        assert "_sa_instance_state" not in str(data)


class TestMergeAPI:
    def test_merge_endpoint(self, client: TestClient) -> None:
        r1 = client.post("/api/categories", json={"name": "运动"})
        r2 = client.post("/api/categories", json={"name": "健身"})
        src = r1.json()["id"]
        tgt = r2.json()["id"]

        r = client.post("/api/categories/merge", json={"source_id": src, "target_id": tgt})
        assert r.status_code == 200
        result = r.json()
        assert result["merged_events"] >= 0
