from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from brand_maker.app import create_app
from brand_maker.config import Settings
from brand_maker.models import BrandResponse


class FakePipeline:
    def __init__(self, response: BrandResponse) -> None:
        self.response = response
        self.calls: list[str] = []

    async def build(self, brand_name: str) -> BrandResponse:
        self.calls.append(brand_name)
        return self.response


def test_health_reports_up_when_configuration_is_valid() -> None:
    settings = Settings(_env_file=None, openrouter_api_key="test-key")

    with TestClient(create_app(settings=settings)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "up"}


def test_app_fails_during_startup_without_api_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValidationError), TestClient(create_app()):
        pass


def test_brand_endpoint_returns_pipeline_response() -> None:
    settings = Settings(_env_file=None, openrouter_api_key="test-key")
    pipeline = FakePipeline(
        BrandResponse(status="error", message="Model provider unavailable.")
    )

    with TestClient(create_app(settings=settings, pipeline=pipeline)) as client:
        response = client.post("/brand", json={"brand_name": "Floogle"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "error",
        "kit": None,
        "message": "Model provider unavailable.",
    }
    assert pipeline.calls == ["Floogle"]


@pytest.mark.parametrize("payload", [{"brand_name": ""}, {"brand_name": "x" * 81}, {}])
def test_brand_endpoint_rejects_invalid_input_without_calling_pipeline(
    payload: dict[str, str],
) -> None:
    settings = Settings(_env_file=None, openrouter_api_key="test-key")
    pipeline = FakePipeline(
        BrandResponse(status="error", message="should never be returned")
    )

    with TestClient(create_app(settings=settings, pipeline=pipeline)) as client:
        response = client.post("/brand", json=payload)

    assert response.status_code == 422
    assert pipeline.calls == []
