"""
Application configuration.
All settings are loaded from environment variables / .env file.
Never hardcode secrets here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # LLM
    groq_api_key: str
    groq_model: str = "openai/gpt-oss-120b"
    
    # Dataset
    dataset_path: str = "data/Support_tickets.csv"

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
