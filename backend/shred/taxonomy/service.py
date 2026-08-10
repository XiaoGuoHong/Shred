from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from shred.db.models import ActivityEvent, Category, CorrectionMemory
from shred.taxonomy.names import normalize_category_name
from shred.taxonomy.schemas import (
    CategoryCreate,
    CategoryNode,
    CategoryRename,
    CategoryView,
    DeleteImpact,
    MergeResult,
)


class TaxonomyService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def tree(self) -> list[CategoryNode]:
        roots = self._session.query(Category).filter(Category.parent_id.is_(None)).order_by(Category.name).all()
        return [self._build_node(r) for r in roots]

    def _build_node(self, category: Category) -> CategoryNode:
        direct_count = (
            self._session.query(func.count(ActivityEvent.id))
            .filter(ActivityEvent.category_id == category.id)
            .scalar()
            or 0
        )
        children = (
            self._session.query(Category)
            .filter(Category.parent_id == category.id)
            .order_by(Category.name)
            .all()
        )
        child_nodes = [self._build_node(c) for c in children]
        total_count = direct_count + sum(c.total_event_count for c in child_nodes)
        return CategoryNode(
            id=category.id,
            name=category.name,
            normalized_name=category.normalized_name,
            parent_id=category.parent_id,
            origin=category.origin,
            event_count=direct_count,
            total_event_count=total_count,
            children=child_nodes,
        )

    def create(self, command: CategoryCreate) -> CategoryView:
        normalized = normalize_category_name(command.name)

        if command.parent_id is not None:
            parent = self._session.get(Category, command.parent_id)
            if parent is None:
                raise ValueError("父分类不存在")
            if parent.parent_id is not None:
                raise ValueError("分类层级不能超过两层")

        existing = (
            self._session.query(Category)
            .filter(
                Category.parent_id == command.parent_id,
                Category.normalized_name == normalized,
            )
            .first()
        )
        if existing is not None:
            raise ValueError("同级分类名称重复")

        category = Category(
            name=command.name,
            normalized_name=normalized,
            parent_id=command.parent_id,
            origin="user",
        )
        self._session.add(category)
        self._session.flush()
        return CategoryView.model_validate(category)

    def rename(self, category_id: str, command: CategoryRename) -> CategoryView:
        category = self._session.get(Category, category_id)
        if category is None:
            raise ValueError("分类不存在")

        normalized = normalize_category_name(command.name)

        existing = (
            self._session.query(Category)
            .filter(
                Category.id != category_id,
                Category.parent_id == category.parent_id,
                Category.normalized_name == normalized,
            )
            .first()
        )
        if existing is not None:
            raise ValueError("同级分类名称重复")

        category.name = command.name
        category.normalized_name = normalized
        self._session.flush()
        return CategoryView.model_validate(category)

    def merge(self, source_id: str, target_id: str) -> MergeResult:
        if source_id == target_id:
            raise ValueError("不能将分类合并到自身")

        source = self._session.get(Category, source_id)
        target = self._session.get(Category, target_id)
        if source is None or target is None:
            raise ValueError("分类不存在")

        if (source.parent_id is None) != (target.parent_id is None):
            raise ValueError("只能合并相同层级的分类")

        merged_events = self._move_events(source_id, target_id)
        reparented_children, merged_children = self._reparent_and_merge_children(source, target)
        self._rewrite_corrections(source_id, target_id)
        self._session.delete(source)
        self._session.flush()

        return MergeResult(
            merged_events=merged_events,
            reparented_children=reparented_children,
            merged_children=merged_children,
        )

    def _move_events(self, source_id: str, target_id: str) -> int:
        result = (
            self._session.query(ActivityEvent)
            .filter(ActivityEvent.category_id == source_id)
            .update({"category_id": target_id}, synchronize_session="fetch")
        )
        return result

    def _reparent_and_merge_children(self, source: Category, target: Category) -> tuple[int, int]:
        source_children = (
            self._session.query(Category).filter(Category.parent_id == source.id).all()
        )
        if not source_children:
            return 0, 0

        target_children = (
            self._session.query(Category).filter(Category.parent_id == target.id).all()
        )
        target_by_name = {c.normalized_name: c for c in target_children}

        reparented = 0
        merged = 0
        for child in source_children:
            if child.normalized_name in target_by_name:
                dup_target = target_by_name[child.normalized_name]
                self._move_events(child.id, dup_target.id)
                self._rewrite_corrections(child.id, dup_target.id)
                self._session.delete(child)
                merged += 1
            else:
                child.parent_id = target.id
                reparented += 1

        return reparented, merged

    def _rewrite_corrections(self, source_id: str, target_id: str) -> None:
        corrections = (
            self._session.query(CorrectionMemory)
            .filter(
                CorrectionMemory.active.is_(True),
                CorrectionMemory.original_category_id == source_id,
            )
            .all()
        )
        for corr in corrections:
            corr.original_category_id = target_id

        corrections = (
            self._session.query(CorrectionMemory)
            .filter(
                CorrectionMemory.active.is_(True),
                CorrectionMemory.final_category_id == source_id,
            )
            .all()
        )
        for corr in corrections:
            corr.final_category_id = target_id

    def impact(self, category_id: str) -> DeleteImpact:
        category = self._session.get(Category, category_id)
        if category is None:
            raise ValueError("分类不存在")

        ids = self._descendant_ids(category_id)
        affected = (
            self._session.query(func.count(ActivityEvent.id))
            .filter(ActivityEvent.category_id.in_(ids))
            .scalar()
            or 0
        )
        return DeleteImpact(
            category_id=category.id,
            category_name=category.name,
            descendant_count=len(ids) - 1,
            affected_event_count=affected,
        )

    def delete(self, category_id: str) -> DeleteImpact:
        category = self._session.get(Category, category_id)
        if category is None:
            raise ValueError("分类不存在")

        impact = self.impact(category_id)
        ids = self._descendant_ids(category_id)

        self._session.query(ActivityEvent).filter(
            ActivityEvent.category_id.in_(ids)
        ).update({"category_id": None, "status": "pending"}, synchronize_session="fetch")

        self._session.query(CorrectionMemory).filter(
            CorrectionMemory.original_category_id.in_(ids)
        ).update({"active": False}, synchronize_session="fetch")

        self._session.query(CorrectionMemory).filter(
            CorrectionMemory.final_category_id.in_(ids)
        ).update({"active": False}, synchronize_session="fetch")

        children = self._session.query(Category).filter(Category.parent_id == category_id).all()
        for child in children:
            self._session.delete(child)
        self._session.delete(category)
        self._session.flush()

        return impact

    def _descendant_ids(self, category_id: str) -> set[str]:
        ids = {category_id}
        children = (
            self._session.query(Category)
            .filter(Category.parent_id == category_id)
            .all()
        )
        for child in children:
            ids.update(self._descendant_ids(child.id))
        return ids

    def resolve_choice(
        self, choice, *, origin_message_id: str
    ) -> Category:
        from shred.classification.contracts import CategoryChoice

        if not isinstance(choice, CategoryChoice):
            raise TypeError("无效的分类选择")

        if choice.existing_id is not None:
            category = self._session.get(Category, choice.existing_id)
            if category is None:
                raise ValueError("分类不存在")
            return category

        if choice.new_path is None:
            raise ValueError("必须提供 existing_id 或 new_path")

        parent: Category | None = None
        for idx, name in enumerate(choice.new_path):
            normalized = normalize_category_name(name)
            existing = (
                self._session.query(Category)
                .filter(
                    Category.parent_id == (parent.id if parent else None),
                    Category.normalized_name == normalized,
                )
                .first()
            )
            if existing is not None:
                parent = existing
                continue

            if idx >= 2:
                raise ValueError("分类层级不能超过两层")

            cat = Category(
                name=name,
                normalized_name=normalized,
                parent_id=parent.id if parent else None,
                origin="agent",
                origin_message_id=origin_message_id,
            )
            self._session.add(cat)
            self._session.flush()
            parent = cat

        assert parent is not None
        return parent
