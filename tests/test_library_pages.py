from pathlib import Path

from fastapi.testclient import TestClient

from brand_maker.app import create_app
from brand_maker.config import Settings
from brand_maker.models import BrandKit, BrandResponse
from brand_maker.storage import SQLiteBrandRepository


class UnusedPipeline:
    async def build(self, brand_name: str, *, brand_context: str | None = None) -> BrandResponse:
        return BrandResponse(status="error", message="unused")


def kit() -> BrandKit:
    return BrandKit.model_validate(
        {
            "brand_name": "Floogle",
            "parody_target": "Google",
            "tagline": "Search less. Guess more.",
            "description": "A search engine that indexes vibes instead of facts.",
            "brand_voice": "Cheerful, confident, and technically wrong on purpose.",
            "personality": ["Playful", "Chaotic", "Helpful"],
            "color_palette": {
                "primary": "#4285F4",
                "secondary": "#EA4335",
                "accent": "#FBBC05",
                "background": "#FFFFFF",
            },
        }
    )


def app_client(tmp_path: Path) -> tuple[TestClient, SQLiteBrandRepository]:
    store = SQLiteBrandRepository(tmp_path / "brands.db")
    settings = Settings(_env_file=None, openrouter_api_key="test-key")
    app = create_app(settings=settings, pipeline=UnusedPipeline(), repository=store)
    return TestClient(app), store


def test_library_page_has_accessible_collection_shell(tmp_path: Path) -> None:
    client, _ = app_client(tmp_path)

    with client:
        response = client.get("/brands")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<body data-page="library">' in response.text
    assert response.text.count("<h1") == 1
    assert 'id="brand-library"' in response.text
    assert 'href="/#brand-form"' in response.text
    assert 'src="/assets/library.js"' in response.text
    assert 'href="/assets/library.css"' in response.text


def test_saved_brand_has_a_full_detail_page(tmp_path: Path) -> None:
    client, store = app_client(tmp_path)
    saved = store.save(kit())

    with client:
        response = client.get(f"/brands/{saved.id}")

    assert response.status_code == 200
    assert f'data-brand-id="{saved.id}"' in response.text
    assert '<body data-page="detail"' in response.text
    assert response.text.count("<h1") == 1
    assert 'id="brand-detail"' in response.text
    assert 'href="/brands"' in response.text


def test_unknown_brand_detail_page_returns_404(tmp_path: Path) -> None:
    client, _ = app_client(tmp_path)

    with client:
        response = client.get("/brands/7b48b1ac-95e3-4fab-bf83-b7009ee2f6c4")

    assert response.status_code == 404
    assert "Brand not found" in response.text


def test_library_assets_are_safe_and_dependency_free(tmp_path: Path) -> None:
    client, _ = app_client(tmp_path)

    with client:
        script = client.get("/assets/library.js")
        styles = client.get("/assets/library.css")

    assert script.status_code == 200
    assert script.headers["content-type"].startswith("text/javascript")
    assert 'fetch("/api/brands' in script.text
    assert "textContent" in script.text
    assert "innerHTML" not in script.text
    assert "Parody of" not in script.text
    assert "eval(" not in script.text
    assert "Build complete brand bible" in script.text
    assert "/brand-systems?sourceBrandId=" in script.text
    assert styles.status_code == 200
    assert styles.headers["content-type"].startswith("text/css")
