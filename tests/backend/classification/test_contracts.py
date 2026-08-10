"""Classification contract tests for invalid AI output at the domain boundary."""

from __future__ import annotations

from datetime import date, time

import pytest
from pydantic import ValidationError

from shred.classification.contracts import (
    CategoryChoice,
    ClassificationDraft,
    ClassificationRequest,
    ClassifierFailure,
    EventDraft,
)


def _new_category() -> CategoryChoice:
    return CategoryChoice(new_path=["工作", "求职"])


def test_category_choice_rejects_two_strategies_to_prevent_ambiguous_category_creation() -> None:
    with pytest.raises(ValidationError):
        CategoryChoice(existing_id="cat-1", new_path=["工作", "求职"])


def test_category_choice_rejects_no_strategy_to_prevent_an_uncategorized_event() -> None:
    with pytest.raises(ValidationError):
        CategoryChoice()


def test_category_choice_rejects_three_level_paths_to_preserve_the_two_level_taxonomy() -> None:
    with pytest.raises(ValidationError):
        CategoryChoice(new_path=["工作", "求职", "面试"])


def test_event_draft_rejects_more_than_three_tags_to_limit_tag_sprawl() -> None:
    with pytest.raises(ValidationError):
        EventDraft(
            title="修改简历",
            source_fragment="把简历改了",
            local_date=date(2026, 8, 10),
            precision="inferred",
            category=_new_category(),
            tags=["一", "二", "三", "四"],
        )


def test_exact_precision_requires_a_clock_time_to_prevent_fake_exact_timestamps() -> None:
    with pytest.raises(ValidationError):
        EventDraft(
            title="面试",
            source_fragment="上午面试",
            local_date=date(2026, 8, 10),
            precision="exact",
            category=_new_category(),
        )


def test_part_of_day_rejects_a_clock_time_to_prevent_conflicting_time_signals() -> None:
    with pytest.raises(ValidationError):
        EventDraft(
            title="面试",
            source_fragment="上午面试",
            local_date=date(2026, 8, 10),
            local_time=time(9, 30),
            precision="part_of_day",
            part_of_day="morning",
            category=_new_category(),
        )


def test_date_precision_rejects_a_part_of_day_to_keep_coarse_dates_unambiguous() -> None:
    with pytest.raises(ValidationError):
        EventDraft(
            title="投简历",
            source_fragment="今天投简历",
            local_date=date(2026, 8, 10),
            precision="date",
            part_of_day="morning",
            category=_new_category(),
        )


def test_new_category_path_normalizes_names_before_a_taxonomy_entry_is_created() -> None:
    choice = CategoryChoice(new_path=["  工　作  "])

    assert choice.new_path == ["工 作"]


def test_classification_draft_requires_an_event_to_prevent_empty_successful_classifications() -> None:
    with pytest.raises(ValidationError):
        ClassificationDraft(events=[])


def test_request_defaults_to_split_mode_to_preserve_multi_event_classification() -> None:
    request = ClassificationRequest(
        text="上午面试，下午改简历",
        submitted_at="2026-08-10T12:00:00+00:00",
        timezone="Asia/Shanghai",
        categories=[],
        corrections=[],
    )

    assert request.mode == "split"


def test_classifier_failure_exposes_only_safe_code_and_summary_for_api_mapping() -> None:
    failure = ClassifierFailure("provider_unavailable", "分类服务暂不可用")

    assert failure.code == "provider_unavailable"
    assert failure.summary == "分类服务暂不可用"
    assert str(failure) == "分类服务暂不可用"
