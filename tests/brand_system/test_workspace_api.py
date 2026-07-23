from pathlib import Path

from fastapi.testclient import TestClient

from brand_maker.app import create_app
from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
from brand_maker.config import Settings
from brand_maker.models import BrandKit, BrandResponse
from brand_maker.storage import SQLiteBrandRepository


class UnusedPipeline:
    async def build(self, brand_name: str) -> BrandResponse:
        raise AssertionError("workspace API must not invoke generation")


def legacy_kit() -> BrandKit:
    return BrandKit.model_validate(
        {
            "brand_name": "Floogle",
            "parody_target": "Google",
            "tagline": "Search less. Guess more.",
            "description": "A search engine that indexes vibes instead of facts.",
            "brand_voice": "Cheerful and confidently incorrect.",
            "personality": ["Playful", "Chaotic", "Helpful"],
            "color_palette": {
                "primary": "#112233",
                "secondary": "#445566",
                "accent": "#778899",
                "background": "#FFFFFF",
            },
        }
    )


def client(tmp_path: Path) -> tuple[TestClient, SQLiteBrandRepository]:
    path = tmp_path / "brands.db"
    settings = Settings(_env_file=None, openrouter_api_key="test-key", database_path=path)
    legacy = SQLiteBrandRepository(path)
    app = create_app(
        settings=settings,
        pipeline=UnusedPipeline(),
        repository=legacy,
        brand_system_repository=SQLiteBrandSystemRepository(path),
    )
    return TestClient(app), legacy


def test_create_list_and_get_local_workspace(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)

    with test_client as api:
        created = api.post(
            "/api/brand-systems",
            json={"brand_name": "Northstar Studio", "owner_name": "Ryan"},
        )
        brand_id = created.json()["brand_id"]
        detail = api.get(f"/api/brand-systems/{brand_id}")
        listing = api.get("/api/brand-systems?page=1&pageSize=12")

    assert created.status_code == 201
    assert created.json()["revision"] == 1
    assert created.json()["owner"] == {"id": "local-owner", "display_name": "Ryan"}
    assert detail.json() == created.json()
    assert listing.status_code == 200
    assert listing.json()["total_items"] == 1
    assert listing.json()["items"][0]["brand_id"] == brand_id


def test_migration_preserves_source_and_marks_missing_sections_incomplete(
    tmp_path: Path,
) -> None:
    test_client, legacy = client(tmp_path)
    source = legacy.save(legacy_kit())

    with test_client as api:
        created = api.post(
            "/api/brand-systems",
            json={"owner_name": "Ryan", "source_brand_id": str(source.id)},
        )

    assert created.status_code == 201
    payload = created.json()
    assert payload["brand_name"] == "Floogle"
    sections = {section["id"]: section for section in payload["sections"]}
    assert sections["section.messaging"]["blocks"][0]["text"] == "Search less. Guess more."
    assert sections["section.color"]["tokens"][0]["value"] == "#112233"
    assert sections["section.motion"]["status"] == "incomplete"
    assert legacy.get(source.id) == source


def test_section_update_uses_expected_revision_and_preserves_stale_state(
    tmp_path: Path,
) -> None:
    test_client, _ = client(tmp_path)

    with test_client as api:
        created = api.post(
            "/api/brand-systems",
            json={"brand_name": "Northstar", "owner_name": "Ryan"},
        ).json()
        brand_id = created["brand_id"]
        section = created["sections"][0]
        section["status"] = "draft"
        updated = api.patch(
            f"/api/brand-systems/{brand_id}/sections/{section['id']}",
            json={"expected_revision": 1, "section": section},
        )
        stale = api.patch(
            f"/api/brand-systems/{brand_id}/sections/{section['id']}",
            json={"expected_revision": 1, "section": section},
        )
        stored = api.get(f"/api/brand-systems/{brand_id}")

    assert updated.status_code == 200
    assert updated.json()["revision"] == 2
    assert stale.status_code == 409
    assert stale.json() == {"detail": "Draft revision conflict."}
    assert stored.json() == updated.json()


def test_workspace_api_rejects_invalid_pagination_and_unknown_sources(
    tmp_path: Path,
) -> None:
    test_client, _ = client(tmp_path)

    with test_client as api:
        invalid_page = api.get("/api/brand-systems?page=0&pageSize=101")
        missing_source = api.post(
            "/api/brand-systems",
            json={
                "owner_name": "Ryan",
                "source_brand_id": "d795ebf9-8f54-44a2-85cd-e73faacb7008",
            },
        )

    assert invalid_page.status_code == 422
    assert missing_source.status_code == 404
    assert missing_source.json() == {"detail": "Source brand not found."}
