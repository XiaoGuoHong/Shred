"""Deterministic classifier used only when SHRED_E2E_FAKE_CLASSIFIER=1.

End-to-end tests exercise the real FastAPI + SQLite pipeline this way
without calling a model provider. The flag is off by default and is
never set by the compose deployment.
"""

from __future__ import annotations

from datetime import UTC

from shred.classification.contracts import (
    CategoryChoice,
    ClassificationDraft,
    ClassificationRequest,
    EventDraft,
)


class E2EFakeClassifier:
    """Classifies any request into two fixed events on the submission date."""

    def classify(self, request: ClassificationRequest) -> ClassificationDraft:
        submitted_at = request.submitted_at
        if submitted_at.tzinfo is None:
            submitted_at = submitted_at.replace(tzinfo=UTC)
        return ClassificationDraft(
            events=[
                EventDraft(
                    title="假模型事件一",
                    source_fragment=request.text[:12],
                    local_date=submitted_at.date(),
                    precision="inferred",
                    category=CategoryChoice(new_path=["工作"]),
                    tags=["测试"],
                ),
                EventDraft(
                    title="假模型事件二",
                    source_fragment=request.text[:12],
                    local_date=submitted_at.date(),
                    precision="inferred",
                    category=CategoryChoice(new_path=["生活"]),
                    tags=[],
                ),
            ]
        )

    def test_connection(self) -> None:
        return None
