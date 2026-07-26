import io
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from brand_maker.app import create_app
from brand_maker.brand_system.models import BrandSection, BrandToken, LocalOwner, WorkingDraft
from brand_maker.config import Settings
from brand_maker.publishing.developer_exports import export_draft_tokens


def test_export_draft_tokens_structures_css_json_and_tailwind() -> None:
    draft = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Aura Studio",
        owner=LocalOwner(display_name="Tester"),
        revision=1,
        sections=[
            BrandSection(
                id="section.colors",
                title="Colors",
                status="draft",
                tokens=[
                    BrandToken(
                        id="token.color.primary",
                        name="Primary Accent",
                        value_type="color",
                        value="#1e40af",
                    )
                ],
            )
        ],
    )

    exports = export_draft_tokens(draft)
    assert "tokens.css" in exports
    assert "tokens.json" in exports
    assert "tailwind.config.js" in exports

    assert "--brand-token-color-primary: #1e40af;" in exports["tokens.css"]
    assert '"#1e40af"' in exports["tokens.json"]
    assert '"token-color-primary": "#1e40af"' in exports["tailwind.config.js"]


def test_draft_css_escapes_token_values_that_could_end_a_declaration() -> None:
    draft = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Aura Studio",
        owner=LocalOwner(display_name="Tester"),
        revision=1,
        sections=[
            BrandSection(
                id="section.colors",
                title="Colors",
                status="draft",
                tokens=[
                    BrandToken(
                        id="token.color.hostile",
                        name="Hostile color",
                        value_type="color",
                        value="red; } body { color: magenta; /*",
                    )
                ],
            )
        ],
    )

    css = export_draft_tokens(draft)["tokens.css"]

    assert "red; } body" not in css
    escaped_declaration = (
        "--brand-token-color-hostile: red\\3b  \\7d  body \\7b  color: magenta\\3b  \\2f *;"
    )
    assert escaped_declaration in css


def test_draft_export_endpoints() -> None:
    with TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test.db"
        settings = Settings(database_path=db_path, openrouter_api_key="test-key")
        app = create_app(settings=settings)

        with TestClient(app) as api:
            # Create workspace
            create_res = api.post(
                "/api/brand-systems",
                json={
                    "brand_name": "Export Test Brand",
                    "owner_name": "Tester",
                },
            )
            assert create_res.status_code == 201
            brand_id = create_res.json()["brand_id"]

            # 1. Test Markdown export
            md_res = api.get(f"/api/brand-systems/{brand_id}/draft-exports/markdown")
            assert md_res.status_code == 200
            assert md_res.headers["content-type"] == "text/markdown; charset=utf-8"
            assert "Export Test Brand" in md_res.text

            # 2. Test CSS tokens export
            css_res = api.get(f"/api/brand-systems/{brand_id}/draft-exports/tokens-css")
            assert css_res.status_code == 200
            assert css_res.headers["content-type"] == "text/css; charset=utf-8"
            assert ":root {" in css_res.text

            # 3. Test JSON tokens export
            json_res = api.get(f"/api/brand-systems/{brand_id}/draft-exports/tokens-json")
            assert json_res.status_code == 200
            assert json_res.headers["content-type"] == "application/json"

            # 4. Test Tailwind export
            tw_res = api.get(f"/api/brand-systems/{brand_id}/draft-exports/tailwind")
            assert tw_res.status_code == 200
            assert "module.exports" in tw_res.text

            # 5. Test PDF export
            pdf_res = api.get(f"/api/brand-systems/{brand_id}/draft-exports/pdf")
            assert pdf_res.status_code == 200
            assert pdf_res.headers["content-type"] == "application/pdf"
            assert pdf_res.content.startswith(b"%PDF")

            # 6. Test Brand Kit (.zip) export
            kit_res = api.get(f"/api/brand-systems/{brand_id}/draft-exports/kit")
            assert kit_res.status_code == 200
            assert kit_res.headers["content-type"] == "application/zip"

            with zipfile.ZipFile(io.BytesIO(kit_res.content)) as zf:
                namelist = zf.namelist()
                assert "tokens.css" in namelist
                assert "tokens.json" in namelist
                assert "tailwind.config.js" in namelist
                assert "Export Test Brand-bible.md" in namelist
                assert "Export Test Brand-bible.pdf" in namelist


