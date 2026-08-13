"""Taxonomy service tests — TDD red phase."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from shred.db.models import (
    ActivityEvent,
    Base,
    Category,
    CorrectionMemory,
    SourceMessage,
)
from shred.taxonomy.schemas import CategoryCreate
from shred.taxonomy.service import TaxonomyService


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://", echo=False)

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection: object, _: object) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")  # type: ignore[attr-defined]

    Base.metadata.create_all(engine)
    try:
        with Session(engine) as s:
            yield s
    finally:
        engine.dispose()


def _root(session: Session, name: str) -> Category:
    cat = Category(name=name, normalized_name=name, origin="user")
    session.add(cat)
    session.flush()
    return cat


def _child(session: Session, name: str, parent: Category) -> Category:
    cat = Category(name=name, normalized_name=name, parent_id=parent.id, origin="user")
    session.add(cat)
    session.flush()
    return cat


def _msg(session: Session) -> SourceMessage:
    from datetime import UTC, datetime

    m = SourceMessage(
        submission_uuid="a" * 36,
        original_text="test",
        submitted_at=datetime.now(UTC),
        timezone="UTC",
        status="created",
    )
    session.add(m)
    session.flush()
    return m


def _event(session: Session, msg: SourceMessage, title: str, pos: int, category: Category | None = None) -> ActivityEvent:
    from datetime import UTC, datetime

    e = ActivityEvent(
        source_message_id=msg.id,
        position=pos,
        title=title,
        source_fragment=title,
        occurred_at=datetime.now(UTC),
        occurrence_precision="date",
        category_id=category.id if category else None,
        status="pending",
    )
    session.add(e)
    session.flush()
    return e


class TestCreate:
    def test_create_root_succeeds(self, session: Session) -> None:
        svc = TaxonomyService(session)
        cmd = CategoryCreate(name="工作")
        result = svc.create(cmd)
        assert result.name == "工作"
        assert result.parent_id is None

    def test_create_child_under_root_succeeds(self, session: Session) -> None:
        root = _root(session, "工作")
        svc = TaxonomyService(session)
        cmd = CategoryCreate(name="编程", parent_id=root.id)
        result = svc.create(cmd)
        assert result.name == "编程"
        assert result.parent_id == root.id

    def test_create_grandchild_raises_depth_exceeded(self, session: Session) -> None:
        root = _root(session, "工作")
        child = _child(session, "编程", root)
        svc = TaxonomyService(session)
        cmd = CategoryCreate(name="Python", parent_id=child.id)
        with pytest.raises(ValueError):
            svc.create(cmd)

    def test_sibling_duplicate_normalized_name_raises_conflict(self, session: Session) -> None:
        root = _root(session, "工作")
        _child(session, "编程", root)
        svc = TaxonomyService(session)
        cmd = CategoryCreate(name="编程", parent_id=root.id)
        with pytest.raises(ValueError):
            svc.create(cmd)


class TestResolveChoice:
    def test_resolve_choice_with_missing_existing_id_raises(self, session: Session) -> None:
        svc = TaxonomyService(session)
        from shred.classification.contracts import CategoryChoice

        choice = CategoryChoice(existing_id="nonexistent-id")
        with pytest.raises(ValueError):
            svc.resolve_choice(choice, origin_message_id="test-msg")

    def test_resolve_choice_with_valid_existing_id_returns_category(self, session: Session) -> None:
        root = _root(session, "工作")
        svc = TaxonomyService(session)
        from shred.classification.contracts import CategoryChoice

        choice = CategoryChoice(existing_id=root.id)
        result = svc.resolve_choice(choice, origin_message_id="test-msg")
        assert result.id == root.id

    def test_resolve_choice_with_new_path_creates_categories(self, session: Session) -> None:
        msg = _msg(session)
        svc = TaxonomyService(session)
        from shred.classification.contracts import CategoryChoice

        choice = CategoryChoice(new_path=["运动", "跑步"])
        result = svc.resolve_choice(choice, origin_message_id=msg.id)
        assert result.name == "跑步"
        assert result.parent_id is not None


class TestMerge:
    def test_merge_two_roots_moves_events(self, session: Session) -> None:
        msg = _msg(session)
        root_a = _root(session, "运动")
        root_b = _root(session, "健身")
        e1 = _event(session, msg, "跑步", 0, root_a)
        e2 = _event(session, msg, "游泳", 1, root_a)

        svc = TaxonomyService(session)
        result = svc.merge(root_a.id, root_b.id)
        session.flush()

        assert result.merged_events == 2
        assert session.get(ActivityEvent, e1.id).category_id == root_b.id
        assert session.get(ActivityEvent, e2.id).category_id == root_b.id

    def test_merge_reparents_unique_children(self, session: Session) -> None:
        root_a = _root(session, "运动")
        root_b = _root(session, "健身")
        child_a = _child(session, "跑步", root_a)

        svc = TaxonomyService(session)
        result = svc.merge(root_a.id, root_b.id)
        session.flush()

        assert result.reparented_children == 1
        assert session.get(Category, child_a.id).parent_id == root_b.id

    def test_merge_recursively_merges_duplicate_children(self, session: Session) -> None:
        msg = _msg(session)
        root_a = _root(session, "运动")
        root_b = _root(session, "健身")
        child_a = _child(session, "跑步", root_a)
        child_b = _child(session, "跑步", root_b)
        e1 = _event(session, msg, "晨跑", 0, child_a)

        svc = TaxonomyService(session)
        result = svc.merge(root_a.id, root_b.id)
        session.flush()

        assert result.merged_children == 1
        assert session.get(ActivityEvent, e1.id).category_id == child_b.id

    def test_merge_rewrites_active_correction_references(self, session: Session) -> None:
        msg = _msg(session)
        root_a = _root(session, "运动")
        root_b = _root(session, "健身")
        ev = _event(session, msg, "跑步", 0, root_a)
        corr = CorrectionMemory(
            event_id=ev.id,
            event_text="跑步",
            original_category_id=root_a.id,
            final_category_id=root_a.id,
            active=True,
        )
        session.add(corr)
        session.flush()

        svc = TaxonomyService(session)
        svc.merge(root_a.id, root_b.id)
        session.flush()

        updated = session.get(CorrectionMemory, corr.id)
        assert updated.original_category_id == root_b.id
        assert updated.final_category_id == root_b.id

    def test_merge_rejects_identical_ids(self, session: Session) -> None:
        root = _root(session, "工作")
        svc = TaxonomyService(session)
        with pytest.raises(ValueError):
            svc.merge(root.id, root.id)

    def test_merge_rejects_different_depths(self, session: Session) -> None:
        root = _root(session, "工作")
        child = _child(session, "编程", root)
        svc = TaxonomyService(session)
        with pytest.raises(ValueError):
            svc.merge(root.id, child.id)


class TestDelete:
    def test_delete_child_makes_events_pending(self, session: Session) -> None:
        msg = _msg(session)
        root = _root(session, "工作")
        child = _child(session, "编程", root)
        e1 = _event(session, msg, "写代码", 0, child)
        e1.status = "classified"
        session.flush()

        svc = TaxonomyService(session)
        impact = svc.delete(child.id)
        session.flush()

        assert impact.affected_event_count >= 1
        updated = session.get(ActivityEvent, e1.id)
        assert updated.status == "pending"
        assert updated.category_id is None

    def test_delete_child_deactivates_corrections(self, session: Session) -> None:
        msg = _msg(session)
        root = _root(session, "工作")
        child = _child(session, "编程", root)
        ev = _event(session, msg, "写代码", 0, child)
        corr = CorrectionMemory(
            event_id=ev.id,
            event_text="写代码",
            original_category_id=child.id,
            final_category_id=child.id,
            active=True,
        )
        session.add(corr)
        session.flush()

        svc = TaxonomyService(session)
        svc.delete(child.id)
        session.flush()

        assert not session.get(CorrectionMemory, corr.id).active

    def test_delete_root_applies_to_all_descendants(self, session: Session) -> None:
        msg = _msg(session)
        root = _root(session, "工作")
        child = _child(session, "编程", root)
        e1 = _event(session, msg, "写代码", 0, child)
        e1.status = "classified"
        e2 = _event(session, msg, "开会", 1, root)
        e2.status = "classified"
        session.flush()

        svc = TaxonomyService(session)
        impact = svc.delete(root.id)
        session.flush()

        assert impact.descendant_count >= 1
        assert session.get(ActivityEvent, e1.id).category_id is None
        assert session.get(ActivityEvent, e2.id).category_id is None
        assert session.get(ActivityEvent, e1.id).status == "pending"
        assert session.get(ActivityEvent, e2.id).status == "pending"


class TestTree:
    def test_tree_returns_root_with_children_and_counts(self, session: Session) -> None:
        msg = _msg(session)
        root = _root(session, "工作")
        child = _child(session, "编程", root)
        _event(session, msg, "写代码", 0, child)
        _event(session, msg, "开会", 1, root)

        svc = TaxonomyService(session)
        tree = svc.tree()

        assert len(tree) == 1
        assert tree[0].name == "工作"
        assert tree[0].event_count == 1
        assert tree[0].total_event_count == 2
        assert len(tree[0].children) == 1
        assert tree[0].children[0].name == "编程"
        assert tree[0].children[0].event_count == 1
        assert tree[0].children[0].total_event_count == 1


class TestRename:
    def test_rename_changes_name(self, session: Session) -> None:
        root = _root(session, "工作")
        svc = TaxonomyService(session)
        from shred.taxonomy.schemas import CategoryRename

        result = svc.rename(root.id, CategoryRename(name="学习"))
        assert result.name == "学习"


class TestImpact:
    def test_impact_returns_counts_without_mutation(self, session: Session) -> None:
        msg = _msg(session)
        root = _root(session, "工作")
        e1 = _event(session, msg, "开会", 0, root)

        svc = TaxonomyService(session)
        impact = svc.impact(root.id)

        assert impact.affected_event_count == 1
        assert impact.category_name == "工作"
        assert session.get(ActivityEvent, e1.id).category_id == root.id
