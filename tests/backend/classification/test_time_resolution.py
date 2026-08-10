"""Time-resolution tests for deterministic local-time anchors."""

from __future__ import annotations

from datetime import UTC, date, datetime, time

import pytest

from shred.classification.contracts import CategoryChoice, EventDraft
from shred.classification.time_resolution import TimeResolutionError, resolve_occurrence


def _draft(
    *,
    local_date: date,
    precision: str,
    local_time: time | None = None,
    part_of_day: str | None = None,
) -> EventDraft:
    return EventDraft(
        title="处理事项",
        source_fragment="处理事项",
        local_date=local_date,
        local_time=local_time,
        precision=precision,
        part_of_day=part_of_day,
        category=CategoryChoice(existing_id="cat-1"),
    )


def test_morning_uses_the_0900_local_anchor_to_prevent_unstable_part_of_day_sorting() -> None:
    resolved = resolve_occurrence(
        _draft(
            local_date=date(2026, 8, 9),
            precision="part_of_day",
            part_of_day="morning",
        ),
        submitted_at=datetime(2026, 8, 10, 12, tzinfo=UTC),
        timezone="Asia/Shanghai",
    )

    assert resolved.occurred_at == datetime(2026, 8, 9, 1, tzinfo=UTC)
    assert resolved.precision == "part_of_day"
    assert resolved.part_of_day == "morning"


def test_date_precision_uses_a_noon_local_anchor_to_sort_dates_consistently() -> None:
    resolved = resolve_occurrence(
        _draft(local_date=date(2026, 8, 9), precision="date"),
        submitted_at=datetime(2026, 8, 10, 12, tzinfo=UTC),
        timezone="Asia/Shanghai",
    )

    assert resolved.occurred_at == datetime(2026, 8, 9, 4, tzinfo=UTC)
    assert resolved.precision == "date"
    assert resolved.part_of_day is None


def test_inferred_precision_keeps_the_submission_instant_to_avoid_invented_history() -> None:
    submitted_at = datetime(2026, 8, 10, 12, 34, 56, tzinfo=UTC)

    resolved = resolve_occurrence(
        _draft(local_date=date(2026, 8, 1), precision="inferred"),
        submitted_at=submitted_at,
        timezone="Asia/Shanghai",
    )

    assert resolved.occurred_at == submitted_at
    assert resolved.precision == "inferred"
    assert resolved.part_of_day is None


def test_future_occurrence_beyond_five_minutes_is_rejected_to_prevent_future_event_fabrication() -> None:
    with pytest.raises(TimeResolutionError):
        resolve_occurrence(
            _draft(
                local_date=date(2026, 8, 10),
                precision="part_of_day",
                part_of_day="morning",
            ),
            submitted_at=datetime(2026, 8, 10, tzinfo=UTC),
            timezone="Asia/Shanghai",
        )


def test_invalid_iana_timezone_is_rejected_to_prevent_silent_local_time_misinterpretation() -> None:
    with pytest.raises(TimeResolutionError):
        resolve_occurrence(
            _draft(local_date=date(2026, 8, 9), precision="date"),
            submitted_at=datetime(2026, 8, 10, tzinfo=UTC),
            timezone="Mars/Olympus_Mons",
        )
