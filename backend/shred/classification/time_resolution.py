from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel

from shred.classification.contracts import EventDraft

_PART_OF_DAY_ANCHORS: dict[str, time] = {
    "dawn": time(3, 0),
    "morning": time(9, 0),
    "noon": time(12, 0),
    "afternoon": time(15, 0),
    "evening": time(19, 0),
    "night": time(22, 0),
}

_DATE_ANCHOR = time(12, 0)
_FUTURE_TOLERANCE = timedelta(minutes=5)


class TimeResolutionError(ValueError):
    pass


class ResolvedOccurrence(BaseModel):
    occurred_at: datetime
    precision: str
    part_of_day: str | None = None


def resolve_occurrence(
    draft: EventDraft,
    submitted_at: datetime,
    timezone: str,
) -> ResolvedOccurrence:
    try:
        tz = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, KeyError):
        raise TimeResolutionError(f"无法识别的时区: {timezone}")

    if draft.precision == "inferred":
        occurred_at = submitted_at
        precision = "inferred"
        part_of_day = None
    elif draft.precision == "exact":
        local_dt = datetime.combine(draft.local_date, draft.local_time)
        occurred_at = local_dt.replace(tzinfo=tz).astimezone(UTC)
        precision = "exact"
        part_of_day = None
    elif draft.precision == "part_of_day":
        anchor = _PART_OF_DAY_ANCHORS[draft.part_of_day]
        local_dt = datetime.combine(draft.local_date, anchor)
        occurred_at = local_dt.replace(tzinfo=tz).astimezone(UTC)
        precision = "part_of_day"
        part_of_day = draft.part_of_day
    elif draft.precision == "date":
        local_dt = datetime.combine(draft.local_date, _DATE_ANCHOR)
        occurred_at = local_dt.replace(tzinfo=tz).astimezone(UTC)
        precision = "date"
        part_of_day = None
    else:
        raise TimeResolutionError(f"未知精度: {draft.precision}")

    if occurred_at - submitted_at > _FUTURE_TOLERANCE:
        raise TimeResolutionError("事件时间不能超过提交时间五分钟")

    return ResolvedOccurrence(
        occurred_at=occurred_at,
        precision=precision,
        part_of_day=part_of_day,
    )
