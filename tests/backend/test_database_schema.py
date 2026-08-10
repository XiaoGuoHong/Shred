"""Integration tests for the Alembic-managed SQLite schema."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from shred.core.config import get_env_settings

EXPECTED_TABLES = {
    "source_messages",
    "activity_events",
    "categories",
    "tags",
    "event_tags",
    "correction_memories",
    "app_settings",
    "alembic_version",
}
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _create_sqlite_engine(url: str) -> Engine:
    engine = create_engine(url)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection: object, _: object) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")  # type: ignore[attr-defined]

    return engine


@pytest.fixture
def migrated_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    database_url = f"sqlite:///{tmp_path / 'shred-test.db'}"
    monkeypatch.setenv("SHRED_DATABASE_URL", database_url)
    get_env_settings.cache_clear()
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.upgrade(config, "head")
    engine = _create_sqlite_engine(database_url)

    try:
        yield engine
    finally:
        engine.dispose()
        get_env_settings.cache_clear()


def _category_values(name: str, normalized_name: str, parent_id: str | None = None) -> dict[str, str | None]:
    return {
        "id": str(uuid4()),
        "name": name,
        "normalized_name": normalized_name,
        "parent_id": parent_id,
        "origin": "user",
    }


def test_initial_migration_creates_required_tables(migrated_engine: Engine) -> None:
    assert EXPECTED_TABLES <= set(inspect(migrated_engine).get_table_names())


def test_alembic_config_defaults_to_durable_data_path() -> None:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))

    assert config.get_main_option("sqlalchemy.url") == "sqlite:////data/shred.db"


def test_initial_migration_requires_event_supporting_fields(migrated_engine: Engine) -> None:
    columns = {
        column["name"]: column
        for column in inspect(migrated_engine).get_columns("activity_events")
    }

    assert columns["source_fragment"]["nullable"] is False
    assert columns["occurred_at"]["nullable"] is False
    assert columns["occurrence_precision"]["nullable"] is False
    assert columns["part_of_day"]["nullable"] is True


def test_category_name_uniqueness_respects_parent_scope(migrated_engine: Engine) -> None:
    with migrated_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO categories (id, name, normalized_name, parent_id, origin) "
                "VALUES (:id, :name, :normalized_name, :parent_id, :origin)"
            ),
            _category_values("Work", "work"),
        )
        with pytest.raises(IntegrityError):
            connection.execute(
                text(
                    "INSERT INTO categories (id, name, normalized_name, parent_id, origin) "
                    "VALUES (:id, :name, :normalized_name, :parent_id, :origin)"
                ),
                _category_values("Work duplicate", "work"),
            )

    parent_one = _category_values("Parent one", "parent-one")
    parent_two = _category_values("Parent two", "parent-two")
    child_one = _category_values("Review", "review", parent_one["id"])
    duplicate_child = _category_values("Review duplicate", "review", parent_one["id"])
    child_under_other_parent = _category_values("Review", "review", parent_two["id"])

    with migrated_engine.begin() as connection:
        insert = text(
            "INSERT INTO categories (id, name, normalized_name, parent_id, origin) "
            "VALUES (:id, :name, :normalized_name, :parent_id, :origin)"
        )
        connection.execute(insert, [parent_one, parent_two, child_one])
        with pytest.raises(IntegrityError):
            connection.execute(insert, duplicate_child)
        connection.execute(insert, child_under_other_parent)


def test_foreign_keys_reject_orphan_events_and_cascade_source_deletion(
    migrated_engine: Engine,
) -> None:
    source_id = str(uuid4())
    event_id = str(uuid4())
    now = datetime.now(UTC).isoformat()
    source_values = {
        "id": source_id,
        "submission_uuid": str(uuid4()),
        "original_text": "Schedule review",
        "submitted_at": now,
        "timezone": "UTC",
        "status": "accepted",
    }
    event_values = {
        "id": event_id,
        "source_message_id": source_id,
        "position": 0,
        "title": "Review",
        "source_fragment": "Schedule review",
        "occurred_at": now,
        "occurrence_precision": "minute",
        "status": "pending",
    }

    with migrated_engine.begin() as connection:
        with pytest.raises(IntegrityError):
            connection.execute(
                text(
                    "INSERT INTO activity_events "
                    "(id, source_message_id, position, title, source_fragment, occurred_at, "
                    "occurrence_precision, status) VALUES "
                    "(:id, :source_message_id, :position, :title, :source_fragment, "
                    ":occurred_at, :occurrence_precision, :status)"
                ),
                {**event_values, "source_message_id": str(uuid4())},
            )
        connection.execute(
            text(
                "INSERT INTO source_messages "
                "(id, submission_uuid, original_text, submitted_at, timezone, status) "
                "VALUES (:id, :submission_uuid, :original_text, :submitted_at, :timezone, :status)"
            ),
            source_values,
        )
        connection.execute(
            text(
                "INSERT INTO activity_events "
                "(id, source_message_id, position, title, source_fragment, occurred_at, "
                "occurrence_precision, status) VALUES "
                "(:id, :source_message_id, :position, :title, :source_fragment, "
                ":occurred_at, :occurrence_precision, :status)"
            ),
            event_values,
        )
        connection.execute(text("DELETE FROM source_messages WHERE id = :id"), {"id": source_id})
        assert connection.scalar(text("SELECT COUNT(*) FROM activity_events WHERE id = :id"), {"id": event_id}) == 0