def test_asset_serving_endpoint() -> None:
    with TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test.db"
        settings = Settings(database_path=db_path, openrouter_api_key="test-key")
        app = create_app(settings=settings)

        with TestClient(app) as api:
            create_res = api.post(
                "/api/brand-systems",
                json={"brand_name": "Asset Brand", "owner_name": "Tester"},
            )
            brand_id = create_res.json()["brand_id"]

            # Upload an asset
            file_content = b"fake logo image content"
            upload_res = api.post(
                f"/api/brand-systems/{brand_id}/asset-uploads",
                data={"expected_revision": 1, "name": "Primary Logo", "required": False},
                files={"file": ("logo.png", file_content, "image/png")},
            )
            assert upload_res.status_code == 201
            draft = upload_res.json()
            asset = draft["assets"][0]
            sha = asset["content_hash"]

            # Serve asset via SHA route
            asset_res = api.get(f"/api/brand-systems/{brand_id}/assets/{sha}")
            assert asset_res.status_code == 200
            assert asset_res.content == file_content
            assert asset_res.headers["content-type"] == "image/png"
            assert asset_res.headers["content-security-policy"] == "default-src 'none'; sandbox"
            assert asset_res.headers["x-content-type-options"] == "nosniff"


def test_unicode_brand_name_headers() -> None:
    with TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test.db"
        settings = Settings(database_path=db_path, openrouter_api_key="test-key")
        app = create_app(settings=settings)

        with TestClient(app) as api:
            create_res = api.post(
                "/api/brand-systems",
                json={"brand_name": "Rocket 🚀 Studio", "owner_name": "Tester"},
            )
            assert create_res.status_code == 201
            brand_id = create_res.json()["brand_id"]

            md_res = api.get(f"/api/brand-systems/{brand_id}/draft-exports/markdown")
            assert md_res.status_code == 200
            assert (
                "filename*=UTF-8''Rocket%20%F0%9F%9A%80%20Studio-bible.md"
                in md_res.headers["content-disposition"]
            )

            pdf_res = api.get(f"/api/brand-systems/{brand_id}/draft-exports/pdf")
            assert pdf_res.status_code == 200

            kit_res = api.get(f"/api/brand-systems/{brand_id}/draft-exports/kit")
            assert kit_res.status_code == 200


def test_zip_export_path_traversal_sanitization() -> None:
    with TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test.db"
        settings = Settings(database_path=db_path, openrouter_api_key="test-key")
        app = create_app(settings=settings)

        with TestClient(app) as api:
            create_res = api.post(
                "/api/brand-systems",
                json={"brand_name": "../escape-brand", "owner_name": "Tester"},
            )
            brand_id = create_res.json()["brand_id"]

            file_content = b"vector content"
            upload_res = api.post(
                f"/api/brand-systems/{brand_id}/asset-uploads",
                data={"expected_revision": 1, "name": "../outside.svg", "required": False},
                files={"file": ("test.svg", file_content, "image/svg+xml")},
            )
            assert upload_res.status_code == 201

            api.post(
                f"/api/brand-systems/{brand_id}/asset-uploads",
                data={"expected_revision": 2, "name": "logo?.svg", "required": False},
                files={"file": ("logo1.svg", file_content, "image/svg+xml")},
            )
            api.post(
                f"/api/brand-systems/{brand_id}/asset-uploads",
                data={"expected_revision": 3, "name": "logo*.svg", "required": False},
                files={"file": ("logo2.svg", file_content, "image/svg+xml")},
            )

            kit_res = api.get(f"/api/brand-systems/{brand_id}/draft-exports/kit")
            assert kit_res.status_code == 200

            with zipfile.ZipFile(io.BytesIO(kit_res.content)) as zf:
                namelist = zf.namelist()
                for name in namelist:
                    assert ".." not in name
                assert "assets/outside.svg" in namelist
                assert "assets/logo_.svg" in namelist
                assert "assets/logo__1.svg" in namelist
                assert len(namelist) == len(set(namelist))


