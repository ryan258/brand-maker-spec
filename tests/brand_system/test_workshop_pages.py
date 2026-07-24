from pathlib import Path

from fastapi.testclient import TestClient

from brand_maker.app import create_app
from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
from brand_maker.config import Settings
from brand_maker.models import BrandResponse
from brand_maker.storage import SQLiteBrandRepository


class UnusedPipeline:
    async def build(self, brand_name: str) -> BrandResponse:
        raise AssertionError("workshop pages must not invoke generation")


def app_client(tmp_path: Path) -> TestClient:
    path = tmp_path / "brands.db"
    return TestClient(
        create_app(
            settings=Settings(_env_file=None, openrouter_api_key="test-key", database_path=path),
            pipeline=UnusedPipeline(),
            repository=SQLiteBrandRepository(path),
            brand_system_repository=SQLiteBrandSystemRepository(path),
        )
    )


def test_workshop_index_has_accessible_creation_and_workspace_regions(
    tmp_path: Path,
) -> None:
    with app_client(tmp_path) as client:
        response = client.get("/brand-systems")

    assert response.status_code == 200
    assert '<html lang="en">' in response.text
    assert '<a class="skip-link" href="#main-content">' in response.text
    assert '<main id="main-content">' in response.text
    assert response.text.count("<h1") == 1
    assert '<form id="workspace-form"' in response.text
    assert '<label for="workspace-name">' in response.text
    assert '<textarea id="brand-context"' in response.text
    assert 'for="brand-context">Brand context' in response.text
    assert 'aria-describedby="brand-context-help"' in response.text
    assert 'id="workspace-status" role="status" aria-live="polite"' in response.text
    assert 'id="workspace-list" aria-busy="true"' in response.text
    assert 'src="/assets/workshop.js"' in response.text


def test_workshop_detail_has_section_editor_and_safe_script(tmp_path: Path) -> None:
    with app_client(tmp_path) as client:
        created = client.post(
            "/api/brand-systems",
            json={"brand_name": "Northstar", "owner_name": "Ryan"},
        ).json()
        page = client.get(f"/brand-systems/{created['brand_id']}")
        script = client.get("/assets/workshop.js")
        styles = client.get("/assets/workshop.css")

    assert page.status_code == 200
    assert 'data-page="workshop"' in page.text
    assert f'data-brand-id="{created["brand_id"]}"' in page.text
    assert '<nav id="section-navigation" aria-label="Brand sections">' in page.text
    assert '<form id="section-form"' in page.text
    assert 'id="editor-status" role="status" aria-live="polite"' in page.text
    assert script.status_code == 200
    assert "fetch(`/api/brand-systems/${encodeURIComponent(brandId)}`)" in script.text
    assert "textContent" in script.text
    assert "innerHTML" not in script.text
    assert "eval(" not in script.text
    assert styles.status_code == 200
    assert "@media (max-width: 48rem)" in styles.text
    assert "prefers-reduced-motion" in styles.text
