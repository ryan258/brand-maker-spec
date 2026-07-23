from pathlib import Path

from fastapi.testclient import TestClient

from brand_maker.app import create_app
from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
from brand_maker.config import Settings
from brand_maker.models import BrandResponse
from brand_maker.storage import SQLiteBrandRepository


class UnusedPipeline:
    async def build(self, brand_name: str) -> BrandResponse:
        raise AssertionError("editing must not invoke generation")


def client(tmp_path: Path) -> TestClient:
    path = tmp_path / "brands.db"
    return TestClient(
        create_app(
            settings=Settings(_env_file=None, openrouter_api_key="test-key", database_path=path),
            pipeline=UnusedPipeline(),
            repository=SQLiteBrandRepository(path),
            brand_system_repository=SQLiteBrandSystemRepository(path),
        )
    )


def test_impact_preview_identifies_changed_and_dependent_ids(tmp_path: Path) -> None:
    with client(tmp_path) as api:
        draft = api.post(
            "/api/brand-systems",
            json={"brand_name": "Northstar", "owner_name": "Ryan"},
        ).json()
        strategy = draft["sections"][0]
        strategy["blocks"] = [
            {
                "id": "block.strategy.purpose",
                "type": "paragraph",
                "text": "Clear purpose.",
                "references": [],
                "heading_level": None,
            }
        ]
        preview = api.post(
            f"/api/brand-systems/{draft['brand_id']}/sections/{strategy['id']}/impact",
            json={"expected_revision": 1, "section": strategy},
        )

    assert preview.status_code == 200
    assert preview.json()["can_apply"] is True
    assert "section.strategy" in preview.json()["changed_ids"]
    assert "block.strategy.purpose" in preview.json()["changed_ids"]
    assert preview.json()["blocking_errors"] == []


def test_invalid_graph_edit_is_rejected_without_changing_stored_draft(
    tmp_path: Path,
) -> None:
    with client(tmp_path) as api:
        draft = api.post(
            "/api/brand-systems",
            json={"brand_name": "Northstar", "owner_name": "Ryan"},
        ).json()
        strategy = draft["sections"][0]
        strategy["blocks"] = [
            {
                "id": "block.strategy.purpose",
                "type": "paragraph",
                "text": "Clear purpose.",
                "references": [{"kind": "rule", "target_id": "rule.missing"}],
                "heading_level": None,
            }
        ]
        update = api.patch(
            f"/api/brand-systems/{draft['brand_id']}/sections/{strategy['id']}",
            json={"expected_revision": 1, "section": strategy},
        )
        stored = api.get(f"/api/brand-systems/{draft['brand_id']}")

    assert update.status_code == 422
    assert update.json() == {"detail": "Section update violates canonical validation."}
    assert stored.json()["revision"] == 1
    assert stored.json()["sections"][0]["blocks"] == []


def test_locked_section_requires_explicit_overwrite_confirmation(tmp_path: Path) -> None:
    with client(tmp_path) as api:
        draft = api.post(
            "/api/brand-systems",
            json={"brand_name": "Northstar", "owner_name": "Ryan"},
        ).json()
        strategy = draft["sections"][0]
        strategy["locked"] = True
        locked = api.patch(
            f"/api/brand-systems/{draft['brand_id']}/sections/{strategy['id']}",
            json={"expected_revision": 1, "section": strategy},
        ).json()
        locked["sections"][0]["status"] = "draft"
        rejected = api.patch(
            f"/api/brand-systems/{draft['brand_id']}/sections/{strategy['id']}",
            json={"expected_revision": 2, "section": locked["sections"][0]},
        )
        accepted = api.patch(
            f"/api/brand-systems/{draft['brand_id']}/sections/{strategy['id']}",
            json={
                "expected_revision": 2,
                "section": locked["sections"][0],
                "confirm_locked": True,
            },
        )

    assert rejected.status_code == 409
    assert rejected.json() == {"detail": "Section is locked; confirmation required."}
    assert accepted.status_code == 200
    assert accepted.json()["revision"] == 3
