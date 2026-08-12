from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from shred.classification.contracts import (
    CategoryContext,
    ClassificationRequest,
    Classifier,
    ClassifierFailure,
    CorrectionContext,
)
from shred.classification.preferences import rank_corrections
from shred.classification.time_resolution import resolve_occurrence
from shred.core.errors import UndoWindowExpired
from shred.db.models import (
    ActivityEvent,
    Category,
    CorrectionMemory,
    EventTag,
    SourceMessage,
    Tag,
)
from shred.messages.schemas import (
    DeleteImpact,
    EventDetail,
    MessageDetail,
    MessageView,
    SubmitMessage,
)
from shred.taxonomy.names import normalize_tag_name
from shred.taxonomy.service import TaxonomyService


class MessageService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self, command: SubmitMessage, classifier: Classifier) -> MessageDetail:
        existing = self._find_by_uuid(command.submission_uuid)
        if existing is not None:
            return self._build_detail(existing)

        submitted_at = command.submitted_at
        if submitted_at.tzinfo is None:
            submitted_at = submitted_at.replace(tzinfo=UTC)

        source = SourceMessage(
            id=str(uuid4()),
            submission_uuid=command.submission_uuid,
            original_text=command.text,
            submitted_at=submitted_at,
            timezone=command.timezone,
            status="processing",
        )
        self._session.add(source)
        self._session.commit()

        try:
            request = self._build_classification_request(source)
            draft = classifier.classify(request)
        except ClassifierFailure as exc:
            return self._mark_pending_and_detail(source.id, exc.code, exc.summary)
        except Exception as exc:  # noqa: BLE001
            return self._mark_pending_and_detail(source.id, "classification_failed", str(exc))

        try:
            self._persist_events(source, draft.events)
            source = self._session.get(SourceMessage, source.id)
            source.status = "classified"
            self._session.commit()
        except Exception:  # noqa: BLE001
            self._session.rollback()
            return self._mark_pending_and_detail(source.id, "event_persistence_failed", "事件持久化失败")

        return self._build_detail(source)

    def retry(self, message_id: str, classifier: Classifier) -> MessageDetail:
        source = self._session.get(SourceMessage, message_id)
        if source is None:
            raise ValueError("消息不存在")
        if source.status not in ("pending", "processing"):
            raise ValueError("只能重试失败或处理中的消息")

        events = self._session.query(ActivityEvent).filter(
            ActivityEvent.source_message_id == message_id
        ).all()
        for event in events:
            self._session.query(EventTag).filter(EventTag.event_id == event.id).delete()
            self._session.delete(event)
        self._session.commit()

        source = self._session.get(SourceMessage, message_id)
        source.status = "processing"
        source.error_code = None
        source.error_summary = None
        self._session.commit()

        try:
            request = self._build_classification_request(source)
            draft = classifier.classify(request)
        except ClassifierFailure as exc:
            return self._mark_pending_and_detail(source.id, exc.code, exc.summary)
        except Exception as exc:  # noqa: BLE001
            return self._mark_pending_and_detail(source.id, "classification_failed", str(exc))

        try:
            self._persist_events(source, draft.events)
            source = self._session.get(SourceMessage, source.id)
            source.status = "classified"
            self._session.commit()
        except Exception:  # noqa: BLE001
            self._session.rollback()
            return self._mark_pending_and_detail(source.id, "event_persistence_failed", "事件持久化失败")

        return self._build_detail(source)

    def get(self, message_id: str) -> MessageDetail:
        source = self._session.get(SourceMessage, message_id)
        if source is None:
            raise ValueError("消息不存在")
        return self._build_detail(source)

    def delete_source(self, message_id: str) -> DeleteImpact:
        source = self._session.get(SourceMessage, message_id)
        if source is None:
            raise ValueError("消息不存在")

        count = self._session.query(ActivityEvent).filter(
            ActivityEvent.source_message_id == message_id
        ).count()

        self._session.delete(source)
        self._session.commit()
        return DeleteImpact(message_id=message_id, deleted_events=count)

    def undo(self, message_id: str, now: datetime) -> None:
        source = self._session.get(SourceMessage, message_id)
        if source is None:
            raise ValueError("消息不存在")
        if source.status != "classified":
            raise ValueError("只能撤销已分类的消息")

        updated_at_utc = source.updated_at.replace(tzinfo=UTC)
        elapsed = (now - updated_at_utc).total_seconds()
        if elapsed > 10:
            raise UndoWindowExpired("撤销窗口已过期")

        events = self._session.query(ActivityEvent).filter(
            ActivityEvent.source_message_id == message_id
        ).all()

        agent_category_ids: set[str] = set()
        for event in events:
            if event.category_id:
                agent_category_ids.add(event.category_id)
            self._session.query(EventTag).filter(EventTag.event_id == event.id).delete()
            self._session.delete(event)

        self._session.delete(source)
        self._session.flush()

        for cat_id in agent_category_ids:
            cat = self._session.get(Category, cat_id)
            if cat is None or cat.origin != "agent":
                continue
            remaining = (
                self._session.query(ActivityEvent)
                .filter(ActivityEvent.category_id == cat_id)
                .count()
            )
            if remaining > 0:
                continue
            children = (
                self._session.query(Category).filter(Category.parent_id == cat_id).all()
            )
            for child in children:
                child_remaining = (
                    self._session.query(ActivityEvent)
                    .filter(ActivityEvent.category_id == child.id)
                    .count()
                )
                if child_remaining == 0:
                    self._session.delete(child)
            self._session.delete(cat)

        self._session.commit()

    def reconcile_stale(self, now: datetime, timeout_seconds: int) -> int:
        from datetime import timedelta

        threshold = now - timedelta(seconds=timeout_seconds + 30)
        stale = (
            self._session.query(SourceMessage)
            .filter(
                SourceMessage.status == "processing",
                SourceMessage.created_at < threshold,
            )
            .all()
        )
        for source in stale:
            source.status = "pending"
            source.error_code = "interrupted_processing"
            source.error_summary = "分类处理中断，请重试"
        if stale:
            self._session.commit()
        return len(stale)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_by_uuid(self, submission_uuid: str) -> SourceMessage | None:
        return (
            self._session.query(SourceMessage)
            .filter(SourceMessage.submission_uuid == submission_uuid)
            .first()
        )

    def _build_detail(self, source: SourceMessage) -> MessageDetail:
        events = (
            self._session.query(ActivityEvent)
            .filter(ActivityEvent.source_message_id == source.id)
            .order_by(ActivityEvent.position)
            .all()
        )

        event_details: list[EventDetail] = []
        for event in events:
            tags = (
                self._session.query(Tag)
                .join(EventTag, EventTag.tag_id == Tag.id)
                .filter(EventTag.event_id == event.id)
                .all()
            )
            tag_names = [t.name for t in tags]
            event_details.append(
                EventDetail(
                    id=event.id,
                    position=event.position,
                    title=event.title,
                    source_fragment=event.source_fragment,
                    occurred_at=event.occurred_at,
                    occurrence_precision=event.occurrence_precision,
                    part_of_day=event.part_of_day,
                    category_path=self._category_path(event.category_id),
                    category_id=event.category_id,
                    tags=tag_names,
                    status=event.status,
                )
            )

        return MessageDetail(
            message=MessageView(
                id=source.id,
                submission_uuid=source.submission_uuid,
                original_text=source.original_text,
                submitted_at=source.submitted_at,
                timezone=source.timezone,
                status=source.status,
                error_code=source.error_code,
                error_summary=source.error_summary,
                created_at=source.created_at,
                updated_at=source.updated_at,
            ),
            events=event_details,
        )

    def _build_classification_request(self, source: SourceMessage) -> ClassificationRequest:
        submitted_at = source.submitted_at
        if submitted_at.tzinfo is None:
            submitted_at = submitted_at.replace(tzinfo=UTC)

        categories = self._session.query(Category).all()
        category_contexts = [
            CategoryContext(
                id=cat.id,
                name=cat.name,
                parent_id=cat.parent_id,
                path=self._category_path(cat.id),
            )
            for cat in categories
        ]

        corrections = self._session.query(CorrectionMemory).filter(
            CorrectionMemory.active.is_(True)
        ).all()
        correction_contexts: list[CorrectionContext] = []
        for corr in corrections:
            original_path = self._category_path(corr.original_category_id)
            final_path = self._category_path(corr.final_category_id)
            correction_contexts.append(
                CorrectionContext(
                    event_text=corr.event_text,
                    original_path=original_path,
                    final_path=final_path,
                )
            )

        ranked = rank_corrections(source.original_text, correction_contexts)

        return ClassificationRequest(
            text=source.original_text,
            submitted_at=submitted_at,
            timezone=source.timezone,
            categories=category_contexts,
            corrections=ranked,
            mode="split",
        )

    def _persist_events(self, source: SourceMessage, drafts: list) -> None:
        taxonomy = TaxonomyService(self._session)

        submitted_at = source.submitted_at
        if submitted_at.tzinfo is None:
            submitted_at = submitted_at.replace(tzinfo=UTC)

        for position, draft in enumerate(drafts):
            resolved = resolve_occurrence(draft, submitted_at, source.timezone)
            category = taxonomy.resolve_choice(draft.category, origin_message_id=source.id)

            event = ActivityEvent(
                source_message_id=source.id,
                position=position,
                title=draft.title,
                source_fragment=draft.source_fragment,
                occurred_at=resolved.occurred_at,
                occurrence_precision=resolved.precision,
                part_of_day=resolved.part_of_day,
                category_id=category.id,
                status="classified",
            )
            self._session.add(event)
            self._session.flush()

            for tag_name in draft.tags[:3]:
                normalized = normalize_tag_name(tag_name)
                tag = (
                    self._session.query(Tag)
                    .filter(Tag.normalized_name == normalized)
                    .first()
                )
                if tag is None:
                    tag = Tag(name=tag_name, normalized_name=normalized)
                    self._session.add(tag)
                    self._session.flush()
                self._session.add(EventTag(event_id=event.id, tag_id=tag.id))

    def _category_path(self, category_id: str | None) -> list[str]:
        if category_id is None:
            return []
        category = self._session.get(Category, category_id)
        if category is None:
            return []
        path: list[Category] = []
        current: Category | None = category
        while current is not None:
            path.append(current)
            current = (
                self._session.get(Category, current.parent_id)
                if current.parent_id
                else None
            )
        return [c.name for c in reversed(path)]

    def _mark_pending_and_detail(
        self, source_id: str, error_code: str, error_summary: str
    ) -> MessageDetail:
        source = self._session.get(SourceMessage, source_id)
        source.status = "pending"
        source.error_code = error_code
        source.error_summary = error_summary
        self._session.commit()
        return self._build_detail(source)
