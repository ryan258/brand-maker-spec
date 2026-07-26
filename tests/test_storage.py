import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from brand_maker.models import BrandKit
from brand_maker.storage import SQLiteBrandRepository


def kit(name: str) -> BrandKit:
    return BrandKit.model_validate(
        {
            "brand_name": name,
            "parody_target": f"{name} target",
            "tagline": f"{name} tagline",
            "description": f"A complete description for {name}.",
            "brand_voice": "Clear, playful, and specific.",
            "personality": ["Playful", "Focused", "Useful"],
            "color_palette": {
                "primary": "#112233",
                "secondary": "#445566",
                "accent": "#778899",
                "background": "#FFFFFF",
            },
        }
    )


def repository(path: Path, brand_id: str, created_at: datetime) -> SQLiteBrandRepository:
    return SQLiteBrandRepository(
        path,
        id_factory=lambda: UUID(brand_id),
        clock=lambda: created_at,
    )


def test_repository_saves_and_reads_a_validated_brand(tmp_path: Path) -> None:
    brand_id = "7b48b1ac-95e3-4fab-bf83-b7009ee2f6c4"
    created_at = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    store = repository(tmp_path / "nested" / "brands.db", brand_id, created_at)

    saved = store.save(kit("Floogle"))

    assert saved.id == UUID(brand_id)
    assert saved.created_at == created_at
    assert store.get(saved.id) == saved
    assert SQLiteBrandRepository(tmp_path / "nested" / "brands.db").get(saved.id) == saved


def test_repository_lists_newest_first_with_bounded_pages(tmp_path: Path) -> None:
    path = tmp_path / "brands.db"
    older = repository(
        path,
        "7b48b1ac-95e3-4fab-bf83-b7009ee2f6c4",
        datetime(2026, 7, 22, 12, 0, tzinfo=UTC),
    ).save(kit("Older"))
    newer = repository(
        path,
        "36d35ed2-cfbd-4ef0-b26d-b78884ee15f9",
        datetime(2026, 7, 23, 12, 0, tzinfo=UTC),
    ).save(kit("Newer"))
    store = SQLiteBrandRepository(path)

    first_page, total = store.list(page=1, page_size=1)
    second_page, _ = store.list(page=2, page_size=1)

    assert total == 2
    assert [item.id for item in first_page] == [newer.id]
    assert [item.id for item in second_page] == [older.id]


def test_repository_returns_none_for_unknown_brand(tmp_path: Path) -> None:
    store = SQLiteBrandRepository(tmp_path / "brands.db")

    assert store.get(UUID("7b48b1ac-95e3-4fab-bf83-b7009ee2f6c4")) is None


def test_repository_closes_each_connection_after_use(tmp_path: Path, monkeypatch) -> None:
    connections: list[sqlite3.Connection] = []
    real_connect = sqlite3.connect

    def tracking_connect(*args, **kwargs) -> sqlite3.Connection:
        connection = real_connect(*args, **kwargs)
        connections.append(connection)
        return connection

    monkeypatch.setattr("brand_maker.storage.sqlite3.connect", tracking_connect)
    store = SQLiteBrandRepository(tmp_path / "brands.db")

    assert len(connections) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        connections[0].execute("SELECT 1")

    connections.clear()
    store.get(UUID("7b48b1ac-95e3-4fab-bf83-b7009ee2f6c4"))
    assert len(connections) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        connections[0].execute("SELECT 1")
