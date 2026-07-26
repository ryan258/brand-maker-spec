"""Append-only clerical amendments and historical reconstruction."""

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from brand_maker.brand_system.models import (
    AmendmentRequest,
    PublicationAmendment,
    PublishedVersion,
    RenderedPublishedVersion,
    WorkingDraft,
)
from brand_maker.brand_system.publication import SQLitePublicationRepository
from brand_maker.sqlite import connect_database, initialize_database

SCHEMA = """
CREATE TABLE IF NOT EXISTS publication_amendments (
    id TEXT PRIMARY KEY, brand_id TEXT NOT NULL, version TEXT NOT NULL,
    amendment_revision INTEGER NOT NULL, target_id TEXT NOT NULL, field TEXT NOT NULL,
    category TEXT NOT NULL, before_value TEXT NOT NULL, after_value TEXT NOT NULL,
    rationale TEXT NOT NULL, owner_id TEXT NOT NULL, approved_at TEXT NOT NULL,
    UNIQUE (brand_id, version, amendment_revision)
)
"""


class AmendmentTargetNotClerical(ValueError):
    pass


class StaleAmendmentValue(RuntimeError):
    pass


class AmendmentRevisionNotFound(LookupError):
    pass


class SQLiteAmendmentRepository:
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
        initialize_database(path, SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = connect_database(self._path)
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _from_row(row: tuple[object, ...]) -> PublicationAmendment:
        return PublicationAmendment.model_validate(
            {
                "id": str(row[0]),
                "brand_id": str(row[1]),
                "version": str(row[2]),
                "amendment_revision": int(str(row[3])),
                "target_id": str(row[4]),
                "field": str(row[5]),
                "category": str(row[6]),
                "before": str(row[7]),
                "after": str(row[8]),
                "rationale": str(row[9]),
                "owner_id": str(row[10]),
                "approved_at": datetime.fromisoformat(str(row[11])),
            }
        )

    def _list(self, brand_id: UUID, version: str) -> list[PublicationAmendment]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT id, brand_id, version, amendment_revision, target_id, field,
                          category, before_value, after_value, rationale, owner_id, approved_at
                   FROM publication_amendments WHERE brand_id = ? AND version = ?
                   ORDER BY amendment_revision""",
                (str(brand_id), version),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    @staticmethod
    def _render(
        base: PublishedVersion, amendments: list[PublicationAmendment]
    ) -> tuple[WorkingDraft, str]:
        payload = base.snapshot.model_dump(mode="json")
        summary = base.change_summary
        for amendment in amendments:
            if amendment.field == "change_summary":
                summary = amendment.after
                continue
            found = False
            for section in payload["sections"]:
                for block in section["blocks"]:
                    if block["id"] == amendment.target_id:
                        block["text"] = amendment.after
                        found = True
            if not found:
                raise AmendmentTargetNotClerical
        return WorkingDraft.model_validate(payload), summary

    def append(
        self, brand_id: UUID, version: str, request: AmendmentRequest
    ) -> PublicationAmendment:
        base = SQLitePublicationRepository(self._path).get(brand_id, version)
        if base is None:
            raise AmendmentRevisionNotFound
        existing = self._list(brand_id, version)
        rendered, summary = self._render(base, existing)
        if request.field == "change_summary":
            if request.target_id != "publication.metadata":
                raise AmendmentTargetNotClerical
            current = summary
        else:
            if request.category == "metadata":
                raise AmendmentTargetNotClerical
            matches = [
                block.text
                for section in rendered.sections
                for block in section.blocks
                if block.id == request.target_id
            ]
            if len(matches) != 1:
                raise AmendmentTargetNotClerical
            current = matches[0]
        if current != request.before:
            raise StaleAmendmentValue
        amendment = PublicationAmendment(
            id=self._id_factory(),
            brand_id=brand_id,
            version=version,
            amendment_revision=len(existing) + 1,
            target_id=request.target_id,
            field=request.field,
            category=request.category,
            before=request.before,
            after=request.after,
            rationale=request.rationale,
            owner_id=base.publisher_id,
            approved_at=self._clock(),
        )
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO publication_amendments "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(amendment.id),
                        str(brand_id),
                        version,
                        amendment.amendment_revision,
                        amendment.target_id,
                        amendment.field,
                        amendment.category,
                        amendment.before,
                        amendment.after,
                        amendment.rationale,
                        amendment.owner_id,
                        amendment.approved_at.isoformat(),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise StaleAmendmentValue from exc
        return amendment

    def reconstruct(self, brand_id: UUID, version: str, revision: int) -> RenderedPublishedVersion:
        base = SQLitePublicationRepository(self._path).get(brand_id, version)
        if base is None:
            raise AmendmentRevisionNotFound
        amendments = self._list(brand_id, version)
        if revision < 0 or revision > len(amendments):
            raise AmendmentRevisionNotFound
        selected = amendments[:revision]
        snapshot, summary = self._render(base, selected)
        return RenderedPublishedVersion(
            brand_id=brand_id,
            version=version,
            amendment_revision=revision,
            rendered_change_summary=summary,
            rendered_snapshot=snapshot,
            amendments=selected,
        )
