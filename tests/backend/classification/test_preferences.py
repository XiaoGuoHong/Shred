"""Correction-ranking tests using real Chinese character-bigram similarity."""

from __future__ import annotations

from shred.classification.contracts import CorrectionContext
from shred.classification.preferences import rank_corrections


def _correction(event_text: str) -> CorrectionContext:
    return CorrectionContext(
        event_text=event_text,
        original_path=["生活"],
        final_path=["工作", "求职"],
    )


def test_bigrams_rank_an_interview_correction_above_unrelated_cleaning() -> None:
    interview = _correction("参加面试复盘")
    cleaning = _correction("拖地")

    ranked = rank_corrections("参加二面", [cleaning, interview])

    assert ranked == [interview]


def test_ranking_limits_positive_matches_to_five_to_bound_prompt_context() -> None:
    corrections = [_correction(f"参加面试复盘{index}") for index in range(6)]

    ranked = rank_corrections("参加二面", corrections)

    assert ranked == corrections[:5]


def test_zero_similarity_falls_back_to_the_three_most_recent_corrections() -> None:
    recent = _correction("读书")
    previous = _correction("跑步")
    oldest = _correction("做饭")
    ignored = _correction("洗车")

    ranked = rank_corrections("面试", [recent, previous, oldest, ignored])

    assert ranked == [recent, previous, oldest]
