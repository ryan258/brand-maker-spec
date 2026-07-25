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
    assert 'for="brand-context">What do you already know?' in response.text
    assert 'aria-describedby="brand-context-help"' in response.text
    assert 'id="workspace-status" role="status" aria-live="polite"' in response.text
    assert 'id="workspace-list" aria-busy="true"' in response.text
    for entry_path in ("raw_idea", "named_concept", "existing_project"):
        assert f'name="entry-path" value="{entry_path}"' in response.text
    for mode in ("advisor", "copilot", "autonomous"):
        assert f'name="assistance-mode" value="{mode}"' in response.text
    assert 'name="research-mode" value="local_only"' in response.text
    assert 'name="research-mode" value="controlled"' in response.text
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
    assert '<label for="derivative-source">Source raster logo</label>' in page.text
    assert 'id="create-favicon-set" type="button"' in page.text
    assert 'id="create-logo-variants" type="button"' in page.text
    assert 'id="create-vector" type="button"' in page.text
    assert 'id="derivative-status" role="status" aria-live="polite"' in page.text
    assert script.status_code == 200
    assert "fetch(`/api/brand-systems/${encodeURIComponent(brandId)}`)" in script.text
    assert 'get("sourceBrandId")' in script.text
    assert "source_brand_id:sourceBrandId||null" in script.text
    assert 'entry_path:sourceBrandId?"quick_start"' in script.text
    assert 'document.querySelector(\'input[name="assistance-mode"]:checked\')' in script.text
    assert "textContent" in script.text
    assert "innerHTML" not in script.text
    assert "eval(" not in script.text
    assert 'createDerivatives("favicon-sets"' in script.text
    assert 'createDerivatives("logo-variant-sets"' in script.text
    assert 'createDerivatives("vectorizations"' in script.text
    assert styles.status_code == 200
    assert "@media (max-width: 48rem)" in styles.text
    assert "prefers-reduced-motion" in styles.text


def test_workshop_authoring_affordances_are_present(tmp_path: Path) -> None:
    with app_client(tmp_path) as client:
        created = client.post(
            "/api/brand-systems",
            json={"brand_name": "Northstar", "owner_name": "Ryan"},
        ).json()
        page = client.get(f"/brand-systems/{created['brand_id']}")
        script = client.get("/assets/workshop.js")

    # The logo generator must sit above the section editor, not below it.
    assert page.text.index('id="logo-form"') < page.text.index('id="section-form"')
    assert '<details class="content-group" open data-add="add-paragraph">' in page.text
    assert '<progress id="section-completeness" max="5" value="0"' in page.text
    for group in ("block", "rule", "token", "example", "pattern"):
        assert f'id="count-{group}-editors"' in page.text
    assert 'thumb.className="asset-thumb"' in script.text
    assert "Duplicate" in script.text
    assert "Move up" in script.text
    assert "dragstart" in script.text


def test_asset_content_is_served_sandboxed_for_thumbnails(tmp_path: Path) -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"pixels"

    with app_client(tmp_path) as client:
        brand_id = client.post(
            "/api/brand-systems",
            json={"brand_name": "Northstar", "owner_name": "Ryan"},
        ).json()["brand_id"]
        asset = client.post(
            f"/api/brand-systems/{brand_id}/asset-uploads",
            data={"expected_revision": 1, "name": "Primary logo", "required": "true"},
            files={"file": ("logo.png", png, "image/png")},
        ).json()["assets"][0]
        served = client.get(f"/api/brand-systems/{brand_id}/assets/{asset['id']}/content")
        missing = client.get(f"/api/brand-systems/{brand_id}/assets/asset.nope/content")

    assert served.status_code == 200
    assert served.content == png
    assert served.headers["content-type"] == "image/png"
    assert served.headers["content-security-policy"] == "default-src 'none'; sandbox"
    assert served.headers["x-content-type-options"] == "nosniff"
    assert missing.status_code == 404
