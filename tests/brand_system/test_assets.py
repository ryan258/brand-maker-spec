from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from brand_maker.app import create_app
from brand_maker.brand_system.assets import AssetChanged, AssetMissing, AssetStore
from brand_maker.brand_system.models import LocalOwner, WorkingDraft
from brand_maker.config import Settings
from brand_maker.models import BrandResponse


def draft() -> WorkingDraft:
    return WorkingDraft(
        brand_id=UUID("d795ebf9-8f54-44a2-85cd-e73faacb7008"),
        brand_name="Northstar",
        owner=LocalOwner(display_name="Ryan"),
        revision=1,
        sections=[],
    )


def test_managed_import_is_content_addressed_and_deduplicated(tmp_path: Path) -> None:
    source = tmp_path / "logo.svg"
    source.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
    store = AssetStore(tmp_path / "managed")

    first = store.import_managed(
        asset_id="asset.logo.primary",
        name="Primary logo",
        source=source,
        media_type="image/svg+xml",
        required=True,
    )
    second = store.import_managed(
        asset_id="asset.logo.copy",
        name="Logo copy",
        source=source,
        media_type="image/svg+xml",
        required=False,
    )

    assert first.content_hash == second.content_hash
    assert first.storage == "managed"
    assert first.source_path is None
    assert len(list((tmp_path / "managed").glob("*/*"))) == 1


def test_publication_snapshot_copies_required_linked_asset(tmp_path: Path) -> None:
    source = tmp_path / "logo.svg"
    source.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
    store = AssetStore(tmp_path / "managed")
    linked = store.register_linked(
        asset_id="asset.logo.primary",
        name="Primary logo",
        source=source,
        media_type="image/svg+xml",
        required=True,
    )
    working = draft().model_copy(update={"assets": [linked]})

    snapshot = store.prepare_publication(working)

    assert working.assets[0].storage == "linked"
    assert snapshot.assets[0].storage == "managed"
    assert snapshot.assets[0].content_hash == linked.content_hash


def test_missing_or_changed_required_link_blocks_publication(tmp_path: Path) -> None:
    source = tmp_path / "logo.svg"
    source.write_text("original", encoding="utf-8")
    store = AssetStore(tmp_path / "managed")
    linked = store.register_linked(
        asset_id="asset.logo.primary",
        name="Primary logo",
        source=source,
        media_type="image/svg+xml",
        required=True,
    )
    working = draft().model_copy(update={"assets": [linked]})
    source.write_text("changed", encoding="utf-8")

    with pytest.raises(AssetChanged):
        store.prepare_publication(working)

    source.unlink()
    with pytest.raises(AssetMissing):
        store.prepare_publication(working)


def test_asset_import_rejects_symlinks_unsupported_types_and_large_files(
    tmp_path: Path,
) -> None:
    source = tmp_path / "asset.bin"
    source.write_bytes(b"12345")
    link = tmp_path / "link.bin"
    link.symlink_to(source)
    store = AssetStore(tmp_path / "managed", max_bytes=4)

    with pytest.raises(ValueError, match="unsupported media type"):
        store.register_linked(
            asset_id="asset.bad.type",
            name="Bad",
            source=source,
            media_type="application/x-executable",
            required=True,
        )
    with pytest.raises(ValueError, match="safety limit"):
        store.register_linked(
            asset_id="asset.too.large",
            name="Large",
            source=source,
            media_type="application/octet-stream",
            required=True,
        )
    with pytest.raises(ValueError, match="symbolic links"):
        AssetStore(tmp_path / "other").register_linked(
            asset_id="asset.link",
            name="Link",
            source=link,
            media_type="application/octet-stream",
            required=True,
        )


class UnusedPipeline:
    async def build(self, brand_name: str) -> BrandResponse:
        raise AssertionError("asset registration must not invoke generation")


def test_asset_registration_api_updates_exact_workspace_revision(tmp_path: Path) -> None:
    source = tmp_path / "logo.svg"
    source.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
    settings = Settings(
        _env_file=None,
        openrouter_api_key="test-key",
        database_path=tmp_path / "brands.db",
    )
    with TestClient(create_app(settings=settings, pipeline=UnusedPipeline())) as api:
        draft_payload = api.post(
            "/api/brand-systems",
            json={"brand_name": "Northstar", "owner_name": "Ryan"},
        ).json()
        response = api.post(
            f"/api/brand-systems/{draft_payload['brand_id']}/assets",
            json={
                "expected_revision": 1,
                "id": "asset.logo.primary",
                "name": "Primary logo",
                "storage": "managed",
                "media_type": "image/svg+xml",
                "source_path": str(source),
                "required": True,
            },
        )

    assert response.status_code == 201
    assert response.json()["revision"] == 2
    assert response.json()["assets"][0]["storage"] == "managed"
