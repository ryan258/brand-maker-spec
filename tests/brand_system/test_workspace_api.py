from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from brand_maker.app import create_app
from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
from brand_maker.config import Settings
from brand_maker.models import BrandKit, BrandResponse
from brand_maker.openrouter import ProviderRefusal
from brand_maker.storage import SQLiteBrandRepository

_PNG = b"\x89PNG\r\n\x1a\n" + b"generated-logo-bytes"


class UnusedPipeline:
    async def build(self, brand_name: str) -> BrandResponse:
        raise AssertionError("workspace API must not invoke generation")


class FakeImageClient:
    def __init__(self, *, refuse: bool = False) -> None:
        self.refuse = refuse
        self.prompts: list[str] = []

        self.references: list[tuple[bytes, str] | None] = []

    async def generate(
        self,
        *,
        prompt: str,
        model: str,
        reference: tuple[bytes, str] | None = None,
        aspect_ratio: str | None = None,
        background: str | None = None,
    ) -> tuple[bytes, str]:
        self.prompts.append(prompt)
        self.references.append(reference)
        if self.refuse:
            raise ProviderRefusal("declined")
        return _PNG, "image/png"


def logo_png() -> bytes:
    image = Image.new("RGBA", (64, 32), (255, 255, 255, 0))
    for x in range(16, 48):
        for y in range(8, 24):
            image.putpixel((x, y), (17, 34, 51, 255))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


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


