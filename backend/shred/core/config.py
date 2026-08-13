from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    app_version: str = "0.1.0"
    database_url: str = "sqlite:///./data/shred.db"
    openai_api_key: SecretStr | None = None
    api_base_url: str = "https://api.openai.com/v1"
    model: str = ""
    model_timeout_seconds: int = 60
    bind_address: str = "127.0.0.1"
    port: int = 8000
    data_dir: str = "./data"
    e2e_fake_classifier: bool = False

    model_config = SettingsConfigDict(env_prefix="SHRED_", env_file=".env")

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def _empty_key_is_unset(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


@lru_cache
def get_env_settings() -> EnvSettings:
    return EnvSettings()
