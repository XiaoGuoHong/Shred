# ruff: noqa: B008

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from shred.classification.contracts import Classifier, ClassifierFailure
from shred.core.config import get_env_settings
from shred.core.database import get_session
from shred.db.models import AppSetting, CorrectionMemory
from shred.settings.schemas import (
    PreferencesClearRequest,
    SettingsUpdate,
    SettingsView,
    TestConnectionResult,
)

settings_router = APIRouter()
preferences_router = APIRouter()


def _get_or_create_settings(session: Session) -> AppSetting:
    existing = session.get(AppSetting, 1)
    if existing is None:
        env = get_env_settings()
        existing = AppSetting(
            id=1,
            api_base_url=env.api_base_url,
            model_name=env.model,
        )
        session.add(existing)
        session.flush()
    return existing


def _build_settings_view(session: Session, app_settings: AppSetting) -> SettingsView:
    env = get_env_settings()
    api_key_configured = env.openai_api_key is not None
    preference_count = (
        session.query(CorrectionMemory)
        .filter(CorrectionMemory.active.is_(True))
        .count()
    )
    return SettingsView(
        api_base_url=app_settings.api_base_url,
        model_name=app_settings.model_name,
        api_key_configured=api_key_configured,
        preference_count=preference_count,
    )


@settings_router.get("", response_model=SettingsView)
def get_settings(session: Session = Depends(get_session)) -> SettingsView:
    app_settings = _get_or_create_settings(session)
    return _build_settings_view(session, app_settings)


@settings_router.patch("", response_model=SettingsView)
def update_settings(
    changes: SettingsUpdate,
    session: Session = Depends(get_session),
) -> SettingsView:
    with session.begin():
        app_settings = _get_or_create_settings(session)
        if changes.api_base_url is not None:
            app_settings.api_base_url = changes.api_base_url
        if changes.model_name is not None:
            app_settings.model_name = changes.model_name
        session.flush()
        return _build_settings_view(session, app_settings)


def get_connection_classifier(
    session: Session = Depends(get_session),
) -> Classifier:
    from shred.classification.openai_adapter import ModelConfig, OpenAIClassifier

    app_settings = _get_or_create_settings(session)
    env = get_env_settings()
    key = env.openai_api_key.get_secret_value() if env.openai_api_key else None

    return OpenAIClassifier(
        model_config=ModelConfig(
            api_base_url=app_settings.api_base_url,
            model_name=app_settings.model_name,
        ),
        openai_api_key=key,
    )


@settings_router.post("/test-connection", response_model=TestConnectionResult)
def test_connection(
    classifier: Classifier = Depends(get_connection_classifier),
) -> TestConnectionResult:
    try:
        classifier.test_connection()
        return TestConnectionResult(ok=True)
    except ClassifierFailure as exc:
        return TestConnectionResult(
            ok=False, error_code=exc.code, error_message=exc.summary
        )
    except Exception:  # noqa: BLE001
        return TestConnectionResult(
            ok=False, error_code="unknown", error_message="连接测试失败"
        )


@preferences_router.delete("", status_code=204)
def clear_preferences(
    command: PreferencesClearRequest,
    session: Session = Depends(get_session),
) -> None:
    if not command.confirm:
        raise HTTPException(status_code=422, detail="需要确认清除偏好数据")

    with session.begin():
        session.query(CorrectionMemory).filter(
            CorrectionMemory.active.is_(True)
        ).update({"active": False}, synchronize_session="fetch")
