from pathlib import Path
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from brand_maker.app import create_app
from brand_maker.brand_system.publication import SQLitePublicationRepository
from brand_maker.config import Settings
from brand_maker.models import BrandResponse
from brand_maker.publishing.archive import (
    InvalidArchive,
    create_archive,
    import_archive,
    restore_archive,
)
from tests.publishing.helpers import published_version


class UnusedPipeline:
    async def build(self, brand_name: str, *, brand_context: str | None = None) -> BrandResponse:
        raise AssertionError("archive import must not invoke generation")


def test_archive_round_trips_without_original_database_or_paths(tmp_path: Path) -> None:
    published = published_version()
    archive = tmp_path / "northstar.brand.zip"

    create_archive(published, tmp_path / "source-assets", archive)
    restored = restore_archive(archive, tmp_path / "restored-assets")

    assert restored.published == published
    assert restored.rendered.amendment_revision == 0


def test_archive_import_repopulates_a_fresh_publication_database(tmp_path: Path) -> None:
    published = published_version()
    archive = tmp_path / "northstar.brand.zip"
    create_archive(published, tmp_path / "source-assets", archive)
    database = tmp_path / "restored.db"

    imported = import_archive(
        archive, asset_root=tmp_path / "restored-assets", database_path=database
    )

    assert imported.published == published
    assert (
        SQLitePublicationRepository(database).get(published.brand_id, published.version)
        == published
    )


def test_archive_import_api_restores_publication_for_normal_routes(tmp_path: Path) -> None:
    published = published_version()
    archive = tmp_path / "northstar.brand.zip"
    create_archive(published, tmp_path / "source-assets", archive)
    settings = Settings(
        _env_file=None,
        openrouter_api_key="test-key",
        database_path=tmp_path / "api-restored.db",
    )

    with TestClient(create_app(settings=settings, pipeline=UnusedPipeline())) as api:
        imported = api.post(
            "/api/brand-system-archives",
            content=archive.read_bytes(),
            headers={"Content-Type": "application/zip"},
        )
        fetched = api.get(f"/api/brand-systems/{published.brand_id}/versions/{published.version}")

    assert imported.status_code == 201
    assert fetched.status_code == 200
    assert fetched.json()["content_hash"] == published.content_hash


def test_archive_rejects_traversal_before_writing_assets(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.zip"
    with ZipFile(archive, "w") as bundle:
        bundle.writestr("../escaped.txt", "no")

    destination = tmp_path / "assets"
    with pytest.raises(InvalidArchive, match="unsafe"):
        restore_archive(archive, destination)

    assert not destination.exists()


def test_archive_rejects_checksum_changes_without_partial_restore(tmp_path: Path) -> None:
    published = published_version()
    valid = tmp_path / "valid.zip"
    create_archive(published, tmp_path / "source-assets", valid)
    damaged = tmp_path / "damaged.zip"
    with ZipFile(valid) as source, ZipFile(damaged, "w") as target:
        for item in source.infolist():
            payload = source.read(item)
            if item.filename == "archive.json":
                payload += b" "
            target.writestr(item.filename, payload)

    destination = tmp_path / "assets"
    with pytest.raises(InvalidArchive, match="checksum"):
        restore_archive(damaged, destination)

    assert not destination.exists()