def test_render_brand_bible_pdf_and_csp() -> None:
    from brand_maker.brand_bible import render_brand_bible

    draft = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Test Brand",
        owner=LocalOwner(display_name="Tester"),
        revision=1,
        sections=[],
    )

    # Web Bible output (CSP clean - no inline onclick)
    web_html = render_brand_bible(draft, for_pdf=False)
    assert 'onclick="' not in web_html
    assert 'id="export-menu-btn"' in web_html

    # PDF Bible output (No cover actions or workshop.js, embedded styles)
    pdf_html = render_brand_bible(draft, for_pdf=True)
    assert '<div class="cover-actions">' not in pdf_html
    assert "workshop.js" not in pdf_html
    assert "<style>" in pdf_html


def test_comment_injection_and_token_mappings() -> None:
    draft = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Rocket\nmodule.exports.hack = 1; */",
        owner=LocalOwner(display_name="Tester"),
        revision=1,
        sections=[
            BrandSection(
                id="section.tokens",
                title="Tokens",
                status="draft",
                tokens=[
                    BrandToken(
                        id="token.foo_bar",
                        name="Foo Underscore",
                        value_type="dimension",
                        value="16px",
                    ),
                    BrandToken(
                        id="token.foo-bar",
                        name="Foo Dash",
                        value_type="duration",
                        value="200ms",
                    ),
                    BrandToken(
                        id="token.flag",
                        name="Flag",
                        value_type="boolean",
                        value="True",
                    ),
                ],
            )
        ],
    )

    exports = export_draft_tokens(draft)

    # Comment injection prevention
    assert "\nmodule.exports.hack" not in exports["tailwind.config.js"]
    header_line = exports["tokens.css"].split("\n")[0]
    comment_body = header_line.removeprefix("/* brand-system: ").removesuffix(" (draft) */")
    assert "*/" not in comment_body

    # Token ID distinction and type mappings
    assert "--brand-token-foo_bar: 16px;" in exports["tokens.css"]
    assert "--brand-token-foo-bar: 200ms;" in exports["tokens.css"]
    assert '"token-foo_bar": "16px"' in exports["tailwind.config.js"]
    assert '"token-foo-bar": "200ms"' in exports["tailwind.config.js"]
    # Boolean boolean flag token is in CSS/JSON but NOT in Tailwind spacing
    assert '"flag"' not in exports["tailwind.config.js"]


def test_early_archive_limit_check() -> None:
    from brand_maker.brand_system.models import AssetRegistration

    with TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test.db"
        settings = Settings(database_path=db_path, openrouter_api_key="test-key")
        app = create_app(settings=settings)

        with TestClient(app) as api:
            create_res = api.post(
                "/api/brand-systems",
                json={"brand_name": "Large Brand", "owner_name": "Tester"},
            )
            brand_id = create_res.json()["brand_id"]

            repo = app.state.brand_system_repository
            draft = repo.get(UUID(brand_id))
            assert draft is not None
            # Add a huge declared asset
            draft.assets.append(
                AssetRegistration(
                    id="asset.huge",
                    name="huge.zip",
                    storage="linked",
                    media_type="application/zip",
                    size_bytes=300_000_000,
                    content_hash="b" * 64,
                    source_path="/tmp/huge.zip",
                    required=True,
                )
            )
            draft.revision = 2
            repo.update(draft, expected_revision=1)

            kit_res = api.get(f"/api/brand-systems/{brand_id}/draft-exports/kit")
            assert kit_res.status_code == 413
            assert "250 MB" in kit_res.json()["detail"]
