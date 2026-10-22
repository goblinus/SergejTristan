"""Конфигурация приложения (pydantic-settings, префикс DIVCAL_)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки, читаемые из окружения и .env."""

    model_config = SettingsConfigDict(
        env_prefix="DIVCAL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./divcal.db"
    log_level: str = "INFO"
    watch_soon_days: int = 14
    watch_default_threshold_days: int = 7
    http_timeout_seconds: int = 30
    http_retries: int = 3
    # Глубина повторного обхода ленты disclosure, календарных дней.
    disclosure_lookback_days: int = 3


@lru_cache
def get_settings() -> Settings:
    """Возвращает единственный экземпляр настроек."""
    return Settings()
