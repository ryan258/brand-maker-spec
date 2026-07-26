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

    async def build(self, brand_name: str, *, brand_context: str | None = None) -> BrandResponse:
        self.calls.append(brand_name)
        return self.response


def test_root_is_an_accessible_getting_started_page() -> None:
    settings = Settings(_env_file=None, openrouter_api_key="test-key")

    with TestClient(create_app(settings=settings)) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<html lang="en">' in response.text
    assert '<a class="skip-link" href="#main-content">Skip to main content</a>' in response.text
    assert '<main id="main-content">' in response.text
    assert response.text.count("<h1") == 1
    assert 'href="/docs"' in response.text
    assert 'href="/redoc"' in response.text
    assert 'href="/health"' in response.text
    assert 'href="/brands"' in response.text
    assert "OPENROUTER_API_KEY" in response.text
    assert "POST /brand" in response.text
    assert "identity, voice, personality, and color" in response.text
    assert "personal brand operating system" in response.text.lower()
    assert "parody" not in response.text.lower()
    assert "test-key" not in response.text
    assert '<form id="brand-form"' in response.text
    assert 'input id="brand-name"' in response.text
    assert 'maxlength="80"' in response.text
    assert 'id="generation-status"' in response.text
    assert 'id="brand-results"' in response.text
    assert 'src="/assets/app.js"' in response.text
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_generation_ui_script_is_served_without_html_injection_apis() -> None:
    settings = Settings(_env_file=None, openrouter_api_key="test-key")

    with TestClient(create_app(settings=settings)) as client:
        response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/javascript")
    assert 'fetch("/api/brands"' in response.text
    assert "view-saved-brand" in response.text
    assert "A parody of" not in response.text
    assert "textContent" in response.text
    assert "innerHTML" not in response.text
    assert "eval(" not in response.text


@pytest.mark.parametrize("path", ["/docs", "/redoc"])
def test_documentation_pages_link_back_home(path: str) -> None:
    settings = Settings(_env_file=None, openrouter_api_key="test-key")

    with TestClient(create_app(settings=settings)) as client:
        response = client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert int(response.headers["content-length"]) == len(response.content)
    assert '<a class="app-home-link" href="/"' in response.text
    assert "Back to home" in response.text


def test_favicon_is_available() -> None:
    settings = Settings(_env_file=None, openrouter_api_key="test-key")

    with TestClient(create_app(settings=settings)) as client:
        response = client.get("/favicon.svg")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")


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
    pipeline = FakePipeline(BrandResponse(status="error", message="Model provider unavailable."))

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
    pipeline = FakePipeline(BrandResponse(status="error", message="should never be returned"))

    with TestClient(create_app(settings=settings, pipeline=pipeline)) as client:
        response = client.post("/brand", json=payload)

    assert response.status_code == 422
    assert pipeline.calls == []
