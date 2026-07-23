from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from brand_maker.brand_system.models import LocalOwner, WorkingDraft
from brand_maker.brand_system.repository import (
    SQLiteBrandSystemRepository,
    StaleDraftRevision,
)
from brand_maker.models import BrandKit
from brand_maker.storage import SQLiteBrandRepository


def draft(brand_id: str, name: str, revision: int = 1) -> WorkingDraft:
    return WorkingDraft(
        brand_id=UUID(brand_id),
        brand_name=name,
        owner=LocalOwner(display_name="Ryan"),
        revision=revision,
        sections=[],
    )


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


def test_repository_creates_and_reads_a_validated_snapshot(tmp_path: Path) -> None:
    store = SQLiteBrandSystemRepository(
        tmp_path / "nested" / "brands.db",
        clock=lambda: datetime(2026, 7, 23, 12, 0, tzinfo=UTC),
    )
    original = draft("d795ebf9-8f54-44a2-85cd-e73faacb7008", "Northstar")

    store.create(original)

    assert store.get(original.brand_id) == original
    assert SQLiteBrandSystemRepository(store.path).get(original.brand_id) == original


def test_expected_revision_update_is_atomic_and_rejects_stale_writes(
    tmp_path: Path,
) -> None:
    store = SQLiteBrandSystemRepository(tmp_path / "brands.db")
    original = draft("d795ebf9-8f54-44a2-85cd-e73faacb7008", "Northstar")
    store.create(original)
    updated = original.model_copy(update={"brand_name": "Northstar Studio", "revision": 2})

    assert store.update(updated, expected_revision=1) == updated

    stale = original.model_copy(update={"brand_name": "Stale edit", "revision": 2})
    with pytest.raises(StaleDraftRevision):
        store.update(stale, expected_revision=1)

    assert store.get(original.brand_id) == updated


def test_repository_lists_recently_updated_workspaces_with_bounded_pages(
    tmp_path: Path,
) -> None:
    moments = iter(
        [
            datetime(2026, 7, 22, 12, 0, tzinfo=UTC),
            datetime(2026, 7, 23, 12, 0, tzinfo=UTC),
        ]
    )
    store = SQLiteBrandSystemRepository(tmp_path / "brands.db", clock=lambda: next(moments))
    older = draft("d795ebf9-8f54-44a2-85cd-e73faacb7008", "Older")
    newer = draft("96f4592c-f119-4dcc-b103-72ca3e145aa1", "Newer")
    store.create(older)
    store.create(newer)

    first_page, total = store.list(page=1, page_size=1)
    second_page, _ = store.list(page=2, page_size=1)

    assert total == 2
    assert [item.brand_id for item in first_page] == [newer.brand_id]
    assert [item.brand_id for item in second_page] == [older.brand_id]


def test_living_brand_tables_do_not_modify_legacy_saved_brands(tmp_path: Path) -> None:
    path = tmp_path / "brands.db"
    saved = SQLiteBrandRepository(path).save(legacy_kit())
    workspace = draft("d795ebf9-8f54-44a2-85cd-e73faacb7008", "Northstar")

    SQLiteBrandSystemRepository(path).create(workspace)

    assert SQLiteBrandRepository(path).get(saved.id) == saved
