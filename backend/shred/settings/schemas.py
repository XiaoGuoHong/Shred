from __future__ import annotations

from pydantic import BaseModel


class SettingsView(BaseModel):
    api_base_url: str
    model_name: str
    api_key_configured: bool
    preference_count: int


class SettingsUpdate(BaseModel):
    api_base_url: str | None = None
    model_name: str | None = None


class PreferencesClearRequest(BaseModel):
    confirm: bool


class TestConnectionResult(BaseModel):
    ok: bool
    error_code: str | None = None
    error_message: str | None = None
