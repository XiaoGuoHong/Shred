"""Event service tests."""

# ruff: noqa: DTZ001

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from shred.classification.contracts import (
    CategoryChoice,
    ClassificationDraft,
    ClassificationRequest,
    ClassifierFailure,
    EventDraft,
)
from shred.db.models import (
    ActivityEvent,
    Base,
    Category,
    CorrectionMemory,
    EventTag,
    SourceMessage,
    Tag,
)
from shred.events.schemas import UpdateEvent
from shred.events.service import EventService


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://", echo=False)

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection: object, _: object) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")  # type: ignore[attr-defined]

    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as s:
        yield s


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
        if self._failure is not None:
            raise self._failure

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def last_request(self) -> ClassificationRequest | None:
        return self._last_request


def _make_source(session: Session, text: str = "测试消息", tz: str = "Asia/Shanghai") -> SourceMessage:
    source = SourceMessage(
        submission_uuid="test-uuid-001",
        original_text=text,
        submitted_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC),
        timezone=tz,
        status="classified",
    )
    session.add(source)
    session.commit()
    return source


def _make_category(session: Session, name: str, parent_id: str | None = None, origin: str = "agent") -> Category:
    cat = Category(name=name, normalized_name=name, parent_id=parent_id, origin=origin)
    session.add(cat)
    session.commit()
    return cat


def _make_event(
    session: Session,
    source: SourceMessage,
    title: str = "测试事件",
    fragment: str = "测试片段",
    category_id: str | None = None,
    position: int = 0,
    status: str = "classified",
) -> ActivityEvent:
    event = ActivityEvent(
        source_message_id=source.id,
        position=position,
        title=title,
        source_fragment=fragment,
        occurred_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC),
        occurrence_precision="date",
        part_of_day=None,
        category_id=category_id,
        status=status,
    )
    session.add(event)
    session.commit()
    return event


def _make_tag(session: Session, name: str) -> Tag:
    tag = Tag(name=name, normalized_name=name)
    session.add(tag)
    session.commit()
    return tag


def _tag_event(session: Session, event_id: str, tag: Tag) -> None:
    session.add(EventTag(event_id=event_id, tag_id=tag.id))
    session.commit()


def _get_corrections(session: Session, event_id: str) -> list[CorrectionMemory]:
    return (
        session.query(CorrectionMemory)
        .filter(CorrectionMemory.event_id == event_id)
        .all()
    )


# ------------------------------------------------------------------
# Correction memory tests
# ------------------------------------------------------------------


class TestCorrectionMemory:
    def test_edit_title_time_tags_no_correction(self, session: Session) -> None:
        source = _make_source(session)
        cat_a = _make_category(session, "工作")
        event = _make_event(session, source, title="旧标题", fragment="工作汇报", category_id=cat_a.id)
        tag = _make_tag(session, "重要")
        _tag_event(session, event.id, tag)

        changes = UpdateEvent(title="新标题", tags=["新标签"])
        svc = EventService(session)
        svc.update(event.id, changes)

        corrections = _get_corrections(session, event.id)
        assert len(corrections) == 0

        session.refresh(event)
        assert event.title == "新标题"

    def test_change_category_creates_active_correction(self, session: Session) -> None:
        source = _make_source(session)
        cat_a = _make_category(session, "工作")
        cat_b = _make_category(session, "学习")
        event = _make_event(session, source, title="写代码", fragment="写代码", category_id=cat_a.id)

        changes = UpdateEvent(category_id=cat_b.id)
        svc = EventService(session)
        svc.update(event.id, changes)

        corrections = _get_corrections(session, event.id)
        assert len(corrections) == 1
        corr = corrections[0]
        assert corr.active is True
        assert corr.original_category_id == cat_a.id
        assert corr.final_category_id == cat_b.id
        assert corr.event_text == event.source_fragment

    def test_change_category_again_updates_same_correction(self, session: Session) -> None:
        source = _make_source(session)
        cat_a = _make_category(session, "工作")
        cat_b = _make_category(session, "学习")
        cat_c = _make_category(session, "娱乐")
        event = _make_event(session, source, title="写代码", fragment="写代码", category_id=cat_a.id)

        svc = EventService(session)

        svc.update(event.id, UpdateEvent(category_id=cat_b.id))
        corrections = _get_corrections(session, event.id)
        assert len(corrections) == 1
        corr_id = corrections[0].id
        assert corrections[0].final_category_id == cat_b.id

        svc.update(event.id, UpdateEvent(category_id=cat_c.id))
        corrections = _get_corrections(session, event.id)
        assert len(corrections) == 1
        assert corrections[0].id == corr_id
        assert corrections[0].original_category_id == cat_a.id
        assert corrections[0].final_category_id == cat_c.id

    def test_return_to_original_removes_active_correction(self, session: Session) -> None:
        source = _make_source(session)
        cat_a = _make_category(session, "工作")
        cat_b = _make_category(session, "学习")
        event = _make_event(session, source, title="写代码", fragment="写代码", category_id=cat_a.id)

        svc = EventService(session)

        svc.update(event.id, UpdateEvent(category_id=cat_b.id))
        corrections = _get_corrections(session, event.id)
        assert len(corrections) == 1
        assert corrections[0].active is True

        svc.update(event.id, UpdateEvent(category_id=cat_a.id))
        corrections = _get_corrections(session, event.id)
        assert len(corrections) == 1
        assert corrections[0].active is False

    def test_only_category_change_triggers_correction(self, session: Session) -> None:
        source = _make_source(session)
        cat_a = _make_category(session, "工作")
        event = _make_event(session, source, title="旧标题", fragment="工作汇报", category_id=cat_a.id)

        svc = EventService(session)

        svc.update(event.id, UpdateEvent(title="新标题"))
        assert len(_get_corrections(session, event.id)) == 0

        svc.update(event.id, UpdateEvent(tags=["标签1", "标签2"]))
        assert len(_get_corrections(session, event.id)) == 0

        svc.update(
            event.id,
            UpdateEvent(occurred_at=datetime(2026, 2, 1, 12, 0, 0, tzinfo=UTC)),
        )
        assert len(_get_corrections(session, event.id)) == 0


