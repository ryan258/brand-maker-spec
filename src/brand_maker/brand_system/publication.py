"""Revision-bound approval and immutable transactional publication."""

import hashlib
import json
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from brand_maker.brand_system.models import (
    ApprovalRecord,
    PublicationManifest,
    PublicationRequest,
    PublishedVersion,
    WorkingDraft,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS brand_system_approvals (
    id TEXT PRIMARY KEY, brand_id TEXT NOT NULL, draft_revision INTEGER NOT NULL,
    owner_id TEXT NOT NULL, approved_at TEXT NOT NULL, rationale TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS brand_system_approval_revision
ON brand_system_approvals (brand_id, draft_revision, approved_at DESC);
CREATE TABLE IF NOT EXISTS published_brand_versions (
    brand_id TEXT NOT NULL, version TEXT NOT NULL, published_at TEXT NOT NULL,
    publisher_id TEXT NOT NULL, draft_revision INTEGER NOT NULL,
    change_summary TEXT NOT NULL, content_hash TEXT NOT NULL,
    manifest_json TEXT NOT NULL, approvals_json TEXT NOT NULL, snapshot_json TEXT NOT NULL,
    PRIMARY KEY (brand_id, version)
);
"""


class PublicationConflict(RuntimeError):
    """Base class for safe publication-state conflicts."""


class DraftNotApproved(PublicationConflict):
    pass


class PublishedVersionExists(PublicationConflict):
    pass


class PublicationDraftNotFound(LookupError):
    pass


class SQLitePublicationRepository:
    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        self._path = path
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._path, timeout=5.0)
        try:
            connection.executescript(SCHEMA)
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def approve(self, brand_id: UUID, expected_revision: int, rationale: str) -> ApprovalRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT draft_json, revision FROM brand_system_workspaces WHERE brand_id = ?",
                (str(brand_id),),
            ).fetchone()
            if row is None:
                raise PublicationDraftNotFound
            if int(row[1]) != expected_revision:
                raise DraftNotApproved
            draft = WorkingDraft.model_validate_json(row[0])
            record = ApprovalRecord(
                id=self._id_factory(),
                brand_id=brand_id,
                draft_revision=expected_revision,
                owner_id=draft.owner.id,
                approved_at=self._clock(),
                rationale=rationale,
            )
            connection.execute(
                "INSERT INTO brand_system_approvals VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(record.id),
                    str(brand_id),
                    expected_revision,
                    record.owner_id,
                    record.approved_at.isoformat(),
                    record.rationale,
                ),
            )
        return record

    @staticmethod
    def _approval(row: tuple[object, ...]) -> ApprovalRecord:
        return ApprovalRecord(
            id=UUID(str(row[0])),
            brand_id=UUID(str(row[1])),
            draft_revision=int(str(row[2])),
            owner_id=str(row[3]),
            approved_at=datetime.fromisoformat(str(row[4])),
            rationale=str(row[5]),
        )

    def publish(
        self,
        brand_id: UUID,
        request: PublicationRequest,
        *,
        snapshot: WorkingDraft | None = None,
    ) -> PublishedVersion:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT draft_json, revision FROM brand_system_workspaces WHERE brand_id = ?",
                (str(brand_id),),
            ).fetchone()
            if row is None:
                raise PublicationDraftNotFound
            if int(row[1]) != request.expected_revision:
                raise DraftNotApproved
            approval_rows = connection.execute(
                """SELECT id, brand_id, draft_revision, owner_id, approved_at, rationale
                   FROM brand_system_approvals WHERE brand_id = ? AND draft_revision = ?
                   ORDER BY approved_at, id""",
                (str(brand_id), request.expected_revision),
            ).fetchall()
            if not approval_rows:
                raise DraftNotApproved
            stored_draft = WorkingDraft.model_validate_json(row[0])
            draft = snapshot or stored_draft
            if draft.brand_id != stored_draft.brand_id or draft.revision != stored_draft.revision:
                raise DraftNotApproved
            if any(asset.required and asset.storage != "managed" for asset in draft.assets):
                raise DraftNotApproved
            canonical = json.dumps(
                draft.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
            )
            content_hash = hashlib.sha256(canonical.encode()).hexdigest()
            approvals = [self._approval(item) for item in approval_rows]
            manifest = PublicationManifest(
                schema_version=draft.schema_version,
                draft_revision=draft.revision,
                section_ids=[section.id for section in draft.sections],
            )
            published = PublishedVersion(
                brand_id=brand_id,
                version=request.version,
                published_at=self._clock(),
                publisher_id=draft.owner.id,
                draft_revision=draft.revision,
                change_summary=request.change_summary,
                content_hash=content_hash,
                manifest=manifest,
                approvals=approvals,
                snapshot=draft,
            )
            try:
                connection.execute(
                    "INSERT INTO published_brand_versions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(brand_id),
                        published.version,
                        published.published_at.isoformat(),
                        published.publisher_id,
                        published.draft_revision,
                        published.change_summary,
                        published.content_hash,
                        manifest.model_dump_json(),
                        json.dumps([item.model_dump(mode="json") for item in approvals]),
                        draft.model_dump_json(),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise PublishedVersionExists from exc
        return published

    def get(self, brand_id: UUID, version: str) -> PublishedVersion | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT published_at, publisher_id, draft_revision, change_summary,
                          content_hash, manifest_json, approvals_json, snapshot_json
                   FROM published_brand_versions WHERE brand_id = ? AND version = ?""",
                (str(brand_id), version),
            ).fetchone()
        if row is None:
            return None
        return PublishedVersion(
            brand_id=brand_id,
            version=version,
            published_at=datetime.fromisoformat(row[0]),
            publisher_id=row[1],
            draft_revision=row[2],
            change_summary=row[3],
            content_hash=row[4],
            manifest=PublicationManifest.model_validate_json(row[5]),
            approvals=[ApprovalRecord.model_validate(item) for item in json.loads(row[6])],
            snapshot=WorkingDraft.model_validate_json(row[7]),
        )
