"""Transactional SQLite snapshots for local living-brand workspaces."""

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from brand_maker.brand_system.models import WorkingDraft, WorkspaceSummary

SCHEMA = """
CREATE TABLE IF NOT EXISTS brand_system_workspaces (
    brand_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    owner_id TEXT NOT NULL,
    brand_name TEXT NOT NULL,
    status TEXT NOT NULL,
    draft_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS brand_system_workspaces_updated
ON brand_system_workspaces (updated_at DESC, brand_id DESC);
CREATE INDEX IF NOT EXISTS brand_system_workspaces_source_brand
ON brand_system_workspaces (json_extract(draft_json, '$.source_brand_id'))
WHERE json_extract(draft_json, '$.source_brand_id') IS NOT NULL;
"""


class BrandSystemRepositoryError(RuntimeError):
    """Base class for safe workspace-persistence failures."""


class WorkspaceAlreadyExists(BrandSystemRepositoryError):
    """A workspace already uses the requested durable identity."""


class StaleDraftRevision(BrandSystemRepositoryError):
    """The expected draft revision no longer matches stored state."""


class SQLiteBrandSystemRepository:
    """Persist validated drafts with atomic optimistic updates."""

    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._path = path
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def path(self) -> Path:
        return self._path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path, timeout=5.0)
        # ponytail: connect + schema-check per query; fine for local single-user.
        # If load grows, keep a persistent connection and move to schema-once + PRAGMA WAL.
        try:
            connection.executescript(SCHEMA)
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def create(self, draft: WorkingDraft) -> WorkingDraft:
        now = self._clock().isoformat()
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO brand_system_workspaces (
                        brand_id, created_at, updated_at, schema_version, revision,
                        owner_id, brand_name, status, draft_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(draft.brand_id),
                        now,
                        now,
                        draft.schema_version,
                        draft.revision,
                        draft.owner.id,
                        draft.brand_name,
                        draft.status,
                        draft.model_dump_json(),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise WorkspaceAlreadyExists("brand system already exists") from exc
        return draft

    def get(self, brand_id: UUID) -> WorkingDraft | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT draft_json FROM brand_system_workspaces WHERE brand_id = ?",
                (str(brand_id),),
            ).fetchone()
        return WorkingDraft.model_validate_json(row[0]) if row is not None else None

    def get_by_source_brand_id(self, source_brand_id: UUID) -> WorkingDraft | None:
        """Return the canonical workspace previously created from a saved kit."""

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT draft_json
                FROM brand_system_workspaces
                WHERE json_extract(draft_json, '$.source_brand_id') = ?
                ORDER BY created_at ASC, brand_id ASC
                LIMIT 1
                """,
                (str(source_brand_id),),
            ).fetchone()
        return WorkingDraft.model_validate_json(row[0]) if row is not None else None

    def update(self, draft: WorkingDraft, *, expected_revision: int) -> WorkingDraft:
        if expected_revision < 1 or draft.revision != expected_revision + 1:
            raise ValueError("updated draft revision must follow expected revision")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE brand_system_workspaces
                SET updated_at = ?, schema_version = ?, revision = ?, owner_id = ?,
                    brand_name = ?, status = ?, draft_json = ?
                WHERE brand_id = ? AND revision = ?
                """,
                (
                    self._clock().isoformat(),
                    draft.schema_version,
                    draft.revision,
                    draft.owner.id,
                    draft.brand_name,
                    draft.status,
                    draft.model_dump_json(),
                    str(draft.brand_id),
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise StaleDraftRevision("draft revision conflict")
        return draft

    def list(self, *, page: int, page_size: int) -> tuple[list[WorkspaceSummary], int]:
        if page < 1 or not 1 <= page_size <= 100:
            raise ValueError("page must be positive and page_size must be between 1 and 100")
        offset = (page - 1) * page_size
        with self._connect() as connection:
            total = int(
                connection.execute("SELECT COUNT(*) FROM brand_system_workspaces").fetchone()[0]
            )
            rows = connection.execute(
                """
                SELECT draft_json
                FROM brand_system_workspaces
                ORDER BY updated_at DESC, brand_id DESC
                LIMIT ? OFFSET ?
                """,
                (page_size, offset),
            ).fetchall()
        return [
            WorkspaceSummary.from_draft(WorkingDraft.model_validate_json(row[0])) for row in rows
        ], total