# ------------------------------------------------------------------
# Delete tests
# ------------------------------------------------------------------


class TestDelete:
    def test_delete_one_event_source_and_other_events_survive(self, session: Session) -> None:
        source = _make_source(session)
        cat = _make_category(session, "工作")
        event1 = _make_event(session, source, title="事件1", fragment="片段1", category_id=cat.id, position=0)
        event2 = _make_event(session, source, title="事件2", fragment="片段2", category_id=cat.id, position=1)

        svc = EventService(session)
        svc.delete(event1.id)

        assert session.get(ActivityEvent, event1.id) is None
        assert session.get(ActivityEvent, event2.id) is not None
        assert session.get(SourceMessage, source.id) is not None

    def test_delete_final_event_source_survives(self, session: Session) -> None:
        source = _make_source(session)
        cat = _make_category(session, "工作")
        event = _make_event(session, source, title="唯一事件", fragment="片段", category_id=cat.id)

        svc = EventService(session)
        svc.delete(event.id)

        assert session.get(ActivityEvent, event.id) is None
        assert session.get(SourceMessage, source.id) is not None

        remaining = (
            session.query(ActivityEvent)
            .filter(ActivityEvent.source_message_id == source.id)
            .count()
        )
        assert remaining == 0

    def test_delete_nonexistent_raises(self, session: Session) -> None:
        svc = EventService(session)
        with pytest.raises(ValueError, match="不存在"):
            svc.delete("nonexistent")


# ------------------------------------------------------------------
# Update tests
# ------------------------------------------------------------------


class TestUpdate:
    def test_update_title_only(self, session: Session) -> None:
        source = _make_source(session)
        cat = _make_category(session, "工作")
        event = _make_event(session, source, title="旧标题", fragment="片段", category_id=cat.id)

        svc = EventService(session)
        result = svc.update(event.id, UpdateEvent(title="新标题"))

        assert result.title == "新标题"
        session.refresh(event)
        assert event.title == "新标题"

    def test_update_tags_full_replacement(self, session: Session) -> None:
        source = _make_source(session)
        cat = _make_category(session, "工作")
        event = _make_event(session, source, title="事件", fragment="片段", category_id=cat.id)
        t1 = _make_tag(session, "旧标签")
        _tag_event(session, event.id, t1)

        svc = EventService(session)
        result = svc.update(event.id, UpdateEvent(tags=["新标签A", "新标签B"]))

        assert set(result.tags) == {"新标签A", "新标签B"}

        tag_links = (
            session.query(EventTag).filter(EventTag.event_id == event.id).all()
        )
        assert len(tag_links) == 2

    def test_update_occurrence_fields(self, session: Session) -> None:
        source = _make_source(session)
        cat = _make_category(session, "工作")
        event = _make_event(session, source, title="事件", fragment="片段", category_id=cat.id)

        new_time = datetime(2026, 6, 1, 8, 0, 0, tzinfo=UTC)
        svc = EventService(session)
        result = svc.update(
            event.id,
            UpdateEvent(
                occurred_at=new_time,
                occurrence_precision="exact",
                part_of_day=None,
            ),
        )

        assert result.occurred_at == new_time
        assert result.occurrence_precision == "exact"
        assert result.part_of_day is None

    def test_update_nonexistent_raises(self, session: Session) -> None:
        svc = EventService(session)
        with pytest.raises(ValueError, match="不存在"):
            svc.update("nonexistent", UpdateEvent(title="新标题"))


