from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    app_version: str = "0.1.0"
    database_url: str = "sqlite:///./data/shred.db"
    openai_api_key: SecretStr | None = None
    api_base_url: str = "https://api.openai.com/v1"
    model: str = ""
    model_timeout_seconds: int = 60

    model_config = SettingsConfigDict(env_prefix="SHRED_", env_file=".env")


@lru_cache
def get_env_settings() -> EnvSettings:
    return EnvSettings()
