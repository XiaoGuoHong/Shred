from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str
    parent_id: str | None = None


class CategoryRename(BaseModel):
    name: str


class CategoryView(BaseModel):
    id: str
    name: str
    normalized_name: str
    parent_id: str | None
    origin: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryNode(BaseModel):
    id: str
    name: str
    normalized_name: str
    parent_id: str | None
    origin: str
    event_count: int
    total_event_count: int
    children: list[CategoryNode]

    model_config = {"from_attributes": True}


class DeleteImpact(BaseModel):
    category_id: str
    category_name: str
    descendant_count: int
    affected_event_count: int


class MergeResult(BaseModel):
    merged_events: int
    reparented_children: int
    merged_children: int


class MergeRequest(BaseModel):
    source_id: str
    target_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ErrorDetail(BaseModel):
    code: str
    message: str
