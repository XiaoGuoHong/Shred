from __future__ import annotations

from datetime import UTC, date, datetime

from shred.classification.contracts import (
    CategoryChoice,
    ClassificationDraft,
    ClassificationRequest,
    ClassifierFailure,
    EventDraft,
)


class FakeClassifier:
    def __init__(
        self,
        drafts: ClassificationDraft | None = None,
        failure: ClassifierFailure | None = None,
    ) -> None:
        self._drafts = drafts
        self._failure = failure
        self._call_count = 0
        self._last_request: ClassificationRequest | None = None

    def classify(self, request: ClassificationRequest) -> ClassificationDraft:
        self._call_count += 1
        self._last_request = request
        if self._failure is not None:
            raise self._failure
        assert self._drafts is not None
        return self._drafts

    def test_connection(self) -> None:
        if self._failure is not None:
            raise self._failure

    @property
    def call_count(self) -> int:
        return self._call_count


def make_interview_drafts(submission_date: date) -> list[EventDraft]:
    return [
        EventDraft(
            title="上午活动",
            source_fragment="上午",
            local_date=submission_date,
            precision="part_of_day",
            part_of_day="morning",
            category=CategoryChoice(new_path=["工作"]),
            tags=[],
        ),
        EventDraft(
            title="预约面试",
            source_fragment="预约",
            local_date=submission_date,
            precision="inferred",
            category=CategoryChoice(new_path=["工作", "面试"]),
            tags=["面试"],
        ),
        EventDraft(
            title="面试安排",
            source_fragment="下周一的面试",
            local_date=submission_date,
            precision="date",
            category=CategoryChoice(new_path=["工作", "面试"]),
            tags=["面试"],
        ),
    ]


def make_interview_classifier(submission_date: date) -> FakeClassifier:
    return FakeClassifier(
        drafts=ClassificationDraft(events=make_interview_drafts(submission_date))
    )


def failing_classifier(code: str = "model_timeout", summary: str = "测试失败") -> FakeClassifier:
    return FakeClassifier(failure=ClassifierFailure(code=code, summary=summary))


def empty_classifier() -> FakeClassifier:
    from shred.classification.contracts import CategoryChoice, EventDraft

    return FakeClassifier(
        drafts=ClassificationDraft(
            events=[
                EventDraft(
                    title="空",
                    source_fragment="空",
                    local_date=datetime.now(UTC).date(),
                    precision="inferred",
                    category=CategoryChoice(new_path=["工作"]),
                )
            ]
        )
    )
