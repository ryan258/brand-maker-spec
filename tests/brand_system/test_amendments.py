from pathlib import Path

from fastapi.testclient import TestClient

from brand_maker.app import create_app
from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
from brand_maker.config import Settings
from brand_maker.models import BrandResponse
from brand_maker.storage import SQLiteBrandRepository


class UnusedPipeline:
    async def build(self, brand_name: str) -> BrandResponse:
        raise AssertionError("amendments must not invoke generation")


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


def published(api: TestClient) -> tuple[str, dict[str, object]]:
    draft = api.post(
        "/api/brand-systems",
        json={
            "brand_name": "Northstar",
            "brand_context": "A complete brand for independent neighborhood bookstores.",
            "owner_name": "Ryan",
        },
    ).json()
    for section in draft["sections"]:
        slug = section["id"].removeprefix("section.")
        section["status"] = "reviewed"
        section["blocks"] = [
            {
                "id": "block.strategy.purpose" if slug == "strategy" else f"block.{slug}.guidance",
                "type": "paragraph",
                "text": (
                    "A clear strategic purpos."
                    if slug == "strategy"
                    else f"Reviewed and accepted {section['title']} guidance."
                ),
                "references": [],
            }
        ]
        draft = api.patch(
            f"/api/brand-systems/{draft['brand_id']}/sections/{section['id']}",
            json={"expected_revision": draft["revision"], "section": section},
        ).json()
    api.post(
        f"/api/brand-systems/{draft['brand_id']}/approvals",
        json={"expected_revision": draft["revision"], "rationale": "Ready."},
    )
    version = api.post(
        f"/api/brand-systems/{draft['brand_id']}/versions",
        json={
            "expected_revision": draft["revision"],
            "version": "1.0.0",
            "change_summary": "Initial publcation.",
        },
    ).json()
    return draft["brand_id"], version


def test_clerical_amendment_preserves_base_and_reconstructs_each_revision(
    tmp_path: Path,
) -> None:
    with client(tmp_path) as api:
        brand_id, base = published(api)
        amendment = api.post(
            f"/api/brand-systems/{brand_id}/versions/1.0.0/amendments",
            json={
                "target_id": "block.strategy.purpose",
                "field": "text",
                "category": "spelling",
                "before": "A clear strategic purpos.",
                "after": "A clear strategic purpose.",
                "rationale": "Correct a typo.",
            },
        )
        original = api.get(f"/api/brand-systems/{brand_id}/versions/1.0.0/revisions/0")
        corrected = api.get(f"/api/brand-systems/{brand_id}/versions/1.0.0/revisions/1")
        unchanged_base = api.get(f"/api/brand-systems/{brand_id}/versions/1.0.0")

    assert amendment.status_code == 201
    assert amendment.json()["amendment_revision"] == 1
    original_text = original.json()["rendered_snapshot"]["sections"][0]["blocks"][0]["text"]
    corrected_text = corrected.json()["rendered_snapshot"]["sections"][0]["blocks"][0]["text"]
    assert original_text == "A clear strategic purpos."
    assert corrected_text == "A clear strategic purpose."
    assert unchanged_base.json() == base


def test_semantic_targets_and_stale_before_values_are_rejected(tmp_path: Path) -> None:
    with client(tmp_path) as api:
        brand_id, _ = published(api)
        semantic = api.post(
            f"/api/brand-systems/{brand_id}/versions/1.0.0/amendments",
            json={
                "target_id": "rule.voice.direct",
                "field": "text",
                "category": "spelling",
                "before": "old",
                "after": "new",
                "rationale": "Not clerical.",
            },
        )
        stale = api.post(
            f"/api/brand-systems/{brand_id}/versions/1.0.0/amendments",
            json={
                "target_id": "block.strategy.purpose",
                "field": "text",
                "category": "spelling",
                "before": "Wrong prior value",
                "after": "A clear strategic purpose.",
                "rationale": "Correct a typo.",
            },
        )

    assert semantic.status_code == 422
    assert semantic.json() == {"detail": "Amendment target is not clerical."}
    assert stale.status_code == 409
    assert stale.json() == {"detail": "Amendment before-value is stale."}
