"""SQLite persistence for immutable generated brand kits."""

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from brand_maker.models import BrandKit, BrandSummary, SavedBrand

SCHEMA = """
CREATE TABLE IF NOT EXISTS saved_brands (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    kit_json TEXT NOT NULL
)
"""


class SQLiteBrandRepository:
    """Persist validated kits using parameterized, short-lived connections."""

    def __init__(
        self,
        path: Path,
        *,
        id_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._path = path
        self._id_factory = id_factory
        self._clock = clock or (lambda: datetime.now(UTC))

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path, timeout=5.0)
        # ponytail: connect + schema-check per query; fine for local single-user.
        # If load grows, keep a persistent connection and move to schema-once + PRAGMA WAL.
        try:
            connection.execute(SCHEMA)
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _from_row(row: tuple[str, str, str]) -> SavedBrand:
        brand_id, created_at, kit_json = row
        return SavedBrand(
            id=UUID(brand_id),
            created_at=datetime.fromisoformat(created_at),
            kit=BrandKit.model_validate_json(kit_json),
        )

    def save(self, kit: BrandKit) -> SavedBrand:
        saved = SavedBrand(id=self._id_factory(), created_at=self._clock(), kit=kit)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO saved_brands (id, created_at, kit_json) VALUES (?, ?, ?)",
                (str(saved.id), saved.created_at.isoformat(), kit.model_dump_json()),
            )
        return saved

    def get(self, brand_id: UUID) -> SavedBrand | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, created_at, kit_json FROM saved_brands WHERE id = ?",
                (str(brand_id),),
            ).fetchone()
        return self._from_row(row) if row is not None else None

    def list(self, *, page: int, page_size: int) -> tuple[list[BrandSummary], int]:
        offset = (page - 1) * page_size
        with self._connect() as connection:
            total = int(connection.execute("SELECT COUNT(*) FROM saved_brands").fetchone()[0])
            rows = connection.execute(
                """
                SELECT id, created_at, kit_json
                FROM saved_brands
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (page_size, offset),
            ).fetchall()
        return [BrandSummary.from_saved(self._from_row(row)) for row in rows], total
