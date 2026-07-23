import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from brand_maker.app import create_app
from brand_maker.config import Settings


def test_health_reports_up_when_configuration_is_valid() -> None:
    settings = Settings(_env_file=None, openrouter_api_key="test-key")

    with TestClient(create_app(settings=settings)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "up"}


def test_app_fails_during_startup_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(ValidationError), TestClient(create_app()):
        pass
