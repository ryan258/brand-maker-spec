from pathlib import Path

from fastapi.testclient import TestClient

from brand_maker.app import create_app
from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
from brand_maker.config import Settings
from brand_maker.models import BrandResponse
from brand_maker.storage import SQLiteBrandRepository


class UnusedPipeline:
    async def build(self, brand_name: str, *, brand_context: str | None = None) -> BrandResponse:
        raise AssertionError("publication must not invoke generation")


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


def create_workspace(api: TestClient) -> dict[str, object]:
    return api.post(
        "/api/brand-systems",
        json={"brand_name": "Northstar", "owner_name": "Ryan"},
    ).json()


def create_ready_workspace(api: TestClient) -> dict[str, object]:
    draft = api.post(
        "/api/brand-systems",
        json={
            "brand_name": "Northstar",
            "brand_context": "A complete brand for independent neighborhood bookstores.",
            "owner_name": "Ryan",
        },
    ).json()
    for section in draft["sections"]:
        section["status"] = "reviewed"
        section["blocks"] = [
            {
                "id": f"block.{section['id'].removeprefix('section.')}.guidance",
                "type": "paragraph",
                "text": f"Reviewed and accepted {section['title']} guidance.",
                "references": [],
            }
        ]
        draft = api.patch(
            f"/api/brand-systems/{draft['brand_id']}/sections/{section['id']}",
            json={"expected_revision": draft["revision"], "section": section},
        ).json()
    return draft


def test_publication_requires_exact_revision_approval(tmp_path: Path) -> None:
    with client(tmp_path) as api:
        draft = create_workspace(api)
        response = api.post(
            f"/api/brand-systems/{draft['brand_id']}/versions",
            json={
                "expected_revision": 1,
                "version": "1.0.0",
                "change_summary": "Initial publication.",
            },
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "Current draft revision is not approved."}


def test_empty_workspace_cannot_be_approved_as_a_complete_brand(tmp_path: Path) -> None:
    with client(tmp_path) as api:
        draft = create_workspace(api)
        response = api.post(
            f"/api/brand-systems/{draft['brand_id']}/approvals",
            json={"expected_revision": 1, "rationale": "Looks complete."},
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "Current draft is not ready for approval."}


def test_approved_draft_publishes_an_immutable_hashed_snapshot(tmp_path: Path) -> None:
    with client(tmp_path) as api:
        draft = create_ready_workspace(api)
        approval = api.post(
            f"/api/brand-systems/{draft['brand_id']}/approvals",
            json={
                "expected_revision": draft["revision"],
                "rationale": "Ready for local use.",
            },
        )
        published = api.post(
            f"/api/brand-systems/{draft['brand_id']}/versions",
            json={
                "expected_revision": draft["revision"],
                "version": "1.0.0",
                "change_summary": "Initial publication.",
            },
        )
        detail = api.get(f"/api/brand-systems/{draft['brand_id']}/versions/1.0.0")
        compliance_rules = api.get(
            f"/api/brand-systems/{draft['brand_id']}/versions/1.0.0/compliance-rules"
        )
        duplicate = api.post(
            f"/api/brand-systems/{draft['brand_id']}/versions",
            json={
                "expected_revision": draft["revision"],
                "version": "1.0.0",
                "change_summary": "Overwrite attempt.",
            },
        )

    assert approval.status_code == 201
    assert approval.json()["draft_revision"] == draft["revision"]
    assert published.status_code == 201
    payload = published.json()
    assert payload["version"] == "1.0.0"
    assert payload["draft_revision"] == draft["revision"]
    assert len(payload["content_hash"]) == 64
    assert payload["manifest"]["section_ids"][0] == "section.strategy"
    assert payload["approvals"][0]["rationale"] == "Ready for local use."
    assert detail.json() == payload
    assert compliance_rules.status_code == 200
    assert compliance_rules.json() == []
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "Published version already exists."}


def test_edit_after_approval_invalidates_publication_authority(tmp_path: Path) -> None:
    with client(tmp_path) as api:
        draft = create_ready_workspace(api)
        api.post(
            f"/api/brand-systems/{draft['brand_id']}/approvals",
            json={"expected_revision": draft["revision"], "rationale": "Looks good."},
        )
        section = draft["sections"][0]
        section["status"] = "draft"
        updated = api.patch(
            f"/api/brand-systems/{draft['brand_id']}/sections/{section['id']}",
            json={"expected_revision": draft["revision"], "section": section},
        ).json()
        publication = api.post(
            f"/api/brand-systems/{draft['brand_id']}/versions",
            json={
                "expected_revision": updated["revision"],
                "version": "1.0.0",
                "change_summary": "Changed after approval.",
            },
        )

    assert publication.status_code == 409
    assert publication.json() == {"detail": "Current draft revision is not approved."}
