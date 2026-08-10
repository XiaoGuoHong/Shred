"""OpenAI adapter tests — parse, repair, and safe-error behaviour."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from shred.classification.contracts import (
    CategoryContext,
    ClassificationDraft,
    ClassificationRequest,
    ClassifierFailure,
)
from shred.classification.openai_adapter import (
    ModelConfig,
    OpenAIClassifier,
    extract_json_object,
)


def _make_mock_response() -> MagicMock:
    resp = MagicMock()
    resp.request = MagicMock()
    return resp


_DEFAULT_CFG = ModelConfig(api_base_url="http://localhost/v1", model_name="test-model")


def _valid_response() -> str:
    return json.dumps({
        "events": [
            {
                "title": "Mock Interview",
                "source_fragment": "have a mock interview at 2pm",
                "local_date": "2026-08-10",
                "local_time": "14:00:00",
                "precision": "exact",
                "category": {"new_path": ["Work", "Interview"]},
                "tags": ["mock", "interview"],
            }
        ]
    })


def _sample_request() -> ClassificationRequest:
    return ClassificationRequest(
        text="have a mock interview at 2pm tomorrow",
        submitted_at=datetime(2026, 8, 9, 12, 0, 0, tzinfo=UTC),
        timezone="Asia/Shanghai",
        categories=[CategoryContext(id="cat-1", name="Work", parent_id=None, path=["Work"])],
        corrections=[],
        mode="split",
    )


def _classifier(
    complete=None, api_key: str = "test-key", config: ModelConfig | None = None
) -> OpenAIClassifier:
    if complete is None:
        complete = lambda messages: _valid_response()
    return OpenAIClassifier(
        complete=complete, openai_api_key=api_key, model_config=config or _DEFAULT_CFG,
    )


class TestExtractJsonObject:
    def test_clean_json_is_parsed(self) -> None:
        result = extract_json_object(_valid_response())

        assert isinstance(result, dict)
        assert result["events"][0]["title"] == "Mock Interview"

    def test_json_inside_markdown_fence_is_extracted(self) -> None:
        raw = "Here is output:\n```json\n" + _valid_response() + "\n```"
        result = extract_json_object(raw)

        assert isinstance(result, dict)
        assert result["events"][0]["title"] == "Mock Interview"

    def test_extra_prose_after_json_is_rejected(self) -> None:
        raw = _valid_response() + "\nHere is some more text"
        with pytest.raises(ValueError):
            extract_json_object(raw)

    def test_multiple_json_objects_are_rejected(self) -> None:
        raw = _valid_response() + "\n" + _valid_response()
        with pytest.raises(ValueError):
            extract_json_object(raw)

    def test_text_without_json_raises(self) -> None:
        with pytest.raises(ValueError):
            extract_json_object("not valid json at all")


class TestClassifySuccess:
    def test_valid_json_produces_classification_draft(self) -> None:
        classifier = _classifier()
        result = classifier.classify(_sample_request())

        assert isinstance(result, ClassificationDraft)
        assert len(result.events) == 1
        assert result.events[0].title == "Mock Interview"

    def test_json_in_fence_is_used(self) -> None:
        raw = "```json\n" + _valid_response() + "\n```"
        classifier = _classifier(complete=lambda messages: raw)
        result = classifier.classify(_sample_request())

        assert result.events[0].title == "Mock Interview"


class TestOneRepair:
    def test_invalid_first_output_causes_exactly_one_repair_call(self) -> None:
        call_count = 0
        valid = _valid_response()

        def complete(messages):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return '{"events": []}'  # invalid — empty events
            return valid

        classifier = _classifier(complete=complete)
        result = classifier.classify(_sample_request())

        assert result.events[0].title == "Mock Interview"
        assert call_count == 2
        assert "events" in classifier._last_repair_messages[1]["content"]

    def test_invalid_repair_raises_model_invalid_response(self) -> None:
        call_count = 0

        def complete(messages):
            nonlocal call_count
            call_count += 1
            return '{"bad": "output"}'

        classifier = _classifier(complete=complete)
        with pytest.raises(ClassifierFailure) as exc:
            classifier.classify(_sample_request())

        assert exc.value.code == "model_invalid_response"
        assert call_count == 2


class TestSafeErrors:
    def test_missing_api_key_fails_before_network_call(self) -> None:
        called = False

        def complete(messages):
            nonlocal called
            called = True
            return _valid_response()

        classifier = OpenAIClassifier(
            complete=complete, openai_api_key=None, model_config=_DEFAULT_CFG,
        )
        with pytest.raises(ClassifierFailure) as exc:
            classifier.classify(_sample_request())

        assert exc.value.code == "model_not_configured"
        assert not called

    def test_missing_model_name_fails_before_network_call(self) -> None:
        called = False

        def complete(messages):
            nonlocal called
            called = True
            return _valid_response()

        cfg = ModelConfig(api_base_url="http://localhost/v1", model_name="")
        classifier = OpenAIClassifier(
            complete=complete, openai_api_key="test-key", model_config=cfg,
        )
        with pytest.raises(ClassifierFailure) as exc:
            classifier.classify(_sample_request())

        assert exc.value.code == "model_not_configured"
        assert not called

    def test_timeout_maps_to_model_timeout(self) -> None:
        from openai import APITimeoutError

        def complete(messages):
            raise APITimeoutError(request=None)

        classifier = _classifier(complete=complete)
        with pytest.raises(ClassifierFailure) as exc:
            classifier.classify(_sample_request())

        assert exc.value.code == "model_timeout"

    def test_authentication_error_maps_to_model_authentication_failed(self) -> None:
        from openai import AuthenticationError

        def complete(messages):
            raise AuthenticationError(
                message="Invalid API key", response=_make_mock_response(), body=None
            )

        classifier = _classifier(complete=complete)
        with pytest.raises(ClassifierFailure) as exc:
            classifier.classify(_sample_request())

        assert exc.value.code == "model_authentication_failed"

    def test_rate_limit_maps_to_model_rate_limited(self) -> None:
        from openai import RateLimitError

        def complete(messages):
            raise RateLimitError(
                message="Rate limit exceeded", response=_make_mock_response(), body=None
            )

        classifier = _classifier(complete=complete)
        with pytest.raises(ClassifierFailure) as exc:
            classifier.classify(_sample_request())

        assert exc.value.code == "model_rate_limited"

    def test_connection_error_maps_to_model_unreachable(self) -> None:
        from openai import APIConnectionError

        def complete(messages):
            raise APIConnectionError(request=None)

        classifier = _classifier(complete=complete)
        with pytest.raises(ClassifierFailure) as exc:
            classifier.classify(_sample_request())

        assert exc.value.code == "model_unreachable"

    def test_error_messages_exclude_keys_and_bodies(self) -> None:
        from openai import AuthenticationError

        def complete(messages):
            raise AuthenticationError(
                message="Incorrect API key: sk-abc123",
                response=_make_mock_response(),
                body={"error": "invalid"},
            )

        classifier = _classifier(complete=complete)
        with pytest.raises(ClassifierFailure) as exc:
            classifier.classify(_sample_request())

        assert "sk-abc123" not in exc.value.summary
        assert "401" not in exc.value.summary


class TestConnection:
    def test_connection_accepts_ok(self) -> None:
        def complete(messages):
            return "OK"

        classifier = _classifier(complete=complete)
        classifier.test_connection()

    def test_connection_rejects_non_ok(self) -> None:
        def complete(messages):
            return "Error: something went wrong"

        classifier = _classifier(complete=complete)
        with pytest.raises(ClassifierFailure):
            classifier.test_connection()
