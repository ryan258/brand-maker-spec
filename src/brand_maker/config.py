"""Environment-backed service configuration."""

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime settings loaded from process environment or `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    openrouter_api_key: SecretStr = Field(
        ...,
        min_length=1,
        validation_alias="OPENROUTER_API_KEY",
        description="OpenRouter bearer token. Never log or serialize this value.",
    )
    primary_model: str = Field(
        "poolside/laguna-s-2.1:free",
        min_length=1,
        validation_alias="BRAND_MAKER_PRIMARY_MODEL",
    )
    fallback_model: str = Field(
        "anthropic/claude-sonnet-4.5",
        min_length=1,
        validation_alias="BRAND_MAKER_FALLBACK_MODEL",
    )
    judge_model: str = Field(
        "anthropic/claude-sonnet-4.5",
        min_length=1,
        validation_alias="BRAND_MAKER_JUDGE_MODEL",
    )
    image_model: str = Field(
        "google/gemini-2.5-flash-image-preview",
        min_length=1,
        validation_alias="BRAND_MAKER_IMAGE_MODEL",
        description="OpenRouter image model used for logo generation.",
    )
    request_timeout_seconds: float = Field(
        45.0,
        gt=0,
        le=120,
        validation_alias="BRAND_MAKER_REQUEST_TIMEOUT_SECONDS",
    )
    database_path: Path = Field(
        Path(".brand-maker/brands.db"),
        validation_alias="BRAND_MAKER_DATABASE_PATH",
        description="Local SQLite file containing immutable generated brand kits.",
    )
