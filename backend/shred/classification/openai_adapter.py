from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)

from shred.classification.contracts import (
    ClassificationDraft,
    ClassificationRequest,
    ClassifierFailure,
)
from shred.classification.prompt import build_classification_messages


class ModelConfig:
    def __init__(self, api_base_url: str, model_name: str) -> None:
        self.api_base_url = api_base_url
        self.model_name = model_name


_MARKDOWN_FENCE = re.compile(r"```(?:json)?\s*\n?(.*?)```", re.DOTALL)


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()

    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
        raise ValueError("Top-level JSON must be an object")
    except json.JSONDecodeError:
        pass

    fence_match = _MARKDOWN_FENCE.search(stripped)
    if fence_match:
        inner = fence_match.group(1).strip()
        try:
            parsed = json.loads(inner)
            if isinstance(parsed, dict):
                return parsed
            raise ValueError("Top-level JSON must be an object")
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON inside fence: {exc}") from exc

    raise ValueError("No valid JSON object found in text")


def _build_completion_callable(
    openai_api_key: str, model_config: ModelConfig, timeout: int
) -> Callable[[list[dict[str, str]]], str]:
    from openai import OpenAI

    client = OpenAI(
        api_key=openai_api_key,
        base_url=model_config.api_base_url,
        timeout=timeout,
        max_retries=0,
    )

    def _complete(messages: list[dict[str, str]]) -> str:
        completion = client.chat.completions.create(
            model=model_config.model_name,
            messages=messages,
            temperature=0,
        )
        return completion.choices[0].message.content or ""

    return _complete


_ERROR_MAP: dict[type[Exception], str] = {
    APITimeoutError: "model_timeout",
    AuthenticationError: "model_authentication_failed",
    RateLimitError: "model_rate_limited",
    APIConnectionError: "model_unreachable",
}

_API_KEY_PATTERN = re.compile(r"sk-[a-zA-Z0-9_-]+")


def _sanitize_error_message(message: str) -> str:
    return _API_KEY_PATTERN.sub("[REDACTED]", message)


class OpenAIClassifier:
    def __init__(
        self,
        *,
        complete: Callable[[list[dict[str, str]]], str] | None = None,
        openai_api_key: str | None = None,
        model_config: ModelConfig | None = None,
    ) -> None:
        self._complete = complete
        self._openai_api_key = openai_api_key
        self._model_config = model_config
        self._last_repair_messages: list[dict[str, str]] = []

        if complete is not None:
            return

        from shred.core.config import get_env_settings

        settings = get_env_settings()
        timeout = settings.model_timeout_seconds

        if model_config is None:
            model_config = ModelConfig(
                api_base_url=settings.api_base_url,
                model_name=settings.model,
            )

        if openai_api_key is None:
            resolved_key = settings.openai_api_key
            if resolved_key is None:
                self._complete = None
                return
            openai_api_key = resolved_key.get_secret_value()

        self._complete = _build_completion_callable(openai_api_key, model_config, timeout)

    def _check_configured(self) -> None:
        if self._complete is None:
            raise ClassifierFailure(
                code="model_not_configured",
                summary="OpenAI API key or model name is not configured",
            )
        if self._openai_api_key is None:
            raise ClassifierFailure(
                code="model_not_configured",
                summary="OpenAI API key or model name is not configured",
            )
        if self._model_config is not None and not self._model_config.model_name:
            raise ClassifierFailure(
                code="model_not_configured",
                summary="OpenAI API key or model name is not configured",
            )

    def _ensure_configured(self) -> Callable[[list[dict[str, str]]], str]:
        self._check_configured()
        assert self._complete is not None
        return self._complete

    def _map_error(self, exc: Exception) -> ClassifierFailure:
        for error_cls, code in _ERROR_MAP.items():
            # isinstance may fail if the error class constructor is broken on init
            if type(exc).__module__.startswith("openai") and isinstance(exc, error_cls):
                    return ClassifierFailure(
                        code=code, summary=_sanitize_error_message(str(exc))
                    )

        exc_module = getattr(type(exc), "__module__", "")
        exc_qualname = type(exc).__qualname__
        if "openai" in exc_module:
            if "Auth" in exc_qualname:
                return ClassifierFailure(
                    code="model_authentication_failed",
                    summary=_sanitize_error_message(str(exc)),
                )
            if "RateLimit" in exc_qualname:
                return ClassifierFailure(
                    code="model_rate_limited",
                    summary=_sanitize_error_message(str(exc)),
                )
            if "Timeout" in exc_qualname:
                return ClassifierFailure(
                    code="model_timeout", summary=_sanitize_error_message(str(exc))
                )
            if "Connection" in exc_qualname:
                return ClassifierFailure(
                    code="model_unreachable",
                    summary=_sanitize_error_message(str(exc)),
                )

        raise exc from None

    def _call_complete(self, messages: list[dict[str, str]]) -> str:
        complete = self._ensure_configured()

        try:
            return complete(messages)
        except ClassifierFailure:
            raise
        except Exception as exc:  # noqa: BLE001
            raise self._map_error(exc)

    def _parse_or_repair(
        self, raw: str, request: ClassificationRequest
    ) -> ClassificationDraft | None:
        try:
            parsed = extract_json_object(raw)
            return ClassificationDraft.model_validate(parsed)
        except (ValueError, Exception):  # noqa: BLE001, S110
            pass

        repair_messages = build_classification_messages(request)
        repair_messages.append({"role": "assistant", "content": raw})
        repair_messages.append({
            "role": "user",
            "content": (
                "The previous output was invalid. Please ensure the response is a single JSON "
                "object with an 'events' array. Each event must have all required fields "
                "as described in the system prompt. Do not include any text outside the JSON."
            ),
        })

        self._last_repair_messages = repair_messages[-2:]

        try:
            repaired_raw = self._call_complete(repair_messages)
            parsed = extract_json_object(repaired_raw)
            return ClassificationDraft.model_validate(parsed)
        except (ValueError, Exception):  # noqa: BLE001
            return None

    def classify(self, request: ClassificationRequest) -> ClassificationDraft:
        messages = build_classification_messages(request)
        raw = self._call_complete(messages)

        draft = self._parse_or_repair(raw, request)
        if draft is not None:
            return draft

        raise ClassifierFailure(
            code="model_invalid_response",
            summary="Model returned invalid JSON that could not be repaired",
        )

    def test_connection(self) -> None:
        complete = self._ensure_configured()
        result = complete([{"role": "user", "content": "Say OK"}])

        if "OK" not in result:
            raise ClassifierFailure(
                code="model_connection_failed",
                summary="Model did not respond with OK",
            )