# ------------------------------------------------------------------
# Reclassification tests
# ------------------------------------------------------------------


class TestReclassify:
    def test_reclassify_sends_single_mode_with_source_fragment(self, session: Session) -> None:
        source = _make_source(session)
        cat = _make_category(session, "工作")
        event = _make_event(session, source, title="写代码", fragment="今天写了Python代码", category_id=cat.id)

        new_draft = EventDraft(
            title="编写Python",
            source_fragment="different_fragment",
            local_date=datetime(2026, 1, 14).date(),
            precision="date",
            category=CategoryChoice(existing_id=cat.id),
            tags=["Python"],
        )
        classifier = FakeClassifier(drafts=ClassificationDraft(events=[new_draft]))

        svc = EventService(session)
        svc.reclassify(event.id, classifier)

        req = classifier.last_request
        assert req is not None
        assert req.mode == "single"
        assert req.text == event.source_fragment

    def test_reclassify_requires_exactly_one_draft(self, session: Session) -> None:
        source = _make_source(session)
        cat = _make_category(session, "工作")
        event = _make_event(session, source, title="事件", fragment="片段", category_id=cat.id)

        drafts = [
            EventDraft(
                title="事件A",
                source_fragment="A",
                local_date=datetime(2026, 1, 14).date(),
                precision="date",
                category=CategoryChoice(existing_id=cat.id),
            ),
            EventDraft(
                title="事件B",
                source_fragment="B",
                local_date=datetime(2026, 1, 14).date(),
                precision="date",
                category=CategoryChoice(existing_id=cat.id),
            ),
        ]
        classifier = FakeClassifier(drafts=ClassificationDraft(events=drafts))

        svc = EventService(session)
        with pytest.raises(ValueError, match="恰好一个"):
            svc.reclassify(event.id, classifier)

    def test_reclassify_preserves_source_fragment(self, session: Session) -> None:
        source = _make_source(session)
        cat = _make_category(session, "工作")
        original_fragment = "今天写了Python代码"
        event = _make_event(session, source, title="写代码", fragment=original_fragment, category_id=cat.id)

        new_draft = EventDraft(
            title="编写Python项目",
            source_fragment="completely_different",
            local_date=datetime(2026, 1, 14).date(),
            precision="date",
            category=CategoryChoice(existing_id=cat.id),
            tags=["Python"],
        )
        classifier = FakeClassifier(drafts=ClassificationDraft(events=[new_draft]))

        svc = EventService(session)
        result = svc.reclassify(event.id, classifier)

        assert result.source_fragment == original_fragment
        session.refresh(event)
        assert event.source_fragment == original_fragment

    def test_reclassify_updates_atomically(self, session: Session) -> None:
        source = _make_source(session)
        cat_a = _make_category(session, "工作")
        cat_b = _make_category(session, "学习")
        event = _make_event(session, source, title="旧标题", fragment="旧片段", category_id=cat_a.id)

        new_draft = EventDraft(
            title="新标题",
            source_fragment="忽略",
            local_date=datetime(2026, 1, 14).date(),
            precision="exact",
            local_time=datetime(2026, 1, 14, 14, 30).time(),
            category=CategoryChoice(existing_id=cat_b.id),
            tags=["新标签"],
        )
        classifier = FakeClassifier(drafts=ClassificationDraft(events=[new_draft]))

        svc = EventService(session)
        result = svc.reclassify(event.id, classifier)

        assert result.title == "新标题"
        assert result.category_id == cat_b.id
        assert result.tags == ["新标签"]
        assert result.occurrence_precision == "exact"

    def test_classifier_failure_event_becomes_pending_not_deleted(self, session: Session) -> None:
        source = _make_source(session)
        cat = _make_category(session, "工作")
        event = _make_event(session, source, title="事件", fragment="片段", category_id=cat.id, status="classified")

        classifier = FakeClassifier(failure=ClassifierFailure(code="model_timeout", summary="超时"))

        svc = EventService(session)
        result = svc.reclassify(event.id, classifier)

        assert result.status == "pending"
        assert result.id == event.id

        session.refresh(event)
        assert event.status == "pending"
        assert session.get(ActivityEvent, event.id) is not None

    def test_reclassify_nonexistent_raises(self, session: Session) -> None:
        classifier = FakeClassifier(
            drafts=ClassificationDraft(
                events=[
                    EventDraft(
                        title="事件",
                        source_fragment="片段",
                        local_date=datetime(2026, 1, 16).date(),
                        precision="date",
                        category=CategoryChoice(new_path=["工作"]),
                    )
                ]
            )
        )

        svc = EventService(session)
        with pytest.raises(ValueError, match="不存在"):
            svc.reclassify("nonexistent", classifier)
