import pytest
from pydantic import ValidationError

from brand_maker.config import Settings


def test_settings_require_non_empty_api_key() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, openrouter_api_key="")


def test_settings_use_current_model_defaults() -> None:
    settings = Settings(_env_file=None, openrouter_api_key="test-key")

    assert settings.primary_model == "poolside/laguna-s-2.1:free"
    assert settings.fallback_model == "anthropic/claude-sonnet-4.5"
    assert settings.request_timeout_seconds == 45
