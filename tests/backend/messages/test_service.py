"""Message service tests."""

# ruff: noqa: DTZ001

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from shred.core.errors import UndoWindowExpired
from shred.db.models import ActivityEvent, Base, Category, SourceMessage, Tag
from shred.messages.schemas import SubmitMessage
from shred.messages.service import MessageService
from tests.backend.messages.fakes import (
    FakeClassifier,
    failing_classifier,
    make_interview_classifier,
)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://", echo=False)

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection: object, _: object) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")  # type: ignore[attr-defined]

    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as s:
        yield s


_NOW = datetime(2026, 1, 15, 2, 0, 0, tzinfo=UTC)


def _submit_command(
    text: str = "上午预约下周一的面试",
    tz: str = "Asia/Shanghai",
    uuid: str = "test-uuid-001",
) -> SubmitMessage:
    return SubmitMessage(text=text, timezone=tz, submitted_at=_NOW, submission_uuid=uuid)


# ------------------------------------------------------------------
# Happy path
# ------------------------------------------------------------------


class TestSubmitHappyPath:
    def test_creates_source_before_classifier_called(self, session: Session) -> None:
        classifier = make_interview_classifier(datetime(2026, 1, 15).date())
        svc = MessageService(session)
        cmd = _submit_command()

        detail = svc.submit(cmd, classifier)

        assert detail.message.status == "classified"
        assert detail.message.submission_uuid == "test-uuid-001"
        assert detail.message.original_text == cmd.text
        assert detail.message.timezone == "Asia/Shanghai"

    def test_three_events_in_source_order(self, session: Session) -> None:
        classifier = make_interview_classifier(datetime(2026, 1, 15).date())
        svc = MessageService(session)

        detail = svc.submit(_submit_command(), classifier)

        assert len(detail.events) == 3
        assert detail.events[0].position == 0
        assert detail.events[1].position == 1
        assert detail.events[2].position == 2

    def test_morning_part_of_day_resolves_to_09_anchor(self, session: Session) -> None:
        classifier = make_interview_classifier(datetime(2026, 1, 15).date())
        svc = MessageService(session)

        detail = svc.submit(_submit_command(), classifier)

        morning_event = detail.events[0]
        assert morning_event.occurrence_precision == "part_of_day"
        assert morning_event.part_of_day == "morning"
        assert morning_event.source_fragment == "上午"

    def test_inferred_event_resolves_to_submission_time(self, session: Session) -> None:
        classifier = make_interview_classifier(datetime(2026, 1, 15).date())
        svc = MessageService(session)

        detail = svc.submit(_submit_command(), classifier)

        inferred = detail.events[1]
        assert inferred.occurrence_precision == "inferred"

    def test_category_paths_resolved_through_taxonomy(self, session: Session) -> None:
        classifier = make_interview_classifier(datetime(2026, 1, 15).date())
        svc = MessageService(session)

        detail = svc.submit(_submit_command(), classifier)

        event2 = detail.events[2]
        assert event2.category_path == ["工作", "面试"]
        assert event2.category_id is not None

    def test_repeat_uuid_returns_existing_idempotently(self, session: Session) -> None:
        classifier = make_interview_classifier(datetime(2026, 1, 15).date())
        svc = MessageService(session)

        first = svc.submit(_submit_command(), classifier)
        assert classifier.call_count == 1

        second = svc.submit(_submit_command(), classifier)
        assert classifier.call_count == 1
        assert first.message.id == second.message.id
        assert second.message.submission_uuid == first.message.submission_uuid

    def test_source_text_preserved_exactly(self, session: Session) -> None:
        classifier = make_interview_classifier(datetime(2026, 1, 15).date())
        svc = MessageService(session)
        text = "上午预约下周一的面试"

        detail = svc.submit(_submit_command(text=text), classifier)

        assert detail.message.original_text == text

    def test_events_have_status_classified(self, session: Session) -> None:
        classifier = make_interview_classifier(datetime(2026, 1, 15).date())
        svc = MessageService(session)

        detail = svc.submit(_submit_command(), classifier)

        for ev in detail.events:
            assert ev.status == "classified"

    def test_tags_created_and_associated(self, session: Session) -> None:
        classifier = make_interview_classifier(datetime(2026, 1, 15).date())
        svc = MessageService(session)

        detail = svc.submit(_submit_command(), classifier)

        assert detail.events[1].tags == ["面试"]
        assert detail.events[2].tags == ["面试"]


# ------------------------------------------------------------------
# Pending and retry
# ------------------------------------------------------------------


