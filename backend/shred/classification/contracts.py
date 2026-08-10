from __future__ import annotations

from datetime import date, datetime, time
from typing import Literal, Protocol

from pydantic import BaseModel, Field, model_validator

from shred.taxonomy.names import normalize_category_name


class CategoryChoice(BaseModel):
    existing_id: str | None = None
    new_path: list[str] | None = None

    @model_validator(mode="after")
    def _validate_exactly_one_strategy(self) -> CategoryChoice:
        has_existing = self.existing_id is not None
        has_new = self.new_path is not None and len(self.new_path) > 0

        if has_existing and has_new:
            raise ValueError("existing_id 与 new_path 不能同时提供")
        if not has_existing and not has_new:
            raise ValueError("必须提供 existing_id 或 new_path")

        if has_new and self.new_path is not None:
            if len(self.new_path) not in (1, 2):
                raise ValueError("new_path 必须包含 1 或 2 个层级")
            self.new_path = [normalize_category_name(n) for n in self.new_path]

        return self


class EventDraft(BaseModel):
    title: str
    source_fragment: str
    local_date: date
    local_time: time | None = None
    precision: Literal["exact", "part_of_day", "date", "inferred"]
    part_of_day: Literal[
        "dawn", "morning", "noon", "afternoon", "evening", "night"
    ] | None = None
    category: CategoryChoice
    tags: list[str] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def _validate_precision_rules(self) -> EventDraft:
        if self.precision == "exact" and self.local_time is None:
            raise ValueError("exact 精度必须提供 local_time")
        if self.precision == "part_of_day":
            if self.part_of_day is None:
                raise ValueError("part_of_day 精度必须提供 part_of_day")
            if self.local_time is not None:
                raise ValueError("part_of_day 精度不能提供 local_time")
        if self.precision in ("date", "inferred") and self.part_of_day is not None:
            raise ValueError(f"{self.precision} 精度不能提供 part_of_day")
        return self


class ClassificationDraft(BaseModel):
    events: list[EventDraft] = Field(min_length=1)


class CategoryContext(BaseModel):
    id: str
    name: str
    parent_id: str | None
    path: list[str]


class CorrectionContext(BaseModel):
    event_text: str
    original_path: list[str]
    final_path: list[str]


class ClassificationRequest(BaseModel):
    text: str
    submitted_at: datetime
    timezone: str
    categories: list[CategoryContext]
    corrections: list[CorrectionContext]
    mode: Literal["split", "single"] = "split"


class Classifier(Protocol):
    def classify(self, request: ClassificationRequest) -> ClassificationDraft: ...

    def test_connection(self) -> None: ...


class ClassifierFailure(RuntimeError):
    def __init__(self, code: str, summary: str) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary
