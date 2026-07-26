"""API integration tests for Personal Brand OS enhancements (8 new routes)."""

from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from PIL import Image

from brand_maker.app import create_app
from brand_maker.brand_system.assets import AssetStore
from brand_maker.brand_system.models import (
    BrandRule,
    BrandSection,
    BrandToken,
    LocalOwner,
    WorkingDraft,
)
from brand_maker.brand_system.repository import SQLiteBrandSystemRepository, StaleDraftRevision
from brand_maker.config import Settings
from brand_maker.generation.repository import SQLiteGenerationRepository
from brand_maker.storage import SQLiteBrandRepository


class DummyCompleter:
    async def complete(
        self, *, messages: list[dict[str, str]], model: str, temperature: float, max_tokens: int
    ) -> str:
        import json
        return json.dumps({
            "prompt_version": "living-brand-section-v2",
            "section_id": "section.strategy",
            "rationale": "Generated valid variant.",
            "section": {
                "id": "section.strategy",
                "title": "Strategy",
                "status": "draft",
                "blocks": [
                    {"id": "block.strat.1", "type": "paragraph", "text": "Narrative block 1."},
                    {"id": "block.strat.2", "type": "paragraph", "text": "Narrative block 2."},
                ],
                "rules": [
                    {
                        "id": "rule.strat.1",
                        "name": "Be authentic",
                        "description": "Always remain true to vision.",
                        "enforcement": "advisory",
                    }
                ],
                "tokens": [],
                "examples": [
                    {"id": "example.strat.1", "kind": "do", "text": "Sample do example."},
                    {"id": "example.strat.2", "kind": "dont", "text": "Sample dont example."},
                ],
                "patterns": [
                    {
                        "id": "pattern.strat.1",
                        "name": "Positioning Framework",
                        "kind": "positioning_framework",
                        "summary": "Core positioning framework.",
                        "specifications": [{"label": "Target", "value": "Audience"}],
                        "do_guidance": ["Do focus on clarity."],
                        "dont_guidance": ["Don't use jargon."],
                    },
                    {
                        "id": "pattern.strat.2",
                        "name": "Audience Profile",
                        "kind": "audience_profile",
                        "summary": "Target audience profile.",
                        "specifications": [{"label": "Persona", "value": "Creator"}],
                        "do_guidance": ["Do speak directly."],
                        "dont_guidance": ["Don't generalize."],
                    },
                ],
            },
        })


class UnusedPipeline:
    async def build(self, brand_name: str):
        raise AssertionError("Must not invoke generation")


def create_test_woff2() -> bytes:
    builder = FontBuilder(1024, isTTF=True)
    builder.setupGlyphOrder([".notdef"])
    pen = TTGlyphPen(None)
    builder.setupGlyf({".notdef": pen.glyph()})
    builder.setupHorizontalMetrics({".notdef": (500, 0)})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupCharacterMap({})
    builder.setupNameTable(
        {
            "familyName": "Test Font",
            "styleName": "Regular",
            "uniqueFontIdentifier": "Test Font Regular",
            "fullName": "Test Font Regular",
            "psName": "Test-Font-Regular",
        }
    )
    builder.setupOS2(
        sTypoAscender=800,
        sTypoDescender=-200,
        usWinAscent=800,
        usWinDescent=200,
    )
    builder.setupPost()
    builder.setupMaxp()
    builder.font.flavor = "woff2"
    output = BytesIO()
    builder.save(output)
    return output.getvalue()


@pytest.fixture
def client(tmp_path: Path):
    db_path = tmp_path / "test.db"
    assets_root = tmp_path / "assets"
    assets_root.mkdir()
    settings = Settings(
        openrouter_api_key="test-key",
        database_path=db_path,
        assets_directory=assets_root,
    )
    workspaces = SQLiteBrandSystemRepository(db_path)
    runs = SQLiteGenerationRepository(db_path)
    asset_store = AssetStore(assets_root)
    completer = DummyCompleter()

    app = create_app(
        settings=settings,
        pipeline=UnusedPipeline(),  # type: ignore[arg-type]
        image_client=None,
        repository=SQLiteBrandRepository(db_path),
        brand_system_repository=workspaces,
        generation_completer=completer,  # type: ignore[arg-type]
    )
    return TestClient(app), workspaces, runs, asset_store


def test_copy_compliance_route(client):
    tc, workspaces, _, _ = client
    workspace = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Fieldwell",
        owner=LocalOwner(display_name="Test Owner"),
        revision=1,
        sections=[
            BrandSection(
                id="section.strategy",
                title="Strategy",
                status="draft",
                rules=[
                    BrandRule(
                        id="rule.id.1",
                        name="No Parody",
                        description="Never say parody in marketing text.",
                        enforcement="blocking",
                    )
                ],
            )
        ],
    )
    workspaces.create(workspace)

    with tc as api:
        response = api.post(
            f"/api/brand-systems/{workspace.brand_id}/compliance/check-copy",
            json={"copy_text": "This is a parody joke system."},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["overall_status"] == "fail"
        assert len(body["violations"]) == 1


def test_token_collisions_route(client):
    tc, workspaces, _, _ = client
    section1 = BrandSection(
        id="section.identity",
        title="Identity",
        status="draft",
        tokens=[
            BrandToken(
                id="token.color.primary",
                name="Primary Green",
                value_type="color",
                value="#1b4d3e",
            )
        ],
    )
    workspace = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Fieldwell",
        owner=LocalOwner(display_name="Test Owner"),
        revision=1,
        sections=[section1],
    )
    workspaces.create(workspace)

    with tc as api:
        response = api.get(f"/api/brand-systems/{workspace.brand_id}/token-collisions")
        assert response.status_code == 200
        body = response.json()
        assert "collisions" in body


def test_wcag_audit_route(client):
    tc, workspaces, _, _ = client
    workspace = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Fieldwell",
        owner=LocalOwner(display_name="Test Owner"),
        revision=1,
        sections=[
            BrandSection(
                id="section.identity",
                title="Identity",
                status="draft",
                tokens=[
                    BrandToken(
                        id="token.color.primary",
                        name="Primary Text",
                        value_type="color",
                        value="#1b4d3e",
                    ),
                    BrandToken(
                        id="token.color.paper.light",
                        name="Paper Background",
                        value_type="color",
                        value="#ffffff",
                    ),
                ],
            )
        ],
    )
    workspaces.create(workspace)

    with tc as api:
        response = api.get(f"/api/brand-systems/{workspace.brand_id}/wcag-audit")
        assert response.status_code == 200
        body = response.json()
        assert len(body["findings"]) >= 1


def test_font_upload_route_success(client):
    tc, workspaces, _, _ = client
    workspace = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Fieldwell",
        owner=LocalOwner(display_name="Test Owner"),
        revision=1,
    )
    workspaces.create(workspace)

    woff2_bytes = create_test_woff2()
    files = {"file": ("custom-font.woff2", woff2_bytes, "font/woff2")}
    data = {"font_family": "Custom Sans", "expected_revision": "1"}

    with tc as api:
        response = api.post(
            f"/api/brand-systems/{workspace.brand_id}/fonts",
            files=files,
            data=data,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["font_family"] == "Custom Sans"
        assert body["asset"]["media_type"] == "font/woff2"
        assert "@font-face" in body["font_face_css"]


def test_font_upload_normalizes_spoofed_media_type(client):
    tc, workspaces, _, _ = client
    workspace = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Fieldwell",
        owner=LocalOwner(display_name="Test Owner"),
        revision=1,
    )
    workspaces.create(workspace)

    with tc as api:
        response = api.post(
            f"/api/brand-systems/{workspace.brand_id}/fonts",
            files={"file": ("custom-font.png", create_test_woff2(), "image/png")},
            data={"font_family": "Custom Sans", "expected_revision": "1"},
        )

    assert response.status_code == 200
    assert response.json()["asset"]["media_type"] == "font/woff2"
    assert "format('woff2')" in response.json()["font_face_css"]


def test_font_upload_rejects_family_without_safe_characters(client, tmp_path: Path):
    tc, workspaces, _, _ = client
    workspace = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Fieldwell",
        owner=LocalOwner(display_name="Test Owner"),
        revision=1,
    )
    workspaces.create(workspace)

    with tc as api:
        response = api.post(
            f"/api/brand-systems/{workspace.brand_id}/fonts",
            files={"file": ("custom-font.woff2", create_test_woff2(), "font/woff2")},
            data={"font_family": "!!!", "expected_revision": "1"},
        )

    assert response.status_code == 422
    assert [path for path in (tmp_path / "assets").rglob("*") if path.is_file()] == []


def test_stale_font_upload_does_not_leave_orphaned_blob(client, tmp_path: Path, monkeypatch):
    tc, workspaces, _, _ = client
    workspace = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Fieldwell",
        owner=LocalOwner(display_name="Test Owner"),
        revision=1,
    )
    workspaces.create(workspace)

    def reject_concurrent_update(*args, **kwargs):
        raise StaleDraftRevision

    monkeypatch.setattr(workspaces, "update", reject_concurrent_update)

    with tc as api:
        response = api.post(
            f"/api/brand-systems/{workspace.brand_id}/fonts",
            files={"file": ("custom-font.woff2", create_test_woff2(), "font/woff2")},
            data={"font_family": "Custom Sans", "expected_revision": "1"},
        )

    assert response.status_code == 409, response.text
    assert [path for path in (tmp_path / "assets").rglob("*") if path.is_file()] == []


def test_font_upload_route_invalid_header(client):
    tc, workspaces, _, _ = client
    workspace = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Fieldwell",
        owner=LocalOwner(display_name="Test Owner"),
        revision=1,
    )
    workspaces.create(workspace)

    files = {"file": ("invalid.woff2", b"NOTAFONTFILE", "font/woff2")}
    data = {"font_family": "Bad Font"}

    with tc as api:
        response = api.post(
            f"/api/brand-systems/{workspace.brand_id}/fonts",
            files=files,
            data=data,
        )
        assert response.status_code == 422
        assert "Invalid font magic bytes" in response.json()["detail"]


def test_logo_contrast_route_success(client, tmp_path: Path):
    tc, workspaces, _, asset_store = client

    # Create PNG logo asset
    img = Image.new("RGBA", (100, 100), (27, 77, 62, 255))
    buf = BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    temp_path = tmp_path / "logo.png"
    temp_path.write_bytes(png_bytes)

    registration = asset_store.import_managed(
        asset_id="asset.logo.primary",
        name="primary-logo.png",
        source=temp_path,
        media_type="image/png",
        required=False,
    )

    workspace = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Fieldwell",
        owner=LocalOwner(display_name="Test Owner"),
        revision=1,
        assets=[registration],
    )
    workspaces.create(workspace)

    with tc as api:
        response = api.get(f"/api/brand-systems/{workspace.brand_id}/logo-contrast-check")
        assert response.status_code == 200
        body = response.json()
        assert len(body["results"]) >= 1


def test_field_regeneration_route(client):
    tc, workspaces, _, _ = client
    workspace = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Fieldwell",
        owner=LocalOwner(display_name="Test Owner"),
        revision=1,
    )
    workspaces.create(workspace)

    with tc as api:
        response = api.post(
            f"/api/brand-systems/{workspace.brand_id}/sections/section.strategy/fields/regenerate",
            json={"field_label": "narrative", "current_text": "Original text"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "text" in body
        assert "rationale" in body


def test_variants_generation_route(client):
    tc, workspaces, _, _ = client
    workspace = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Fieldwell",
        owner=LocalOwner(display_name="Test Owner"),
        revision=1,
    )
    workspaces.create(workspace)

    with tc as api:
        response = api.post(
            f"/api/brand-systems/{workspace.brand_id}/sections/section.strategy/variants",
            json={"postures": ["balanced"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert "variants" in body
        assert len(body["variants"]) >= 1


@pytest.mark.parametrize(
    "postures",
    [
        ["conservative", "balanced", "bold", "balanced"],
        ["reckless"],
    ],
)
def test_variants_generation_route_rejects_unbounded_or_unknown_postures(client, postures):
    tc, workspaces, _, _ = client
    workspace = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Fieldwell",
        owner=LocalOwner(display_name="Test Owner"),
        revision=1,
    )
    workspaces.create(workspace)

    with tc as api:
        response = api.post(
            f"/api/brand-systems/{workspace.brand_id}/sections/section.strategy/variants",
            json={"postures": postures},
        )

    assert response.status_code == 422


def test_generation_stream_rejects_unknown_run(client):
    tc, _, _, _ = client

    with tc as api:
        response = api.get(f"/api/generation-runs/{uuid4()}/stream")

    assert response.status_code == 404
