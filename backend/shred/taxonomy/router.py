# ruff: noqa: B008

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from shred.core.database import get_session
from shred.taxonomy.schemas import (
    CategoryCreate,
    CategoryNode,
    CategoryRename,
    CategoryView,
    DeleteImpact,
    ErrorDetail,
    ErrorResponse,
    MergeRequest,
    MergeResult,
)
from shred.taxonomy.service import TaxonomyService

router = APIRouter()


def _error(code: str, message: str, status: int) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail=ErrorResponse(error=ErrorDetail(code=code, message=message)).model_dump(),
    )


@router.get("", response_model=list[CategoryNode])
def list_tree(session: Session = Depends(get_session)) -> list[CategoryNode]:
    return TaxonomyService(session).tree()


@router.post("", response_model=CategoryView, status_code=201)
def create_category(
    command: CategoryCreate, session: Session = Depends(get_session)
) -> CategoryView:
    with session.begin():
        try:
            return TaxonomyService(session).create(command)
        except ValueError as e:
            msg = str(e)
            if "重复" in msg:
                raise _error("category_name_conflict", msg, 409)
            if "层级" in msg:
                raise _error("category_depth_exceeded", msg, 422)
            raise _error("invalid_request", msg, 422)


@router.patch("/{category_id}", response_model=CategoryView)
def rename_category(
    category_id: str,
    command: CategoryRename,
    session: Session = Depends(get_session),
) -> CategoryView:
    with session.begin():
        try:
            return TaxonomyService(session).rename(category_id, command)
        except ValueError as e:
            msg = str(e)
            if "不存在" in msg:
                raise _error("category_not_found", msg, 404)
            if "重复" in msg:
                raise _error("category_name_conflict", msg, 409)
            raise _error("invalid_request", msg, 422)


@router.post("/merge", response_model=MergeResult)
def merge_categories(
    command: MergeRequest, session: Session = Depends(get_session)
) -> MergeResult:
    with session.begin():
        try:
            return TaxonomyService(session).merge(command.source_id, command.target_id)
        except ValueError as e:
            msg = str(e)
            if "不存在" in msg:
                raise _error("category_not_found", msg, 404)
            if "自身" in msg:
                raise _error("invalid_merge", msg, 422)
            if "相同层级" in msg:
                raise _error("invalid_merge", msg, 422)
            raise _error("invalid_request", msg, 422)


@router.post("/{category_id}/delete-impact", response_model=DeleteImpact)
def get_delete_impact(
    category_id: str, session: Session = Depends(get_session)
) -> DeleteImpact:
    try:
        return TaxonomyService(session).impact(category_id)
    except ValueError as e:
        raise _error("category_not_found", str(e), 404)


@router.delete("/{category_id}", response_model=DeleteImpact)
def delete_category(
    category_id: str, session: Session = Depends(get_session)
) -> DeleteImpact:
    with session.begin():
        try:
            return TaxonomyService(session).delete(category_id)
        except ValueError as e:
            raise _error("category_not_found", str(e), 404)
