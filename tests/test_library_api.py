from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

from brand_maker.app import create_app
from brand_maker.config import Settings
from brand_maker.models import BrandKit, BrandResponse
from brand_maker.storage import SQLiteBrandRepository


class FakePipeline:
    def __init__(self, response: BrandResponse) -> None:
        self.response = response
        self.calls: list[str] = []
        self.contexts: list[str | None] = []

    async def build(self, brand_name: str, *, brand_context: str | None = None) -> BrandResponse:
        self.calls.append(brand_name)
        self.contexts.append(brand_context)
        return self.response


def brand_kit(name: str = "Floogle") -> BrandKit:
    return BrandKit.model_validate(
        {
            "brand_name": name,
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


def test_create_brand_saves_success_and_exposes_full_detail(tmp_path: Path) -> None:
    pipeline = FakePipeline(BrandResponse(status="ok", kit=brand_kit()))
    path = tmp_path / "brands.db"
    store = SQLiteBrandRepository(path)
    settings = Settings(_env_file=None, openrouter_api_key="test-key", database_path=path)

    with TestClient(create_app(settings=settings, pipeline=pipeline, repository=store)) as client:
        created = client.post("/api/brands", json={"brand_name": "Floogle"})
        brand_id = created.json()["id"]
        workspace_id = created.json()["workspace_id"]
        detail = client.get(f"/api/brands/{brand_id}")
        workspace = client.get(f"/api/brand-systems/{workspace_id}")
        reopened = client.post(
            "/api/brand-systems",
            json={"owner_name": "Ryan", "source_brand_id": brand_id},
        )

    assert created.status_code == 200
    assert created.json()["status"] == "ok"
    assert UUID(brand_id)
    assert created.json()["kit"]["brand_name"] == "Floogle"
    assert UUID(workspace_id)
    assert workspace.status_code == 200
    assert workspace.json()["source_brand_id"] == brand_id
    assert workspace.json()["maturity"] == "concept"
    assert workspace.json()["brief"]["entry_path"] == "quick_start"
    assert reopened.status_code == 201
    assert reopened.json()["brand_id"] == workspace_id
    assert detail.status_code == 200
    assert detail.json()["id"] == brand_id
    assert detail.json()["kit"]["tagline"] == "Search less. Guess more."
    # The kit page needs this to link back into the workspace instead of offering to build one.
    assert detail.json()["workspace_id"] == workspace_id
    assert pipeline.calls == ["Floogle"]
    assert pipeline.contexts == [None]


def test_quick_start_context_reaches_generation_and_the_workspace(tmp_path: Path) -> None:
    # Pasted context is worth little if it only shapes the one-shot kit: it has to land on
    # the workspace, which is what every later section generation replays.
    pipeline = FakePipeline(BrandResponse(status="ok", kit=brand_kit()))
    path = tmp_path / "brands.db"
    store = SQLiteBrandRepository(path)
    settings = Settings(_env_file=None, openrouter_api_key="test-key", database_path=path)
    notes = "We sell refurbished lab equipment to university biology departments."

    with TestClient(create_app(settings=settings, pipeline=pipeline, repository=store)) as client:
        created = client.post("/api/brands", json={"brand_name": "Floogle", "brand_context": notes})
        workspace = client.get(f"/api/brand-systems/{created.json()['workspace_id']}")
        # A whole pasted brand bible must fit; only past the workspace's own ceiling is it
        # rejected, and rejected before a generation call is spent.
        bible = client.post(
            "/api/brands", json={"brand_name": "Floogle", "brand_context": "x" * 50_000}
        )
        too_long = client.post(
            "/api/brands", json={"brand_name": "Floogle", "brand_context": "x" * 50_001}
        )
        blank = client.post("/api/brands", json={"brand_name": "Floogle", "brand_context": "   "})

    assert created.status_code == 200
    assert workspace.json()["brand_context"] == notes
    assert bible.status_code == 200
    assert too_long.status_code == 422
    # Blank context must not count as supplied, or it displaces the kit description.
    assert blank.status_code == 200
    assert pipeline.contexts == [notes, "x" * 50_000, None]


def test_trashed_quick_start_cannot_be_duplicated_from_its_saved_kit(tmp_path: Path) -> None:
    pipeline = FakePipeline(BrandResponse(status="ok", kit=brand_kit()))
    path = tmp_path / "brands.db"
    settings = Settings(_env_file=None, openrouter_api_key="test-key", database_path=path)

    with TestClient(create_app(settings=settings, pipeline=pipeline)) as client:
        created = client.post("/api/brands", json={"brand_name": "Floogle"}).json()
        client.request(
            "DELETE",
            f"/api/brand-systems/{created['workspace_id']}",
            json={"expected_revision": 1, "reason": "Try a different direction."},
        )
        duplicate = client.post(
            "/api/brand-systems",
            json={"owner_name": "Ryan", "source_brand_id": created["id"]},
        )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "The source workspace is in recoverable trash."


def test_create_brand_does_not_save_terminal_failure(tmp_path: Path) -> None:
    pipeline = FakePipeline(BrandResponse(status="error", message="Model provider unavailable."))
    store = SQLiteBrandRepository(tmp_path / "brands.db")
    settings = Settings(_env_file=None, openrouter_api_key="test-key")

    with TestClient(create_app(settings=settings, pipeline=pipeline, repository=store)) as client:
        created = client.post("/api/brands", json={"brand_name": "Floogle"})
        listing = client.get("/api/brands")

    assert created.json() == {
        "status": "error",
        "id": None,
        "workspace_id": None,
        "created_at": None,
        "kit": None,
        "message": "Model provider unavailable.",
    }
    assert listing.json()["total_items"] == 0


def test_brand_list_is_paginated_newest_first(tmp_path: Path) -> None:
    path = tmp_path / "brands.db"
    first = SQLiteBrandRepository(path, clock=lambda: datetime(2026, 7, 22, tzinfo=UTC)).save(
        brand_kit("First")
    )
    second = SQLiteBrandRepository(path, clock=lambda: datetime(2026, 7, 23, tzinfo=UTC)).save(
        brand_kit("Second")
    )
    store = SQLiteBrandRepository(path)
    settings = Settings(_env_file=None, openrouter_api_key="test-key")
    pipeline = FakePipeline(BrandResponse(status="error", message="unused"))

    with TestClient(create_app(settings=settings, pipeline=pipeline, repository=store)) as client:
        response = client.get("/api/brands?page=1&pageSize=1")
        unbuilt = client.get(f"/api/brands/{first.id}")

    assert unbuilt.json()["workspace_id"] is None
    assert response.status_code == 200
    assert response.json()["page_size"] == 1
    assert response.json()["total_items"] == 2
    assert response.json()["total_pages"] == 2
    assert response.json()["items"][0]["id"] == str(second.id)
    assert response.json()["items"][0]["id"] != str(first.id)


def test_brand_library_validates_pagination_and_unknown_ids(tmp_path: Path) -> None:
    store = SQLiteBrandRepository(tmp_path / "brands.db")
    settings = Settings(_env_file=None, openrouter_api_key="test-key")
    pipeline = FakePipeline(BrandResponse(status="error", message="unused"))

    with TestClient(create_app(settings=settings, pipeline=pipeline, repository=store)) as client:
        invalid_page = client.get("/api/brands?page=0&pageSize=101")
        oversized_page = client.get("/api/brands?page=999999999999999999999999999999&pageSize=12")
        missing = client.get("/api/brands/7b48b1ac-95e3-4fab-bf83-b7009ee2f6c4")

    assert invalid_page.status_code == 422
    assert oversized_page.status_code == 422
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Brand not found."}
