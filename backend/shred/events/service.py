from __future__ import annotations

from datetime import UTC

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
from shred.db.models import (
    ActivityEvent,
    Category,
    CorrectionMemory,
    EventTag,
    SourceMessage,
    Tag,
)
from shred.events.schemas import (
    EventDetail,
    EventView,
    SourceMessageContext,
    UpdateEvent,
)
from shred.taxonomy.names import normalize_tag_name
from shred.taxonomy.service import TaxonomyService


class EventService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, event_id: str) -> EventDetail:
        event = self._session.get(ActivityEvent, event_id)
        if event is None:
            raise ValueError("事件不存在")
        return self._build_detail(event)

    def update(self, event_id: str, changes: UpdateEvent) -> EventView:
        event = self._session.get(ActivityEvent, event_id)
        if event is None:
            raise ValueError("事件不存在")

        update_data = changes.model_dump(exclude_unset=True)

        old_category_id = event.category_id

        if "title" in update_data and update_data["title"] is not None:
            event.title = update_data["title"]

        if "occurred_at" in update_data:
            event.occurred_at = update_data["occurred_at"]
        if "occurrence_precision" in update_data:
            event.occurrence_precision = update_data["occurrence_precision"]
        if "part_of_day" in update_data:
            event.part_of_day = update_data["part_of_day"]

        if "category_id" in update_data and update_data["category_id"] != old_category_id:
            self._handle_correction(event, old_category_id, update_data["category_id"])
            event.category_id = update_data["category_id"]

        if "tags" in update_data:
            self._replace_tags(event, update_data["tags"] or [])

        self._session.flush()
        return self._build_view(event)

    def delete(self, event_id: str) -> None:
        event = self._session.get(ActivityEvent, event_id)
        if event is None:
            raise ValueError("事件不存在")
        self._session.delete(event)
        self._session.flush()

    def reclassify(self, event_id: str, classifier: Classifier) -> EventView:
        event = self._session.get(ActivityEvent, event_id)
        if event is None:
            raise ValueError("事件不存在")

        source = self._session.get(SourceMessage, event.source_message_id)
        if source is None:
            raise ValueError("来源消息不存在")

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

        corrections = (
            self._session.query(CorrectionMemory)
            .filter(CorrectionMemory.active.is_(True))
            .all()
        )
        correction_contexts: list[CorrectionContext] = []
        for corr in corrections:
            correction_contexts.append(
                CorrectionContext(
                    event_text=corr.event_text,
                    original_path=self._category_path(corr.original_category_id),
                    final_path=self._category_path(corr.final_category_id),
                )
            )

        ranked = rank_corrections(event.source_fragment, correction_contexts)

        submitted_at = source.submitted_at
        if submitted_at.tzinfo is None:
            submitted_at = submitted_at.replace(tzinfo=UTC)

        request = ClassificationRequest(
            text=event.source_fragment,
            submitted_at=submitted_at,
            timezone=source.timezone,
            categories=category_contexts,
            corrections=ranked,
            mode="single",
        )

        try:
            draft = classifier.classify(request)
        except ClassifierFailure:
            event.status = "pending"
            self._session.flush()
            return self._build_view(event)
        except Exception:  # noqa: BLE001
            event.status = "pending"
            self._session.flush()
            return self._build_view(event)

        if len(draft.events) != 1:
            raise ValueError("重新分类必须生成恰好一个事件草稿")

        new_draft = draft.events[0]
        taxonomy = TaxonomyService(self._session)

        resolved = resolve_occurrence(new_draft, submitted_at, source.timezone)
        category = taxonomy.resolve_choice(new_draft.category, origin_message_id=source.id)

        event.title = new_draft.title
        event.occurred_at = resolved.occurred_at
        event.occurrence_precision = resolved.precision
        event.part_of_day = resolved.part_of_day
        event.category_id = category.id

        self._replace_tags(event, new_draft.tags)

        self._session.flush()
        return self._build_view(event)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _handle_correction(
        self,
        event: ActivityEvent,
        old_category_id: str | None,
        new_category_id: str | None,
    ) -> None:
        existing = (
            self._session.query(CorrectionMemory)
            .filter(
                CorrectionMemory.event_id == event.id,
                CorrectionMemory.active.is_(True),
            )
            .first()
        )

        if existing is not None:
            if new_category_id == existing.original_category_id:
                existing.active = False
            else:
                existing.final_category_id = new_category_id
        else:
            correction = CorrectionMemory(
                event_id=event.id,
                event_text=event.source_fragment,
                original_category_id=old_category_id,
                final_category_id=new_category_id,
                active=True,
            )
            self._session.add(correction)

    def _replace_tags(self, event: ActivityEvent, tag_names: list[str]) -> None:
        self._session.query(EventTag).filter(EventTag.event_id == event.id).delete()

        for tag_name in tag_names[:3]:
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

    def _build_view(self, event: ActivityEvent) -> EventView:
        tags = (
            self._session.query(Tag)
            .join(EventTag, EventTag.tag_id == Tag.id)
            .filter(EventTag.event_id == event.id)
            .all()
        )
        return EventView(
            id=event.id,
            position=event.position,
            title=event.title,
            source_fragment=event.source_fragment,
            occurred_at=event.occurred_at,
            occurrence_precision=event.occurrence_precision,
            part_of_day=event.part_of_day,
            category_id=event.category_id,
            category_path=self._category_path(event.category_id),
            tags=[t.name for t in tags],
            status=event.status,
        )

    def _build_detail(self, event: ActivityEvent) -> EventDetail:
        view = self._build_view(event)

        source = self._session.get(SourceMessage, event.source_message_id)
        source_ctx = None
        if source is not None:
            source_ctx = SourceMessageContext(
                id=source.id,
                original_text=source.original_text,
                submitted_at=source.submitted_at,
                timezone=source.timezone,
            )

        return EventDetail(
            id=view.id,
            position=view.position,
            title=view.title,
            source_fragment=view.source_fragment,
            occurred_at=view.occurred_at,
            occurrence_precision=view.occurrence_precision,
            part_of_day=view.part_of_day,
            category_id=view.category_id,
            category_path=view.category_path,
            tags=view.tags,
            status=view.status,
            source_message=source_ctx,
        )
