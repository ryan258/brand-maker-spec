from pathlib import Path

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
    assert settings.judge_model == "anthropic/claude-sonnet-4.5"
    assert settings.request_timeout_seconds == 45
    assert settings.database_path == Path(".brand-maker/brands.db")


def test_settings_read_documented_environment_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "environment-key")
    monkeypatch.setenv("BRAND_MAKER_PRIMARY_MODEL", "custom/primary")
    monkeypatch.setenv("BRAND_MAKER_REQUEST_TIMEOUT_SECONDS", "12")
    monkeypatch.setenv("BRAND_MAKER_DATABASE_PATH", "/tmp/brand-maker-test.db")

    settings = Settings(_env_file=None)

    assert settings.openrouter_api_key.get_secret_value() == "environment-key"
    assert settings.primary_model == "custom/primary"
    assert settings.request_timeout_seconds == 12
    assert settings.database_path == Path("/tmp/brand-maker-test.db")