class TestClassifierFailure:
    def test_source_preserved_with_pending_status(self, session: Session) -> None:
        classifier = failing_classifier("model_timeout", "请求超时")
        svc = MessageService(session)

        detail = svc.submit(_submit_command(), classifier)

        assert detail.message.status == "pending"
        assert detail.message.error_code == "model_timeout"
        assert detail.message.error_summary == "请求超时"
        assert len(detail.events) == 0

    def test_source_text_preserved_after_failure(self, session: Session) -> None:
        classifier = failing_classifier()
        svc = MessageService(session)
        text = "上午预约下周一的面试"

        detail = svc.submit(_submit_command(text=text), classifier)

        assert detail.message.original_text == text

    def test_retry_clears_failure_and_classifies(self, session: Session) -> None:
        fail_cls = failing_classifier()
        svc = MessageService(session)
        pending = svc.submit(_submit_command(), fail_cls)
        assert pending.message.status == "pending"

        success_cls = make_interview_classifier(datetime(2026, 1, 15).date())
        retried = svc.retry(pending.message.id, success_cls)

        assert retried.message.status == "classified"
        assert retried.message.error_code is None
        assert retried.message.error_summary is None
        assert len(retried.events) == 3

    def test_retry_on_nonexistent_message_raises(self, session: Session) -> None:
        svc = MessageService(session)
        classifier = make_interview_classifier(datetime(2026, 1, 15).date())

        with pytest.raises(ValueError, match="不存在"):
            svc.retry("nonexistent", classifier)

    def test_retry_on_classified_message_raises(self, session: Session) -> None:
        classifier = make_interview_classifier(datetime(2026, 1, 15).date())
        svc = MessageService(session)
        detail = svc.submit(_submit_command(), classifier)

        with pytest.raises(ValueError, match="失败或处理中"):
            svc.retry(detail.message.id, classifier)


class TestEventPersistenceFailure:
    def test_no_partial_events_on_draft_persistence_error(self, session: Session) -> None:
        from shred.classification.contracts import (
            CategoryChoice,
            ClassificationDraft,
            EventDraft,
        )

        bad_draft = EventDraft(
            title="bad",
            source_fragment="x",
            local_date=datetime(2027, 1, 1).date(),
            precision="exact",
            local_time=datetime(2027, 1, 1, 12, 0).time(),
            category=CategoryChoice(new_path=["工作"]),
        )
        cls = FakeClassifier(drafts=ClassificationDraft(events=[bad_draft]))

        svc = MessageService(session)
        cmd = _submit_command()
        detail = svc.submit(cmd, cls)

        assert detail.message.status == "pending"
        count = (
            session.query(ActivityEvent)
            .filter(ActivityEvent.source_message_id == detail.message.id)
            .count()
        )
        assert count == 0

    def test_no_orphaned_tags_on_failure(self, session: Session) -> None:
        from shred.classification.contracts import (
            CategoryChoice,
            ClassificationDraft,
            EventDraft,
        )

        bad_draft = EventDraft(
            title="bad",
            source_fragment="x",
            local_date=datetime(2027, 1, 1).date(),
            precision="exact",
            local_time=datetime(2027, 1, 1, 12, 0).time(),
            category=CategoryChoice(new_path=["工作"]),
            tags=["orphan_tag"],
        )
        cls = FakeClassifier(drafts=ClassificationDraft(events=[bad_draft]))

        svc = MessageService(session)
        cmd = _submit_command()
        svc.submit(cmd, cls)

        tag_count = session.query(Tag).filter(Tag.name == "orphan_tag").count()
        assert tag_count == 0


# ------------------------------------------------------------------
# Crash / stale recovery
# ------------------------------------------------------------------


class TestReconcileStale:
    def test_processing_older_than_timeout_plus_30_becomes_pending(self, session: Session) -> None:
        old_time = datetime.now(UTC) - timedelta(seconds=120)
        source = SourceMessage(
            submission_uuid="stale-1",
            original_text="旧消息",
            submitted_at=old_time,
            timezone="UTC",
            status="processing",
            created_at=old_time,
        )
        session.add(source)
        session.commit()

        svc = MessageService(session)
        count = svc.reconcile_stale(datetime.now(UTC), timeout_seconds=60)

        session.expire_all()
        updated = session.get(SourceMessage, source.id)
        assert count == 1
        assert updated.status == "pending"
        assert updated.error_code == "interrupted_processing"

    def test_recent_processing_unchanged(self, session: Session) -> None:
        recent = datetime.now(UTC) - timedelta(seconds=10)
        source = SourceMessage(
            submission_uuid="recent-1",
            original_text="新消息",
            submitted_at=recent,
            timezone="UTC",
            status="processing",
            created_at=recent,
        )
        session.add(source)
        session.commit()

        svc = MessageService(session)
        count = svc.reconcile_stale(datetime.now(UTC), timeout_seconds=60)

        session.expire_all()
        updated = session.get(SourceMessage, source.id)
        assert count == 0
        assert updated.status == "processing"

    def test_non_processing_unchanged(self, session: Session) -> None:
        old_time = datetime.now(UTC) - timedelta(seconds=200)
        source = SourceMessage(
            submission_uuid="classified-1",
            original_text="已分类",
            submitted_at=old_time,
            timezone="UTC",
            status="classified",
            created_at=old_time,
        )
        session.add(source)
        session.commit()

        svc = MessageService(session)
        count = svc.reconcile_stale(datetime.now(UTC), timeout_seconds=60)

        assert count == 0