def client(
    tmp_path: Path, image_client: object | None = None
) -> tuple[TestClient, SQLiteBrandRepository]:
    path = tmp_path / "brands.db"
    settings = Settings(_env_file=None, openrouter_api_key="test-key", database_path=path)
    legacy = SQLiteBrandRepository(path)
    app = create_app(
        settings=settings,
        pipeline=UnusedPipeline(),
        repository=legacy,
        brand_system_repository=SQLiteBrandSystemRepository(path),
        image_client=image_client,  # type: ignore[arg-type]
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


def test_workspace_preserves_optional_long_form_brand_context(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)
    context = (
        "We serve independent neighborhood bookstores.\n\n"
        "The brand should feel literate and warm without becoming nostalgic."
    )

    with test_client as api:
        created = api.post(
            "/api/brand-systems",
            json={
                "brand_name": "Northstar Studio",
                "brand_context": f"  {context}  ",
                "owner_name": "Ryan",
            },
        )
        fetched = api.get(f"/api/brand-systems/{created.json()['brand_id']}")

    assert created.status_code == 201
    assert created.json()["brand_context"] == context
    assert fetched.json()["brand_context"] == context


def test_workspace_rejects_whitespace_only_or_oversized_context(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)

    with test_client as api:
        whitespace = api.post(
            "/api/brand-systems",
            json={
                "brand_name": "Northstar",
                "brand_context": "   ",
                "owner_name": "Ryan",
            },
        )
        oversized = api.post(
            "/api/brand-systems",
            json={
                "brand_name": "Northstar",
                "brand_context": "x" * 50_001,
                "owner_name": "Ryan",
            },
        )

    assert whitespace.status_code == 422
    assert oversized.status_code == 422


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


def test_asset_upload_stores_managed_file_and_bumps_revision(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)

    with test_client as api:
        brand_id = api.post(
            "/api/brand-systems",
            json={"brand_name": "Northstar", "owner_name": "Ryan"},
        ).json()["brand_id"]
        png = b"\x89PNG\r\n\x1a\n" + b"pixels"
        uploaded = api.post(
            f"/api/brand-systems/{brand_id}/asset-uploads",
            data={"expected_revision": 1, "name": "Primary logo", "required": "true"},
            files={"file": ("logo.png", png, "image/png")},
        )
        stale = api.post(
            f"/api/brand-systems/{brand_id}/asset-uploads",
            data={"expected_revision": 1, "name": "Second try", "required": "false"},
            files={"file": ("logo.png", png, "image/png")},
        )
        rejected = api.post(
            f"/api/brand-systems/{brand_id}/asset-uploads",
            data={"expected_revision": 2, "name": "Script", "required": "true"},
            files={"file": ("evil.exe", b"MZ", "application/x-msdownload")},
        )

    assert uploaded.status_code == 201
    body = uploaded.json()
    assert body["revision"] == 2
    asset = body["assets"][0]
    assert asset["storage"] == "managed"
    assert asset["media_type"] == "image/png"
    assert asset["source_path"] is None  # managed copy carries no host path
    assert stale.status_code == 409  # expected_revision is now 2, not 1
    assert rejected.status_code == 422


def test_section_patch_persists_manually_authored_rules_tokens_examples_patterns(
    tmp_path: Path,
) -> None:
    test_client, _ = client(tmp_path)

    with test_client as api:
        created = api.post(
            "/api/brand-systems",
            json={"brand_name": "Northstar", "owner_name": "Ryan"},
        ).json()
        brand_id = created["brand_id"]
        section = next(s for s in created["sections"] if not s["locked"])
        section["rules"] = [
            {
                "id": f"rule.{section['id'].split('.')[-1]}.one",
                "name": "Tell the truth",
                "description": "No hype.",
                "enforcement": "blocking",
                "references": [],
            }
        ]
        section["tokens"] = [
            {
                "id": f"token.{section['id'].split('.')[-1]}.brand",
                "name": "Brand color",
                "value_type": "color",
                "value": "#112233",
                "references": [],
            }
        ]
        section["examples"] = [
            {
                "id": f"example.{section['id'].split('.')[-1]}.do",
                "kind": "do",
                "text": "Say it plainly.",
                "references": [],
            }
        ]
        section["patterns"] = [
            {
                "id": f"pattern.{section['id'].split('.')[-1]}.voice",
                "name": "Say / never say",
                "kind": "say_never_say",
                "summary": "Concrete language choices.",
                "specifications": [{"label": "Say", "value": "Plain words."}],
                "do_guidance": ["Be direct."],
                "dont_guidance": ["Avoid jargon."],
                "references": [],
            }
        ]
        saved = api.patch(
            f"/api/brand-systems/{brand_id}/sections/{section['id']}",
            json={"expected_revision": 1, "section": section},
        )
        bible = api.get(f"/brand-systems/{brand_id}/bible")

    assert saved.status_code == 200
    stored = next(s for s in saved.json()["sections"] if s["id"] == section["id"])
    assert stored["rules"][0]["name"] == "Tell the truth"
    assert stored["tokens"][0]["value"] == "#112233"
    assert stored["examples"][0]["text"] == "Say it plainly."
    assert stored["patterns"][0]["do_guidance"] == ["Be direct."]
    assert "Tell the truth" in bible.text  # renders on the living bible page


def test_logo_generation_stores_managed_asset_from_brand_tokens(tmp_path: Path) -> None:
    fake = FakeImageClient()
    test_client, _ = client(tmp_path, image_client=fake)

    with test_client as api:
        brand_id = api.post(
            "/api/brand-systems",
            json={
                "brand_name": "Northstar",
                "brand_context": "Independent bookstores.",
                "owner_name": "Ryan",
            },
        ).json()["brand_id"]
        generated = api.post(
            f"/api/brand-systems/{brand_id}/logo-generations",
            json={"expected_revision": 1, "instructions": "line mark"},
        )

    assert generated.status_code == 201
    body = generated.json()
    assert body["revision"] == 2
    asset = body["assets"][0]
    assert asset["storage"] == "managed"
    assert asset["media_type"] == "image/png"
    assert asset["required"] is False
    # The prompt is built from the brand's own name/context, not caller-controlled markup.
    assert "Northstar" in fake.prompts[0]
    assert "Independent bookstores." in fake.prompts[0]
    assert "line mark" in fake.prompts[0]


def test_logo_generation_returns_503_when_image_client_unconfigured(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)  # no image client injected

    with test_client as api:
        brand_id = api.post(
            "/api/brand-systems",
            json={"brand_name": "Northstar", "owner_name": "Ryan"},
        ).json()["brand_id"]
        response = api.post(
            f"/api/brand-systems/{brand_id}/logo-generations",
            json={"expected_revision": 1},
        )

    assert response.status_code == 503


def test_logo_generation_maps_model_refusal_to_422(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path, image_client=FakeImageClient(refuse=True))

    with test_client as api:
        brand_id = api.post(
            "/api/brand-systems",
            json={"brand_name": "Northstar", "owner_name": "Ryan"},
        ).json()["brand_id"]
        response = api.post(
            f"/api/brand-systems/{brand_id}/logo-generations",
            json={"expected_revision": 1},
        )

    assert response.status_code == 422


def test_favicon_set_and_vectorization_append_managed_derivatives_atomically(
    tmp_path: Path,
) -> None:
    test_client, _ = client(tmp_path)

    with test_client as api:
        brand_id = api.post(
            "/api/brand-systems",
            json={"brand_name": "Northstar", "owner_name": "Ryan"},
        ).json()["brand_id"]
        uploaded = api.post(
            f"/api/brand-systems/{brand_id}/asset-uploads",
            data={"expected_revision": 1, "name": "Primary logo", "required": "false"},
            files={"file": ("logo.png", logo_png(), "image/png")},
        ).json()
        source_id = uploaded["assets"][0]["id"]
        icons = api.post(
            f"/api/brand-systems/{brand_id}/assets/{source_id}/favicon-sets",
            json={"expected_revision": 2},
        )
        vector = api.post(
            f"/api/brand-systems/{brand_id}/assets/{source_id}/vectorizations",
            json={"expected_revision": 3},
        )

    assert icons.status_code == 201
    assert icons.json()["revision"] == 3
    icon_assets = icons.json()["assets"][1:]
    assert len(icon_assets) == 6
    assert all(item["storage"] == "managed" for item in icon_assets)
    assert [item["name"] for item in icon_assets] == [
        "Primary logo — favicon 16",
        "Primary logo — favicon 32",
        "Primary logo — favicon 48",
        "Primary logo — apple touch icon 180",
        "Primary logo — app icon 192",
        "Primary logo — app icon 512",
    ]
    assert vector.status_code == 201
    assert vector.json()["revision"] == 4
    assert vector.json()["assets"][-1]["media_type"] == "image/svg+xml"
    assert vector.json()["assets"][-1]["name"] == "Primary logo — vector"


def test_ai_logo_variants_use_selected_source_reference(tmp_path: Path) -> None:
    fake = FakeImageClient()
    test_client, _ = client(tmp_path, image_client=fake)

    with test_client as api:
        brand_id = api.post(
            "/api/brand-systems",
            json={"brand_name": "Northstar", "owner_name": "Ryan"},
        ).json()["brand_id"]
        uploaded = api.post(
            f"/api/brand-systems/{brand_id}/asset-uploads",
            data={"expected_revision": 1, "name": "Primary logo", "required": "false"},
            files={"file": ("logo.png", logo_png(), "image/png")},
        ).json()
        source_id = uploaded["assets"][0]["id"]
        variants = api.post(
            f"/api/brand-systems/{brand_id}/assets/{source_id}/logo-variant-sets",
            json={"expected_revision": 2},
        )

    assert variants.status_code == 201
    assert variants.json()["revision"] == 3
    assert [item["name"] for item in variants.json()["assets"][1:]] == [
        "Primary logo — monochrome",
        "Primary logo — inverted",
        "Primary logo — horizontal lockup",
        "Primary logo — icon only",
    ]
    assert len(fake.references) == 4
    assert all(reference == (logo_png(), "image/png") for reference in fake.references)


def test_logo_derivatives_reject_unknown_stale_and_non_raster_sources(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)

    with test_client as api:
        brand_id = api.post(
            "/api/brand-systems",
            json={"brand_name": "Northstar", "owner_name": "Ryan"},
        ).json()["brand_id"]
        uploaded = api.post(
            f"/api/brand-systems/{brand_id}/asset-uploads",
            data={"expected_revision": 1, "name": "Broken", "required": "false"},
            files={"file": ("broken.png", b"not an image", "image/png")},
        ).json()
        source_id = uploaded["assets"][0]["id"]
        stale = api.post(
            f"/api/brand-systems/{brand_id}/assets/{source_id}/favicon-sets",
            json={"expected_revision": 1},
        )
        malformed = api.post(
            f"/api/brand-systems/{brand_id}/assets/{source_id}/favicon-sets",
            json={"expected_revision": 2},
        )
        missing = api.post(
            f"/api/brand-systems/{brand_id}/assets/asset.logo.missing/vectorizations",
            json={"expected_revision": 2},
        )

    assert stale.status_code == 409
    assert malformed.status_code == 422
    assert missing.status_code == 404


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
