"""Transactional SQLite snapshots for local living-brand workspaces."""

import json
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from brand_maker.brand_system.audit import AuditEvent
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
CREATE TABLE IF NOT EXISTS brand_system_audit_events (
    event_id TEXT PRIMARY KEY,
    brand_id TEXT NOT NULL,
    action TEXT NOT NULL,
    from_revision INTEGER,
    to_revision INTEGER NOT NULL,
    changed_fields_json TEXT NOT NULL,
    reason TEXT,
    before_json TEXT,
    after_json TEXT NOT NULL,
    target_event_id TEXT,
    created_at TEXT NOT NULL,
    reversible INTEGER NOT NULL DEFAULT 0,
    undone_at TEXT,
    undone_by_event_id TEXT,
    redo_discarded INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS brand_system_audit_brand_order
ON brand_system_audit_events (brand_id, created_at DESC, event_id DESC);
INSERT INTO brand_system_audit_events (
    event_id, brand_id, action, from_revision, to_revision,
    changed_fields_json, reason, before_json, after_json,
    target_event_id, created_at, reversible
)
SELECT
    lower(hex(randomblob(16))), workspace.brand_id, 'workspace.history_started',
    NULL, workspace.revision, '[]', NULL, NULL, workspace.draft_json,
    NULL, workspace.created_at, 0
FROM brand_system_workspaces AS workspace
WHERE NOT EXISTS (
    SELECT 1 FROM brand_system_audit_events AS event
    WHERE event.brand_id = workspace.brand_id
);
"""


class BrandSystemRepositoryError(RuntimeError):
    """Base class for safe workspace-persistence failures."""


class WorkspaceAlreadyExists(BrandSystemRepositoryError):
    """A workspace already uses the requested durable identity."""


class StaleDraftRevision(BrandSystemRepositoryError):
    """The expected draft revision no longer matches stored state."""


class NothingToUndo(BrandSystemRepositoryError):
    """No applied reversible mutation remains in this workspace."""


class NothingToRedo(BrandSystemRepositoryError):
    """No undid mutation remains on the current history branch."""


def _changed_fields(before: WorkingDraft, after: WorkingDraft) -> list[str]:
    previous = before.model_dump(mode="json")
    current = after.model_dump(mode="json")
    previous.pop("revision", None)
    current.pop("revision", None)
    return sorted(key for key in previous | current if previous.get(key) != current.get(key))


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
        event_id = uuid4()
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
                connection.execute(
                    """
                    INSERT INTO brand_system_audit_events (
                        event_id, brand_id, action, from_revision, to_revision,
                        changed_fields_json, reason, before_json, after_json,
                        target_event_id, created_at, reversible
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(event_id),
                        str(draft.brand_id),
                        "workspace.created",
                        None,
                        draft.revision,
                        "[]",
                        None,
                        None,
                        draft.model_dump_json(),
                        None,
                        now,
                        0,
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

    def update(
        self,
        draft: WorkingDraft,
        *,
        expected_revision: int,
        action: str = "workspace.updated",
        reason: str | None = None,
    ) -> WorkingDraft:
        if expected_revision < 1 or draft.revision != expected_revision + 1:
            raise ValueError("updated draft revision must follow expected revision")
        if not action or len(action) > 100:
            raise ValueError("audit action must be between 1 and 100 characters")
        if reason is not None and not 1 <= len(reason) <= 500:
            raise ValueError("audit reason must be between 1 and 500 characters")
        now = self._clock().isoformat()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT draft_json FROM brand_system_workspaces WHERE brand_id = ?",
                (str(draft.brand_id),),
            ).fetchone()
            if row is None:
                raise StaleDraftRevision("draft revision conflict")
            before = WorkingDraft.model_validate_json(row[0])
            cursor = connection.execute(
                """
                UPDATE brand_system_workspaces
                SET updated_at = ?, schema_version = ?, revision = ?, owner_id = ?,
                    brand_name = ?, status = ?, draft_json = ?
                WHERE brand_id = ? AND revision = ?
                """,
                (
                    now,
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
            connection.execute(
                """
                UPDATE brand_system_audit_events
                SET redo_discarded = 1
                WHERE brand_id = ? AND undone_at IS NOT NULL
                """,
                (str(draft.brand_id),),
            )
            connection.execute(
                """
                INSERT INTO brand_system_audit_events (
                    event_id, brand_id, action, from_revision, to_revision,
                    changed_fields_json, reason, before_json, after_json,
                    target_event_id, created_at, reversible
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    str(draft.brand_id),
                    action,
                    before.revision,
                    draft.revision,
                    json.dumps(_changed_fields(before, draft)),
                    reason,
                    before.model_dump_json(),
                    draft.model_dump_json(),
                    None,
                    now,
                    1,
                ),
            )
        return draft

    def list_audit(
        self, brand_id: UUID, *, page: int, page_size: int
    ) -> tuple[list[AuditEvent], int]:
        """Return newest-first mutation metadata without exposing stored snapshots."""

        if page < 1 or not 1 <= page_size <= 100:
            raise ValueError("page must be positive and page_size must be between 1 and 100")
        offset = (page - 1) * page_size
        with self._connect() as connection:
            total = int(
                connection.execute(
                    "SELECT COUNT(*) FROM brand_system_audit_events WHERE brand_id = ?",
                    (str(brand_id),),
                ).fetchone()[0]
            )
            rows = connection.execute(
                """
                SELECT event_id, brand_id, action, from_revision, to_revision,
                       changed_fields_json, reason, target_event_id, created_at,
                       undone_at, redo_discarded
                FROM brand_system_audit_events
                WHERE brand_id = ?
                ORDER BY rowid DESC
                LIMIT ? OFFSET ?
                """,
                (str(brand_id), page_size, offset),
            ).fetchall()
        return [
            AuditEvent(
                event_id=UUID(row[0]),
                brand_id=UUID(row[1]),
                action=row[2],
                from_revision=row[3],
                to_revision=row[4],
                changed_fields=json.loads(row[5]),
                reason=row[6],
                target_event_id=UUID(row[7]) if row[7] is not None else None,
                created_at=row[8],
                undone_at=row[9],
                redo_discarded=bool(row[10]),
            )
            for row in rows
        ], total

    def undo(self, brand_id: UUID, *, expected_revision: int) -> WorkingDraft:
        """Restore the snapshot before the latest applied reversible mutation."""

        return self._move_history(brand_id, expected_revision=expected_revision, redo=False)

    def redo(self, brand_id: UUID, *, expected_revision: int) -> WorkingDraft:
        """Replay the latest undone mutation when no new edit forked history."""

        return self._move_history(brand_id, expected_revision=expected_revision, redo=True)

    def _move_history(
        self, brand_id: UUID, *, expected_revision: int, redo: bool
    ) -> WorkingDraft:
        if expected_revision < 1:
            raise ValueError("expected revision must be positive")
        now = self._clock().isoformat()
        with self._connect() as connection:
            current_row = connection.execute(
                "SELECT draft_json FROM brand_system_workspaces WHERE brand_id = ?",
                (str(brand_id),),
            ).fetchone()
            if current_row is None:
                raise StaleDraftRevision("draft revision conflict")
            current = WorkingDraft.model_validate_json(current_row[0])
            if current.revision != expected_revision:
                raise StaleDraftRevision("draft revision conflict")

            if redo:
                event_row = connection.execute(
                    """
                    SELECT original.event_id, original.after_json
                    FROM brand_system_audit_events AS original
                    JOIN brand_system_audit_events AS undo_event
                      ON undo_event.event_id = original.undone_by_event_id
                    WHERE original.brand_id = ? AND original.undone_at IS NOT NULL
                      AND original.redo_discarded = 0
                    ORDER BY undo_event.rowid DESC
                    LIMIT 1
                    """,
                    (str(brand_id),),
                ).fetchone()
                if event_row is None:
                    raise NothingToRedo("nothing to redo")
                action = "workspace.redone"
                snapshot_json = event_row[1]
            else:
                event_row = connection.execute(
                    """
                    SELECT event_id, before_json
                    FROM brand_system_audit_events
                    WHERE brand_id = ? AND reversible = 1 AND undone_at IS NULL
                    ORDER BY rowid DESC
                    LIMIT 1
                    """,
                    (str(brand_id),),
                ).fetchone()
                if event_row is None:
                    raise NothingToUndo("nothing to undo")
                action = "workspace.undone"
                snapshot_json = event_row[1]

            restored_payload = WorkingDraft.model_validate_json(snapshot_json).model_dump(
                mode="json"
            )
            restored_payload["revision"] = current.revision + 1
            restored = WorkingDraft.model_validate(restored_payload)
            event_id = uuid4()
            cursor = connection.execute(
                """
                UPDATE brand_system_workspaces
                SET updated_at = ?, schema_version = ?, revision = ?, owner_id = ?,
                    brand_name = ?, status = ?, draft_json = ?
                WHERE brand_id = ? AND revision = ?
                """,
                (
                    now,
                    restored.schema_version,
                    restored.revision,
                    restored.owner.id,
                    restored.brand_name,
                    restored.status,
                    restored.model_dump_json(),
                    str(brand_id),
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise StaleDraftRevision("draft revision conflict")
            connection.execute(
                """
                INSERT INTO brand_system_audit_events (
                    event_id, brand_id, action, from_revision, to_revision,
                    changed_fields_json, reason, before_json, after_json,
                    target_event_id, created_at, reversible
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event_id),
                    str(brand_id),
                    action,
                    current.revision,
                    restored.revision,
                    json.dumps(_changed_fields(current, restored)),
                    None,
                    current.model_dump_json(),
                    restored.model_dump_json(),
                    event_row[0],
                    now,
                    0,
                ),
            )
            if redo:
                connection.execute(
                    """
                    UPDATE brand_system_audit_events
                    SET undone_at = NULL, undone_by_event_id = NULL
                    WHERE event_id = ?
                    """,
                    (event_row[0],),
                )
            else:
                connection.execute(
                    """
                    UPDATE brand_system_audit_events
                    SET undone_at = ?, undone_by_event_id = ?
                    WHERE event_id = ?
                    """,
                    (now, str(event_id), event_row[0]),
                )
        return restored

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