# ------------------------------------------------------------------
# Undo
# ------------------------------------------------------------------


class TestUndo:
    def test_undo_within_10s_deletes_source_and_events(self, session: Session) -> None:
        classifier = make_interview_classifier(datetime(2026, 1, 15).date())
        svc = MessageService(session)
        detail = svc.submit(_submit_command(), classifier)

        events_count = (
            session.query(ActivityEvent)
            .filter(ActivityEvent.source_message_id == detail.message.id)
            .count()
        )
        assert events_count > 0

        svc.undo(detail.message.id, datetime.now(UTC))

        assert session.get(SourceMessage, detail.message.id) is None
        remaining = (
            session.query(ActivityEvent)
            .filter(ActivityEvent.source_message_id == detail.message.id)
            .count()
        )
        assert remaining == 0

    def test_undo_removes_unused_agent_categories_only(self, session: Session) -> None:
        classifier = make_interview_classifier(datetime(2026, 1, 15).date())
        svc = MessageService(session)
        detail = svc.submit(_submit_command(), classifier)

        agent_cat = (
            session.query(Category)
            .filter(Category.origin == "agent")
            .first()
        )
        assert agent_cat is not None

        user_cat = Category(name="用户分类", normalized_name="用户分类", origin="user")
        session.add(user_cat)
        session.commit()

        svc.undo(detail.message.id, datetime.now(UTC))

        still_exists = session.get(Category, user_cat.id)
        assert still_exists is not None
        removed = session.get(Category, agent_cat.id)
        assert removed is None

    def test_undo_after_10s_raises_window_expired(self, session: Session) -> None:
        classifier = make_interview_classifier(datetime(2026, 1, 15).date())
        svc = MessageService(session)
        detail = svc.submit(_submit_command(), classifier)

        far_future = datetime.now(UTC) + timedelta(seconds=30)

        with pytest.raises(UndoWindowExpired):
            svc.undo(detail.message.id, far_future)

    def test_undo_nonexistent_raises(self, session: Session) -> None:
        svc = MessageService(session)
        with pytest.raises(ValueError, match="不存在"):
            svc.undo("nonexistent", datetime.now(UTC))

    def test_undo_non_classified_raises(self, session: Session) -> None:
        fail_cls = failing_classifier()
        svc = MessageService(session)
        pending = svc.submit(_submit_command(), fail_cls)

        with pytest.raises(ValueError, match="已分类"):
            svc.undo(pending.message.id, datetime.now(UTC))


# ------------------------------------------------------------------
# Get
# ------------------------------------------------------------------


class TestGet:
    def test_get_returns_full_detail(self, session: Session) -> None:
        classifier = make_interview_classifier(datetime(2026, 1, 15).date())
        svc = MessageService(session)
        submitted = svc.submit(_submit_command(), classifier)

        detail = svc.get(submitted.message.id)

        assert detail.message.id == submitted.message.id
        assert detail.message.original_text == submitted.message.original_text
        assert len(detail.events) == 3

    def test_get_nonexistent_raises(self, session: Session) -> None:
        svc = MessageService(session)
        with pytest.raises(ValueError, match="不存在"):
            svc.get("nonexistent")


# ------------------------------------------------------------------
# Delete source
# ------------------------------------------------------------------


class TestDeleteSource:
    def test_delete_removes_source_and_cascades(self, session: Session) -> None:
        classifier = make_interview_classifier(datetime(2026, 1, 15).date())
        svc = MessageService(session)
        detail = svc.submit(_submit_command(), classifier)

        impact = svc.delete_source(detail.message.id)

        assert impact.deleted_events == 3
        assert impact.message_id == detail.message.id
        assert session.get(SourceMessage, detail.message.id) is None

    def test_delete_nonexistent_raises(self, session: Session) -> None:
        svc = MessageService(session)
        with pytest.raises(ValueError, match="不存在"):
            svc.delete_source("nonexistent")
