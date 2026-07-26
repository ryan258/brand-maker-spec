import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from brand_maker.brand_system.models import LocalOwner, WorkingDraft
from brand_maker.brand_system.repository import (
    NothingToRedo,
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


def test_repository_initializes_sqlite_for_concurrent_local_tabs(tmp_path: Path) -> None:
    path = tmp_path / "brands.db"
    SQLiteBrandSystemRepository(path)

    with sqlite3.connect(path) as connection:
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]

    assert journal_mode == "wal"


def test_existing_workspace_receives_a_non_reversible_history_baseline(tmp_path: Path) -> None:
    path = tmp_path / "brands.db"
    original = draft("d795ebf9-8f54-44a2-85cd-e73faacb7008", "Northstar")
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE brand_system_workspaces (
                brand_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                schema_version TEXT NOT NULL, revision INTEGER NOT NULL, owner_id TEXT NOT NULL,
                brand_name TEXT NOT NULL, status TEXT NOT NULL, draft_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO brand_system_workspaces VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(original.brand_id),
                "2026-07-23T12:00:00+00:00",
                "2026-07-23T12:00:00+00:00",
                original.schema_version,
                original.revision,
                original.owner.id,
                original.brand_name,
                original.status,
                original.model_dump_json(),
            ),
        )

    store = SQLiteBrandSystemRepository(path)
    history, total = store.list_audit(original.brand_id, page=1, page_size=10)

    assert total == 1
    assert history[0].action == "workspace.history_started"
    assert history[0].to_revision == 1


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


def test_audit_history_supports_revision_safe_undo_and_redo(tmp_path: Path) -> None:
    store = SQLiteBrandSystemRepository(tmp_path / "brands.db")
    original = draft("d795ebf9-8f54-44a2-85cd-e73faacb7008", "Northstar")
    store.create(original)
    updated = original.model_copy(update={"brand_name": "Northstar Studio", "revision": 2})
    store.update(
        updated,
        expected_revision=1,
        action="workspace.renamed",
        reason="Clarify the studio positioning.",
    )

    history, total = store.list_audit(original.brand_id, page=1, page_size=10)
    assert total == 2
    assert history[0].action == "workspace.renamed"
    assert history[0].changed_fields == ["brand_name"]
    assert history[0].reason == "Clarify the studio positioning."

    undone = store.undo(original.brand_id, expected_revision=2)
    assert undone.brand_name == "Northstar"
    assert undone.revision == 3

    redone = store.redo(original.brand_id, expected_revision=3)
    assert redone.brand_name == "Northstar Studio"
    assert redone.revision == 4

    events = store.list_audit(original.brand_id, page=1, page_size=10)[0]
    actions = [event.action for event in events]
    assert actions[:2] == ["workspace.redone", "workspace.undone"]


def test_new_edit_after_undo_discards_redo_branch(tmp_path: Path) -> None:
    store = SQLiteBrandSystemRepository(tmp_path / "brands.db")
    original = draft("d795ebf9-8f54-44a2-85cd-e73faacb7008", "Northstar")
    store.create(original)
    store.update(
        original.model_copy(update={"brand_name": "First edit", "revision": 2}),
        expected_revision=1,
    )
    undone = store.undo(original.brand_id, expected_revision=2)
    store.update(
        undone.model_copy(update={"brand_name": "New direction", "revision": 4}),
        expected_revision=3,
    )

    with pytest.raises(NothingToRedo):
        store.redo(original.brand_id, expected_revision=4)


def test_undo_rejects_a_stale_revision_without_changing_the_workspace(tmp_path: Path) -> None:
    store = SQLiteBrandSystemRepository(tmp_path / "brands.db")
    original = draft("d795ebf9-8f54-44a2-85cd-e73faacb7008", "Northstar")
    store.create(original)
    updated = original.model_copy(update={"brand_name": "Current", "revision": 2})
    store.update(updated, expected_revision=1)

    with pytest.raises(StaleDraftRevision):
        store.undo(original.brand_id, expected_revision=1)

    assert store.get(original.brand_id) == updated


def test_soft_delete_hides_workspace_and_restore_recovers_it(tmp_path: Path) -> None:
    store = SQLiteBrandSystemRepository(tmp_path / "brands.db")
    original = draft("d795ebf9-8f54-44a2-85cd-e73faacb7008", "Northstar")
    store.create(original)

    trashed = store.soft_delete(
        original.brand_id,
        expected_revision=1,
        reason="Pause this direction without losing the work.",
    )

    assert trashed.brand_id == original.brand_id
    assert trashed.reason == "Pause this direction without losing the work."
    assert store.get(original.brand_id) is None
    assert store.list(page=1, page_size=10)[1] == 0
    assert store.list_trash(page=1, page_size=10)[1] == 1

    restored = store.restore_from_trash(original.brand_id, expected_revision=1)
    assert restored == original
    assert store.get(original.brand_id) == original
    assert store.list_trash(page=1, page_size=10)[1] == 0
    events = store.list_audit(original.brand_id, page=1, page_size=10)[0]
    actions = [event.action for event in events]
    assert actions[:2] == ["workspace.restored", "workspace.trashed"]


def test_soft_delete_and_restore_reject_stale_revisions(tmp_path: Path) -> None:
    store = SQLiteBrandSystemRepository(tmp_path / "brands.db")
    original = draft("d795ebf9-8f54-44a2-85cd-e73faacb7008", "Northstar")
    store.create(original)

    with pytest.raises(StaleDraftRevision):
        store.soft_delete(original.brand_id, expected_revision=2, reason=None)

    store.soft_delete(original.brand_id, expected_revision=1, reason=None)
    with pytest.raises(StaleDraftRevision):
        store.restore_from_trash(original.brand_id, expected_revision=2)


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
